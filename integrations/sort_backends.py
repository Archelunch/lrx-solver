"""Run pinned GEPA 0.1.4 and SkyDiscover AdaEvolve/EvoX 0.2.0 on the sort-m9 task.

Version 2 (after attempt 1 found per-state search): 0.2 s CPU per state, a
worst-r uniformity term, the cyclic-sweep control as seed, and live runs under
live-v2-*. The v1 sources are preserved in autoresearch/sort-m9-260925/v1/.

Mirrors integrations/corr_backends.py and reuses integrations/lift_backends.py's
fixed plumbing unchanged (rejection notes, broker chat client, per-arm ledgers
and contact sub-caps, reflection minibatch min(3, n), EvoX strategy evolution
off below 100 iterations, the Seatbelt launcher from official_backends). The
candidate is a program with sort_word(v); the score comes from
integrations/sort_evaluator.py in a trusted coordinator-side service. One
evaluation covers the whole frozen development set (1500 states), so GEPA gets
a single example, as in corr. The packet adds exact-table prefix diagnostics
for at most 3 worst states.

The staged copy of this file runs inside the optimizer sandbox next to staged
copies of lift_backends.py and official_backends.py, so the module top level
imports only the standard library and those two files.
"""
from __future__ import annotations

import argparse
import ast
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
    from integrations import lift_backends as lb
    from integrations import official_backends as ob
except ImportError:  # staged copy inside the optimizer sandbox
    import lift_backends as lb
    import official_backends as ob

ROOT = Path(__file__).resolve().parents[1]
SORT_DIR = ROOT / "autoresearch" / "sort-m9-260925"
TASK = "sort-m9-260925"
PACKET_MARK = "SORT_PACKET_V1"
PACKET_MAX = 2000  # SkyDiscover truncates artifacts at 2000 characters
ENGINES = ("gepa", "adaevolve", "evox")

STRUCTURAL_FACTS = (
    "Exact facts at m=9, r=1..5 (complete BFS tables): the sorting radius equals T_9(n) = 45, 52, 59, "
    "66, 73. The 15 states at distance T are near-reversals: 10 of 15 read 9,8,...,1 cyclically, e.g. "
    "(2,1,0^r,9,8,...,3) for r=1,2,3 and (0^r,9,8,...,1) for r=2,3. d(v) <= min_q d_q(v) + K with "
    "K = 14,15,17,18,20 for r=1..5, where d_q is the (8,r) distance after deleting label q; K is "
    "attained only near the root. No rotation, reflection or complement symmetry preserves d."
)
SYSTEM = (
    "Find a constructive, uniform LRX sorting procedure. Goal: an algorithm that is uniform in r "
    "(and ideally in m) and provably stays within the budget T_m(n) = m(m+1)/2 + (r-1)(m-2) (45 + 7(r-1) "
    "at m=9), with a route whose length can be bounded by an argument. Useful ingredients: sweep "
    "strategies that use zero blocks as buffers, comparison-transfer routes that carry one label "
    "through a block, cycle-based service of labels in cyclic order, choosing the final rotation. "
    "The candidate source must define sort_word(v) -> str. v is a list of length n = m + r holding labels "
    "1..m once (m = max(v)) and r >= 1 zeros; return a word over L, R, X that sorts v to (1, 2, ..., m, "
    "0, ..., 0). L rotates the vector left (the first entry moves to the end), R rotates it right, and X "
    "swaps the first two entries. The trusted evaluator replays the word literally. Each call gets 0.2 s "
    "of CPU time (and module import 0.5 s); any state-space search (BFS, bidirectional BFS, IDA*, beam or "
    "A* search over vectors, or caching such search across calls) times out on almost every state, and a "
    "timeout counts as an unsorted state. Build the word directly from the structure of v. Score: "
    "fraction of development states sorted within T (primary), plus 0.5 times the worst per-r "
    "within-budget rate (so the program must work for every r, not only small r), plus a small term for "
    "low mean excess over the exact distance, minus the fraction not sorted. Stdlib only, at most 64 KiB, "
    "at most 1000 letters per word. Development states are m=9, r=1..5; the holdout has unseen states "
    "and unseen (m, r), so the program must work for any m and r. Misses prove nothing. Do not read "
    "files, the network, or environment variables. " + STRUCTURAL_FACTS
)
OBJECTIVE = (
    "Improve this constructive Python sort_word(v) program (the seed is a cyclic-sweep sorter: it "
    "chooses a target rotation and a cyclic assignment of the interchangeable zeros, gives each entry "
    "a displacement on the universal cover, and sweeps the window swapping pairs that must cross). "
    "Return the entire replacement Python source in one fenced code block, with no prose and no "
    "docstring longer than a few lines. Raise the within-budget rate, first on the worst r, without "
    "search: each state has 0.2 s of CPU. Only development states are shown."
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------- packet
def _worst(rows):
    """Unsorted words first, then over-budget words by overshoot, then other failures, then excess."""
    def key(r):
        if r["status"] == "NOT_SORTED":
            return (0, 0, r["id"])
        if r["valid"] and not r["within"]:
            return (1, -(r["length"] - r["budget"]), r["id"])
        if not r["valid"]:
            return (2, 0, r["id"])
        return (3, -r["excess"], r["id"])
    return sorted(rows, key=key)


def per_r_line(result, label):
    return f"{label} per (m,r) within/states, timeouts, mean excess: " + ", ".join(
        f"{k} {g['within']}/{g['states']} t{g.get('timeouts', 0)} "
        f"e{'n/a' if g['mean_excess'] is None else round(g['mean_excess'], 2)}" for k, g in result["per_r"].items())


def packet(result: dict, best: str, states_by_id=None, tables=None, baseline=None) -> str:
    """Compact development-only feedback: totals, per-r within and timeout counts (this candidate and
    the seed), <= 3 worst states with exact d, T, length and first wrong prefix, structural facts."""
    N = result["states"]
    me = result["mean_excess"]
    head = [f"{PACKET_MARK} (development only; search signal, not proof)",
            f"this candidate: within budget {result['within_budget']}/{N}, worst r {result['worst_r']} at "
            f"{result['min_r_within_rate']:.3f}, sorted {result['valid']}/{N}, timeouts (0.2 s CPU) "
            f"{result['timeouts']}, mean excess {'n/a' if me is None else f'{me:.3f}'}, max excess "
            f"{result['max_excess']}; combined {result['combined_score']:.4f}; best so far: {best}",
            per_r_line(result, "this candidate")] + ([baseline] if baseline else [])
    body = []
    for row in _worst(result["results"])[:3]:
        if row["valid"] and row["within"] and row["excess"] == 0:
            break
        state = (states_by_id or {}).get(row["id"], {})
        v = tuple(state.get("v", ()))
        line = (f"- {row['id']} v={v} T={row['budget']} d={row['d']} {row['status']}"
                + (f" len={row['length']}" if row["length"] is not None else ""))
        if row["status"] == "NOT_SORTED":
            line += f" ends at {tuple(row['final'])}"
        elif not row["valid"]:
            line += f": {str(row.get('failure'))[:160]}"
        word = row.get("word")
        if word and tables is not None and v:
            try:
                t = tables.prefix_trace(state, word)
                off, lost = t["first_off_shortest_path"], t["first_budget_lost"]
                if off:
                    line += f"; leaves every shortest path at step {off['step']} (prefix {off['prefix'][-12:]})"
                if lost:
                    line += f"; T unreachable after step {lost['step']}"
            except KeyError:
                pass
        if word:
            line += f"; word {word[:90]}" + ("..." if len(word) > 90 else "")
        body.append(line)
    tail = [STRUCTURAL_FACTS]
    text = "\n".join(head + body + tail)
    while len(text) > PACKET_MAX and body:
        body.pop()
        text = "\n".join(head + body + tail)
    return text[:PACKET_MAX]


def preflight_source(content, finish_reason=None) -> str:
    """A fenced Python block defining sort_word(v); checked before any evaluation.

    Prose is allowed around the fence(s); the last fenced block that defines
    sort_word(...) wins. Truncated output is never accepted or repaired.
    """
    if finish_reason in ("length", "max_tokens"):
        raise ValueError("proposal was truncated by the model output limit")
    if not isinstance(content, str):
        raise ValueError("proposal had no text content")
    fences = list(re.finditer(r"```(?:python)?\s*\n(.*?)```", content, re.IGNORECASE | re.DOTALL))
    if not fences:
        raise ValueError("proposal must contain a fenced Python source block defining sort_word(v)")
    chosen = None
    for m in fences:
        candidate = m.group(1)
        try:
            tree = ast.parse(candidate)
        except SyntaxError:
            continue
        if any(isinstance(node, ast.FunctionDef) and node.name == "sort_word" for node in tree.body):
            chosen = candidate
    if chosen is None:
        raise ValueError("proposal must define sort_word(v) in a fenced Python source block")
    if len(chosen.encode()) > 65536:
        raise ValueError("proposal exceeds source size cap")
    return chosen


# ------------------------------------------------------ trusted verifier side
def tables_from_manifest(manifest: Path, keys):
    """Exact tables for the development (m, r), sha256-verified, for packet diagnostics only."""
    from integrations.sort_evaluator import Tables

    prov = {(t["m"], t["r"]): t for t in json.loads(Path(manifest).read_text())["tables"]}
    return Tables({k: (ROOT / prov[k]["path"], prov[k]["table_sha256"]) for k in keys})


class SortVerifier:
    """Coordinator-side trusted evaluation. Candidate code runs only in sort_evaluator's sandbox."""

    def __init__(self, states_path, run_dir, *, cache_dir, engine, provenance, max_requests,
                 jobs=8, require_os_sandbox=True, tables=None):
        from integrations.sort_evaluator import guard_not_holdout, load_set

        guard_not_holdout(states_path)
        self.states = load_set(states_path)
        self.by_id = {s["id"]: s for s in self.states}
        self.cache_dir, self.engine, self.provenance = cache_dir, engine, provenance
        self.jobs, self.max_requests, self.tables = jobs, max_requests, tables
        self.require_os_sandbox = require_os_sandbox  # tests only; engines always use Seatbelt
        self.evidence = Path(run_dir) / "verified" / "evaluations"
        self.evidence.mkdir(parents=True)
        self.lock = threading.Lock()
        self.state = {"requests": 0, "evaluations": [], "distinct_source_hashes": [],
                      "best": None, "failures": 0, "states": len(self.states)}
        self.baseline = None  # per-r line of the first (seed) evaluation, repeated in every packet

    def _current_best(self, extra=None):
        """Best over every evaluation on record, recomputed from the manifest (TRACE-AUDIT defect 7)."""
        best = None
        for row in self.state["evaluations"] + ([extra] if extra else []):
            if best is None or row["combined_score"] > best["combined_score"]:
                best = {k: row[k] for k in ("combined_score", "within_budget", "min_r_within_rate", "valid",
                                            "mean_excess", "candidate_hash")}
        return best

    def _best_text(self, best) -> str:
        if not best:
            return "none"
        me = best["mean_excess"]
        return (f"combined {best['combined_score']:.4f} (within {best['within_budget']}/{len(self.states)}, "
                f"worst-r rate {best['min_r_within_rate']:.3f}, mean excess {'n/a' if me is None else f'{me:.3f}'})")

    def evaluate(self, source: str, *, final=False) -> dict:
        from integrations import sort_evaluator as E

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
            res = E.evaluate(path, self.states, jobs=self.jobs, cache_dir=self.cache_dir,
                             require_os_sandbox=self.require_os_sandbox)
            row = {k: res[k] for k in ("combined_score", "within_budget", "min_r_within_rate", "valid", "invalid",
                                       "timeouts", "mean_excess", "cache_hit")}
            row.update(candidate_hash=digest, ordinal=ordinal, final=final)
            best = self._current_best(extra=row)
            self.state["best"] = best
            if self.baseline is None:
                self.baseline = per_r_line(res, "seed")
            feedback = packet(res, self._best_text(best), self.by_id, self.tables, self.baseline)
            summary = {k: res[k] for k in ("combined_score", "within_budget", "within_fraction",
                                           "min_r_within_rate", "worst_r", "valid",
                                           "invalid", "invalid_fraction", "mean_excess", "max_excess",
                                           "timeouts", "incomplete", "per_r", "cache_hit")}
            summary.update(candidate_hash=digest, evaluation_cache_key=res["cache_key"], feedback=feedback)
            artifact = self.evidence / f"result-{ordinal:04d}.json"
            artifact.write_text(json.dumps({"summary": summary, "result": res}, default=str) + "\n")
            summary["evaluation"] = str(artifact)
            row["packet_sha256"] = _sha(feedback.encode())
            self.state["evaluations"].append(row)
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
                    source = json.loads(self.rfile.read(length))["source"]
                    if not isinstance(source, str) or len(source.encode()) > 65536:
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
FIRST_PROMPT_FILES = {"gepa": "first-prompt.sha256", "sequential": "first-prompt-sequential.sha256",
                      "adaevolve": "first-prompt-adaevolve.sha256", "evox": "first-prompt-evox.sha256"}


def first_prompt_mismatch(messages, expected_sha256) -> bool:
    """True only when an expected hash was given and the messages do not match it."""
    return bool(expected_sha256) and lb.messages_sha256(messages) != expected_sha256


def is_solution_request(messages) -> bool:
    """A SkyDiscover program-proposal request: not strategy/variation meta-search
    (ob._evox_call_kind) and not a connectivity probe (it must carry the program)."""
    return bool(messages) and ob._evox_call_kind(messages) == "solution" and "sort_word" in json.dumps(messages)


def verify_first_solution_prompt(ledger_path, expected_sha256):
    """AdaEvolve/EvoX: SkyDiscover's own client has no pre-send hook, so compare the first
    solution request in the arm's own ledger receipts after the run. None when there is
    nothing to check, else (actual_sha256, matches)."""
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


# ------------------------------------------------------------- approval
def approval_material(broker_config: Path, campaign_config: Path) -> dict:
    """Everything a live arm sends or spends, derived from the configs; hashed for approval."""
    from integrations.research_budget import _dry_run_payload
    from integrations.sort_evaluator import CONTRACT, VERSION, evaluator_hash

    bc, cc = lb._load_config(broker_config), lb._load_config(campaign_config)
    _, development = lb.development_from_manifest(ROOT / cc["frozen_manifest"])
    def _hash_of(name):
        path = broker_config.parent / name
        return path.read_text().split()[0] if path.is_file() else None

    return {"broker_config": bc, "campaign_config": cc,
            "first_prompt_sha256": _hash_of(FIRST_PROMPT_FILES["gepa"]),
            "first_prompt_sequential_sha256": _hash_of(FIRST_PROMPT_FILES["sequential"]),
            "first_prompt_adaevolve_sha256": _hash_of(FIRST_PROMPT_FILES["adaevolve"]),
            "first_prompt_evox_sha256": _hash_of(FIRST_PROMPT_FILES["evox"]),
            "upstream_endpoint": bc["upstream_url"].rstrip("/") + "/chat/completions",
            "dry_run_payload": _dry_run_payload(bc), "system_prompt": SYSTEM, "objective": OBJECTIVE,
            "packet_format": {"marker": PACKET_MARK, "max_chars": PACKET_MAX, "scope": "development only"},
            "seed_sha256": _sha((ROOT / cc["seed"]).read_bytes()),
            "frozen_manifest_sha256": _sha((ROOT / cc["frozen_manifest"]).read_bytes()),
            "development_sha256": development,
            "evaluator": {"version": VERSION, "contract": CONTRACT, "hash": evaluator_hash()},
            "sort_backends_sha256": _sha(Path(__file__).read_bytes()),
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
    config["prompt"]["system_message"] = SYSTEM
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
        "    me = out['mean_excess']\n"
        "    metrics = {'combined_score': float(out['combined_score']),\n"
        "               'within_fraction': float(out['within_fraction']),\n"
        "               'invalid_fraction': float(out['invalid_fraction']),\n"
        "               'min_r_within_rate': float(out['min_r_within_rate']),\n"
        "               'mean_excess': float(me) if me is not None else -1.0}\n"
        "    return EvaluationResult(metrics=metrics, artifacts={'feedback': out['feedback']})\n")
    return path


class SortBrokerLM(ob.BrokerLM):
    """GEPA reflection model via the broker; sort preflight and packet receipts."""

    receipts: list
    expected_first_sha256 = None

    @staticmethod
    def _preflight(content, finish_reason):
        preflight_source(content, finish_reason)

    def __call__(self, request):
        messages = [{"role": "user", "content": request}] if isinstance(request, str) else list(request)
        if self.calls == 0 and self.expected_first_sha256 and \
                lb.messages_sha256(messages) != self.expected_first_sha256:
            raise ob.BrokerHalted("first proposer prompt differs from the approved first-prompt.sha256")
        text = request if isinstance(request, str) else json.dumps(request)
        receipt = {"call": self.calls + 1, "packet_seen": PACKET_MARK in text,
                   "request_sha256": _sha(text.encode()), "request_chars": len(text)}
        self.receipts.append(receipt)
        try:
            return super().__call__(request)
        finally:
            receipt["finish_reason"] = self.last_finish_reason


def _gepa_worker(args) -> dict:
    from gepa.optimize_anything import EngineConfig, GEPAConfig, ReflectionConfig, optimize_anything

    train = val = [{"id": "development"}]  # one global pass over all 1500 development states
    lm = SortBrokerLM(args.broker_url, args.model, args.max_tokens, None, args.llm_timeout, args.reasoning_effort)
    lm.receipts = []
    lm.expected_first_sha256 = args.expected_first_prompt_sha256

    def verify(source):
        payload = json.dumps({"source": source}).encode()
        with urlopen(Request(args.verifier_url, payload, {"Content-Type": "application/json"}),
                     timeout=args.eval_timeout) as response:
            return json.load(response)

    def evaluator(candidate, example):
        r = verify(candidate)
        return float(r["combined_score"]), {"within_budget": r["within_budget"], "valid": r["valid"],
                                            "min_r_within_rate": r["min_r_within_rate"],
                                            "mean_excess": r["mean_excess"], "feedback": r["feedback"]}

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
        raise TypeError("GEPA returned a non-source candidate")
    (args.run_dir / "best.py").write_text(best)
    full = verify(best)
    lineage = {k: getattr(result, k, None) for k in ("parents", "val_aggregate_scores", "discovery_eval_counts",
                                                     "total_metric_calls", "num_full_val_evals")}
    candidates = [c if isinstance(c, str) else json.dumps(c) for c in getattr(result, "candidates", [])]
    summary = {"engine": "gepa", "upstream": ob.UPSTREAM["gepa"], "best_path": str(args.run_dir / "best.py"),
               "best_score": full["combined_score"], "best_idx": getattr(result, "best_idx", None),
               "candidate_sha256": [_sha(c.encode()) for c in candidates], "lineage": lineage,
               "reflection_calls": lm.calls, "model_valid_responses": lm.valid_responses,
               "model_preflight_failures": lm.preflight_failures, "reflection_receipts": lm.receipts,
               "final_request": full}
    (args.run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    return summary


def _research_status(seed, best, proposals):
    if best is None:
        return "INCOMPLETE"
    if best["within_budget"] > seed["within_budget"] and best["invalid"] <= seed["invalid"]:
        return "MORE_WITHIN_BUDGET"
    if best["within_budget"] == seed["within_budget"] and best["mean_excess"] is not None and \
            seed["mean_excess"] is not None and best["mean_excess"] < seed["mean_excess"]:
        return "GRADED_PROGRESS"
    return "NO_GAIN" if proposals else "NO_VALID_PROPOSAL"


_RESULT_KEYS = ("combined_score", "within_budget", "min_r_within_rate", "valid", "invalid", "timeouts",
                "mean_excess", "per_r")


def _setup(args, engine):
    provenance = lb._verify_inputs(args.instances.resolve(), args.frozen_manifest.resolve())
    run_dir = args.run_dir.resolve()
    if run_dir.exists():
        raise FileExistsError(run_dir)
    (run_dir / "output" / "tmp").mkdir(parents=True)
    stage = run_dir / "stage"
    stage.mkdir()
    seed = stage / "initial_program.py"
    shutil.copyfile(args.seed, seed)
    provenance = dict(provenance, seed_sha256=_sha(seed.read_bytes()))
    from integrations.sort_evaluator import load_set
    keys = sorted({(s["m"], s["r"]) for s in load_set(args.instances)})
    tables = None if args.no_tables else tables_from_manifest(args.frozen_manifest, keys)
    verifier = SortVerifier(args.instances, run_dir, cache_dir=args.cache_dir, engine=engine,
                            provenance=provenance, max_requests=args.max_evals, jobs=args.jobs, tables=tables)
    (stage / "dataset.json").write_text(json.dumps({"train": ["development"], "val": ["development"]}) + "\n")
    seed_eval = verifier.evaluate(seed.read_text(), final=True)
    return run_dir, stage, seed, verifier, provenance, seed_eval


def _finish(manifest, run_dir, verifier, seed_eval, best_source: str):
    from tools.orchestrator import trusted_status

    final = verifier.evaluate(best_source, final=True)
    seed_hash = seed_eval["candidate_hash"]
    st = verifier.state
    manifest.update({
        "candidate_evaluations": {k: st[k] for k in ("requests", "failures", "best", "states")},
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

    args.broker_url = ob._broker_url(args.broker_url)
    python = args.python.absolute()
    upstream = ob._installed_identity(python, args.engine)
    run_dir, stage, seed, verifier, provenance, seed_eval = _setup(args, args.engine)
    shutil.copyfile(Path(ob.__file__), stage / "official_backends.py")
    shutil.copyfile(Path(lb.__file__), stage / "lift_backends.py")
    shutil.copyfile(Path(__file__), stage / "sort_official_worker.py")
    server, verifier_url = verifier.serve()
    env = ob._worker_environment(stage, run_dir, args.broker_url)
    if args.engine == "gepa":
        command = [str(python), str(stage / "sort_official_worker.py"), "_gepa_worker",
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
    manifest = {"engine": args.engine, "task": TASK, "upstream": upstream, **provenance,
                "seed_result": {k: seed_eval[k] for k in _RESULT_KEYS},
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
    if args.engine in ("adaevolve", "evox"):
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
    best = (run_dir / "output" / "best.py" if args.engine == "gepa"
            else run_dir / "output" / "sky" / "best" / "best_program.py")
    trusted_best = ob._snapshot_best(best, run_dir / "output", run_dir / "verified")
    manifest["status"] = "COMPLETE"
    return _finish(manifest, run_dir, verifier, seed_eval, trusted_best.read_text())


# ------------------------------------------------------ sequential refinement
def _sequential(args) -> dict:
    """Control arm: same broker, system prompt and packet; greedy accept on combined_score."""
    args.broker_url = ob._broker_url(args.broker_url)
    run_dir, stage, seed, verifier, provenance, seed_eval = _setup(args, "sequential")
    best_source, best = seed.read_text(), seed_eval
    trace = []
    manifest = {"engine": "sequential", "task": TASK, **provenance, "broker_url": args.broker_url,
                "model": args.model, "iterations": args.iterations, "max_tokens": args.max_tokens,
                "reasoning_effort": args.reasoning_effort, "max_evals": args.max_evals, "run_dir": str(run_dir)}
    status = "COMPLETE"
    history, last_request_sha256 = [], None
    for step in range(1, args.iterations + 1):
        user = (OBJECTIVE + "\n\n" + lb.rejection_note(history) + "Current program:\n```python\n" + best_source
                + "\n```\n\n" + "Evaluator feedback:\n" + best["feedback"])
        request_sha256 = _sha(user.encode())
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        row = {"step": step, "packet_seen": PACKET_MARK in user, "request_sha256": request_sha256}
        if step == 1 and first_prompt_mismatch(messages, args.expected_first_prompt_sha256):
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
        accepted = result["combined_score"] > best["combined_score"]
        row.update({"candidate_hash": result["candidate_hash"], "score": result["combined_score"],
                    "within_budget": result["within_budget"], "accepted": accepted})
        if accepted:
            best_source, best = source, result
        else:
            reason = (f"rejected: combined {result['combined_score']:.4f} (within {result['within_budget']}, "
                      f"invalid {result['invalid']}) did not beat {best['combined_score']:.4f}")
            row["outcome"] = reason
            history.append({"step": step, "reason": reason})
        trace.append(row)
    (run_dir / "sequential-trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in trace))
    (run_dir / "verified").mkdir(exist_ok=True)
    (run_dir / "verified" / "best.py").write_text(best_source)
    manifest.update({"status": status, "steps": trace,
                     "mechanism_evidence": {"accepted_steps": [r["step"] for r in trace if r.get("accepted")],
                                            "packet_seen_steps": [r["step"] for r in trace if r["packet_seen"]],
                                            "truncated_steps": [r["step"] for r in trace if r.get("finish_reason")
                                                                in ("length", "max_tokens")]}})
    return _finish(manifest, run_dir, verifier, seed_eval, best_source)


def write_first_prompt(capture_dir: Path, out_md: Path, run_dir: Path, engine: str = "gepa") -> str:
    """Render an arm's first captured proposer request verbatim for user approval.

    GEPA and sequential are matched by our client's role header and guarded before
    sending; AdaEvolve/EvoX are matched by content (is_solution_request) and checked
    after the run from the arm's ledger receipts.
    """
    role = {"gepa": "gepa_reflection", "sequential": "sequential_refinement"}.get(engine)
    for path in sorted(Path(capture_dir).glob("request-*.json")):
        item = json.loads(path.read_text())
        if (item["role"] == role) if role else is_solution_request(item["body"].get("messages")):
            break
    else:
        raise FileNotFoundError(f"no captured first {engine} proposer request")
    body = item["body"]
    messages = body["messages"]
    digest = lb.messages_sha256(messages)
    fence = "`" * 6
    when = ("A live run halts before its first model request if these messages hash differently."
            if role else "A live run is marked FIRST_PROMPT_MISMATCH and fails if its first solution request "
                         "in the arm's ledger receipts hashes differently (SkyDiscover has no pre-send hook).")
    lines = [f"# First {engine} proposer prompt ({TASK}, sort-contract-2)", "",
             f"This is the exact `messages` array the {engine} arm sends to the local broker for its first "
             "program proposal on the seed, captured offline from a zero-provider run through the mock with the "
             "frozen development set. Only development states appear; the holdout set is never loaded.", "",
             f"- Messages SHA-256 (canonical JSON, sorted keys, no spaces): `{digest}`",
             f"- Message roles: {[m['role'] for m in messages]}",
             f"- Client request fields: model `{body.get('model')}`, max_tokens `{body.get('max_tokens')}`, "
             f"reasoning_effort `{body.get('reasoning_effort')}`",
             f"- Captured from: `{Path(run_dir).name}` ({path.name})", f"- {when}", ""]
    for i, m in enumerate(messages, 1):
        lines += [f"## Message {i}: {m['role']}", "", fence + "text", m["content"], fence, ""]
    out_md.write_text("\n".join(lines))
    out_md.with_suffix(".sha256").write_text(
        f"{digest}  messages of {out_md.name} (canonical JSON of the messages array)\n")
    return digest


# ------------------------------------------------------------- live wrapper
def _live(args):
    """Approval check, broker from broker-config.json, then one arm with its own ledger and sub-cap."""
    if not os.environ.get(lb._load_config(args.broker_config)["api_key_env"]):
        raise SystemExit("provider key must be supplied through the environment")
    digest = check_approval(args.broker_config, args.campaign_config)
    bc, cc = lb._load_config(args.broker_config), lb._load_config(args.campaign_config)
    arm = cc["engines"][args.engine]
    sub_cap, remaining = lb.arm_contact_budget(bc, cc, args.engine)
    if sub_cap == 0 or remaining == 0:
        raise SystemExit(f"refusing to start arm {args.engine}: sub-cap {sub_cap} contacts, "
                         f"{remaining} contacts remaining in the shared pool of {bc['max_requests']}")
    stamp = time.strftime("%y%m%d-%H%M%S")
    run_dir = SORT_DIR / f"live-v2-{args.engine}-{stamp}"  # v2: 0.2 s CPU contract (sort-eval-2)
    broker_log = SORT_DIR / f"broker-v2-{args.engine}-{stamp}.log"
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
        instances, _ = lb.development_from_manifest(ROOT / cc["frozen_manifest"])
        argv = ["--instances", str(instances), "--frozen-manifest", str(ROOT / cc["frozen_manifest"]),
                "--seed", str(ROOT / cc["seed"]), "--run-dir", str(run_dir),
                "--broker-url", f"http://127.0.0.1:{port}/v1", "--model", bc["model"],
                "--max-tokens", str(bc["max_tokens"]), "--reasoning-effort", bc["reasoning_effort"],
                "--iterations", str(arm["iterations"]), "--max-evals", str(arm["max_evals"]),
                "--wall-seconds", str(arm["wall_seconds"]), "--llm-timeout", str(int(bc["timeout"]) + 30),
                "--eval-timeout", str(cc["eval_timeout"]), "--cache-dir", str(ROOT / cc["eval_cache"]),
                "--python", str(ROOT / cc["python"]), "--evox-switch-interval", str(cc["evox_switch_interval"]),
                "--ledger", ledger]
        first = SORT_DIR / FIRST_PROMPT_FILES[args.engine]
        if first.is_file():  # soft-optional: a missing file means no guard, never a crash
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
        p.add_argument("--instances", type=Path, default=SORT_DIR / "frozen" / "development.json")
        p.add_argument("--frozen-manifest", type=Path, default=SORT_DIR / "frozen" / "manifest.json")
        p.add_argument("--seed", type=Path, default=ROOT / "integrations" / "sort_control_sweep.py")
        p.add_argument("--run-dir", required=True, type=Path)
        p.add_argument("--python", type=Path, default=ROOT / ".venv-official" / "bin" / "python")
        p.add_argument("--broker-url", required=True)
        p.add_argument("--model", default="gemini-3.8-flash")
        p.add_argument("--iterations", type=int, default=2)
        p.add_argument("--max-tokens", type=int, default=8192)
        p.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh"))
        p.add_argument("--max-evals", type=int, default=64)
        p.add_argument("--wall-seconds", type=int, default=1800)
        p.add_argument("--llm-timeout", type=int, default=240)
        p.add_argument("--eval-timeout", type=int, default=900)
        p.add_argument("--cache-dir", type=Path, default=SORT_DIR / "eval-cache")
        p.add_argument("--jobs", type=int, default=8)
        p.add_argument("--no-tables", action="store_true", help="omit exact-table prefix diagnostics")
        p.add_argument("--evox-switch-interval", type=int, default=2)
        p.add_argument("--offline-no-auto-variation", action="store_true")
        p.add_argument("--ledger", type=Path, help="this arm's broker ledger, for the EvoX meta-search share")
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
    fp.add_argument("--engine", default="gepa", choices=ENGINES + ("sequential",))
    fp.add_argument("--output", type=Path, help="default first-prompt.md (gepa) or first-prompt-<engine>.md")
    for name in ("approval-hash", "check-approval", "live"):
        p = sub.add_parser(name)
        p.add_argument("--broker-config", type=Path, default=SORT_DIR / "broker-config.json")
        p.add_argument("--campaign-config", type=Path, default=SORT_DIR / "campaign-config.json")
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
        output = args.output or SORT_DIR / (FIRST_PROMPT_FILES[args.engine][:-len(".sha256")] + ".md")
        print(write_first_prompt(args.capture_dir, output, args.run_dir, args.engine))
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
