"""Run pinned GEPA 0.1.4 and SkyDiscover AdaEvolve/EvoX 0.2.0 on the bound-m task.

Search-side plumbing for autoresearch/bound-m-260925 (TASK.md, SPEC-track2.md),
mirroring integrations/sort_backends.py and reusing integrations/lift_backends.py
and official_backends.py (rejection notes, broker chat client, per-arm ledgers
and contact sub-caps, reflection minibatch min(3, n), the Seatbelt launcher).
The candidate is a program with certify(family); scores come from
integrations/bound_evaluator.py in a trusted coordinator-side service.

Staged evaluation: SkyDiscover and the sequential control score a candidate on
the 30-family screen; a candidate valid on the whole screen that ties or beats
the best screen score gets a full development evaluation (303 families, m = 9
and 10). GEPA evaluates per family (trainset = development minus screen,
valset = screen, reflection minibatch 3). The holdout (including every m = 11
family) is never loaded here.

SkyDiscover settings (survey 2026-09-25): explicit combined_score, cascade
evaluation off, fixed random_seed, inject_evaluator_context off, AdaEvolve
num_context_programs 1 with the sample SEARCH/REPLACE example removed from its
diff template, and EvoX strategy evolution disabled (it writes and runs
LLM-generated Python search strategies outside the candidate sandbox, which
AGENTS.md forbids): switch_interval = iterations + 1 and
auto_generate_variation_operators false. The packet (at most 3000 characters)
is split over two artifacts because SkyDiscover truncates each at 2000.

The staged copy of this file runs inside the optimizer sandbox next to staged
copies of lift_backends.py and official_backends.py, so the module top level
imports only the standard library and those two files.
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
    from integrations import lift_backends as lb
    from integrations import official_backends as ob
except ImportError:  # staged copy inside the optimizer sandbox
    import lift_backends as lb
    import official_backends as ob

ROOT = Path(__file__).resolve().parents[1]
BOUND_DIR = ROOT / "autoresearch" / "bound-m-260925"
TASK = "bound-m-260925"
PACKET_MARK = "BOUND_PACKET_V1"
PACKET_MAX = 3000
ARTIFACT_MAX = 2000  # SkyDiscover truncates each artifact at 2000 characters
ENGINES = ("gepa", "adaevolve", "evox")
SKY_RANDOM_SEED = 260925
MECHANISM = ("Mechanism: each X that touches zero block j costs 2 on beta_j; each net rotation step across "
             "block j (per segment between X letters) costs 1.")

SYSTEM = (
    "Find a uniform construction of LRX sorting words whose length is provably bounded for a whole family "
    "of states. L rotates the vector left (first entry to the end), R rotates right, X swaps the first two "
    "entries. A family (a, S) is a label order a (a permutation of 1..m) and a set S of nonempty gaps "
    "(gap g lies after the first g labels; g = 0 leading, g = m trailing); its states have l_j >= 1 zeros "
    "in the j-th gap of S, and its unit base has exactly one zero per gap. The candidate source must "
    "define certify(family) -> {'words': [...]} returning 1..32 words over L, R, X (at most 4000 letters "
    "each) that sort the unit base to (1, ..., m, 0, ..., 0) and never swap two zeros; optional 'weights' "
    "(rational strings) and 'note' are only reported. The trusted evaluator prices each word with the "
    "research group's Lemma 1 (exact, the same for every m): a word stretches to every block length, "
    "|W(z)| <= B + sum_j beta_j z_j with z_j = l_j - 1, B = (number of X) + sum over segments of "
    "|net rotation|, beta_j = 2 * (X letters touching block j) + sum over segments of |signed crossings "
    "of block j|, where a segment ends at every X. It then solves an exact LP over your words: the family "
    "is CERTIFIED when some mixture has weighted B < T + 1 and every weighted beta_j <= m - 2, with "
    "T = m(m+1)/2 + (k-1)(m-2) and k = |S|. That proves d(v) <= T_m(n) for every state of the family at "
    "every number of zeros. The binding constraint is usually the slope: sweeps cross zero blocks too "
    "often. Each family gets 3 s of CPU (module import 1 s); exact LP or search over a few hundred "
    "candidate words per family fits. Score per m: percentage of families certified (the worst m counts "
    "twice), plus small terms for valid output and a small gap. Development families are m = 9 and 10, "
    "reversal-type orders oversampled; the holdout has unseen families and an unseen m, so the program must "
    "work for any m with no tables: string constants over L/R/X of 24+ characters, literal containers with "
    "more than 64 elements and bytes constants over 256 bytes are rejected. Stdlib only, at most 64 KiB. "
    "Do not read files, the network, or environment variables. Misses prove nothing."
)
OBJECTIVE = (
    "Improve this Python certify(family) program (the seed builds a pool of cyclic-sweep sorting words: "
    "every target rotation, cyclic assignment of the zeros and sweep direction, prices each word by the "
    "Lemma 1 cost, and returns the 16 with the lowest (max slope, base)). Return the entire replacement "
    "Python source in one fenced code block, with no prose and no docstring longer than a few lines. Raise "
    "the number of certified families, first on the worst m, by constructing words whose slopes beta_j stay "
    "at most m-2 (fewer X letters touching each zero block, fewer rotation passes across it) and by choosing "
    "the returned word set well. Only development families are shown."
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _f(x, nd=2):
    return str(round(float(Fr(x)), nd)) if x is not None else "n/a"


# ------------------------------------------------------------------- packet
def _order_key(row):
    return (-float(Fr(row["gap"])), row["k"], row["id"])


def failing(rows, n=3):
    """Worst g first, ties to smaller k; the picks come from different order classes when possible."""
    bad = sorted((r for r in rows if r["status"] != "CERTIFIED"), key=_order_key)
    picked, classes = [], set()
    for r in bad:
        if r.get("class") not in classes:
            picked.append(r)
            classes.add(r.get("class"))
        if len(picked) == n:
            return picked
    for r in bad:
        if r not in picked and len(picked) < n:
            picked.append(r)
    return picked


def totals_lines(result, label):
    lines = []
    for m, g in result["per_m"].items():
        lines.append(f"{label} m={m}: certified {g['certified']}/{g['families']}, boundary {g['boundary']}, "
                     f"invalid {g['invalid']}, incomplete {g['incomplete']} (timeouts {g['timeouts']}), "
                     f"W {_f(g['W'])}{'' if g['W_complete'] else ' (incomplete)'}, G {_f(g['G'], 3)}; per k "
                     + " ".join(f"k{k}:{c}/{t}" for k, (c, t) in g["per_k"].items()))
    return lines


def family_lines(row, fam):
    T, s = row["budget_unit"], row["slope_bound"]
    head = (f"- {row['id']} ({row.get('class')}) m={row['m']} k={row['k']} mask={row['mask']} gaps={fam['gaps']} "
            f"unit_base={fam['unit_base']} T={T} s={s}: {row['status']} g={_f(row['gap'], 3)}")
    t = row.get("trace", {})
    if not row["valid"]:
        fw = t.get("failed_word")
        why = (f"word {fw['index']} (len {fw['length']}): {fw['reason']}"
               + (f"; first bad letter {fw['first_bad_letter']} ...{fw['prefix']}" if "first_bad_letter" in fw else "")
               + (f"; final vector prefix {fw['final_prefix']}" if "final_prefix" in fw else "")
               + ("; LEMMA-1 LITERAL FAILURE (evaluator alarm)" if row.get("lemma1_literal_failure") else "")
               if fw else str(t.get("failure"))[:240])
        return [head, "  " + why]
    lp = row.get("gap_lp") or row["lp"]
    w = [Fr(x) for x in lp["weights"]]
    slopes = t.get("slopes") or []
    lines = [head, f"  gap-LP mixture: Bbar {_f(lp['base'])} vs T+1={T + 1}; weighted slopes (j:gap:slope:excess"
             "[*=tight]) " + " ".join(f"{x['j']}:{x['gap_index']}:{_f(x['slope'])}:{_f(x['excess'])}"
                                      f"{'*' if x['tight'] else ''}" for x in slopes)]
    order = sorted(range(len(row["words"])), key=lambda i: (-w[i], row["words"][i]["base"]))[:6]
    for i in order:
        x = row["words"][i]
        lines.append(f"  word {i} w={_f(w[i], 3)} len={x['length']} B={x['base']} beta={x['beta']} "
                     f"= 2*A{x['A']} + rot{x['rotation_passes']} same_sign={x['same_sign']}")
    lines.append(f"  bound: {row['bound']['statement']}")
    return lines


def packet(result, fams_by_id, best_text, scope, baseline=None):
    """Development-only feedback: totals, best so far, <= 3 failing families with exact LP data."""
    head = [f"{PACKET_MARK} ({scope}; development only; search signal, not proof)"]
    head += totals_lines(result, "this candidate")
    if scope.startswith("family"):
        r = result["results"][0]
        score = 1.0 if r["status"] == "CERTIFIED" else (0.5 / (1 + float(Fr(r["gap"]))) if r["valid"] else 0.0)
        head.append(f"this family: per-family score {score:.4f} (1 certified, 0.5/(1+g) valid miss, 0 invalid); "
                    f"best so far: {best_text}")
    else:
        head.append(f"this candidate combined {result['combined_score']:.4f}; best so far: {best_text}")
    if baseline:
        head.append(baseline)
    blocks = [family_lines(r, fams_by_id[r["id"]]) for r in failing(result["results"])]
    tail = [MECHANISM]

    def render():
        return "\n".join(head + [ln for b in blocks for ln in b] + tail)

    text = render()
    while len(text) > PACKET_MAX and any(len(b) > 3 for b in blocks):
        big = max(blocks, key=len)
        big.pop(-2)  # drop the lowest-weight word line, keep the bound line
        text = render()
    while len(text) > PACKET_MAX and blocks:
        blocks.pop()
        text = render()
    return text[:PACKET_MAX]


def _contract_id():
    from integrations.bound_evaluator import CONTRACT
    return CONTRACT.split(":", 1)[0]


def split_packet(text):
    """Two SkyDiscover artifacts of at most ARTIFACT_MAX characters, cut at a line break."""
    if len(text) <= ARTIFACT_MAX:
        return text, ""
    cut = text.rfind("\n", 0, ARTIFACT_MAX)
    cut = cut if cut > 0 else ARTIFACT_MAX
    return text[:cut], text[cut:].lstrip("\n")


def _table_guard(source):
    try:
        from integrations.bound_evaluator import source_guard
    except ImportError:  # staged copy: the trusted evaluator still enforces the guard
        return None
    return source_guard(source)


def preflight_source(content, finish_reason=None) -> str:
    """A fenced Python block defining certify(family); checked before any evaluation.

    Prose is allowed around the fence(s); the last fenced block that defines
    certify(...) wins. Truncated output is never accepted or repaired.
    """
    if finish_reason in ("length", "max_tokens"):
        raise ValueError("proposal was truncated by the model output limit")
    if not isinstance(content, str):
        raise ValueError("proposal had no text content")
    fences = list(re.finditer(r"```(?:python)?\s*\n(.*?)```", content, re.IGNORECASE | re.DOTALL))
    if not fences:
        raise ValueError("proposal must contain a fenced Python source block defining certify(family)")
    chosen = None
    for m in fences:
        candidate = m.group(1)
        try:
            tree = ast.parse(candidate)
        except SyntaxError:
            continue
        if any(isinstance(node, ast.FunctionDef) and node.name == "certify" for node in tree.body):
            chosen = candidate
    if chosen is None:
        raise ValueError("proposal must define certify(family) in a fenced Python source block")
    if len(chosen.encode()) > 65536:
        raise ValueError("proposal exceeds source size cap")
    guard = _table_guard(chosen)
    if guard:
        raise ValueError("source guard: " + guard)
    return chosen


# ------------------------------------------------------ trusted verifier side
class BoundVerifier:
    """Coordinator-side staged evaluation. Candidate code runs only in bound_evaluator's sandbox."""

    def __init__(self, families_path, run_dir, *, cache_dir, engine, provenance, max_requests, jobs=8,
                 require_os_sandbox=True):
        from integrations.bound_evaluator import guard_not_holdout, load_set

        guard_not_holdout(families_path)
        raw = json.loads(Path(families_path).read_text())
        self.full = load_set(families_path)
        if any(f["m"] not in (9, 10) for f in self.full):
            raise ValueError("development families must be m = 9 or 10")
        self.by_id = {f["id"]: f for f in self.full}
        self.screen_ids = list(raw["screen"])
        self.screen = [self.by_id[i] for i in self.screen_ids]
        self.cache_dir, self.engine, self.provenance = cache_dir, engine, provenance
        self.jobs, self.max_requests = jobs, max_requests
        self.require_os_sandbox = require_os_sandbox  # tests only; engines always use Seatbelt
        self.evidence = Path(run_dir) / "verified" / "evaluations"
        self.evidence.mkdir(parents=True)
        self.lock = threading.Lock()
        self.state = {"requests": 0, "evaluations": [], "distinct_source_hashes": [],
                      "screen_valid_source_hashes": [], "full_evaluations": 0, "best_screen": None,
                      "best_full": None, "failures": 0, "screen_ids": self.screen_ids,
                      "families": len(self.full)}
        self.baseline = None

    def _current_best(self, extra=None):
        """Best screen/full scores over every evaluation on record (TRACE-AUDIT defect 7)."""
        rows = self.state["evaluations"] + ([extra] if extra else [])
        bs = bf = None
        for r in rows:
            if r["scope"] == "screen" and r["valid"] == r["families"] and \
                    (bs is None or r["combined_score"] > bs["score"]):
                bs = {"score": r["combined_score"], "certified": r["certified"], "source_sha256": r["candidate_hash"]}
            if r.get("full") and (bf is None or r["full"]["combined_score"] > bf["score"]):
                bf = {"score": r["full"]["combined_score"], "certified": r["full"]["certified"],
                      "per_m": r["full"]["per_m_certified"], "max_W": r["full"]["max_W"],
                      "source_sha256": r["candidate_hash"]}
        return bs, bf

    def _best_text(self, bs, bf):
        text = (f"screen {bs['score']:.4f} ({bs['certified']}/{len(self.screen)} certified)" if bs else "screen none")
        if bf:
            text += (f"; full development {bf['certified']}/{len(self.full)} certified ("
                     + ", ".join(f"m={m}: {c}" for m, c in bf["per_m"].items()) + f"), worst gap {_f(bf['max_W'])}")
        return text

    def evaluate(self, source: str, family_id=None, *, final=False) -> dict:
        from integrations import bound_evaluator as E

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
            subset, scope = (([self.by_id[family_id]], "family " + family_id) if family_id
                             else (self.screen, "screen"))
            res = E.evaluate(path, subset, jobs=self.jobs, cache_dir=self.cache_dir,
                             require_os_sandbox=self.require_os_sandbox)
            promising = False
            if family_id is None:
                prior, _ = self._current_best()
                promising = res["valid"] == res["families"] and (prior is None or res["combined_score"] >= prior["score"])
                if promising and digest not in self.state["screen_valid_source_hashes"]:
                    self.state["screen_valid_source_hashes"].append(digest)
            full = None
            if promising or final:
                full = E.evaluate(path, self.full, jobs=self.jobs, cache_dir=self.cache_dir,
                                  require_os_sandbox=self.require_os_sandbox)
                self.state["full_evaluations"] += 1
            fsum = ({"combined_score": full["combined_score"], "certified": full["certified"],
                     "valid": full["valid"], "families": full["families"], "max_W": full["max_W"],
                     "per_m_certified": {m: g["certified"] for m, g in full["per_m"].items()},
                     "per_m": {m: {x: g[x] for x in ("certified", "families", "pct", "boundary", "invalid",
                                                    "incomplete", "timeouts", "W", "W_complete", "G", "per_k")}
                               for m, g in full["per_m"].items()},
                     "cache_key": full["cache_key"]} if full else None)
            row = {"scope": scope, "candidate_hash": digest, "combined_score": res["combined_score"],
                   "certified": res["certified"], "valid": res["valid"], "families": res["families"],
                   "cache_hit": res["cache_hit"], "full": fsum}
            bs, bf = self._current_best(extra=row)
            self.state["best_screen"], self.state["best_full"] = bs, bf
            if self.baseline is None and full:
                self.baseline = "seed full development: " + ", ".join(
                    f"m={m} {g['certified']}/{g['families']}" for m, g in full["per_m"].items())
            feedback = packet(res, self.by_id, self._best_text(bs, bf), scope, self.baseline)
            part1, part2 = split_packet(feedback)
            example = E.per_example_metric(res["results"][0]) if family_id else None
            summary = {"combined_score": res["combined_score"], "certified": res["certified"], "valid": res["valid"],
                       "families": res["families"], "boundary": res["boundary"], "incomplete": res["incomplete"],
                       "timeouts": res["timeouts"], "max_W": res["max_W"], "max_W_float": float(Fr(res["max_W"])),
                       "scope": scope, "example_score": example, "candidate_hash": digest,
                       "cache_hit": res["cache_hit"], "evaluation_cache_key": res["cache_key"],
                       "feedback": feedback, "feedback_part1": part1, "feedback_part2": part2, "full": fsum}
            artifact = self.evidence / f"result-{ordinal:04d}.json"
            artifact.write_text(json.dumps({"summary": summary, "stage": res, "full": full}, default=str) + "\n")
            summary["evaluation"] = str(artifact)
            row.update(ordinal=ordinal, packet_sha256=_sha(feedback.encode()))
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
                    payload = json.loads(self.rfile.read(length))
                    source, fid = payload["source"], payload.get("family_id")
                    if not isinstance(source, str) or len(source.encode()) > 65536:
                        return self._reply(413, {"error": "candidate source size exceeded"})
                    if fid is not None and fid not in verifier.by_id:
                        return self._reply(400, {"error": "unknown development family"})
                    return self._reply(200, verifier.evaluate(source, fid))
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
    return bool(expected_sha256) and lb.messages_sha256(messages) != expected_sha256


def is_solution_request(messages) -> bool:
    return bool(messages) and ob._evox_call_kind(messages) == "solution" and "certify" in json.dumps(messages)


def verify_first_solution_prompt(ledger_path, expected_sha256):
    """AdaEvolve/EvoX: compare the first solution request in the arm's ledger receipts after the run."""
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


# ------------------------------------------------------------ official engines
def _sky_templates(python: Path, stage: Path) -> Path:
    """AdaEvolve diff template without the sample SEARCH/REPLACE example (TRACE-AUDIT defect 10)."""
    found = sorted(Path(python).absolute().parent.parent.glob(
        "lib/python3*/site-packages/skydiscover/optimize/context_builder/adaevolve/templates/diff_user_message.txt"))
    if not found:
        raise FileNotFoundError("SkyDiscover AdaEvolve diff template not found under the official venv")
    text = found[0].read_text()
    start, end = text.find("Example of valid diff format:"), text.find("**CRITICAL**")
    if start < 0 or end < start:
        raise ValueError("unexpected AdaEvolve diff template layout; refusing to guess")
    out = stage / "sky-templates"
    out.mkdir(exist_ok=True)
    (out / "diff_user_message.txt").write_text(text[:start] + text[end:])
    return out


def sky_config_dict(args, stage: Path) -> dict:
    evolve = False  # EvoX strategy evolution runs generated Python outside the sandbox: never enabled here
    config = {
        "max_iterations": args.iterations, "checkpoint_interval": 1, "log_level": "INFO", "language": "python",
        "llm": {"models": [{"name": args.model, "weight": 1.0}], "api_base": args.broker_url,
                "api_key": "local-broker", "max_tokens": args.max_tokens, "temperature": 0.7,
                "timeout": args.llm_timeout, "retries": 0, "reasoning_effort": args.reasoning_effort},
        "search": {"type": args.engine, "num_context_programs": 1,
                   "database": {"random_seed": SKY_RANDOM_SEED,
                                **({"auto_generate_variation_operators": evolve} if args.engine == "evox" else {})},
                   "switch_interval": args.iterations + 1 if args.engine == "evox" else None,
                   "share_llm": args.engine == "evox"},
        "prompt": {"system_message": SYSTEM},
        "evaluator": {"timeout": args.eval_timeout, "max_retries": 0, "cascade_evaluation": False,
                      "inject_evaluator_context": False},
        "diff_based_generation": True, "max_solution_length": 40000, "monitor": {"enabled": False},
    }
    if args.engine == "adaevolve":
        config["prompt"]["template_dir"] = str(_sky_templates(args.python, stage))  # "prompt" = ContextBuilderConfig
    return config


def _sky_config(args, stage: Path) -> Path:
    path = stage / "sky-config.yaml"  # JSON is valid YAML
    path.write_text(json.dumps(sky_config_dict(args, stage), indent=2) + "\n")
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
        "               'screen_certified': float(out['certified']),\n"
        "               'screen_valid': float(out['valid']),\n"
        "               'screen_max_gap': float(out['max_W_float']),\n"
        "               'full_certified': float(full.get('certified', -1))}\n"
        "    artifacts = {'feedback': out['feedback_part1']}\n"
        "    if out['feedback_part2']:\n"
        "        artifacts['feedback_continued'] = out['feedback_part2']\n"
        "    return EvaluationResult(metrics=metrics, artifacts=artifacts)\n")
    return path


class BoundBrokerLM(ob.BrokerLM):
    """GEPA reflection model via the broker; bound preflight and packet receipts."""

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

    data = json.loads(args.dataset.read_text())
    train = [{"id": f} for f in data["train"]]
    val = [{"id": f} for f in data["screen"]]
    lm = BoundBrokerLM(args.broker_url, args.model, args.max_tokens, None, args.llm_timeout, args.reasoning_effort)
    lm.receipts = []
    lm.expected_first_sha256 = args.expected_first_prompt_sha256

    def verify(source, family_id=None):
        payload = json.dumps({"source": source, "family_id": family_id}).encode()
        with urlopen(Request(args.verifier_url, payload, {"Content-Type": "application/json"}),
                     timeout=args.eval_timeout) as response:
            return json.load(response)

    def evaluator(candidate, example):
        r = verify(candidate, example["id"])
        return float(r["example_score"]), {"family_id": example["id"], "certified": r["certified"],
                                           "valid": r["valid"], "gap": r["max_W"], "feedback": r["feedback"]}

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
               "best_screen_score": full["combined_score"], "best_idx": getattr(result, "best_idx", None),
               "candidate_sha256": [_sha(c.encode()) for c in candidates], "lineage": lineage,
               "reflection_calls": lm.calls, "model_valid_responses": lm.valid_responses,
               "model_preflight_failures": lm.preflight_failures, "reflection_receipts": lm.receipts,
               "minibatch": minibatch, "metric_calls_per_proposal": per_proposal, "final_request": full}
    (args.run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    return summary


def _research_status(seed_full, best_full, proposals):
    """Development only. A claim of progress over control (b) needs the holdout (bound_finalize)."""
    if not best_full or not seed_full:
        return "INCOMPLETE"
    if best_full["certified"] > seed_full["certified"] and best_full["valid"] >= seed_full["valid"]:
        return "MORE_CERTIFIED"
    if best_full["certified"] == seed_full["certified"] and Fr(best_full["max_W"]) < Fr(seed_full["max_W"]):
        return "GRADED_PROGRESS"
    return "NO_GAIN" if proposals else "NO_VALID_PROPOSAL"


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
    verifier = BoundVerifier(args.instances, run_dir, cache_dir=args.cache_dir, engine=engine,
                             provenance=provenance, max_requests=args.max_evals, jobs=args.jobs)
    (stage / "dataset.json").write_text(json.dumps({
        "train": [f["id"] for f in verifier.full if f["id"] not in set(verifier.screen_ids)],
        "screen": verifier.screen_ids}) + "\n")
    seed_eval = verifier.evaluate(seed.read_text(), final=True)
    return run_dir, stage, seed, verifier, provenance, seed_eval


def _finish(manifest, run_dir, verifier, seed_eval, best_source: str):
    from tools.orchestrator import trusted_status

    final = verifier.evaluate(best_source, final=True)
    seed_hash = seed_eval["candidate_hash"]
    st = verifier.state
    manifest.update({
        "candidate_evaluations": {k: st[k] for k in ("requests", "full_evaluations", "failures", "best_screen",
                                                     "best_full", "screen_ids", "families")},
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
    shutil.copyfile(Path(lb.__file__), stage / "lift_backends.py")
    shutil.copyfile(Path(__file__), stage / "bound_official_worker.py")
    server, verifier_url = verifier.serve()
    env = ob._worker_environment(stage, run_dir, args.broker_url)
    if args.engine == "gepa":
        command = [str(python), str(stage / "bound_official_worker.py"), "_gepa_worker",
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
                                       loopback_ports=[urlparse(args.broker_url).port, urlparse(verifier_url).port],
                                       allow_python_multiprocessing=True))
    wrapped = sandbox_command(command, profile)
    manifest = {"engine": args.engine, "task": TASK, "upstream": upstream, **provenance,
                "seed_full": seed_eval["full"], "broker_url": args.broker_url, "model": args.model,
                "iterations": args.iterations, "max_tokens": args.max_tokens,
                "reasoning_effort": args.reasoning_effort, "max_evals": args.max_evals,
                "wall_seconds": args.wall_seconds, "verifier_url": verifier_url, "command": command,
                "sandbox_command": wrapped, "sandbox_profile": str(profile), "run_dir": str(run_dir),
                "sky_random_seed": SKY_RANDOM_SEED if args.engine != "gepa" else None,
                "evox_strategy_evolution": False if args.engine == "evox" else None}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
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
        manifest["mechanism_evidence"].update({k: s[k] for k in ("lineage", "best_idx", "candidate_sha256",
                                                                 "reflection_receipts", "minibatch",
                                                                 "metric_calls_per_proposal")})
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
    """Control arm: same broker, system prompt and packet; greedy accept on the screen combined_score."""
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
                + "\n```\n\n" + "Evaluator feedback:\n" + best["feedback"]
                + "\n\nProvide ONLY the complete new program within ```python ... ``` blocks.")
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
                    "certified": result["certified"], "accepted": accepted})
        if accepted:
            best_source, best = source, result
        else:
            reason = (f"rejected: screen combined {result['combined_score']:.4f} (certified {result['certified']}, "
                      f"valid {result['valid']}/{result['families']}) did not beat {best['combined_score']:.4f}")
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
    """Render an arm's first captured proposer request verbatim for user approval."""
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
    lines = [f"# First {engine} proposer prompt ({TASK}, {_contract_id()})", "",
             f"This is the exact `messages` array the {engine} arm sends to the local broker for its first "
             "program proposal on the seed, captured offline from a zero-provider run through the mock with the "
             "frozen development set. Only development families (m = 9, 10) appear; the holdout is never loaded.",
             "", f"- Messages SHA-256 (canonical JSON, sorted keys, no spaces): `{digest}`",
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


# ------------------------------------------------------------- approval
def approval_material(broker_config: Path, campaign_config: Path) -> dict:
    """Everything a live arm sends or spends, derived from the configs; hashed for approval."""
    from integrations.bound_evaluator import CONTRACT, VERSION, evaluator_hash
    from integrations.research_budget import _dry_run_payload

    bc, cc = lb._load_config(broker_config), lb._load_config(campaign_config)
    _, development = lb.development_from_manifest(ROOT / cc["frozen_manifest"])

    def _hash_of(name):
        path = broker_config.parent / name
        return path.read_text().split()[0] if path.is_file() else None

    return {"broker_config": bc, "campaign_config": cc,
            **{f"first_prompt_{e}_sha256": _hash_of(f) for e, f in FIRST_PROMPT_FILES.items()},
            "upstream_endpoint": bc["upstream_url"].rstrip("/") + "/chat/completions",
            "dry_run_payload": _dry_run_payload(bc), "system_prompt": SYSTEM, "objective": OBJECTIVE,
            "packet_format": {"marker": PACKET_MARK, "max_chars": PACKET_MAX, "artifact_max": ARTIFACT_MAX,
                              "scope": "development only"},
            "sky_settings": {"random_seed": SKY_RANDOM_SEED, "cascade_evaluation": False,
                             "inject_evaluator_context": False, "num_context_programs": 1,
                             "evox_strategy_evolution": False, "adaevolve_diff_example_removed": True},
            "seed_sha256": _sha((ROOT / cc["seed"]).read_bytes()),
            "frozen_manifest_sha256": _sha((ROOT / cc["frozen_manifest"]).read_bytes()),
            "development_sha256": development,
            "evaluator": {"version": VERSION, "contract": CONTRACT, "hash": evaluator_hash()},
            "bound_backends_sha256": _sha(Path(__file__).read_bytes()),
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
    run_dir = BOUND_DIR / f"live-{args.engine}-{stamp}"
    broker_log = BOUND_DIR / f"broker-{args.engine}-{stamp}.log"
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
                "--python", str(ROOT / cc["python"]), "--ledger", ledger]
        first = BOUND_DIR / FIRST_PROMPT_FILES[args.engine]
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
        p.add_argument("--instances", type=Path, default=BOUND_DIR / "frozen" / "development.json")
        p.add_argument("--frozen-manifest", type=Path, default=BOUND_DIR / "frozen" / "manifest.json")
        p.add_argument("--seed", type=Path, default=ROOT / "integrations" / "bound_control_sweep.py")
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
        p.add_argument("--cache-dir", type=Path, default=BOUND_DIR / "eval-cache")
        p.add_argument("--jobs", type=int, default=8)
        p.add_argument("--ledger", type=Path, help="this arm's broker ledger, for the EvoX meta-search share")
        p.add_argument("--expected-first-prompt-sha256",
                       help="GEPA/sequential: halt before the first model request unless its messages hash matches")
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
        p.add_argument("--broker-config", type=Path, default=BOUND_DIR / "broker-config.json")
        p.add_argument("--campaign-config", type=Path, default=BOUND_DIR / "campaign-config.json")
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
        output = args.output or BOUND_DIR / (FIRST_PROMPT_FILES[args.engine][:-len(".sha256")] + ".md")
        print(write_first_prompt(args.capture_dir, output, args.run_dir, args.engine))
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
