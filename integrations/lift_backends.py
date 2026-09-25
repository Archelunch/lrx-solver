"""Run pinned GEPA 0.1.4 and SkyDiscover AdaEvolve/EvoX 0.2.0 on the lift task.

Reuses the official-integration launcher pieces (integrations/official_backends.py,
unchanged): the Seatbelt-confined optimizer process, the broker-only model
client, the installed-identity check, the best-program snapshot, and the
mechanism evidence. Changed for the lift task (autoresearch/lift-m9-260924/TASK.md):
the candidate is a program with lift(instance); the score comes from
integrations/lift_evaluator.py in a trusted coordinator-side service with
staged evaluation; the feedback is a compact development-only packet.
Sequential refinement uses the same broker, prompt and packet with no engine.

The staged copy of this file runs inside the optimizer sandbox, so the module
top level imports only the standard library and official_backends.
"""
from __future__ import annotations

import argparse
import ast
from fractions import Fraction as Fr
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
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
    from integrations import official_backends as ob
except ImportError:  # staged copy inside the optimizer sandbox
    import official_backends as ob

ROOT = Path(__file__).resolve().parents[1]
LIFT_DIR = ROOT / "autoresearch" / "lift-m9-260924"
PACKET_MARK = "LIFT_PACKET_V1"
PACKET_MAX = 2000  # SkyDiscover truncates artifacts at 2000 characters
SCREEN_PARENTS = 14
ENGINES = ("gepa", "adaevolve", "evox")

SYSTEM = (
    "Find a label-insertion gadget for LRX sorting. The candidate source must define "
    "lift(instance) and return {'words': [...], 'weights': optional rational strings, "
    "'note': optional}: at most 16 strings over L,R,X, each at most 4000 letters, and each "
    "sorting the child unit base to (1..9, 0^k). L rotates the vector left, R rotates it "
    "right, and X swaps its first two entries. The source must be at most 64 KiB, use the "
    "standard library only, and finish each instance within 10 seconds. The instance is "
    "{m: 8, parent: {id, labels, mask, unit_base, certificate: {kind, rows: [{weight, word, "
    "base, slopes}]}}, insert: {label: 9, position, split}, child: {id, labels, mask, "
    "unit_base, k, budget_unit, slope_bound}}. Parent rows are certified m=8 words on the "
    "parent unit base, with exact Lemma 1 base and one slope per zero block. The trusted "
    "evaluator replays every word, recomputes base and slopes, and solves the exact LP. A "
    "certificate needs weighted base < budget_unit+1 = 39+7k and every weighted slope <= 7. "
    "A uniform gadget adds at most n letters and raises each slope by at most 1. Misses "
    "prove nothing. Do not read files, the network, or environment variables."
)
OBJECTIVE = (
    "Improve this executable Python lift(instance) gadget. Return the entire replacement "
    "Python source in one fenced code block. Maximize exact m=9 family certificates, then "
    "reduce the exact LP gap on misses. Only development instances are shown."
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


# ------------------------------------------------------------ screen + packet
def screen_parents(instances, count=SCREEN_PARENTS):
    """Deterministic development screen: `count` parents spread over parent k."""
    groups = {}
    for inst in instances:
        groups.setdefault(inst["parent"]["id"], inst["parent"]["mask"])
    order = sorted(groups, key=lambda p: (bin(groups[p]).count("1"), p))
    if len(order) <= count:
        return order
    return [order[round(i * (len(order) - 1) / (count - 1))] for i in range(count)]


def packet(result, instances, best, scope):
    """Compact development-only feedback: <= 3 failures, best score, one failed construction."""
    by_id = {inst["id"]: inst for inst in instances}
    n = result["instances"]
    head = [f"{PACKET_MARK} ({scope}; development only; search signal, not proof)",
            f"this candidate: {result['certificates']}/{n} certificates, {result['valid']}/{n} valid, "
            f"gap_sum {float(Fr(result['gap_sum'])):.3f}; best so far: {best}"]
    rows = result["results"]
    invalid = [r for r in rows if not r["valid"]]
    misses = sorted((r for r in rows if r["valid"] and r["status"] != "CERTIFICATE"),
                    key=lambda r: Fr(r["gap"]))
    body = []
    for r in invalid[:3]:
        t = r["trace"]
        why = t.get("failed_word") or t.get("failure")
        body.append(f"- {r['id']}: {r['status']}: {json.dumps(why)[:240]}")
    for r in misses[:max(0, 3 - len(body))]:
        inst = by_id[r["id"]]
        t, lp = r["trace"], r.get("gap_lp", {})
        prow = [{"row": i, "w": x.get("weight"), "base": x["base"], "slopes": x["slopes"]}
                for i, x in enumerate(inst["parent"]["certificate"]["rows"][:4])]
        body.append(
            f"- {r['id']} child {inst['child']['unit_base']} k={r['k']} need base<{r['budget_unit'] + 1}, "
            f"slopes<=7: gap {float(Fr(r['gap'])):.3f}, mixture base {float(Fr(lp.get('base', '0'))):.2f}, "
            f"overshoot {t.get('base_overshoot')}, slopes over 7 {t.get('slopes_over')}; "
            f"parent rows used {t.get('parent_rows_used')}; parent rows {_canonical(prow)}")
    tail = []
    if misses:
        c = misses[0]["trace"]["construction"]
        tail.append(f"failed construction ({misses[0]['id']}, word {c['index']}, LP weight {c['weight']}): "
                    f"base {c['base']}, slopes {c['slopes']}, word {c['word'][:300]}"
                    + ("..." if c["truncated"] or len(c["word"]) > 300 else ""))
    text = "\n".join(head + body + tail)
    while len(text) > PACKET_MAX and body:
        body.pop()
        text = "\n".join(head + body + tail)
    return text[:PACKET_MAX]


def preflight_source(content, finish_reason=None) -> str:
    """A fenced Python block defining lift(instance); checked before any evaluation.

    Prose is allowed before/after the fence(s). With multiple fenced blocks, the
    last one that defines lift(...) is used (models sometimes show scratch work
    or an earlier draft first). Truncated output is never accepted or repaired:
    that check runs first and short-circuits everything below.
    """
    if finish_reason in ("length", "max_tokens"):
        raise ValueError("proposal was truncated by the model output limit")
    if not isinstance(content, str):
        raise ValueError("proposal had no text content")
    fences = list(re.finditer(r"```(?:python)?\s*\n(.*?)```", content, re.IGNORECASE | re.DOTALL))
    if not fences:
        raise ValueError("proposal must contain a fenced Python source block defining lift(instance)")
    chosen = None
    for m in fences:
        candidate = m.group(1)
        try:
            tree = ast.parse(candidate)
        except SyntaxError:
            continue
        if any(isinstance(node, ast.FunctionDef) and node.name == "lift" for node in tree.body):
            chosen = candidate  # keep scanning; last matching fence wins
    if chosen is None:
        raise ValueError("proposal must define lift(instance) in a fenced Python source block")
    if len(chosen.encode()) > 65536:
        raise ValueError("proposal exceeds source size cap")
    return chosen


# ------------------------------------------------------ trusted verifier side
class LiftVerifier:
    """Coordinator-side staged evaluation. Candidate code runs only in lift_evaluator's sandbox."""

    def __init__(self, instances_path, run_dir, *, cache_dir, archive_path, engine, provenance,
                 max_requests, jobs=8, timeout=10.0, require_os_sandbox=True):
        from integrations.lift_evaluator import load_instances

        loaded = load_instances(instances_path)
        self.full = loaded
        self.raw = [send for send, _ in loaded]
        self.by_parent = {}
        for item in loaded:
            self.by_parent.setdefault(item[0]["parent"]["id"], []).append(item)
        self.screen_ids = screen_parents(self.raw)
        self.screen = [x for p in self.screen_ids for x in self.by_parent[p]]
        self.cache_dir, self.archive_path = cache_dir, archive_path
        self.engine, self.provenance, self.jobs, self.timeout = engine, provenance, jobs, timeout
        self.max_requests = max_requests
        self.require_os_sandbox = require_os_sandbox  # tests only; engines always use Seatbelt
        self.evidence = Path(run_dir) / "verified" / "evaluations"
        self.evidence.mkdir(parents=True)
        self.lock = threading.Lock()
        self.state = {"requests": 0, "evaluations": [], "distinct_source_hashes": [],
                      "screen_valid_source_hashes": [], "full_evaluations": 0,
                      "best_screen": None, "best_full": None, "failures": 0,
                      "screen_parent_ids": self.screen_ids,
                      "screen_instances": len(self.screen)}

    def _current_best(self, extra=None):
        """Best screen/full scores across every evaluation on record, all scopes.

        Recomputed at packet-build time from the evaluation manifest (self.state
        ["evaluations"]) rather than trusted to incrementally-maintained fields,
        so a parent-scoped (GEPA) call that happens to carry a full-development
        result (e.g. a final confirmation) is counted the same as a screen-scope
        call (autoresearch/TRACE-AUDIT-260925.md defect 7). `extra`, if given, is
        this call's own not-yet-appended row.
        """
        rows = self.state["evaluations"] + ([extra] if extra else [])
        best_screen = None
        for row in rows:
            if row["scope"] == "screen" and row["valid"] == row["instances"]:
                if best_screen is None or row["combined_score"] > best_screen["score"]:
                    best_screen = {"score": row["combined_score"], "certificates": row["certificates"],
                                   "source_sha256": row["candidate_hash"]}
        best_full = None
        for row in rows:
            if row.get("full_valid") is not None and row["full_valid"] == row["full_instances"]:
                if best_full is None or row["full_combined_score"] > best_full["score"]:
                    best_full = {"score": row["full_combined_score"], "certificates": row["full_certificates"],
                                 "gap_sum": row["full_gap_sum"], "source_sha256": row["candidate_hash"]}
        return best_screen, best_full

    def _best_text(self, best_screen, best_full):
        return (f"screen {best_screen['score']:.4f} ({best_screen['certificates']}/{len(self.screen)} "
                "certificates)" if best_screen else "none") + \
               (f"; full development {best_full['certificates']}/{len(self.full)} certificates"
                if best_full else "")

    def evaluate(self, source: str, parent_id=None, *, final=False) -> dict:
        from integrations import lift_evaluator as E

        with self.lock:
            if self.state["requests"] >= self.max_requests:
                raise PermissionError("evaluation request budget exhausted")
            self.state["requests"] += 1
            ordinal = self.state["requests"]
            path = self.evidence / f"candidate-{ordinal:04d}.py"
            path.write_text(source)
            digest = _sha(source.encode())
            if digest not in self.state["distinct_source_hashes"]:
                self.state["distinct_source_hashes"].append(digest)
            subset, scope = ((self.by_parent[parent_id], "parent " + parent_id) if parent_id
                             else (self.screen, "screen"))
            res = E.evaluate(path, subset, timeout=self.timeout, jobs=self.jobs, cache_dir=self.cache_dir,
                             require_os_sandbox=self.require_os_sandbox)
            full = None
            promising = False
            if parent_id is None:
                n = res["instances"]
                prior_best_screen, _ = self._current_best()
                promising = res["valid"] == n and (prior_best_screen is None or
                                                    res["combined_score"] >= prior_best_screen["score"])
                if promising and digest not in self.state["screen_valid_source_hashes"]:
                    self.state["screen_valid_source_hashes"].append(digest)
            # A full-development eval runs on any promising screen-scope candidate
            # or any final confirmation, regardless of scope, so a parent-scoped
            # finalist can also set best_full.
            if promising or final:
                full = E.evaluate(path, self.full, timeout=self.timeout, jobs=self.jobs,
                                  cache_dir=self.cache_dir, require_os_sandbox=self.require_os_sandbox)
                self.state["full_evaluations"] += 1
            row = {"scope": scope, "candidate_hash": digest, "combined_score": res["combined_score"],
                   "certificates": res["certificates"], "valid": res["valid"], "instances": res["instances"],
                   "gap_sum_float": float(Fr(res["gap_sum"])), "cache_hit": res["cache_hit"],
                   "full_certificates": full["certificates"] if full else None,
                   "full_combined_score": full["combined_score"] if full else None,
                   "full_valid": full["valid"] if full else None,
                   "full_instances": full["instances"] if full else None,
                   "full_gap_sum": full["gap_sum"] if full else None}
            best_screen, best_full = self._current_best(extra=row)
            self.state["best_screen"], self.state["best_full"] = best_screen, best_full
            feedback = packet(res, [x for x, _ in subset], self._best_text(best_screen, best_full), scope)
            summary = {"combined_score": res["combined_score"], "certificates": res["certificates"],
                       "valid": res["valid"], "instances": res["instances"], "gap_sum": res["gap_sum"],
                       "gap_sum_float": float(Fr(res["gap_sum"])), "timeouts": res["timeouts"],
                       "scope": scope, "candidate_hash": digest, "cache_hit": res["cache_hit"],
                       "evaluation_cache_key": res["cache_key"], "feedback": feedback,
                       "full": ({x: full[x] for x in ("certificates", "valid", "instances", "gap_sum",
                                                      "combined_score", "cache_key")} if full else None)}
            artifact = self.evidence / f"result-{ordinal:04d}.json"
            artifact.write_text(json.dumps({"summary": summary, "stage": res, "full": full}, default=str) + "\n")
            summary["evaluation"] = str(artifact)
            row.update(ordinal=ordinal, packet_sha256=_sha(feedback.encode()))
            self.state["evaluations"].append(row)
            if self.archive_path:
                from integrations.research_archive import DevelopmentArchive
                archive = DevelopmentArchive(self.archive_path)
                try:
                    traces = [{"case_id": r["id"], "status": r["status"], "gap": r["gap"], "trace": r["trace"]}
                              for r in res["results"] if r["status"] != "CERTIFICATE"][:40]
                    archive.add(run_id=Path(self.evidence).parents[1].name, engine=self.engine, source=source,
                                score=res["combined_score"], feedback={"summary": feedback, "scope": scope,
                                                                       "full": summary["full"]},
                                traces=traces, provenance=self.provenance,
                                claim_status="finite_development" if res["valid"] == res["instances"] else "invalid")
                finally:
                    archive.close()
            return summary

    def serve(self):
        verifier = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != "/evaluate":
                    return self._reply(404, {"error": "not found"})
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 75000:
                    return self._reply(413, {"error": "source request size exceeded"})
                try:
                    payload = json.loads(self.rfile.read(length))
                    source, parent = payload["source"], payload.get("parent_id")
                    if not isinstance(source, str) or len(source.encode()) > 65536:
                        return self._reply(413, {"error": "candidate source size exceeded"})
                    if parent is not None and parent not in verifier.by_parent:
                        return self._reply(400, {"error": "unknown development parent"})
                    return self._reply(200, verifier.evaluate(source, parent))
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


# ------------------------------------------------------------- inputs, approval
def _load_config(path):
    return json.loads(Path(path).read_text())


def _verify_inputs(instances: Path, manifest: Path) -> dict:
    from tools.orchestrator import trusted_status

    trust = trusted_status()
    if not trust["ok"]:
        raise RuntimeError(f"trusted core lock mismatch: {trust}")
    if instances.name != "development.json" or "holdout" in str(instances):
        raise ValueError("engines may load only the frozen development set, never holdout")
    frozen = json.loads(manifest.read_text())
    if frozen.get("files", {}).get("development.json") != _sha(instances.read_bytes()):
        raise RuntimeError("frozen development hash mismatch")
    return {"trusted_status": trust, "frozen_manifest": str(manifest),
            "frozen_manifest_sha256": _sha(manifest.read_bytes()),
            "development_sha256": _sha(instances.read_bytes())}


def development_from_manifest(manifest: Path) -> tuple[Path, str]:
    """The development set named by the frozen manifest, with its recorded hash (read at run time)."""
    digest = json.loads(Path(manifest).read_text())["files"]["development.json"]
    path = Path(manifest).parent / "development.json"
    if _sha(path.read_bytes()) != digest:
        raise RuntimeError("frozen development hash mismatch")
    return path, digest


def messages_sha256(messages) -> str:
    return _sha(_canonical(messages).encode())


def approval_material(broker_config: Path, campaign_config: Path) -> dict:
    """Everything a live arm sends or spends, derived from the configs; hashed for approval."""
    from integrations.lift_evaluator import CONTRACT, VERSION
    from integrations.research_budget import _dry_run_payload

    bc, cc = _load_config(broker_config), _load_config(campaign_config)
    _, development = development_from_manifest(ROOT / cc["frozen_manifest"])
    first = broker_config.parent / "first-prompt.sha256"
    return {"broker_config": bc, "campaign_config": cc,
            "first_prompt_sha256": first.read_text().split()[0] if first.is_file() else None,
            "upstream_endpoint": bc["upstream_url"].rstrip("/") + "/chat/completions",
            "dry_run_payload": _dry_run_payload(bc), "system_prompt": SYSTEM, "objective": OBJECTIVE,
            "packet_format": {"marker": PACKET_MARK, "max_chars": PACKET_MAX, "scope": "development only"},
            "seed_sha256": _sha((ROOT / cc["seed"]).read_bytes()),
            "frozen_manifest_sha256": _sha((ROOT / cc["frozen_manifest"]).read_bytes()),
            "development_sha256": development,
            "evaluator": {"version": VERSION, "contract": CONTRACT},
            "lift_backends_sha256": _sha(Path(__file__).read_bytes())}


def approval_hash(broker_config: Path, campaign_config: Path) -> str:
    return _sha(_canonical(approval_material(broker_config, campaign_config)).encode())


def check_approval(broker_config: Path, campaign_config: Path) -> str:
    computed = approval_hash(broker_config, campaign_config)
    approved = broker_config.parent / "payload-approved.sha256"
    if not approved.is_file():
        raise SystemExit(f"refusing to start: {approved} is missing (created only after user approval)")
    token = approved.read_text().split()
    if not token or token[0] != computed:
        raise SystemExit(f"refusing to start: payload hash {computed} does not match {approved}")
    stored = _load_config(broker_config).get("dry_run_payload_sha256")
    if stored is not None and stored != computed:
        raise SystemExit("refusing to start: broker-config dry_run_payload_sha256 disagrees")
    return computed


# ------------------------------------------------------------ official engines
EVOX_STRATEGY_EVOLUTION_MIN_ITERATIONS = 100


def evox_strategy_evolution_enabled(iterations, offline_no_auto_variation) -> bool:
    """Whether EvoX's search-strategy meta-search should run at all.

    On short runs it burns a large share of calls on strategy code that is
    rarely adopted and has crashed on a bad generated program (an
    AttributeError from a strategy's own broken database implementation,
    autoresearch/TRACE-AUDIT-260925.md defect 9); below
    EVOX_STRATEGY_EVOLUTION_MIN_ITERATIONS it is not worth the risk or cost.

    Strategy evolution is gated by stagnation vs `switch_interval`
    (skydiscover...evox/controller.py `_should_evolve_search`: it fires once
    `_stagnant_count >= switch_interval`), not by
    `auto_generate_variation_operators` (that only controls whether an
    evolved strategy also gets custom variation operators) and not
    reliably by `search.share_llm` either: two smoke runs confirmed strategy
    calls kept happening with auto_generate_variation_operators=False and
    with share_llm=False, because the launcher's sandboxed worker
    environment (official_backends._worker_environment) sets
    OPENAI_API_BASE/OPENAI_API_KEY to the same broker for the whole
    subprocess, so SkyDiscover's meta-LLM pool stays reachable regardless of
    share_llm. The lever that actually works is `switch_interval` itself:
    when this function returns False, `_sky_config` sets switch_interval to
    iterations + 1, which `_stagnant_count` can never reach within the run
    (a smoke run with iterations=6 confirmed 0 strategy/variation calls
    after this fix, vs 3 strategy + 2 variation calls before it).
    `auto_generate_variation_operators` is kept tied to this function too,
    as a secondary, harmless-if-inert precaution.
    """
    return not offline_no_auto_variation and iterations >= EVOX_STRATEGY_EVOLUTION_MIN_ITERATIONS


def _sky_config(args, stage: Path) -> Path:
    config = {
        "max_iterations": args.iterations, "checkpoint_interval": 1, "log_level": "INFO",
        "language": "python",
        "llm": {"models": [{"name": args.model, "weight": 1.0}], "api_base": args.broker_url,
                "api_key": "local-broker", "max_tokens": args.max_tokens, "temperature": 0.7,
                "timeout": args.llm_timeout, "retries": 0, "reasoning_effort": args.reasoning_effort},
        "search": {"type": args.engine, "num_context_programs": 2,
                   "database": {"auto_generate_variation_operators":
                                evox_strategy_evolution_enabled(args.iterations, args.offline_no_auto_variation)}
                   if args.engine == "evox" else {},
                   "switch_interval": (args.evox_switch_interval
                                       if evox_strategy_evolution_enabled(args.iterations,
                                                                          args.offline_no_auto_variation)
                                       else args.iterations + 1) if args.engine == "evox" else None,
                   "share_llm": args.engine == "evox"},
        "prompt": {"system_message": SYSTEM},
        "evaluator": {"timeout": args.eval_timeout, "max_retries": 0, "cascade_evaluation": False},
        "diff_based_generation": True, "max_solution_length": 40000, "monitor": {"enabled": False},
    }
    path = stage / "sky-config.yaml"  # JSON is valid YAML
    path.write_text(json.dumps(config, indent=2) + "\n")
    return path


def _sky_evaluator(stage: Path, verifier_url: str, timeout: int) -> Path:
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
        "    full = out.get('full') or {}\n"
        "    metrics = {'combined_score': float(out['combined_score']),\n"
        "               'screen_certificates': float(out['certificates']),\n"
        "               'screen_valid': float(out['valid']), 'screen_gap_sum': out['gap_sum_float'],\n"
        "               'full_certificates': float(full.get('certificates', -1))}\n"
        "    return EvaluationResult(metrics=metrics, artifacts={'feedback': out['feedback']})\n")
    return path


class LiftBrokerLM(ob.BrokerLM):
    """GEPA reflection model via the broker; lift preflight and packet receipts."""

    receipts: list

    @staticmethod
    def _preflight(content, finish_reason):
        preflight_source(content, finish_reason)

    expected_first_sha256 = None

    def __call__(self, request):
        messages = [{"role": "user", "content": request}] if isinstance(request, str) else list(request)
        if self.calls == 0 and self.expected_first_sha256 and \
                messages_sha256(messages) != self.expected_first_sha256:
            raise ob.BrokerHalted("first proposer prompt differs from the approved first-prompt.sha256")
        text = request if isinstance(request, str) else json.dumps(request)
        receipt = {"call": self.calls + 1, "packet_seen": PACKET_MARK in text,
                  "request_sha256": _sha(text.encode()), "request_chars": len(text)}
        self.receipts.append(receipt)
        try:
            return super().__call__(request)
        finally:
            receipt["finish_reason"] = self.last_finish_reason


def reflection_minibatch_size(train) -> int:
    """GEPA's reflection minibatch, capped at the train set size (never oversample a small set)."""
    return min(3, len(train))


def gepa_metric_calls_per_proposal(minibatch, val) -> int:
    """Metric calls one proposal costs: minibatch eval + reflection re-eval + valset eval."""
    return 2 * minibatch + len(val)


def _gepa_worker(args) -> dict:
    from gepa.optimize_anything import EngineConfig, GEPAConfig, ReflectionConfig, optimize_anything

    data = json.loads(args.dataset.read_text())
    train = [{"id": p} for p in data["train"]]
    val = [{"id": p} for p in data["screen"]]
    lm = LiftBrokerLM(args.broker_url, args.model, args.max_tokens, None, args.llm_timeout,
                      args.reasoning_effort)
    lm.receipts = []
    lm.expected_first_sha256 = args.expected_first_prompt_sha256

    def verify(source, parent_id=None):
        payload = json.dumps({"source": source, "parent_id": parent_id}).encode()
        with urlopen(Request(args.verifier_url, payload, {"Content-Type": "application/json"}),
                     timeout=args.eval_timeout) as response:
            return json.load(response)

    def evaluator(candidate, example):
        r = verify(candidate, example["id"])
        return float(r["combined_score"]), {
            "parent_id": example["id"], "certificates": r["certificates"], "valid": r["valid"],
            "instances": r["instances"], "gap_sum": r["gap_sum_float"], "feedback": r["feedback"]}

    minibatch = reflection_minibatch_size(train)
    per_proposal = gepa_metric_calls_per_proposal(minibatch, val)
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
        raise TypeError("GEPA returned a non-source candidate")
    (args.run_dir / "best.py").write_text(best)
    full = verify(best)
    lineage = {k: getattr(result, k, None) for k in ("parents", "val_aggregate_scores",
                                                     "discovery_eval_counts", "total_metric_calls",
                                                     "num_full_val_evals")}
    candidates = [c if isinstance(c, str) else json.dumps(c) for c in getattr(result, "candidates", [])]
    summary = {"engine": "gepa", "upstream": ob.UPSTREAM["gepa"], "best_path": str(args.run_dir / "best.py"),
               "best_screen_score": full["combined_score"], "best_idx": getattr(result, "best_idx", None),
               "candidate_sha256": [_sha(c.encode()) for c in candidates], "lineage": lineage,
               "reflection_calls": lm.calls, "reflection_batch_calls": lm.calls,
               "model_valid_responses": lm.valid_responses,
               "model_preflight_failures": lm.preflight_failures, "mandatory_hard_case_ids": [],
               "reflection_receipts": lm.receipts, "final_request": full}
    (args.run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    return summary


def _research_status(seed_full, best_full, valid_proposals):
    if best_full is None:
        return "INCOMPLETE"
    if best_full["certificates"] > seed_full["certificates"]:
        return "NEW_CERTIFICATES"
    if best_full["certificates"] == seed_full["certificates"] and \
            Fr(best_full["gap_sum"]) < Fr(seed_full["gap_sum"]):
        return "GRADED_PROGRESS"
    return "NO_GAIN" if valid_proposals else "NO_VALID_PROPOSAL"


def _setup(args, engine):
    provenance = _verify_inputs(args.instances.resolve(), args.frozen_manifest.resolve())
    run_dir = args.run_dir.resolve()
    if run_dir.exists():
        raise FileExistsError(run_dir)
    (run_dir / "output" / "tmp").mkdir(parents=True)
    stage = run_dir / "stage"
    stage.mkdir()
    seed = stage / "initial_program.py"
    shutil.copyfile(args.seed, seed)
    provenance = dict(provenance, seed_sha256=_sha(seed.read_bytes()))
    verifier = LiftVerifier(args.instances, run_dir, cache_dir=args.cache_dir, archive_path=args.archive,
                            engine=engine, provenance=provenance, max_requests=args.max_evals,
                            jobs=args.jobs)
    (stage / "dataset.json").write_text(json.dumps({"train": sorted(verifier.by_parent),
                                                    "screen": verifier.screen_ids}) + "\n")
    seed_eval = verifier.evaluate(seed.read_text(), final=True)
    return run_dir, stage, seed, verifier, provenance, seed_eval


def _finish(manifest, run_dir, verifier, seed_eval, best_source: str):
    from tools.orchestrator import trusted_status

    final = verifier.evaluate(best_source, final=True)
    seed_hash = seed_eval["candidate_hash"]
    st = verifier.state
    manifest.update({
        "candidate_evaluations": {k: st[k] for k in ("requests", "full_evaluations", "failures",
                                                     "best_screen", "best_full", "screen_parent_ids",
                                                     "screen_instances")},
        "evaluation_trace": st["evaluations"],
        "proposal_hashes": [h for h in st["distinct_source_hashes"] if h != seed_hash],
        "screen_valid_proposal_hashes": [h for h in st["screen_valid_source_hashes"] if h != seed_hash],
        "seed_full": seed_eval["full"], "verified_best_hash": final["candidate_hash"],
        "verified_best_full": final["full"], "verified_best_screen_score": final["combined_score"],
        "trusted_status_after": trusted_status()})
    manifest["research_status"] = _research_status(seed_eval["full"], final["full"],
                                                   manifest["screen_valid_proposal_hashes"])
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    return manifest


def _launch(args) -> dict:
    from integrations.program_sandbox import sandbox_command, sandbox_profile

    args.broker_url = ob._broker_url(args.broker_url)
    python = args.python.absolute()
    upstream = ob._installed_identity(python, args.engine)
    run_dir, stage, seed, verifier, provenance, seed_eval = _setup(args, args.engine)
    shutil.copyfile(Path(ob.__file__), stage / "official_backends.py")
    shutil.copyfile(Path(__file__), stage / "lift_official_worker.py")
    server, verifier_url = verifier.serve()
    env = ob._worker_environment(stage, run_dir, args.broker_url)
    if args.engine == "gepa":
        command = [str(python), str(stage / "lift_official_worker.py"), "_gepa_worker",
                   "--seed", str(seed), "--dataset", str(stage / "dataset.json"),
                   "--run-dir", str(run_dir / "output"), "--broker-url", args.broker_url,
                   "--model", args.model, "--verifier-url", verifier_url,
                   "--max-tokens", str(args.max_tokens), "--proposals", str(args.iterations),
                   "--llm-timeout", str(args.llm_timeout), "--eval-timeout", str(args.eval_timeout)]
        if args.expected_first_prompt_sha256:
            command += ["--expected-first-prompt-sha256", args.expected_first_prompt_sha256]
        if args.reasoning_effort:
            command += ["--reasoning-effort", args.reasoning_effort]
    else:
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
    manifest = {"engine": args.engine, "task": "lift-m9-260924", "upstream": upstream, **provenance,
                "seed_screen": {k: seed_eval[k] for k in ("combined_score", "certificates", "valid",
                                                          "instances", "gap_sum")},
                "broker_url": args.broker_url, "model": args.model, "iterations": args.iterations,
                "max_tokens": args.max_tokens, "reasoning_effort": args.reasoning_effort,
                "max_evals": args.max_evals, "wall_seconds": args.wall_seconds,
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
        manifest["mechanism_evidence"].update({"lineage": s["lineage"], "best_idx": s["best_idx"],
                                               "candidate_sha256": s["candidate_sha256"],
                                               "reflection_receipts": s["reflection_receipts"]})
    if returncode:
        manifest["status"] = manifest["research_status"] = "INCOMPLETE"
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
        raise RuntimeError(f"official {args.engine} exited {returncode}; see {run_dir / 'console.log'}")
    best = (run_dir / "output" / "best.py" if args.engine == "gepa"
            else run_dir / "output" / "sky" / "best" / "best_program.py")
    trusted_best = ob._snapshot_best(best, run_dir / "output", run_dir / "verified")
    manifest["status"] = "COMPLETE"
    return _finish(manifest, run_dir, verifier, seed_eval, trusted_best.read_text())


# ------------------------------------------------------ sequential refinement
def _chat(broker_url, model, max_tokens, reasoning_effort, messages, timeout):
    body = {"model": model, "messages": messages, "max_tokens": max_tokens}
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    req = Request(broker_url + "/chat/completions", json.dumps(body).encode(),
                  {"Content-Type": "application/json", "Authorization": "Bearer local-broker",
                   "X-LRX-Call-Role": "sequential_refinement"})
    with urlopen(req, timeout=timeout) as response:
        choice = json.load(response)["choices"][0]
    return choice["message"]["content"], choice.get("finish_reason")


def rejection_note(history, n=3) -> str:
    """Render up to the last `n` rejected attempts (most recent last) for the next prompt.

    Sequential refinement otherwise resends the same prompt verbatim after a
    rejection, so the model gets no signal about what just failed.
    """
    if not history:
        return ""
    lines = ["Recent rejected attempts (most recent last; do not repeat these):"]
    lines += [f"- step {h['step']}: {h['reason']}" for h in history[-n:]]
    return "\n".join(lines) + "\n\n"


def _sequential(args) -> dict:
    """Control arm: same broker, system prompt and packet; greedy accept on screen score."""
    args.broker_url = ob._broker_url(args.broker_url)
    run_dir, stage, seed, verifier, provenance, seed_eval = _setup(args, "sequential")
    best_source, best = seed.read_text(), seed_eval
    trace = []
    manifest = {"engine": "sequential", "task": "lift-m9-260924", **provenance,
                "broker_url": args.broker_url, "model": args.model, "iterations": args.iterations,
                "max_tokens": args.max_tokens, "reasoning_effort": args.reasoning_effort,
                "max_evals": args.max_evals, "run_dir": str(run_dir)}
    status = "COMPLETE"
    history, last_request_sha256 = [], None
    for step in range(1, args.iterations + 1):
        note = rejection_note(history)
        user = (OBJECTIVE + "\n\n" + note + "Current program:\n```python\n" + best_source + "\n```\n\n"
                + "Evaluator feedback:\n" + best["feedback"])
        request_sha256 = _sha(user.encode())
        row = {"step": step, "packet_seen": PACKET_MARK in user, "request_sha256": request_sha256}
        if request_sha256 == last_request_sha256:
            row["outcome"] = "guard: refusing to resend an identical consecutive prompt"
            trace.append(row)
            status = "GUARD_STOPPED"
            break
        last_request_sha256 = request_sha256
        try:
            content, finish = _chat(args.broker_url, args.model, args.max_tokens, args.reasoning_effort,
                                    [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                                    args.llm_timeout)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            row["outcome"] = f"broker stopped: {exc}"
            trace.append(row)
            status = "BROKER_STOPPED"
            break
        row["finish_reason"] = finish
        try:
            source = preflight_source(content, finish)
        except (SyntaxError, ValueError) as exc:
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
        accepted = result["valid"] == result["instances"] and result["combined_score"] > best["combined_score"]
        row.update({"candidate_hash": result["candidate_hash"], "screen_score": result["combined_score"],
                    "screen_valid": result["valid"], "accepted": accepted})
        if accepted:
            best_source, best = source, result
        else:
            reason = (f"rejected: screen_score {result['combined_score']:.4f} (valid {result['valid']}/"
                      f"{result['instances']}) did not beat {best['combined_score']:.4f}")
            row["outcome"] = reason
            history.append({"step": step, "reason": reason})
        trace.append(row)
    (run_dir / "sequential-trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in trace))
    (run_dir / "verified").mkdir(exist_ok=True)
    (run_dir / "verified" / "best.py").write_text(best_source)
    manifest.update({"status": status, "steps": trace,
                     "mechanism_evidence": {"accepted_steps": [r["step"] for r in trace if r.get("accepted")],
                                            "packet_seen_steps": [r["step"] for r in trace if r["packet_seen"]],
                                            "truncated_steps": [r["step"] for r in trace
                                                                if r.get("finish_reason") in
                                                                ("length", "max_tokens")]}})
    return _finish(manifest, run_dir, verifier, seed_eval, best_source)


def write_first_prompt(capture_dir: Path, out_md: Path, run_dir: Path) -> str:
    """Render the first captured GEPA reflection request verbatim for user approval."""
    for path in sorted(Path(capture_dir).glob("request-*.json")):
        item = json.loads(path.read_text())
        if item["role"] == "gepa_reflection":
            break
    else:
        raise FileNotFoundError("no captured GEPA reflection request")
    body = item["body"]
    messages = body["messages"]
    digest = messages_sha256(messages)
    fence = "`" * 6
    lines = ["# First GEPA proposer prompt (lift-m9-260924)", "",
             "This is the exact `messages` array the GEPA reflection client sends to the local "
             "broker on iteration 1 for the seed program. The broker forwards it unchanged, "
             "adding only transport fields (see `broker-config.json` and the `--dry-run` payload). "
             "It was captured offline from a zero-provider GEPA run with the frozen development set. "
             "Only development data appears; the holdout set is never loaded.", "",
             f"- Messages SHA-256 (canonical JSON, sorted keys, no spaces): `{digest}`",
             f"- Message roles: {[m['role'] for m in messages]}. GEPA sends no separate system "
             "message; the system text is embedded in the user message as GEPA's background.",
             f"- Client request fields: model `{body.get('model')}`, max_tokens `{body.get('max_tokens')}`, "
             f"reasoning_effort `{body.get('reasoning_effort')}`",
             f"- Captured from: `{Path(run_dir).name}` ({path.name})",
             "- A live GEPA run halts before its first model request if these messages hash differently.", ""]
    for i, m in enumerate(messages, 1):
        lines += [f"## Message {i}: {m['role']}", "", fence + "text", m["content"], fence, ""]
    out_md.write_text("\n".join(lines))
    out_md.with_suffix(".sha256").write_text(
        f"{digest}  messages of {out_md.name} (canonical JSON of the messages array)\n")
    return digest


def _arm_ledger_path(bc, engine) -> Path:
    """This arm's own ledger, isolated from every other arm's ledger."""
    base = Path(bc["ledger"])
    return base.with_name(base.stem + f".{engine}" + base.suffix)


def arm_contact_budget(bc, cc, engine) -> tuple[int, int]:
    """(sub_cap, remaining) contacts this arm may use out of the shared pool.

    Each arm gets its own ledger file, so one arm's calls can never drain
    contacts reserved for another (autoresearch/TRACE-AUDIT-260925.md defect 2).
    `remaining` is the shared campaign-config.json/broker-config.json pool
    (bc["max_requests"]) minus whatever every OTHER arm's ledger has already
    recorded; the caller refuses to start when either sub_cap or remaining is 0.
    """
    sub_cap = cc["engines"][engine].get("max_requests")
    if not isinstance(sub_cap, int) or sub_cap < 0:
        raise ValueError(f"campaign-config engines.{engine}.max_requests must be a non-negative integer")
    used_elsewhere = 0
    for other in cc["engines"]:
        if other == engine:
            continue
        path = ROOT / _arm_ledger_path(bc, other)
        if path.is_file():
            used_elsewhere += len(json.loads(path.read_text()).get("attempts", []))
    remaining = max(0, bc["max_requests"] - used_elsewhere)
    return sub_cap, remaining


# ------------------------------------------------------------- live wrapper
def _live(args):
    """Approval check, broker from broker-config.json, then one arm. No hard-coded caps."""
    if not os.environ.get(_load_config(args.broker_config)["api_key_env"]):
        raise SystemExit("provider key must be supplied through the environment")
    digest = check_approval(args.broker_config, args.campaign_config)
    bc, cc = _load_config(args.broker_config), _load_config(args.campaign_config)
    arm = cc["engines"][args.engine]
    sub_cap, remaining = arm_contact_budget(bc, cc, args.engine)
    if sub_cap == 0 or remaining == 0:
        raise SystemExit(f"refusing to start arm {args.engine}: sub-cap {sub_cap} contacts, "
                          f"{remaining} contacts remaining in the shared pool of {bc['max_requests']}")
    arm_max_requests = min(sub_cap, remaining)
    stamp = time.strftime("%y%m%d-%H%M%S")
    run_dir = LIFT_DIR / f"live-{args.engine}-{stamp}"
    broker_log = LIFT_DIR / f"broker-{args.engine}-{stamp}.log"
    if run_dir.exists() or broker_log.exists():
        raise SystemExit("fresh run or broker log path already exists")
    port = cc["broker_port"]
    broker = [sys.executable, "-m", "integrations.research_budget", "serve",
              "--upstream-url", bc["upstream_url"], "--model", bc["model"], "--api-key-env", bc["api_key_env"],
              "--ledger", str(ROOT / _arm_ledger_path(bc, args.engine)), "--max-requests", str(arm_max_requests),
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
        instances, _ = development_from_manifest(ROOT / cc["frozen_manifest"])
        argv = ["--instances", str(instances), "--frozen-manifest", str(ROOT / cc["frozen_manifest"]),
                "--seed", str(ROOT / cc["seed"]), "--run-dir", str(run_dir),
                "--broker-url", f"http://127.0.0.1:{port}/v1", "--model", bc["model"],
                "--max-tokens", str(bc["max_tokens"]), "--reasoning-effort", bc["reasoning_effort"],
                "--iterations", str(arm["iterations"]), "--max-evals", str(arm["max_evals"]),
                "--wall-seconds", str(arm["wall_seconds"]), "--llm-timeout", str(int(bc["timeout"]) + 30),
                "--eval-timeout", str(cc["eval_timeout"]), "--cache-dir", str(ROOT / cc["eval_cache"]),
                "--archive", str(ROOT / cc["archive"]), "--python", str(ROOT / cc["python"]),
                "--evox-switch-interval", str(cc["evox_switch_interval"]),
                "--ledger", str(ROOT / _arm_ledger_path(bc, args.engine))]
        if args.engine == "gepa":
            argv += ["--expected-first-prompt-sha256",
                     (LIFT_DIR / "first-prompt.sha256").read_text().split()[0]]
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
        p.add_argument("--instances", type=Path, default=LIFT_DIR / "frozen" / "development.json")
        p.add_argument("--frozen-manifest", type=Path, default=LIFT_DIR / "frozen" / "manifest.json")
        p.add_argument("--seed", type=Path, default=ROOT / "integrations" / "lift_control_naive.py")
        p.add_argument("--run-dir", required=True, type=Path)
        p.add_argument("--python", type=Path, default=ROOT / ".venv-official" / "bin" / "python")
        p.add_argument("--broker-url", required=True)
        p.add_argument("--model", default="grok-4.7")
        p.add_argument("--iterations", type=int, default=2)
        p.add_argument("--max-tokens", type=int, default=4096)
        p.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh"))
        p.add_argument("--max-evals", type=int, default=64)
        p.add_argument("--wall-seconds", type=int, default=1800)
        p.add_argument("--llm-timeout", type=int, default=240)
        p.add_argument("--eval-timeout", type=int, default=400)
        p.add_argument("--cache-dir", type=Path, default=LIFT_DIR / "eval-cache")
        p.add_argument("--archive", type=Path)
        p.add_argument("--jobs", type=int, default=8)
        p.add_argument("--evox-switch-interval", type=int, default=2)
        p.add_argument("--offline-no-auto-variation", action="store_true")
        p.add_argument("--ledger", type=Path,
                       help="this arm's broker ledger, for the EvoX meta-search share report")
        p.add_argument("--expected-first-prompt-sha256",
                       help="GEPA: halt before the first model request unless its messages hash matches")
    w = sub.add_parser("_gepa_worker")
    for flag in ("seed", "dataset", "run-dir"):
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
    fp.add_argument("--output", type=Path, default=LIFT_DIR / "first-prompt.md")
    for name in ("approval-hash", "check-approval", "live"):
        p = sub.add_parser(name)
        p.add_argument("--broker-config", type=Path, default=LIFT_DIR / "broker-config.json")
        p.add_argument("--campaign-config", type=Path, default=LIFT_DIR / "campaign-config.json")
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
        print(write_first_prompt(args.capture_dir, args.output, args.run_dir))
        return
    if args.action == "check-approval":
        print(check_approval(args.broker_config, args.campaign_config))
        return
    actions = {"run": _launch, "sequential": _sequential, "_gepa_worker": _gepa_worker, "live": _live}
    result = actions[args.action](args)
    keep = ("engine", "status", "research_status", "run_dir", "seed_full", "verified_best_full",
            "mechanism_evidence")
    print(json.dumps({k: result.get(k) for k in keep} if isinstance(result, dict) else result, default=str))


if __name__ == "__main__":
    main()
