"""Run pinned GEPA 0.1.4 and SkyDiscover AdaEvolve/EvoX 0.2.0 on the corr-cert task.

Reuses the official-integration launcher pieces (integrations/official_backends.py,
unchanged): the Seatbelt-confined optimizer process, the broker-only model
client, the installed-identity check, the best-program snapshot, and the
mechanism evidence. Candidate here is a program with coefficients(m); the
score comes from integrations/corr_evaluator.py in a trusted coordinator-side
service; the feedback is a compact development-only packet. Sequential
refinement uses the same broker, prompt and packet with no engine.

Unlike the lift task, evaluating a corr-cert candidate over the whole frozen
development m-set (m=4..12) is cheap (well under a second, see TASK.md's
"Evaluation cost note"), so there is no staged screen/full split here: every
candidate gets a single full development evaluation.

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
CORR_DIR = ROOT / "autoresearch" / "corr-cert-260924"
PACKET_MARK = "CORR_PACKET_V1"
PACKET_MAX = 2000  # SkyDiscover truncates artifacts at 2000 characters
ENGINES = ("gepa", "adaevolve", "evox")

STRUCTURAL_REMINDER = (
    "LP optimum is 0 for every m; E=0 only at the reversal orders p_i = -i mod m; forced "
    "tight rows at q = m-(b-a) and triple rows at (m-(b-a), m-(c-b)); linear potentials "
    "alpha=xq+c1, beta=xt+c2, gamma=-xs+c3 satisfy (5) iff c1+c2+c3<=0 and c1+c2+c3+xm<=0."
)

# Exact epsilon=0 certificates, m=4 (Q=1, no triple terms) and m=5 (Q=1, 16 nonzero triple
# coefficients, all +-5, in width-2 windows of q). From certs-exact/m4.json, m5.json.
WORKED_EXAMPLES = (
    "Two exact epsilon=0 certificates, printed compactly (indices a<b<...<m-1; mu_a and "
    "alpha/beta/gamma[a,b,c] are lists over q=1..m-1; a triple/pair not listed is all zero):\n"
    "m=4, Q=1: lambda (0,1)=12 (0,2)=4 (0,3)=0 (1,2)=-24 (1,3)=-12 (2,3)=-20; "
    "mu_0=[-8,-4,0] mu_1=[-4,0,4] mu_2=[4,0,-4] mu_3=[0,-4,-8]; all alpha/beta/gamma=0 "
    "(pure linear potentials, no triple terms needed at m=4).\n"
    "m=5, Q=1: lambda (0,1)=25 (0,2)=20 (0,3)=15 (0,4)=0 (1,2)=-15 (1,3)=0 (1,4)=-5 "
    "(2,3)=-35 (2,4)=-20 (3,4)=-35; mu_0=[-14,-18,3,4] mu_1=[-17,-9,-16,2] mu_2=[-10,0,0,-10] "
    "mu_3=[2,-16,-9,-17] mu_4=[4,3,-18,-14]; nonzero triples (16 nonzero entries, all +-5, "
    "each a width-2 run of consecutive q): "
    "(0,1,2) alpha=[0,-5,-5,0] beta=[0,0,0,5] gamma=[0,0,-5,0]; "
    "(0,1,4) alpha=[-5,-5,0,0] beta=[0,0,0,-5] gamma=[0,0,5,0]; "
    "(0,3,4) alpha=[0,0,0,-5] beta=[-5,-5,0,0] gamma=[0,0,5,0]; "
    "(2,3,4) alpha=[0,0,0,5] beta=[0,-5,-5,0] gamma=[0,0,-5,0]."
)

# From the deterministic ansatz control (autoresearch/corr-cert-260924/REPORT.md, step 4):
# low-degree polynomial+step families fit m=4..8 exactly but fail on unseen m. Given as
# negative results, not as a hint to imitate; do not just widen the same ansatz.
RESIDUAL_FACTS = (
    "A deterministic control already tried polynomial coefficients: degree<=3 polynomials in "
    "(a,b,c,m) plus step/indicator terms at the kappa thresholds, and q times those steps, fit "
    "m=4..8 exactly but failed at the first untried m=9 (about 1200 violated rows). The "
    "bottleneck is triples with a unit gap (b-a==1 or c-b==1); freeing only those triples' "
    "coefficients from the polynomial made the fit exact through m=10, so unit-gap triples "
    "need dependence the low-degree polynomials could not express. In the infeasibility "
    "structure, about 60% of the violation mass sits on wrapping rows (q+t>m) and about a "
    "third at the equality-order row q=m-(b-a); the heaviest gap classes are (b-a,c-b) in "
    "{(1,1),(1,2),(2,1),(1,3)}. This does not prescribe a fix; possibilities worth exploring "
    "include triple potentials depending on min/max of the gaps, floor/mod expressions, or "
    "piecewise definitions with breakpoints tied to both q and m-q. Every known epsilon=0 "
    "certificate is tight at the reversal-order rows q=m-(b-a) and (m-(b-a), m-(c-b))."
)

SYSTEM = (
    "Find universal coefficients for the Theorem 3 correlation certificate (THEOREM.md). "
    "The candidate source must define coefficients(m) -> dict returning the JSON-safe "
    "encoding: {'m': m, 'Q': positive int, 'lambda': {'a,b': int}, 'mu': {'a': [int]*(m-1)}, "
    "'alpha'/'beta'/'gamma': {'a,b,c': [int]*(m-1)}} with comma-joined decimal keys, a<b or "
    "a<b<c, and mu[a] indexed q=1..m-1. All values must be exact Python ints. The source must "
    "be at most 64 KiB, use the standard library only, and finish each m within 10 seconds. "
    "The trusted evaluator decodes this into corrcert.py's cert dict and calls "
    "corrcert.check_certificate(m, cert) exactly: it passes iff every triple condition (5) and "
    "pair condition (6) holds and epsilon < 1. Misses prove nothing about any m. " + STRUCTURAL_REMINDER +
    "\n" + WORKED_EXAMPLES + "\n" + RESIDUAL_FACTS +
    " coefficients(m) may compute its output algorithmically for the given m (loops, or a "
    "small exact linear solve restricted to the known-tight rows, are fine); it must stay "
    "standard-library and finish within 10 seconds per m regardless of method. A construction "
    "with a human-checkable argument for why it holds for every m is worth more than a lookup "
    "table over development m; the holdout set tests m your program has never seen. "
    "Do not read files, the network, or environment variables."
)
OBJECTIVE = (
    "Improve this executable Python coefficients(m) program. Return the entire replacement "
    "Python source in one fenced code block. Maximize the number of development m in 4..12 "
    "that pass corrcert.check_certificate exactly, then reduce the exact violation magnitude "
    "on m that fail. Only development instances are shown; a program that is uniform in m is "
    "far more valuable than one hard-coded per m."
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


# ------------------------------------------------------------------- packet
def packet(result: dict, best: str) -> str:
    """Compact development-only feedback: per failing m, up to 3 worst violated
    constraints plus kappa at pair violations, epsilon, and the structural reminder."""
    from integrations.corr_task import corrcert

    n = len(result["m_values"])
    head = [f"{PACKET_MARK} (development only; search signal, not proof)",
            f"this candidate: {result['passes']}/{n} m passing, "
            f"violation_sum {float(Fr(result['violation_sum'])):.3f}; best so far: {best}"]
    body = []
    for row in result["results"]:
        if row["passed"]:
            continue
        m = row["m"]
        body.append(f"- m={m} {row['status']}: epsilon={row['epsilon']}, failure={row.get('failure')}")
        for v in row["violations"][:3]:
            kind = v[0]
            if kind == "triple5":
                _, a, b, c, q, t, slack = v
                wrap = "wrap" if q + t > m else "nonwrap"
                body.append(f"  triple5 (a,b,c)=({a},{b},{c}) gaps=(b-a={b - a},c-b={c - b}) "
                            f"q={q} t={t} {wrap} slack={slack}")
            elif kind == "pair6":
                _, a, b, _c, q, _t, slack = v
                kappa = corrcert.kappa(m, a, b, q)
                body.append(f"  pair6 (a,b)=({a},{b}) gap=(b-a={b - a}) q={q} slack={slack} "
                            f"kappa_ab(q)={kappa}")
            else:
                body.append(f"  {v}")
    tail = [STRUCTURAL_REMINDER]
    text = "\n".join(head + body + tail)
    while len(text) > PACKET_MAX and body:
        body.pop()
        text = "\n".join(head + body + tail)
    return text[:PACKET_MAX]


def preflight_source(content, finish_reason=None) -> str:
    """A fenced Python block defining coefficients(m); checked before any evaluation.

    Prose is allowed before/after the fence(s). With multiple fenced blocks, the
    last one that defines coefficients(...) is used (models sometimes show scratch
    work or an earlier draft first). Truncated output is never accepted or
    repaired: that check runs first and short-circuits everything below.
    """
    if finish_reason in ("length", "max_tokens"):
        raise ValueError("proposal was truncated by the model output limit")
    if not isinstance(content, str):
        raise ValueError("proposal had no text content")
    fences = list(re.finditer(r"```(?:python)?\s*\n(.*?)```", content, re.IGNORECASE | re.DOTALL))
    if not fences:
        raise ValueError("proposal must contain a fenced Python source block defining coefficients(m)")
    chosen = None
    for m in fences:
        candidate = m.group(1)
        try:
            tree = ast.parse(candidate)
        except SyntaxError:
            continue
        if any(isinstance(node, ast.FunctionDef) and node.name == "coefficients" for node in tree.body):
            chosen = candidate  # keep scanning; last matching fence wins
    if chosen is None:
        raise ValueError("proposal must define coefficients(m) in a fenced Python source block")
    if len(chosen.encode()) > 65536:
        raise ValueError("proposal exceeds source size cap")
    return chosen


# ------------------------------------------------------ trusted verifier side
class CorrVerifier:
    """Coordinator-side trusted evaluation. Candidate code runs only in corr_evaluator's sandbox."""

    def __init__(self, m_set_path, run_dir, *, cache_dir, engine, provenance, max_requests,
                 jobs=4, timeout=10.0, require_os_sandbox=True):
        from integrations.corr_evaluator import load_instances

        self.m_values = load_instances(m_set_path)
        self.cache_dir = cache_dir
        self.engine, self.provenance, self.jobs, self.timeout = engine, provenance, jobs, timeout
        self.max_requests = max_requests
        self.require_os_sandbox = require_os_sandbox  # tests only; engines always use Seatbelt
        self.evidence = Path(run_dir) / "verified" / "evaluations"
        self.evidence.mkdir(parents=True)
        self.lock = threading.Lock()
        self.state = {"requests": 0, "evaluations": [], "distinct_source_hashes": [],
                      "best": None, "failures": 0, "m_values": self.m_values}

    def _best_text(self) -> str:
        b = self.state["best"]
        return f"{b['passes']}/{len(self.m_values)} passing, violation_sum {b['violation_sum']}" if b else "none"

    def evaluate(self, source: str, *, final=False) -> dict:
        from integrations import corr_evaluator as E

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
            res = E.evaluate(path, self.m_values, timeout=self.timeout, jobs=self.jobs,
                             cache_dir=self.cache_dir, require_os_sandbox=self.require_os_sandbox)
            best = self.state["best"]
            if best is None or res["combined_score"] > best["combined_score"]:
                self.state["best"] = {"combined_score": res["combined_score"], "passes": res["passes"],
                                      "violation_sum": res["violation_sum"], "source_sha256": digest}
            feedback = packet(res, self._best_text())
            summary = {"combined_score": res["combined_score"], "passes": res["passes"],
                       "violation_sum": res["violation_sum"], "m_values": res["m_values"],
                       "passed_m": sorted(row["m"] for row in res["results"] if row["passed"]),
                       "invalid": res["invalid"], "timeouts": res["timeouts"],
                       "candidate_hash": digest, "cache_hit": res["cache_hit"],
                       "evaluation_cache_key": res["cache_key"], "feedback": feedback}
            artifact = self.evidence / f"result-{ordinal:04d}.json"
            artifact.write_text(json.dumps({"summary": summary, "result": res}, default=str) + "\n")
            summary["evaluation"] = str(artifact)
            self.state["evaluations"].append({k: summary[k] for k in (
                "candidate_hash", "combined_score", "passes", "invalid", "cache_hit")} |
                {"ordinal": ordinal, "packet_sha256": _sha(feedback.encode()), "final": final})
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
                    source = payload["source"]
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


# ------------------------------------------------------------- inputs, approval
def _load_config(path):
    return json.loads(Path(path).read_text())


def _verify_inputs(m_set: Path, manifest: Path) -> dict:
    from tools.orchestrator import trusted_status

    trust = trusted_status()
    if not trust["ok"]:
        raise RuntimeError(f"trusted core lock mismatch: {trust}")
    if m_set.name != "development.json" or "holdout" in str(m_set):
        raise ValueError("engines may load only the frozen development m-set, never holdout")
    frozen = json.loads(manifest.read_text())
    if frozen.get("files", {}).get("development.json") != _sha(m_set.read_bytes()):
        raise RuntimeError("frozen development hash mismatch")
    return {"trusted_status": trust, "frozen_manifest": str(manifest),
            "frozen_manifest_sha256": _sha(manifest.read_bytes()),
            "development_sha256": _sha(m_set.read_bytes())}


def development_from_manifest(manifest: Path) -> tuple[Path, str]:
    """The development m-set named by the frozen manifest, with its recorded hash."""
    digest = json.loads(Path(manifest).read_text())["files"]["development.json"]
    path = Path(manifest).parent / "development.json"
    if _sha(path.read_bytes()) != digest:
        raise RuntimeError("frozen development hash mismatch")
    return path, digest


def worked_examples_from_manifest(manifest: Path) -> list[int]:
    """The m values SYSTEM already gives away verbatim as worked examples (WORKED_EXAMPLES).

    A finalist "passing" one of these proves nothing: it can be had by copying
    the prompt. Absent for other tasks' manifests, so this defaults to [].
    """
    return sorted(json.loads(Path(manifest).read_text()).get("worked_examples", []))


def messages_sha256(messages) -> str:
    return _sha(_canonical(messages).encode())


def first_prompt_mismatch(messages, expected_sha256) -> bool:
    """True only when an expected hash was given and the messages don't match it.

    No expected hash (not yet captured/approved) means nothing to check.
    """
    return bool(expected_sha256) and messages_sha256(messages) != expected_sha256


def _is_corr_solution_request(messages) -> bool:
    """A real coefficients(m) proposal request, not a bare connectivity probe.

    ob._evox_call_kind only recognizes strategy/variation meta-search
    positively and defaults everything else (including a probe like "ping" or
    a downstream-context summary request, neither of which ask for a
    program) to "solution" -- a real gap found while wiring this guard for
    the sort task, whose own solution classifier requires its task's program
    marker for the same reason. Every captured real corr solution_diff
    request contains "coefficients" (corr's required candidate function
    name, per SYSTEM); no probe does.
    """
    return ob._evox_call_kind(messages) == "solution" and \
        "coefficients" in json.dumps(messages).lower()


def verify_first_solution_prompt(ledger_path, expected_sha256):
    """Compare AdaEvolve/EvoX's first solution-proposal prompt against an approved hash.

    Unlike GEPA (CorrBrokerLM.__call__ checks the messages before sending),
    SkyDiscover's own LLM client never passes through our Python client, so
    there is no pre-send interception point; this checks the arm's own
    broker ledger receipts after the run instead. Returns None when there is
    nothing to check (no ledger or no expected hash given), else
    (actual_sha256, matches: bool) for the first receipt that is a real
    coefficients(m) proposal (_is_corr_solution_request), not meta-search or
    a bare connectivity probe.
    """
    if not ledger_path or not expected_sha256:
        return None
    receipts_dir = Path(ledger_path).with_suffix(Path(ledger_path).suffix + ".receipts")
    if not receipts_dir.is_dir():
        return None
    for path in sorted(receipts_dir.glob("attempt-*.json")):
        try:
            receipt = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        payload = receipt.get("forwarded_request_payload") or receipt.get("request_payload") or {}
        messages = payload.get("messages", [])
        if messages and _is_corr_solution_request(messages):
            actual = messages_sha256(messages)
            return actual, actual == expected_sha256
    return None


def approval_material(broker_config: Path, campaign_config: Path) -> dict:
    """Everything a live arm sends or spends, derived from the configs; hashed for approval."""
    from integrations.corr_evaluator import CONTRACT, VERSION
    from integrations.research_budget import _dry_run_payload

    bc, cc = _load_config(broker_config), _load_config(campaign_config)
    _, development = development_from_manifest(ROOT / cc["frozen_manifest"])

    def _hash_of(name):
        path = broker_config.parent / name
        return path.read_text().split()[0] if path.is_file() else None

    return {"broker_config": bc, "campaign_config": cc,
            "first_prompt_sha256": _hash_of("first-prompt.sha256"),
            "first_prompt_sequential_sha256": _hash_of("first-prompt-sequential.sha256"),
            "first_prompt_adaevolve_sha256": _hash_of("first-prompt-adaevolve.sha256"),
            "first_prompt_evox_sha256": _hash_of("first-prompt-evox.sha256"),
            "upstream_endpoint": bc["upstream_url"].rstrip("/") + "/chat/completions",
            "dry_run_payload": _dry_run_payload(bc), "system_prompt": SYSTEM, "objective": OBJECTIVE,
            "packet_format": {"marker": PACKET_MARK, "max_chars": PACKET_MAX, "scope": "development only"},
            "seed_sha256": _sha((ROOT / cc["seed"]).read_bytes()),
            "frozen_manifest_sha256": _sha((ROOT / cc["frozen_manifest"]).read_bytes()),
            "development_sha256": development,
            "evaluator": {"version": VERSION, "contract": CONTRACT},
            "corr_backends_sha256": _sha(Path(__file__).read_bytes())}


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
        "from fractions import Fraction\nfrom pathlib import Path\nimport json\n"
        "from urllib.request import Request, urlopen\n"
        "from skydiscover.optimize.evaluation.evaluation_result import EvaluationResult\n"
        "def evaluate(program_path):\n"
        "    source = Path(program_path).read_text(encoding='utf-8')\n"
        "    payload = json.dumps({'source': source}).encode('utf-8')\n"
        f"    req = Request({verifier_url!r}, payload, {{'Content-Type': 'application/json'}})\n"
        f"    with urlopen(req, timeout={timeout}) as response:\n"
        "        out = json.load(response)\n"
        "    metrics = {'combined_score': float(out['combined_score']), 'passes': float(out['passes']),\n"
        "               'violation_sum': float(Fraction(out['violation_sum']))}\n"
        "    return EvaluationResult(metrics=metrics, artifacts={'feedback': out['feedback']})\n")
    return path


class CorrBrokerLM(ob.BrokerLM):
    """GEPA reflection model via the broker; corr-cert preflight and packet receipts."""

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
    """GEPA's reflection minibatch, capped at the train set size (never oversample a small set).

    The corr-cert task has exactly one "example" (a single global pass over the
    whole development set), so this must be 1, not GEPA's library default of 3
    (autoresearch/TRACE-AUDIT-260925.md defect 5: an unset minibatch silently
    tripled every packet and metric-call cost).
    """
    return min(3, len(train))


def gepa_metric_calls_per_proposal(minibatch, val) -> int:
    """Metric calls one proposal costs: minibatch eval + reflection re-eval + valset eval."""
    return 2 * minibatch + len(val)


def _gepa_worker(args) -> dict:
    from gepa.optimize_anything import EngineConfig, GEPAConfig, ReflectionConfig, optimize_anything

    # Scoring here is a single global pass over the whole development set (no
    # per-instance decomposition, unlike the lift task's per-parent screen), so
    # GEPA gets exactly one "example": evaluating a candidate means evaluating
    # it against every development m at once.
    train = val = [{"id": "development"}]
    lm = CorrBrokerLM(args.broker_url, args.model, args.max_tokens, None, args.llm_timeout,
                      args.reasoning_effort)
    lm.receipts = []
    lm.expected_first_sha256 = args.expected_first_prompt_sha256

    def verify(source):
        payload = json.dumps({"source": source}).encode()
        with urlopen(Request(args.verifier_url, payload, {"Content-Type": "application/json"}),
                     timeout=args.eval_timeout) as response:
            return json.load(response)

    def evaluator(candidate, example):
        r = verify(candidate)
        return float(r["combined_score"]), {
            "passes": r["passes"], "violation_sum": r["violation_sum"], "feedback": r["feedback"]}

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
               "best_score": full["combined_score"], "best_idx": getattr(result, "best_idx", None),
               "candidate_sha256": [_sha(c.encode()) for c in candidates], "lineage": lineage,
               "reflection_calls": lm.calls, "reflection_batch_calls": lm.calls,
               "model_valid_responses": lm.valid_responses,
               "model_preflight_failures": lm.preflight_failures, "mandatory_hard_case_ids": [],
               "reflection_receipts": lm.receipts, "final_request": full}
    (args.run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    return summary


def _research_status(seed_result, best_result, valid_proposals, worked_examples=()):
    """NEW_CERTIFICATES requires an m the finalist passes that neither the seed nor
    SYSTEM's worked examples (m=4, m=5, verbatim certificates) already give away
    (autoresearch/TRACE-AUDIT-260925.md defect 8: every arm trivially passes m=4/5
    by copying the prompt, which is not research progress).
    """
    if best_result is None:
        return "INCOMPLETE"
    novel = set(best_result.get("passed_m", [])) - set(seed_result.get("passed_m", [])) - set(worked_examples)
    if novel:
        return "NEW_CERTIFICATES"
    if best_result["passes"] == seed_result["passes"] and \
            Fr(best_result["violation_sum"]) < Fr(seed_result["violation_sum"]):
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
    verifier = CorrVerifier(args.instances, run_dir, cache_dir=args.cache_dir,
                            engine=engine, provenance=provenance, max_requests=args.max_evals,
                            jobs=args.jobs)
    (stage / "dataset.json").write_text(json.dumps({"m_values": verifier.m_values}) + "\n")
    seed_eval = verifier.evaluate(seed.read_text(), final=True)
    return run_dir, stage, seed, verifier, provenance, seed_eval


def _finish(manifest, run_dir, verifier, seed_eval, best_source: str):
    from tools.orchestrator import trusted_status

    final = verifier.evaluate(best_source, final=True)
    seed_hash = seed_eval["candidate_hash"]
    st = verifier.state
    worked_examples = worked_examples_from_manifest(manifest["frozen_manifest"]) \
        if manifest.get("frozen_manifest") else []
    manifest.update({
        "candidate_evaluations": {k: st[k] for k in ("requests", "failures", "best", "m_values")},
        "evaluation_trace": st["evaluations"],
        "proposal_hashes": [h for h in st["distinct_source_hashes"] if h != seed_hash],
        "seed_result": {k: seed_eval[k] for k in ("passes", "violation_sum", "combined_score", "passed_m")},
        "verified_best_hash": final["candidate_hash"],
        "verified_best_result": {k: final[k] for k in
                                 ("passes", "violation_sum", "combined_score", "passed_m")},
        "worked_examples": worked_examples,
        "trusted_status_after": trusted_status()})
    manifest["research_status"] = _research_status(manifest["seed_result"], manifest["verified_best_result"],
                                                   manifest["proposal_hashes"], worked_examples)
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    return manifest


def _launch(args) -> dict:
    from integrations.program_sandbox import sandbox_command, sandbox_profile

    args.broker_url = ob._broker_url(args.broker_url)
    python = args.python.absolute()
    upstream = ob._installed_identity(python, args.engine)
    run_dir, stage, seed, verifier, provenance, seed_eval = _setup(args, args.engine)
    shutil.copyfile(Path(ob.__file__), stage / "official_backends.py")
    shutil.copyfile(Path(__file__), stage / "corr_official_worker.py")
    server, verifier_url = verifier.serve()
    env = ob._worker_environment(stage, run_dir, args.broker_url)
    if args.engine == "gepa":
        command = [str(python), str(stage / "corr_official_worker.py"), "_gepa_worker",
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
    manifest = {"engine": args.engine, "task": "corr-cert-260924", "upstream": upstream, **provenance,
                "seed_result": {k: seed_eval[k] for k in ("combined_score", "passes", "violation_sum")},
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
        if check is not None:
            actual, matches = check
            manifest["first_solution_prompt_check"] = {"actual_sha256": actual, "matches": matches}
            if not matches:
                manifest["status"] = manifest["research_status"] = "FIRST_PROMPT_MISMATCH"
                (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
                raise RuntimeError("first solution prompt differs from the approved first-prompt.sha256")
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
    """Control arm: same broker, system prompt and packet; greedy accept on combined_score."""
    args.broker_url = ob._broker_url(args.broker_url)
    run_dir, stage, seed, verifier, provenance, seed_eval = _setup(args, "sequential")
    best_source, best = seed.read_text(), seed_eval
    trace = []
    manifest = {"engine": "sequential", "task": "corr-cert-260924", **provenance,
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
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        row = {"step": step, "packet_seen": PACKET_MARK in user, "request_sha256": request_sha256}
        expected = getattr(args, "expected_first_prompt_sha256", None)
        if step == 1 and first_prompt_mismatch(messages, expected):
            row["outcome"] = "guard: first prompt differs from the approved first-prompt.sha256"
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
            content, finish = _chat(args.broker_url, args.model, args.max_tokens, args.reasoning_effort,
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
                    "passes": result["passes"], "accepted": accepted})
        if accepted:
            best_source, best = source, result
        else:
            reason = (f"rejected: score {result['combined_score']:.4f} (passes {result['passes']}) "
                      f"did not beat {best['combined_score']:.4f}")
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


def write_first_prompt(capture_dir: Path, out_md: Path, run_dir: Path, *,
                       role: str = "gepa_reflection", label: str = "GEPA proposer",
                       has_system_message: bool = False) -> str:
    """Render the first captured request of `role` verbatim for user approval.

    Used for GEPA (default) and, with role="sequential_refinement", the
    sequential control arm -- both go through our own Python broker client,
    so a pre-send hash guard (first_prompt_mismatch) is possible for them.
    AdaEvolve/EvoX have no role header (SkyDiscover's own client); use
    write_first_solution_prompt for those instead.
    """
    for path in sorted(Path(capture_dir).glob("request-*.json")):
        item = json.loads(path.read_text())
        if item["role"] == role:
            break
    else:
        raise FileNotFoundError(f"no captured {role} request")
    body = item["body"]
    messages = body["messages"]
    digest = messages_sha256(messages)
    fence = "`" * 6
    system_note = ("A separate system message carries the fixed background." if has_system_message
                   else f"{label.split()[0]} sends no separate system message; the system text is "
                        "embedded in the user message.")
    lines = [f"# First {label} prompt (corr-cert-260924)", "",
             f"This is the exact `messages` array the {label} client sends to the local "
             "broker on iteration 1 for the seed program. The broker forwards it unchanged, "
             "adding only transport fields (see `broker-config.json` and the `--dry-run` payload). "
             "It was captured offline from a zero-provider run with the frozen development set. "
             "Only development data (m=4..12) appears; the holdout set (m=13..20) is never loaded.", "",
             f"- Messages SHA-256 (canonical JSON, sorted keys, no spaces): `{digest}`",
             f"- Message roles: {[m['role'] for m in messages]}. {system_note}",
             f"- Client request fields: model `{body.get('model')}`, max_tokens `{body.get('max_tokens')}`, "
             f"reasoning_effort `{body.get('reasoning_effort')}`",
             f"- Captured from: `{Path(run_dir).name}` ({path.name})",
             f"- A live {label} run halts before its first model request if these messages hash differently.", ""]
    for i, m in enumerate(messages, 1):
        lines += [f"## Message {i}: {m['role']}", "", fence + "text", m["content"], fence, ""]
    out_md.write_text("\n".join(lines))
    out_md.with_suffix(".sha256").write_text(
        f"{digest}  messages of {out_md.name} (canonical JSON of the messages array)\n")
    return digest


def write_first_solution_prompt(capture_dir: Path, out_md: Path, run_dir: Path, *, label: str) -> str:
    """Render AdaEvolve/EvoX's first solution-proposal request verbatim for approval.

    Classified by content (_is_corr_solution_request), not a role header:
    SkyDiscover's own client never passes through our Python broker client,
    so there is no role header and no pre-send interception point (see
    verify_first_solution_prompt, checked after the run instead).
    """
    for path in sorted(Path(capture_dir).glob("request-*.json")):
        item = json.loads(path.read_text())
        messages = item["body"]["messages"]
        if messages and _is_corr_solution_request(messages):
            break
    else:
        raise FileNotFoundError(f"no captured {label} solution request")
    body = item["body"]
    messages = body["messages"]
    digest = messages_sha256(messages)
    fence = "`" * 6
    lines = [f"# First {label} solution prompt (corr-cert-260924)", "",
             f"The first request classified as a solution proposal (not strategy/variation/probe "
             f"meta-search) that SkyDiscover's own client sent for {label}. Checked after the run "
             "from the arm's broker ledger receipts (verify_first_solution_prompt), not before "
             "sending -- SkyDiscover's client never passes through our Python broker client.", "",
             f"- Messages SHA-256 (canonical JSON, sorted keys, no spaces): `{digest}`",
             f"- Client request fields: model `{body.get('model')}`, max_tokens `{body.get('max_tokens')}`",
             f"- Captured from: `{Path(run_dir).name}` ({path.name})", ""]
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
    run_dir = CORR_DIR / f"live-{args.engine}-{stamp}"
    broker_log = CORR_DIR / f"broker-{args.engine}-{stamp}.log"
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
                "--python", str(ROOT / cc["python"]), "--evox-switch-interval", str(cc["evox_switch_interval"]),
                "--ledger", str(ROOT / _arm_ledger_path(bc, args.engine))]
        first_prompt_hash_file = {"gepa": "first-prompt.sha256",
                                  "sequential": "first-prompt-sequential.sha256",
                                  "adaevolve": "first-prompt-adaevolve.sha256",
                                  "evox": "first-prompt-evox.sha256"}[args.engine]
        first_prompt_hash_path = CORR_DIR / first_prompt_hash_file
        if first_prompt_hash_path.is_file():
            argv += ["--expected-first-prompt-sha256", first_prompt_hash_path.read_text().split()[0]]
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
        p.add_argument("--instances", type=Path, default=CORR_DIR / "frozen" / "development.json")
        p.add_argument("--frozen-manifest", type=Path, default=CORR_DIR / "frozen" / "manifest.json")
        p.add_argument("--seed", type=Path, default=ROOT / "integrations" / "corr_control_f1.py")
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
        p.add_argument("--cache-dir", type=Path, default=CORR_DIR / "eval-cache")
        p.add_argument("--jobs", type=int, default=4)
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
    fp.add_argument("--output", type=Path, default=CORR_DIR / "first-prompt.md")
    fp.add_argument("--engine", default="gepa", choices=ENGINES + ("sequential",))
    for name in ("approval-hash", "check-approval", "live"):
        p = sub.add_parser(name)
        p.add_argument("--broker-config", type=Path, default=CORR_DIR / "broker-config.json")
        p.add_argument("--campaign-config", type=Path, default=CORR_DIR / "campaign-config.json")
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
        if args.engine == "gepa":
            print(write_first_prompt(args.capture_dir, args.output, args.run_dir))
        elif args.engine == "sequential":
            print(write_first_prompt(args.capture_dir, args.output, args.run_dir,
                                     role="sequential_refinement", label="sequential control",
                                     has_system_message=True))
        else:
            print(write_first_solution_prompt(args.capture_dir, args.output, args.run_dir,
                                              label=args.engine))
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
