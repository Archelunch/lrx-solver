"""Run pinned GEPA 0.1.4, SkyDiscover AdaEvolve 0.2.0 and a sequential control on Track 3 (Lean).

Mirrors integrations/sort_backends.py and reuses lift_backends.py/official_backends.py
plumbing by import (neither file is edited): rejection notes, broker chat client,
per-arm ledgers and contact sub-caps, reflection minibatch min(3, n), the Seatbelt
launcher and best-program snapshot. The candidate is one Lean body; the verifier
(integrations/lean_evaluator.py) runs in the parent, so Lean sandboxes are never
nested inside the optimizer sandbox. EvoX is excluded (its outer loop writes and
runs generated Python search strategies; AGENTS.md). GEPA gets 11 instances
(L1-L3, M1-M7, M9); one cached Lean run serves every instance of a candidate.
AdaEvolve: cascade off, fixed random_seed, evaluator-context injection off,
one context program, full rewrites, language "lean".

The staged copy of this file runs inside the optimizer sandbox next to staged
copies of lift_backends.py, official_backends.py and lean_task.py, so the module
top level imports only the standard library and those files.
"""
from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from integrations import lean_task as LT
    from integrations import lift_backends as lb
    from integrations import official_backends as ob
except ImportError:  # staged copy inside the optimizer sandbox
    import lean_task as LT
    import lift_backends as lb
    import official_backends as ob

ROOT = Path(__file__).resolve().parents[1]
LEAN_DIR = ROOT / "autoresearch" / "lean-loop-260925"
TASK = "lean-loop-260925"
PACKET_MARK = "LEAN_PACKET_V1"
ENGINES = ("gepa", "adaevolve")
RANDOM_SEED = 260925


def _defs_text() -> str:
    """Locked statement text; the staged worker reads the copy staged next to it."""
    staged = Path(__file__).with_name("Defs.lean")
    return (staged if staged.is_file() else LT.PROJECT / "LrxLean" / "Defs.lean").read_text()


SYSTEM = (
    "You prove theorems in Lean 4 (v4.34.0, core library only: no Mathlib, no Batteries). The locked module "
    "LrxLean.Defs, shown below, defines the LRX model: a vector is a List Nat; L rotates left, R rotates right, "
    "X swaps the first two entries; `exec w v` applies the word w left to right. Prove the target Props "
    "LRX.Stmt.L1, LRX.Stmt.L2, LRX.Stmt.L3; the milestone Props M1..M7 and M9 earn partial credit. Your answer "
    "is one Lean body in a single ```lean block. The evaluator wraps it in a trusted header (import "
    "LrxLean.Defs, maxHeartbeats 400000, open LRX, then the scope Cand) and a trusted footer. State each result "
    "as `theorem L1 : Stmt.L1 := by ...`; the type must be literally Stmt.<id> (begin the proof with "
    "`unfold Stmt.L1` or `intro`). Helper theorems and defs are allowed; write `theorem`, not `lemma`. "
    "Outside comments, these whole words are rejected (so never use them as names either): "
    + ", ".join(LT._WORDS) + "; also unsafe, builtin_, @[init, +native, debug., `open` of Lean/IO/System/Std, "
    "and identifiers starting with Lean., IO., System. or Std. Anywhere, comments included: any # command "
    "(#check, #eval, #print, ...) and a ``` fence inside the body. `sorry` is accepted "
    "but earns nothing. A declaration counts only if the kernel accepts it and it uses no axioms beyond "
    "propext, Classical.choice and Quot.sound. Blocks with errors are removed and the rest is re-checked. "
    "Score: closed targets / 3 + 0.2 x closed milestones / 8 + at most 0.05 for distinct helper theorems about "
    "the LRX definitions used by closed targets or milestones "
    "- 0.01 per error (at most 0.05). Lemma 1 (stretch macros) and Lemma 4 (deleting a zero atom) are the "
    "research group's results; these statements formalise them.\n\nLocked definitions (LrxLean/Defs.lean):\n"
    "```lean\n" + _defs_text() + "```"
)
OBJECTIVE = (
    "Improve this Lean body: close more of the targets L1, L2, L3 (and the milestones) with complete, "
    "sorry-free proofs, keeping every theorem that already closes. Return the entire replacement body in one "
    "```lean block with no prose."
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def preflight_source(content, finish_reason=None) -> str:
    """A model response: the last ```lean block, size cap and lexical ban, before any evaluation."""
    return LT.preflight_body(LT.extract_body(content, finish_reason))


# ------------------------------------------------------ trusted verifier side
class LeanVerifier:
    """Coordinator-side trusted evaluation; Lean runs only in lean_evaluator's sandboxes."""

    def __init__(self, run_dir, *, cache_dir, engine, provenance, max_requests, require_os_sandbox=True):
        from integrations.lean_evaluator import check_toolchain
        from integrations.lean_task import verify_lock

        self.lock_digest, self.toolchain = verify_lock(), check_toolchain()
        self.cache_dir, self.engine, self.provenance = cache_dir, engine, provenance
        self.max_requests, self.require_os_sandbox = max_requests, require_os_sandbox
        self.evidence = Path(run_dir) / "verified" / "evaluations"
        self.evidence.mkdir(parents=True)
        self.lock = threading.Lock()
        self.memo = {}
        self.state = {"requests": 0, "evaluations": [], "distinct_source_hashes": [], "best": None,
                      "failures": 0, "memo_hits": 0}

    def _current_best(self):
        """Best over every evaluation on record (TRACE-AUDIT defect 7), from any scope."""
        best = None
        for row in self.state["evaluations"]:
            if best is None or row["combined_score"] > best["combined_score"]:
                best = {k: row[k] for k in ("combined_score", "closed_targets", "closed_milestones",
                                            "candidate_hash")}
        return best

    @staticmethod
    def _best_text(best) -> str:
        if not best:
            return "none"
        return (f"combined {best['combined_score']:.4f} (targets {best['closed_targets'] or 'none'}, "
                f"milestones {best['closed_milestones'] or 'none'})")

    def evaluate(self, source: str, parent_id=None, *, final=False) -> dict:
        from integrations import lean_evaluator as E

        digest = _sha(source.encode())
        with self.lock:
            if not final and digest in self.memo:
                self.state["memo_hits"] += 1
                out = dict(self.memo[digest])
                out["feedback"] = E.packet(out["_result"], self._best_text(self.state["best"]))
                return {k: v for k, v in out.items() if k != "_result"}
            if self.state["requests"] >= self.max_requests:
                raise PermissionError("evaluation request budget exhausted")
            self.state["requests"] += 1
            ordinal = self.state["requests"]
        (self.evidence / f"candidate-{ordinal:04d}.lean").write_text(source)
        res = E.evaluate(source, cache_dir=None if final else self.cache_dir,
                         require_sandbox=self.require_os_sandbox)
        with self.lock:
            if digest not in self.state["distinct_source_hashes"]:
                self.state["distinct_source_hashes"].append(digest)
            row = {"combined_score": res["combined_score"], "status": res["status"],
                   "closed_targets": res.get("closed_targets", []),
                   "closed_milestones": res.get("closed_milestones", []), "candidate_hash": digest,
                   "ordinal": ordinal, "final": final, "cache_hit": res.get("cache_hit", False)}
            self.state["evaluations"].append(row)
            self.state["best"] = self._current_best()
            feedback = E.packet(res, self._best_text(self.state["best"]))
            summary = {"combined_score": res["combined_score"], "status": res["status"],
                       "reason": res.get("reason"), "statuses": res.get("statuses", {}),
                       "closed_targets": row["closed_targets"], "closed_milestones": row["closed_milestones"],
                       "aux_count": len(res.get("aux", [])), "candidate_hash": digest,
                       "cache_hit": row["cache_hit"], "feedback": feedback,
                       "instance_feedback": {i: E.instance_feedback(res, i) for i in LT.IDS}}
            artifact = self.evidence / f"result-{ordinal:04d}.json"
            artifact.write_text(json.dumps({"summary": summary, "result": res}, default=str) + "\n")
            summary["evaluation"] = str(artifact)
            row["packet_sha256"] = _sha(feedback.encode())
            if not final:
                self.memo[digest] = dict(summary, _result=res)
            return summary

    def serve(self):
        verifier = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != "/evaluate":
                    return self._reply(404, {"error": "not found"})
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 45000:
                    return self._reply(413, {"error": "source request size exceeded"})
                try:
                    source = json.loads(self.rfile.read(length))["source"]
                    if not isinstance(source, str) or len(source.encode()) > 40000:
                        return self._reply(413, {"error": "candidate source size exceeded"})
                    return self._reply(200, verifier.evaluate(source))
                except PermissionError as exc:
                    return self._reply(429, {"error": str(exc)})
                except Exception as exc:
                    with verifier.lock:
                        verifier.state["failures"] += 1
                    return self._reply(500, {"error": f"trusted evaluation failed: {type(exc).__name__}: {exc}"})

            def _reply(self, status, payload):
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server, f"http://127.0.0.1:{server.server_port}/evaluate"


# ------------------------------------------------------------- first-prompt guards
FIRST_PROMPT_FILES = {"gepa": "first-prompt-gepa.sha256", "sequential": "first-prompt-sequential.sha256",
                      "adaevolve": "first-prompt-adaevolve.sha256"}


def is_solution_request(messages) -> bool:
    return bool(messages) and ob._evox_call_kind(messages) == "solution" and "Stmt." in json.dumps(messages)


def verify_first_solution_prompt(ledger_path, expected_sha256):
    """AdaEvolve: compare the first solution request in the arm's own ledger receipts after the run."""
    if not ledger_path or not expected_sha256:
        return None
    receipts = Path(str(ledger_path) + ".receipts")
    if not receipts.is_dir():
        return None
    for path in sorted(receipts.glob("attempt-*.json")):
        try:
            receipt = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        payload = receipt.get("request_payload") or receipt.get("forwarded_request_payload") or {}
        messages = payload.get("messages", [])
        if is_solution_request(messages):
            actual = lb.messages_sha256(messages)
            return actual, actual == expected_sha256
    return None


def write_first_prompt(capture_dir: Path, out_md: Path, run_dir: Path, engine: str) -> str:
    """Render an arm's first captured proposer request verbatim for user approval."""
    role = {"gepa": "gepa_reflection", "sequential": "sequential_refinement"}.get(engine)
    for path in sorted(Path(capture_dir).glob("request-*.json")):
        item = json.loads(path.read_text())
        if (item["role"] == role) if role else (not item["role"] and is_solution_request(item["body"].get("messages"))):
            break
    else:
        raise FileNotFoundError(f"no captured first {engine} proposer request")
    body = item["body"]
    messages = body["messages"]
    digest = lb.messages_sha256(messages)
    fence = "`" * 6
    lines = [f"# First {engine} proposer prompt ({TASK})", "",
             f"Exact `messages` array the {engine} arm sends to the local broker for its first proposal on the "
             "seed (sorry stubs), captured offline through the mock with zero provider calls.", "",
             f"- Messages SHA-256 (canonical JSON): `{digest}`",
             f"- Message roles: {[m['role'] for m in messages]}",
             f"- Client request fields: model `{body.get('model')}`, max_tokens `{body.get('max_tokens')}`, "
             f"reasoning_effort `{body.get('reasoning_effort')}`",
             f"- Captured from: `{Path(run_dir).name}` ({path.name})", ""]
    for i, m in enumerate(messages, 1):
        lines += [f"## Message {i}: {m['role']}", "", fence + "text", m["content"], fence, ""]
    out_md.write_text("\n".join(lines))
    out_md.with_suffix(".sha256").write_text(f"{digest}  messages of {out_md.name}\n")
    return digest


# ------------------------------------------------------------- approval
def approval_material(broker_config: Path, campaign_config: Path) -> dict:
    from integrations.lean_evaluator import CONTRACT, VERSION, evaluator_hash
    from integrations.research_budget import _dry_run_payload

    bc, cc = lb._load_config(broker_config), lb._load_config(campaign_config)

    def _hash_of(name):
        path = broker_config.parent / name
        return path.read_text().split()[0] if path.is_file() else None

    return {"broker_config": bc, "campaign_config": cc,
            **{f"first_prompt_{e}_sha256": _hash_of(f) for e, f in FIRST_PROMPT_FILES.items()},
            "upstream_endpoint": bc["upstream_url"].rstrip("/") + "/chat/completions",
            "dry_run_payload": _dry_run_payload(bc), "system_prompt": SYSTEM, "objective": OBJECTIVE,
            "packet_format": {"marker": PACKET_MARK, "max_chars": 3000},
            "seed_sha256": _sha((ROOT / cc["seed"]).read_bytes()),
            "lean_lock": json.loads(LT.LOCK_PATH.read_text()), "lean_lock_digest": LT.verify_lock(),
            "evaluator": {"version": VERSION, "contract": CONTRACT, "hash": evaluator_hash()},
            "lean_backends_sha256": _sha(Path(__file__).read_bytes()),
            "lift_backends_sha256": _sha(Path(lb.__file__).read_bytes()),
            "official_backends_sha256": _sha(Path(ob.__file__).read_bytes())}


def approval_hash(broker_config: Path, campaign_config: Path) -> str:
    return _sha(lb._canonical(approval_material(broker_config, campaign_config)).encode())


def check_approval(broker_config: Path, campaign_config: Path) -> str:
    computed = approval_hash(broker_config, campaign_config)
    approved = broker_config.parent / "payload-approved.sha256"
    if not approved.is_file():
        raise SystemExit(f"refusing to start: {approved} is missing (created only after user approval)")
    token = approved.read_text().split()
    if not token or token[0] != computed:
        raise SystemExit(f"refusing to start: payload hash {computed} does not match {approved}")
    return computed


# ------------------------------------------------------------ official engines
def _sky_config(args, stage: Path) -> Path:
    path = lb._sky_config(args, stage)
    config = json.loads(path.read_text())
    config["language"] = "lean"
    config["diff_based_generation"] = False
    config["prompt"]["system_message"] = SYSTEM
    config["search"]["num_context_programs"] = 1
    config["search"].setdefault("database", {})["random_seed"] = RANDOM_SEED
    config["evaluator"].update(cascade_evaluation=False, inject_evaluator_context=False)
    path.write_text(json.dumps(config, indent=2) + "\n")
    return path


def _sky_evaluator(stage: Path, verifier_url: str, timeout: int) -> Path:
    ids = list(LT.IDS)
    path = stage / "evaluator.py"
    path.write_text(
        "from pathlib import Path\nimport json\nfrom urllib.request import Request, urlopen\n"
        "from skydiscover.optimize.evaluation.evaluation_result import EvaluationResult\n"
        "def evaluate(program_path):\n"
        "    source = Path(program_path).read_text(encoding='utf-8')\n"
        "    payload = json.dumps({'source': source}).encode('utf-8')\n"
        f"    req = Request({verifier_url!r}, payload, {{'Content-Type': 'application/json'}})\n"
        f"    with urlopen(req, timeout={timeout}) as response:\n"
        "        out = json.load(response)\n"
        "    metrics = {'combined_score': float(out['combined_score'])}\n"
        f"    for i in {ids!r}:\n"
        "        metrics['closed_' + i] = 1.0 if out['statuses'].get(i) == 'closed' else 0.0\n"
        "    return EvaluationResult(metrics=metrics, artifacts={'feedback': out['feedback']})\n")
    return path


class LeanBrokerLM(ob.BrokerLM):
    """GEPA reflection model via the broker. GEPA keeps the text between the first and last
    fence, so exactly one fenced block is required."""

    receipts: list
    expected_first_sha256 = None

    @staticmethod
    def _preflight(content, finish_reason):
        body = LT.extract_body(content, finish_reason)
        if content.count("```") != 2:
            raise ValueError("proposal must contain exactly one fenced ```lean block")
        LT.preflight_body(body)

    def __call__(self, request):
        messages = [{"role": "user", "content": request}] if isinstance(request, str) else list(request)
        if self.calls == 0 and self.expected_first_sha256 and \
                lb.messages_sha256(messages) != self.expected_first_sha256:
            raise ob.BrokerHalted("first proposer prompt differs from the approved first-prompt-gepa.sha256")
        text = request if isinstance(request, str) else json.dumps(request)
        receipt = {"call": self.calls + 1, "packet_seen": PACKET_MARK in text or "Stmt." in text,
                   "request_sha256": _sha(text.encode()), "request_chars": len(text)}
        self.receipts.append(receipt)
        try:
            return super().__call__(request)
        finally:
            receipt["finish_reason"] = self.last_finish_reason


def _gepa_worker(args) -> dict:
    from gepa.optimize_anything import EngineConfig, GEPAConfig, ReflectionConfig, optimize_anything

    train = val = [{"id": i} for i in LT.IDS]  # 11 instances; train = val (no separate validation)
    lm = LeanBrokerLM(args.broker_url, args.model, args.max_tokens, None, args.llm_timeout, args.reasoning_effort)
    lm.receipts = []
    lm.expected_first_sha256 = args.expected_first_prompt_sha256
    seen = {}

    def verify(source):
        key = _sha(source.encode())
        if key not in seen:
            payload = json.dumps({"source": source}).encode()
            with urlopen(Request(args.verifier_url, payload, {"Content-Type": "application/json"}),
                         timeout=args.eval_timeout) as response:
                seen[key] = json.load(response)
        return seen[key]

    def evaluator(candidate, example):
        r = verify(candidate)
        ident = example["id"]
        closed = r["statuses"].get(ident) == "closed"
        return (1.0 if closed else 0.0), {"id": ident, "status": r["statuses"].get(ident, r["status"]),
                                          "feedback": r["instance_feedback"][ident],
                                          "closed_in_this_body": [i for i in LT.IDS
                                                                  if r["statuses"].get(i) == "closed"]}

    minibatch = lb.reflection_minibatch_size(train)
    per_proposal = lb.gepa_metric_calls_per_proposal(minibatch, val)
    result = optimize_anything(
        seed_candidate=args.seed.read_text(), evaluator=evaluator, dataset=train, valset=val,
        objective=OBJECTIVE, background=SYSTEM,
        config=GEPAConfig(
            engine=EngineConfig(run_dir=str(args.run_dir / "gepa"), seed=0,
                                max_candidate_proposals=args.proposals,
                                max_metric_calls=len(val) + (args.proposals + 1) * per_proposal,
                                max_workers=1, parallel=False),
            reflection=ReflectionConfig(reflection_lm=lm, reflection_minibatch_size=minibatch)))
    best = result.best_candidate
    if not isinstance(best, str):
        raise TypeError("GEPA returned a non-text candidate")
    (args.run_dir / "best.lean").write_text(best)
    full = verify(best)
    candidates = [c if isinstance(c, str) else json.dumps(c) for c in getattr(result, "candidates", [])]
    summary = {"engine": "gepa", "upstream": ob.UPSTREAM["gepa"], "best_path": str(args.run_dir / "best.lean"),
               "best_score": full["combined_score"], "best_idx": getattr(result, "best_idx", None),
               "candidate_sha256": [_sha(c.encode()) for c in candidates],
               "lineage": {k: getattr(result, k, None) for k in ("parents", "val_aggregate_scores",
                                                                 "total_metric_calls", "num_full_val_evals")},
               "reflection_calls": lm.calls, "model_valid_responses": lm.valid_responses,
               "model_preflight_failures": lm.preflight_failures, "reflection_receipts": lm.receipts,
               "reflection_minibatch_size": minibatch, "final_request": full}
    (args.run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    return summary


def _research_status(seed, best, proposals):
    if best is None:
        return "INCOMPLETE"
    if set(best["closed_targets"]) - set(seed["closed_targets"]):
        return "TARGET_CLOSED"
    if len(best["closed_milestones"]) > len(seed["closed_milestones"]):
        return "MILESTONE_PROGRESS"
    return "NO_GAIN" if proposals else "NO_VALID_PROPOSAL"


_RESULT_KEYS = ("combined_score", "status", "statuses", "closed_targets", "closed_milestones", "aux_count")


def _setup(args, engine):
    run_dir = args.run_dir.resolve()
    if run_dir.exists():
        raise FileExistsError(run_dir)
    (run_dir / "output" / "tmp").mkdir(parents=True)
    stage = run_dir / "stage"
    stage.mkdir()
    seed = stage / "initial_program.lean"
    shutil.copyfile(args.seed, seed)
    provenance = {"seed_sha256": _sha(seed.read_bytes()), "lean_lock_digest": LT.verify_lock()}
    verifier = LeanVerifier(run_dir, cache_dir=args.cache_dir, engine=engine, provenance=provenance,
                            max_requests=args.max_evals)
    seed_eval = verifier.evaluate(seed.read_text(), final=True)
    return run_dir, stage, seed, verifier, provenance, seed_eval


def _finish(manifest, run_dir, verifier, seed_eval, best_source: str):
    from tools.orchestrator import trusted_status

    final = verifier.evaluate(best_source, final=True)  # uncached, independent re-audit
    seed_hash = seed_eval["candidate_hash"]
    st = verifier.state
    manifest.update({
        "candidate_evaluations": {k: st[k] for k in ("requests", "failures", "best", "memo_hits")},
        "evaluation_trace": st["evaluations"],
        "proposal_hashes": [h for h in st["distinct_source_hashes"] if h != seed_hash],
        "seed_result": {k: seed_eval[k] for k in _RESULT_KEYS},
        "verified_best_hash": final["candidate_hash"],
        "verified_best_result": {k: final[k] for k in _RESULT_KEYS},
        "trusted_status_after": trusted_status()})
    manifest["research_status"] = _research_status(manifest["seed_result"], manifest["verified_best_result"],
                                                   manifest["proposal_hashes"])
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    return manifest


def _launch(args) -> dict:
    from integrations.program_sandbox import sandbox_command, sandbox_profile

    if args.engine not in ENGINES:
        raise SystemExit(f"engine {args.engine} is excluded from Track 3")
    args.broker_url = ob._broker_url(args.broker_url)
    python = args.python.absolute()
    upstream = ob._installed_identity(python, args.engine)
    run_dir, stage, seed, verifier, provenance, seed_eval = _setup(args, args.engine)
    for mod in (ob, lb, LT):
        shutil.copyfile(Path(mod.__file__), stage / Path(mod.__file__).name)
    shutil.copyfile(Path(__file__), stage / "lean_official_worker.py")
    shutil.copyfile(LT.PROJECT / "LrxLean" / "Defs.lean", stage / "Defs.lean")
    server, verifier_url = verifier.serve()
    env = ob._worker_environment(stage, run_dir, args.broker_url)
    if args.engine == "gepa":
        command = [str(python), str(stage / "lean_official_worker.py"), "_gepa_worker",
                   "--seed", str(seed), "--run-dir", str(run_dir / "output"), "--broker-url", args.broker_url,
                   "--model", args.model, "--verifier-url", verifier_url,
                   "--max-tokens", str(args.max_tokens), "--proposals", str(args.iterations),
                   "--llm-timeout", str(args.llm_timeout), "--eval-timeout", str(args.eval_timeout)]
        if args.expected_first_prompt_sha256:
            command += ["--expected-first-prompt-sha256", args.expected_first_prompt_sha256]
        if args.reasoning_effort:
            command += ["--reasoning-effort", args.reasoning_effort]
    else:
        args.evox_switch_interval, args.offline_no_auto_variation = args.iterations + 1, True
        config = _sky_config(args, stage)
        evaluator = _sky_evaluator(stage, verifier_url, args.eval_timeout)
        command = [str(python), "-m", "skydiscover", "optimize", str(seed), str(evaluator),
                   "--config", str(config), "--search", args.engine, "--iterations", str(args.iterations),
                   "--output", str(run_dir / "output" / "sky"), "--log-level", "INFO"]
    base_python = Path(os.path.realpath(python))
    read_paths = ["/System", "/usr", "/Library", "/opt/homebrew", "/private/etc", "/dev",
                  str(python.parent.parent), str(base_python.parent.parent), str(stage)]
    profile = run_dir / "worker.sb"
    profile.write_text(sandbox_profile(read_paths=read_paths, write_paths=[run_dir / "output"],
                                       loopback_ports=[urlparse(args.broker_url).port,
                                                       urlparse(verifier_url).port],
                                       allow_python_multiprocessing=True))
    wrapped = sandbox_command(command, profile)
    manifest = {"engine": args.engine, "task": TASK, "upstream": upstream, **provenance,
                "seed_result": {k: seed_eval[k] for k in _RESULT_KEYS},
                "broker_url": args.broker_url, "model": args.model, "iterations": args.iterations,
                "max_tokens": args.max_tokens, "reasoning_effort": args.reasoning_effort,
                "max_evals": args.max_evals, "wall_seconds": args.wall_seconds, "random_seed": RANDOM_SEED,
                "verifier_url": verifier_url, "command": command, "sandbox_command": wrapped,
                "sandbox_profile": str(profile), "run_dir": str(run_dir)}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    start = time.monotonic()
    try:
        with (run_dir / "console.log").open("w") as log:
            proc = subprocess.Popen(wrapped, cwd=run_dir / "output", env=env, stdout=log,
                                    stderr=subprocess.STDOUT, text=True, start_new_session=True)
            try:
                returncode = proc.wait(timeout=args.wall_seconds)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                returncode = proc.returncode
                manifest["reason"] = "official optimizer wall time limit"
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    finally:
        server.shutdown()
        server.server_close()
    manifest["returncode"] = returncode
    manifest["engine_seconds"] = time.monotonic() - start
    manifest["mechanism_evidence"] = ob._mechanism_evidence(run_dir, args.engine, args.iterations,
                                                             getattr(args, "ledger", None))
    if args.engine == "gepa" and (run_dir / "output" / "summary.json").is_file():
        s = json.loads((run_dir / "output" / "summary.json").read_text())
        manifest["mechanism_evidence"].update({k: s.get(k) for k in (
            "lineage", "best_idx", "candidate_sha256", "reflection_receipts", "reflection_minibatch_size")})
    if args.engine == "adaevolve":
        check = verify_first_solution_prompt(getattr(args, "ledger", None),
                                             getattr(args, "expected_first_prompt_sha256", None))
        manifest["first_solution_prompt_check"] = (None if check is None else
                                                   {"actual_sha256": check[0], "matches": check[1]})
        if check is not None and not check[1]:
            manifest["status"] = manifest["research_status"] = "FIRST_PROMPT_MISMATCH"
            (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
            raise RuntimeError("first solution prompt differs from the approved first-prompt hash")
    if returncode:
        manifest["status"] = manifest["research_status"] = "INCOMPLETE"
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
        raise RuntimeError(f"official {args.engine} exited {returncode}; see {run_dir / 'console.log'}")
    best = (run_dir / "output" / "best.lean" if args.engine == "gepa"
            else run_dir / "output" / "sky" / "best" / "best_program.lean")
    trusted_best = ob._snapshot_best(best, run_dir / "output", run_dir / "verified")
    manifest["status"] = "COMPLETE"
    return _finish(manifest, run_dir, verifier, seed_eval, trusted_best.read_text())


# ------------------------------------------------------ sequential refinement
def _sequential(args) -> dict:
    """Control arm (c): same broker, system prompt and packet; greedy accept on combined_score."""
    args.broker_url = ob._broker_url(args.broker_url)
    run_dir, stage, seed, verifier, provenance, seed_eval = _setup(args, "sequential")
    best_source, best = seed.read_text(), seed_eval
    trace, history, last_request_sha256 = [], [], None
    manifest = {"engine": "sequential", "task": TASK, **provenance, "broker_url": args.broker_url,
                "model": args.model, "iterations": args.iterations, "max_tokens": args.max_tokens,
                "reasoning_effort": args.reasoning_effort, "max_evals": args.max_evals, "run_dir": str(run_dir)}
    status = "COMPLETE"
    for step in range(1, args.iterations + 1):
        user = (OBJECTIVE + "\n\n" + lb.rejection_note(history) + "Current body:\n```lean\n" + best_source
                + "\n```\n\nEvaluator feedback:\n" + best["feedback"])
        request_sha256 = _sha(user.encode())
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        row = {"step": step, "packet_seen": PACKET_MARK in user, "request_sha256": request_sha256}
        if step == 1 and args.expected_first_prompt_sha256 and \
                lb.messages_sha256(messages) != args.expected_first_prompt_sha256:
            row["outcome"] = "guard: first prompt differs from the approved first-prompt-sequential.sha256"
            trace.append(row)
            status = "FIRST_PROMPT_MISMATCH"
            break
        if request_sha256 == last_request_sha256:
            row["outcome"] = "guard: refusing to resend an identical consecutive prompt"
            trace.append(row)
            status = "GUARD_STOPPED"
            break
        last_request_sha256 = request_sha256
        try:
            content, finish = lb._chat(args.broker_url, args.model, args.max_tokens, args.reasoning_effort,
                                       messages, args.llm_timeout)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            row["outcome"] = f"broker stopped: {exc}"
            trace.append(row)
            status = "BROKER_STOPPED"
            break
        row["finish_reason"] = finish
        try:
            source = preflight_source(content, finish)
        except ValueError as exc:
            reason = f"invalid proposal: {exc}"
            row["outcome"] = reason
            history.append({"step": step, "reason": reason})
            trace.append(row)
            continue
        try:
            result = verifier.evaluate(source)
        except PermissionError as exc:
            row["outcome"] = str(exc)
            trace.append(row)
            status = "EVAL_BUDGET"
            break
        accepted = result["combined_score"] > best["combined_score"]
        row.update({"candidate_hash": result["candidate_hash"], "score": result["combined_score"],
                    "closed_targets": result["closed_targets"], "accepted": accepted})
        if accepted:
            best_source, best = source, result
        else:
            reason = (f"rejected: combined {result['combined_score']:.4f} ({result['status']}, targets "
                      f"{result['closed_targets'] or 'none'}) did not beat {best['combined_score']:.4f}")
            row["outcome"] = reason
            history.append({"step": step, "reason": reason})
        trace.append(row)
    (run_dir / "sequential-trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in trace))
    (run_dir / "verified").mkdir(exist_ok=True)
    (run_dir / "verified" / "best.lean").write_text(best_source)
    manifest.update({"status": status, "steps": trace,
                     "mechanism_evidence": {"accepted_steps": [r["step"] for r in trace if r.get("accepted")],
                                            "packet_seen_steps": [r["step"] for r in trace if r["packet_seen"]],
                                            "truncated_steps": [r["step"] for r in trace if r.get("finish_reason")
                                                                in ("length", "max_tokens")]}})
    return _finish(manifest, run_dir, verifier, seed_eval, best_source)


# ------------------------------------------------------------- live wrapper
def _live(args):
    """Approval check, broker from broker-config.json, then one arm with its own ledger and sub-cap."""
    if args.engine not in ENGINES + ("sequential",):
        raise SystemExit(f"engine {args.engine} is excluded from Track 3")
    if not os.environ.get(lb._load_config(args.broker_config)["api_key_env"]):
        raise SystemExit("provider key must be supplied through the environment")
    digest = check_approval(args.broker_config, args.campaign_config)
    bc, cc = lb._load_config(args.broker_config), lb._load_config(args.campaign_config)
    arm = cc["engines"][args.engine]
    sub_cap, remaining = lb.arm_contact_budget(bc, cc, args.engine)
    if sub_cap == 0 or remaining == 0:
        raise SystemExit(f"refusing to start arm {args.engine}: sub-cap {sub_cap}, remaining {remaining}")
    stamp = time.strftime("%y%m%d-%H%M%S")
    run_dir = LEAN_DIR / f"live-{args.engine}-{stamp}"
    broker_log = LEAN_DIR / f"broker-{args.engine}-{stamp}.log"
    if run_dir.exists() or broker_log.exists():
        raise SystemExit("fresh run or broker log path already exists")
    port = cc["broker_port"]
    ledger = str(ROOT / lb._arm_ledger_path(bc, args.engine))
    broker = [sys.executable, "-m", "integrations.research_budget", "serve",
              "--upstream-url", bc["upstream_url"], "--model", bc["model"], "--api-key-env", bc["api_key_env"],
              "--ledger", ledger, "--max-requests", str(min(sub_cap, remaining)),
              "--max-usd", str(bc["max_usd"]), "--input-usd-per-million", str(bc["input_usd_per_million"]),
              "--output-usd-per-million", str(bc["output_usd_per_million"]), "--port", str(port),
              "--max-tokens", str(bc["max_tokens"]), "--reasoning-reserve", str(bc["reasoning_cap_tokens"]),
              "--reasoning-effort", bc["reasoning_effort"], "--reasoning-cap-tokens", str(bc["reasoning_cap_tokens"]),
              "--timeout", str(bc["timeout"])] + (["--upstream-stream"] if bc.get("upstream_stream") else [])
    with broker_log.open("w") as log:
        proc = subprocess.Popen(broker, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            try:
                with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                    if r.status == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            raise SystemExit("local research broker did not become ready")
        argv = ["--seed", str(ROOT / cc["seed"]), "--run-dir", str(run_dir),
                "--broker-url", f"http://127.0.0.1:{port}/v1", "--model", bc["model"],
                "--max-tokens", str(bc["max_tokens"]), "--reasoning-effort", bc["reasoning_effort"],
                "--iterations", str(arm["iterations"]), "--max-evals", str(arm["max_evals"]),
                "--wall-seconds", str(arm["wall_seconds"]), "--llm-timeout", str(int(bc["timeout"]) + 30),
                "--eval-timeout", str(cc["eval_timeout"]), "--cache-dir", str(ROOT / cc["eval_cache"]),
                "--python", str(ROOT / cc["python"]), "--ledger", ledger]
        first = LEAN_DIR / FIRST_PROMPT_FILES[args.engine]
        if first.is_file():
            argv += ["--expected-first-prompt-sha256", first.read_text().split()[0]]
        if args.engine == "sequential":
            out = _sequential(_parser().parse_args(["sequential"] + argv))
        else:
            out = _launch(_parser().parse_args(["run", "--engine", args.engine] + argv))
        out["approved_payload_sha256"] = digest
        (run_dir / "manifest.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
        return out
    finally:
        proc.terminate()
        proc.wait()


def _parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("run", "sequential"):
        p = sub.add_parser(name)
        if name == "run":
            p.add_argument("--engine", required=True, choices=ENGINES)
        p.add_argument("--seed", type=Path, default=LT.SEED_PATH)
        p.add_argument("--run-dir", required=True, type=Path)
        p.add_argument("--python", type=Path, default=ROOT / ".venv-official" / "bin" / "python")
        p.add_argument("--broker-url", required=True)
        p.add_argument("--model", default="gemini-3.8-flash")
        p.add_argument("--iterations", type=int, default=2)
        p.add_argument("--max-tokens", type=int, default=8192)
        p.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh"))
        p.add_argument("--max-evals", type=int, default=40)
        p.add_argument("--wall-seconds", type=int, default=1800)
        p.add_argument("--llm-timeout", type=int, default=240)
        p.add_argument("--eval-timeout", type=int, default=600)
        p.add_argument("--cache-dir", type=Path, default=LEAN_DIR / "eval-cache")
        p.add_argument("--ledger", type=Path)
        p.add_argument("--expected-first-prompt-sha256")
    w = sub.add_parser("_gepa_worker")
    for flag in ("seed", "run-dir"):
        w.add_argument("--" + flag, required=True, type=Path)
    for flag in ("broker-url", "verifier-url", "model"):
        w.add_argument("--" + flag, required=True)
    for flag in ("max-tokens", "proposals", "llm-timeout", "eval-timeout"):
        w.add_argument("--" + flag, required=True, type=int)
    w.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh"))
    w.add_argument("--expected-first-prompt-sha256")
    fp = sub.add_parser("first-prompt")
    fp.add_argument("--capture-dir", required=True, type=Path)
    fp.add_argument("--run-dir", required=True, type=Path)
    fp.add_argument("--engine", required=True, choices=ENGINES + ("sequential",))
    for name in ("approval-hash", "check-approval", "live"):
        p = sub.add_parser(name)
        p.add_argument("--broker-config", type=Path, default=LEAN_DIR / "broker-config.json")
        p.add_argument("--campaign-config", type=Path, default=LEAN_DIR / "campaign-config.json")
        if name == "approval-hash":
            p.add_argument("--write-material", type=Path)
        if name == "live":
            p.add_argument("--engine", required=True, choices=ENGINES + ("sequential",))
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.action == "approval-hash":
        if args.write_material:
            material = approval_material(args.broker_config, args.campaign_config)
            args.write_material.write_text(json.dumps(material, indent=2, sort_keys=True) + "\n")
        print(approval_hash(args.broker_config, args.campaign_config))
        return
    if args.action == "first-prompt":
        out = LEAN_DIR / (FIRST_PROMPT_FILES[args.engine][:-len(".sha256")] + ".md")
        print(write_first_prompt(args.capture_dir, out, args.run_dir, args.engine))
        return
    if args.action == "check-approval":
        print(check_approval(args.broker_config, args.campaign_config))
        return
    actions = {"run": _launch, "sequential": _sequential, "_gepa_worker": _gepa_worker, "live": _live}
    result = actions[args.action](args)
    keep = ("engine", "status", "research_status", "run_dir", "seed_result", "verified_best_result",
            "mechanism_evidence")
    print(json.dumps({k: result.get(k) for k in keep} if isinstance(result, dict) else result, default=str))


if __name__ == "__main__":
    main()
