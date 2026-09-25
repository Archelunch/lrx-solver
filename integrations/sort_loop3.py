"""Loop v3 for the sort-m9 task (autoresearch/loop-v3-260925/SPEC-track1.md).

Search-side only. New module so that the v2 approval hash (sort_backends.py,
lift_backends.py, official_backends.py) and the evaluator hash stay unchanged.
Adds: explicit seeds; GEPA over 30 frozen instances with a batch evaluator;
SkyDiscover Pareto objectives with fitness_key full_score; a 100-state screen
cascade; packet v2 with exact-table divergence and capped optimal-word reveal;
reflection-model routing through a second broker and ledger; EvoX strategy
evolution forced off with a post-run leak check; a sequential control with the
same packet; per-(arm, seed) guards, ledgers and approval material.

The staged copy runs inside the optimizer sandbox next to staged
sort_backends.py, lift_backends.py and official_backends.py, so the module top
level imports only the standard library and those three files.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
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
    from integrations import sort_backends as sb
except ImportError:  # staged copy inside the optimizer sandbox
    import lift_backends as lb
    import official_backends as ob
    import sort_backends as sb

ROOT = Path(__file__).resolve().parents[1]
CAMP = ROOT / "autoresearch" / "sort-m9-v3-260925"
TASK = "sort-m9-v3-260925"
PACKET_MARK = "SORT_PACKET_V2"
KEY_MAX, INSTANCE_MAX, SEQ_MAX, WORST_N = 2000, 2500, 6000, 5
ENGINES = ("gepa", "adaevolve", "evox")
ARMS = ("gepa", "sequential", "adaevolve", "evox")
FAILED_SCORE = -2.0
NO_VALID_EXCESS = -1000.0
REFLECT_SYSTEM = ("Diagnose why the program fails on the listed states and propose concrete changes. "
                  "Do not write code.")
DIAGNOSIS_APPEND = "\n\nReviewer diagnosis (separate model; untrusted advice):\n"
DIAGNOSIS_PLACEHOLDER = "<DIAGNOSIS>"
INSTANCE_SCORE_TEXT = ("instance_score = within/N + 0.25/(1 + mean excess over valid states) - invalid/N; "
                       "middle term 0 when no state is valid; no worst-r term (one r per instance)")
PACKET_FORMAT = {"marker": PACKET_MARK, "keys": ["feedback", "worst_states", "worst_states_2"],
                 "key_max_chars": KEY_MAX, "instance_max_chars": INSTANCE_MAX, "sequential_max_chars": SEQ_MAX,
                 "worst_states": WORST_N, "word_elision": "above 160 letters: first 120 + '...' + last 30 + '(len N)'",
                 "optimal_words": "development only; distinct revealed states capped by reveal_optimal_max_states"}
EVOX_NOTE = ("EvoX's outer loop writes and runs LLM-generated Python search strategies. AGENTS.md forbids executing "
             "generated code outside the evaluator sandbox, so it is disabled in every run. The EvoX arm is EvoX's "
             "solution-level search only.")
SKY_METRIC_KEYS = {"screen": ("combined_score", "screen_score", "screen_within_rate", "screen_worst_r_rate",
                              "full_score", "stage"),
                   "full": ("combined_score", "full_score", "within_rate", "worst_r_rate", "invalid_rate", "stage",
                            "neg_mean_excess")}
STATUS_EXIT = {3: "BROKER_STOPPED", 4: "FIRST_PROMPT_MISMATCH", 5: "EVAL_BUDGET"}
EXCLUDED = ("FIRST_PROMPT_MISMATCH", "STRATEGY_EVOLUTION_LEAK", "INCOMPLETE", "BROKER_STOPPED")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(path):
    return json.loads(Path(path).read_text())


# ------------------------------------------------------------ frozen v3 inputs
def build_instances(states, groups=6):
    """Per r, states sorted by (d, id), cut into `groups` consecutive equal groups r{r}-s{k} (k=1 lowest d)."""
    out = {}
    for r in sorted({s["r"] for s in states}):
        rows = sorted((s for s in states if s["r"] == r), key=lambda s: (s["d"], s["id"]))
        if len(rows) % groups:
            raise ValueError(f"r={r}: {len(rows)} states do not split into {groups} equal groups")
        size = len(rows) // groups
        for k in range(groups):
            out[f"r{r}-s{k + 1}"] = [s["id"] for s in rows[k * size:(k + 1) * size]]
    return out


def build_screen(states, per_r=20):
    """Per r, every radius state (d == budget) plus evenly spaced picks from the rest in (d, id) order."""
    ids = []
    for r in sorted({s["r"] for s in states}):
        rows = sorted((s for s in states if s["r"] == r), key=lambda s: (s["d"], s["id"]))
        radius = [s for s in rows if s["d"] == s["budget"]]
        rest = [s for s in rows if s["d"] != s["budget"]]
        need = per_r - len(radius)
        step = len(rest) / need
        ids += [s["id"] for s in radius] + [rest[int(step * i + step / 2)]["id"] for i in range(need)]
    return ids


def load_frozen_v3(manifest_path, development_sha):
    """(instances dict, screen id list) after hash checks against the frozen-v3 manifest."""
    manifest_path = Path(manifest_path)
    man = _load(manifest_path)
    if man["development_sha256"] != development_sha:
        raise RuntimeError("frozen-v3 was built from a different development set")
    inst, screen = manifest_path.parent / "instances.json", manifest_path.parent / "screen-ids.json"
    if _sha(inst.read_bytes()) != man["instances_sha256"] or _sha(screen.read_bytes()) != man["screen_sha256"]:
        raise RuntimeError("frozen-v3 instance or screen hash mismatch")
    return _load(inst)["instances"], _load(screen)["ids"]


# ------------------------------------------------------------ scores and metrics
def instance_score(rows) -> float:
    N = len(rows)
    valid = [r for r in rows if r["valid"]]
    within = sum(bool(r["within"]) for r in rows)
    middle = 0.25 / (1 + sum(r["excess"] for r in valid) / len(valid)) if valid else 0.0
    return within / N + middle - (N - len(valid)) / N


def sky_metrics(res, scope) -> dict:
    """SkyDiscover metrics (all floats). Stage 1 carries full_score -2 so it never ranks against full scores."""
    c = float(res["combined_score"])
    if scope == "screen":
        return {"combined_score": c, "screen_score": c, "screen_within_rate": float(res["within_fraction"]),
                "screen_worst_r_rate": float(res["min_r_within_rate"]), "full_score": FAILED_SCORE, "stage": 1.0}
    me = res["mean_excess"]
    return {"combined_score": c, "full_score": c, "within_rate": float(res["within_fraction"]),
            "worst_r_rate": float(res["min_r_within_rate"]), "invalid_rate": float(res["invalid_fraction"]),
            "stage": 2.0, "neg_mean_excess": NO_VALID_EXCESS if me is None else -float(me)}


# ------------------------------------------------------------ exact-table words
def optimal_word(tables, v) -> str:
    """Greedy descent on the exact table (the Cayley graph is undirected: L^-1 = R, X^-1 = X)."""
    from src.lrx.certificates import replay_visible

    cur, word = tuple(v), ""
    d0 = d = tables.distance(cur)
    while d > 0:
        for ch in "LRX":
            nxt = replay_visible(cur, ch)
            if tables.distance(nxt) == d - 1:
                cur, word, d = nxt, word + ch, d - 1
                break
        else:
            raise AssertionError("no descending letter: table bug")
    if len(word) != d0:
        raise AssertionError("optimal word length differs from d: table bug")
    return word


def divergence(tables, state, word):
    """First step t with d_t >= d_{t-1} (same as prefix_trace's first_off_shortest_path) and the first
    step after which T is unreachable. None when the word never leaves a shortest path."""
    from src.lrx.certificates import replay_visible

    cur, prev, T = tuple(state["v"]), state["d"], state["budget"]
    off = lost = None
    for t, ch in enumerate(word, 1):
        cur = replay_visible(cur, ch)
        dt = tables.distance(cur)
        if off is None and dt >= prev:
            off = {"step": t, "prefix": word[:t], "d_before": prev, "d_after": dt}
        if lost is None and t + dt > T:
            lost = t
        if off is not None and lost is not None:
            break
        prev = dt
    if off is None:
        return None
    return dict(off, first_budget_lost=lost)


def aligned_optimal(tables, v, word, t) -> str:
    """The candidate's first t-1 letters (all on a shortest path) followed by an exact shortest completion."""
    from src.lrx.certificates import replay_visible

    return word[:t - 1] + optimal_word(tables, replay_visible(tuple(v), word[:t - 1]))


# ------------------------------------------------------------ packet v2
class Reveal:
    """Caps the distinct development states whose optimal word a run may reveal; records them."""

    def __init__(self, cap):
        self.cap, self.ids, self._seen = int(cap), [], set()

    def allow(self, state_id) -> bool:
        if state_id in self._seen:
            return True
        if len(self.ids) >= self.cap:
            return False
        self._seen.add(state_id)
        self.ids.append(state_id)
        return True

    def tentative(self):
        return Tentative(self)


class Tentative:
    """Grants reveals against the cap for one packet; only ids whose blocks survive the size caps are recorded."""

    def __init__(self, reveal):
        self.reveal, self.granted = reveal, set()

    def allow(self, state_id) -> bool:
        if state_id in self.reveal._seen or state_id in self.granted:
            return True
        if len(self.reveal.ids) + len(self.granted) >= self.reveal.cap:
            return False
        self.granted.add(state_id)
        return True

    def commit(self, shown_ids):
        for state_id in shown_ids:
            if state_id in self.granted and state_id not in self.reveal._seen:
                self.reveal._seen.add(state_id)
                self.reveal.ids.append(state_id)


class Withhold:
    """Reveals nothing and records nothing: for packets that never reach a proposer prompt."""

    ids, cap = (), 0

    @staticmethod
    def allow(_state_id) -> bool:
        return False

    @staticmethod
    def commit(_shown_ids):
        return None


def elide(word) -> str:
    return word if len(word) <= 160 else f"{word[:120]}...{word[-30:]}(len {len(word)})"


def state_block(row, state, tables, reveal) -> str:
    v = tuple(state.get("v", ()))
    lines = [f"- {row['id']} v={v} r={row['r']} T={row['budget']} d={row['d']} {row['status']}"
             + (f" len={row['length']}" if row.get("length") is not None else "")]
    word = row.get("word")
    if word:
        lines.append("  word: " + elide(word))
    if row["status"] == "NOT_SORTED":
        lines.append(f"  ends at {tuple(row['final'])}")
    elif not row["valid"]:
        lines.append(f"  failure: {str(row.get('failure'))[:160]}")
    if tables is not None and v:
        try:
            if word:
                div = divergence(tables, state, word)
                if div:
                    lines.append(f"  leaves every shortest path at step {div['step']} (d {div['d_before']} -> "
                                 f"{div['d_after']})" + (f"; T unreachable after step {div['first_budget_lost']}"
                                                         if div["first_budget_lost"] else ""))
                    lines.append("  aligned optimal: " + aligned_optimal(tables, v, word, div["step"])
                                 if reveal.allow(row["id"]) else "  optimal word withheld (reveal cap)")
            else:
                lines.append("  optimal: " + optimal_word(tables, v) if reveal.allow(row["id"])
                             else "  optimal word withheld (reveal cap)")
        except KeyError:
            pass
    return "\n".join(lines)


def packet_parts(result, rows, best_text, states_by_id, tables, seed_result, reveal, scope, score=None):
    N, me = result["states"], result["mean_excess"]
    shown = f"combined {result['combined_score']:.4f}" if score is None else f"instance score {score:.4f}"
    head = [f"{PACKET_MARK} (development only; search signal, not proof). Scope: {scope}, {N} states.",
            f"this candidate: within budget {result['within_budget']}/{N}, worst r {result['worst_r']} at "
            f"{result['min_r_within_rate']:.3f}, sorted {result['valid']}/{N}, timeouts (0.2 s CPU) "
            f"{result['timeouts']}, mean excess {'n/a' if me is None else f'{me:.3f}'}, max excess "
            f"{result['max_excess']}; {shown}; best so far (full development): "
            f"{best_text}",
            sb.per_r_line(result, "this candidate")]
    if seed_result is not None:
        head.append(sb.per_r_line(seed_result, "seed"))
    head.append(sb.STRUCTURAL_FACTS)
    blocks = []
    for row in sb._worst(rows)[:WORST_N]:
        if row["valid"] and row["within"] and row["excess"] == 0:
            break
        blocks.append(state_block(row, (states_by_id or {}).get(row["id"], {}), tables, reveal))
    return "\n".join(head)[:KEY_MAX], blocks


def block_ids(rows, n) -> list:
    """State ids of the first n packet blocks (packet_parts emits blocks in sb._worst order)."""
    return [r["id"] for r in sb._worst(rows)[:n]]


def split_blocks_n(blocks, keys=("worst_states", "worst_states_2"), cap=KEY_MAX):
    """(artifact texts, number of leading blocks kept)."""
    out, i = {}, 0
    for key in keys:
        text = ""
        while i < len(blocks) and len(text) + len(blocks[i]) + 1 <= cap:
            text, i = (text + "\n" if text else "") + blocks[i], i + 1
        if text:
            out[key] = text
    return out, i


def split_blocks(blocks, keys=("worst_states", "worst_states_2"), cap=KEY_MAX) -> dict:
    return split_blocks_n(blocks, keys, cap)[0]


def packet_v2(result, rows, best_text, states_by_id, tables, seed_result, reveal, scope="full") -> dict:
    head, blocks = packet_parts(result, rows, best_text, states_by_id, tables, seed_result, reveal, scope)
    return dict({"feedback": head}, **split_blocks(blocks))


def packet_text_n(head, blocks, cap):
    """(packet text, number of leading blocks kept whole)."""
    blocks = list(blocks)
    text = "\n".join([head] + blocks)
    while len(text) > cap and blocks:
        blocks.pop()
        text = "\n".join([head] + blocks)
    return text[:cap], len(blocks) if len(text) <= cap else 0


def packet_text(head, blocks, cap) -> str:
    return packet_text_n(head, blocks, cap)[0]


def artifacts_text(artifacts, cap=SEQ_MAX) -> str:
    return "\n".join(artifacts[k] for k in PACKET_FORMAT["keys"] if k in artifacts)[:cap]


# ------------------------------------------------------------ trusted verifier
class SortVerifierV3:
    """Coordinator-side trusted evaluation over screen, full and instance scopes."""

    def __init__(self, states_path, run_dir, *, cache_dir, engine, instances, screen_ids, budgets, reveal_cap,
                 jobs=8, require_os_sandbox=True, tables=None, reveal_minibatch=None):
        from integrations.sort_evaluator import guard_not_holdout, load_set

        guard_not_holdout(states_path)
        self.states = load_set(states_path)
        self.by_id = {s["id"]: s for s in self.states}
        self.instances = {k: [self.by_id[i] for i in ids] for k, ids in instances.items()}
        self.screen = [self.by_id[i] for i in screen_ids]
        if sorted(i for ids in instances.values() for i in ids) != sorted(self.by_id):
            raise ValueError("instances must partition the development set")
        self.cache_dir, self.engine, self.jobs, self.tables = cache_dir, engine, jobs, tables
        self.budgets = dict(budgets)
        self.require_os_sandbox = require_os_sandbox  # tests only; engines always use Seatbelt
        self.reveal = Reveal(reveal_cap)
        self.evidence = Path(run_dir) / "verified" / "evaluations"
        self.evidence.mkdir(parents=True)
        self.lock = threading.Lock()
        self.used = {"requests": 0, "screen": 0, "full": 0, "instances": 0, "states": 0}
        self.state = {"evaluations": [], "failures": 0, "distinct_source_hashes": []}
        self.seed = {}  # scope -> the seed's aggregate result (first evaluation of that scope)
        self.seed_instance = {}
        # GEPA instance coverage per candidate digest: ids evaluated so far, and their rows until the union
        # covers every instance (then one full row is appended and the rows are dropped).
        self.inst_seen, self.inst_rows, self.covered = {}, {}, set()
        # Instance packets reach GEPA's reflection only as the parent's minibatch re-evaluation (cache_evaluation
        # is off): a request of at most this many instances for a candidate already evaluated on them.
        self.reveal_minibatch = reveal_minibatch
        self._ordinal = 0

    # -- bookkeeping
    def _reserve(self, scope, final):
        if not final:
            if self.used["requests"] >= self.budgets.get("max_requests", float("inf")):
                raise PermissionError("evaluation request budget exhausted")
            cap = self.budgets.get(f"max_{scope}_evals", float("inf"))
            if self.used[scope] >= cap:
                raise PermissionError(f"{scope} evaluation budget exhausted")
            if self.used["states"] >= self.budgets.get("max_state_evals", float("inf")):
                raise PermissionError("state evaluation budget exhausted")
            self.used["requests"] += 1
            self.used[scope] += 1

    def _candidate(self, source):
        self._ordinal += 1
        ordinal = self._ordinal
        path = self.evidence / f"candidate-{ordinal:04d}.py"
        path.write_text(source)
        digest = _sha(source.encode())
        if digest not in self.state["distinct_source_hashes"]:
            self.state["distinct_source_hashes"].append(digest)
        return ordinal, path, digest

    def best_full(self):
        """Argmax of full-development combined score over every full row; ties go to the lowest ordinal."""
        best = None
        for row in self.state["evaluations"]:
            if row["scope"] == "full" and (best is None or row["combined_score"] > best["combined_score"]):
                best = row
        return best

    def _best_text(self, best):
        if not best:
            return "none yet"
        me = best["mean_excess"]
        return (f"combined {best['combined_score']:.4f} (within {best['within_budget']}/{len(self.states)}, "
                f"worst-r rate {best['min_r_within_rate']:.3f}, mean excess {'n/a' if me is None else f'{me:.3f}'})")

    def _row(self, res, scope, ordinal, digest, path, final, instances=None):
        row = {k: res[k] for k in ("combined_score", "within_budget", "min_r_within_rate", "valid", "invalid",
                                   "timeouts", "mean_excess")}
        row.update(scope=scope, ordinal=ordinal, candidate_hash=digest, candidate_path=str(path), final=final,
                   states=res["states"], cache_hit=res.get("cache_hit"))
        if instances is not None:
            row["instances"] = instances
        return row

    # -- screen / full
    def evaluate(self, source: str, scope: str = "full", *, final=False, use_cache=True, show=None) -> dict:
        """show: whether this packet can reach a proposer prompt (default: not for final evaluations)."""
        from integrations import sort_evaluator as E

        if scope not in ("screen", "full"):
            raise ValueError("scope must be screen or full")
        with self.lock:
            self._reserve(scope, final)
            ordinal, path, digest = self._candidate(source)
        states = self.screen if scope == "screen" else self.states
        res = E.evaluate(path, states, jobs=self.jobs, cache_dir=self.cache_dir if use_cache else None,
                         require_os_sandbox=self.require_os_sandbox)
        with self.lock:
            self.used["states"] += 0 if res.get("cache_hit") else len(states)
            if scope not in self.seed:
                self.seed[scope] = res
                if scope == "full":
                    by = {s["id"]: r for r, s in zip(res["results"], states)}
                    for iid, members in self.instances.items():
                        self.seed_instance[iid] = dict(E.aggregate([by[s["id"]] for s in members]))
            row = self._row(res, scope, ordinal, digest, path, final)
            self.state["evaluations"].append(row)
            reveal = self.reveal.tentative() if (not final if show is None else show) else Withhold()
            head, blocks = packet_parts(res, res["results"], self._best_text(self.best_full()), self.by_id,
                                        self.tables, self.seed[scope], reveal, scope)
            split, kept_split = split_blocks_n(blocks)
            artifacts = dict({"feedback": head}, **split)
            packet, kept_packet = packet_text_n(head, blocks, SEQ_MAX)
            # sequential shows the packet text; SkyDiscover engines show the artifacts
            reveal.commit(block_ids(res["results"], kept_packet if self.engine == "sequential" else kept_split))
            summary = {k: res[k] for k in ("combined_score", "within_budget", "within_fraction", "min_r_within_rate",
                                           "worst_r", "valid", "invalid", "invalid_fraction", "mean_excess",
                                           "max_excess", "timeouts", "incomplete", "per_r", "cache_hit", "states")}
            summary.update(scope=scope, candidate_hash=digest, ordinal=ordinal, evaluation_cache_key=res["cache_key"],
                           metrics=sky_metrics(res, scope), artifacts=artifacts, feedback=head, packet=packet)
            row["packet_sha256"] = _sha(summary["packet"].encode())
            (self.evidence / f"result-{ordinal:04d}.json").write_text(
                json.dumps({"summary": summary, "result": res}, default=str) + "\n")
            return summary

    # -- GEPA instances
    def evaluate_instances(self, source: str, ids, *, final=False) -> dict:
        from integrations import sort_evaluator as E

        ids = list(dict.fromkeys(ids))
        if not ids or any(i not in self.instances for i in ids):
            raise ValueError("unknown instance id")
        if "full" not in self.seed:
            raise RuntimeError("the seed must be evaluated on the full set first")
        with self.lock:
            self._reserve("instances", final)
            ordinal, path, digest = self._candidate(source)
            seen_before = set(self.inst_seen.get(digest, ()))
        small = self.reveal_minibatch is not None and len(ids) <= self.reveal_minibatch
        workers = min(len(ids), self.jobs)
        per = max(1, self.jobs // workers)
        with ThreadPoolExecutor(workers) as pool:
            got = dict(pool.map(lambda i: (i, E.evaluate(path, self.instances[i], jobs=per, cache_dir=self.cache_dir,
                                                         require_os_sandbox=self.require_os_sandbox)), ids))
        with self.lock:
            self.used["states"] += sum(0 if r.get("cache_hit") else r["states"] for r in got.values())
            self.inst_seen.setdefault(digest, set()).update(ids)
            whole = set(ids) == set(self.instances)
            completes = not whole and digest not in self.covered and self.inst_seen[digest] == set(self.instances)
            if not whole and digest not in self.covered:
                self.inst_rows.setdefault(digest, {}).update({i: got[i]["results"] for i in ids})
            full = whole or completes
            agg = None
            if whole:
                agg = E.aggregate([row for i in ids for row in got[i]["results"]])
            elif completes:  # GEPA sent the valset remainder: the union of this candidate's requests is complete
                union = self.inst_rows.pop(digest)
                agg = E.aggregate([row for i in self.instances for row in union[i]])
            if full:
                self.covered.add(digest)
                self.inst_rows.pop(digest, None)
                row = self._row(agg, "full", ordinal, digest, path, final, instances="all")
                row["request_instances"] = "all" if whole else ids
            else:
                inst_rows = [row for i in ids for row in got[i]["results"]]
                row = self._row(E.aggregate(inst_rows), "instances", ordinal, digest, path, final, ids)
            row["cache_hit"] = all(r.get("cache_hit") for r in got.values())
            self.state["evaluations"].append(row)
            best_text = self._best_text(self.best_full())
            out = []
            for i in ids:
                res, seed = got[i], self.seed_instance[i]
                rows = res["results"]
                ds = [r["d"] for r in rows]
                score = instance_score(rows)
                reveal = self.reveal.tentative() if small and i in seen_before else Withhold()
                head, blocks = packet_parts(res, rows, best_text, self.by_id, self.tables, seed, reveal,
                                            f"instance {i} (d {min(ds)}..{max(ds)})", score)
                feedback, kept = packet_text_n(head, blocks, INSTANCE_MAX)
                reveal.commit(block_ids(rows, kept))
                me = res["mean_excess"]
                out.append({"instance": i, "score": score, "side_info": {
                    "instance": i, "r": rows[0]["r"], "d_range": [min(ds), max(ds)], "within": res["within_budget"],
                    "states": res["states"], "invalid": res["invalid"], "timeouts": res["timeouts"],
                    "mean_excess": me, "seed_within": seed["within_budget"], "seed_mean_excess": seed["mean_excess"],
                    "feedback": feedback}})
            payload = {"results": out, "ordinal": ordinal, "candidate_hash": digest, "scope": row["scope"]}
            if full:
                payload["full"] = {k: agg[k] for k in ("combined_score", "within_budget", "min_r_within_rate",
                                                       "valid", "invalid", "timeouts", "mean_excess", "per_r")}
            (self.evidence / f"result-{ordinal:04d}.json").write_text(json.dumps(
                {"summary": dict(payload, instances=ids, scope=row["scope"]),
                 "result": {i: got[i] for i in ids}}, default=str) + "\n")
            return payload

    def serve(self):
        verifier = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path not in ("/evaluate", "/evaluate_instances"):
                    return self._reply(404, {"error": "not found"})
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 75000:
                    return self._reply(413, {"error": "source request size exceeded"})
                try:
                    body = json.loads(self.rfile.read(length))
                    source = body["source"]
                    if not isinstance(source, str) or len(source.encode()) > 65536:
                        return self._reply(413, {"error": "candidate source size exceeded"})
                    if self.path == "/evaluate":
                        return self._reply(200, verifier.evaluate(source, body.get("scope", "full")))
                    return self._reply(200, verifier.evaluate_instances(source, body["instances"]))
                except PermissionError as exc:
                    return self._reply(429, {"error": str(exc)})
                except Exception as exc:
                    with verifier.lock:
                        verifier.state["failures"] += 1
                    return self._reply(500, {"error": f"trusted evaluation failed: {type(exc).__name__}: {exc}"})

            def _reply(self, status, payload):
                data = json.dumps(payload, default=str).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server, f"http://127.0.0.1:{server.server_port}"


# ------------------------------------------------------------ SkyDiscover evaluator stub
def sky_evaluator_source(verifier_url: str, timeout: int) -> str:
    """The staged evaluator.py. AdaEvolve paradigm prompts include this text, so it holds only the HTTP call."""
    return (
        "from pathlib import Path\nimport json\nfrom urllib.request import Request, urlopen\n"
        "from skydiscover.optimize.evaluation.evaluation_result import EvaluationResult\n"
        f"URL = {verifier_url.rstrip('/') + '/evaluate'!r}\n"
        f"FAILED = {{'full_score': {FAILED_SCORE}, 'combined_score': {FAILED_SCORE}, 'stage': 0.0}}\n\n\n"
        "def _call(program_path, scope):\n"
        "    try:\n"
        "        source = Path(program_path).read_text(encoding='utf-8')\n"
        "        payload = json.dumps({'source': source, 'scope': scope}).encode('utf-8')\n"
        "        req = Request(URL, payload, {'Content-Type': 'application/json'})\n"
        f"        with urlopen(req, timeout={int(timeout)}) as response:\n"
        "            out = json.load(response)\n"
        "        metrics = {k: float(v) for k, v in out['metrics'].items()}\n"
        "        return EvaluationResult(metrics=metrics, artifacts={k: str(v) for k, v in out['artifacts'].items()})\n"
        "    except Exception as exc:\n"
        "        return EvaluationResult(metrics=dict(FAILED), artifacts={\n"
        "            'feedback': 'evaluation failed: %s: %s' % (type(exc).__name__, str(exc)[:300])})\n\n\n"
        "def evaluate_stage1(program_path):\n    return _call(program_path, 'screen')\n\n\n"
        "def evaluate_stage2(program_path):\n    return _call(program_path, 'full')\n\n\n"
        "def evaluate(program_path):\n    return evaluate_stage2(program_path)\n")


# ------------------------------------------------------------ engine knobs
def sky_worker_environment(stage, run_dir, broker_url) -> dict:
    """ob._worker_environment without OPENAI_API_BASE/OPENAI_BASE_URL: SkyDiscover 0.2.0 load_config
    (optimize/config.py:912-917) overwrites the api_base of every model, guide models included, with that
    variable, which would send AdaEvolve's reflection (guide) calls to the flash broker."""
    env = ob._worker_environment(stage, run_dir, broker_url)
    env.pop("OPENAI_API_BASE", None)
    env.pop("OPENAI_BASE_URL", None)
    return env


def reflection_cap(cc, engine) -> int:
    ref = cc.get("reflection") or {}
    return int(ref.get("max_requests", {}).get(engine, 0)) if ref.get("enabled") else 0


def _llm_timeout(bc):
    return int(bc["timeout"]) + 30


def sky_config_v3(cc, engine, seed, bc, rbc=None) -> dict:
    arm, thr = cc["engines"][engine], float(cc["screen_threshold"])
    it = int(arm["iterations"])
    if cc.get("evox_strategy_evolution") is not False:
        raise ValueError("evox_strategy_evolution must be false")
    pareto = {"pareto_objectives": ["within_rate", "worst_r_rate", "neg_mean_excess"],
              "higher_is_better": {"within_rate": True, "worst_r_rate": True, "neg_mean_excess": True,
                                   "full_score": True},
              "fitness_key": "full_score", "pareto_objectives_weight": 0.0, "random_seed": int(seed)}
    database = dict(pareto, auto_generate_variation_operators=False) if engine == "evox" else \
        dict(pareto, use_paradigm_breakthrough=True)
    flash = f"http://127.0.0.1:{cc['broker_port']}/v1"
    # Explicit per-model api_base: a bare gemini-* name would otherwise resolve to Google's URL, and the Sky
    # worker environment carries no OPENAI_API_BASE (load_config would overwrite every model, guide included).
    llm = {"models": [{"name": bc["model"], "weight": 1.0, "api_base": flash, "api_key": "local-broker"}],
           "api_base": flash, "api_key": "local-broker",
           "max_tokens": bc["max_tokens"], "temperature": 0.7, "timeout": _llm_timeout(bc), "retries": 0,
           "reasoning_effort": bc.get("reasoning_effort")}
    if engine == "adaevolve" and reflection_cap(cc, engine) > 0:
        if rbc is None:
            raise ValueError("AdaEvolve reflection routing needs the reflection broker config")
        llm["guide_models"] = [{"name": rbc["model"], "api_base": f"http://127.0.0.1:{cc['reflection']['broker_port']}/v1",
                                "api_key": "local-broker", "max_tokens": rbc["max_tokens"],
                                "timeout": _llm_timeout(rbc), "retries": 0,
                                "reasoning_effort": rbc.get("reasoning_effort")}]
    return {"max_iterations": it, "checkpoint_interval": 1, "log_level": "INFO", "language": "python",
            "max_parallel_iterations": 1, "llm": llm,
            "search": {"type": engine, "num_context_programs": 2, "database": database,
                       "switch_interval": it + 1 if engine == "evox" else None, "share_llm": engine == "evox"},
            "prompt": {"system_message": sb.SYSTEM},
            "evaluator": {"timeout": int(cc["eval_timeout"]), "max_retries": 0, "cascade_evaluation": True,
                          "cascade_thresholds": [thr, thr], "inject_evaluator_context": False},
            "diff_based_generation": True, "max_solution_length": 40000, "monitor": {"enabled": False}}


def engine_knobs(cc, engine, seed, bc, rbc=None) -> dict:
    """Single source of every engine setting for one (arm, seed); used by the launcher and the approval hash."""
    arm = cc["engines"][engine]
    common = {"seed": int(seed), "iterations": int(arm["iterations"]), "reflection_max_requests":
              reflection_cap(cc, engine), "flash_max_requests": int(arm["max_requests"]),
              "wall_seconds": int(arm["wall_seconds"])}
    if engine == "gepa":
        return dict(common, engine={
            "seed": int(seed), "max_candidate_proposals": int(arm["iterations"]),
            "max_metric_calls": int(arm["max_metric_calls"]), "candidate_selection_strategy": "pareto",
            "frontier_type": arm["frontier_type"], "val_evaluation_policy": "full_eval",
            # cache_evaluation off: the parent's minibatch is re-evaluated (a verifier cache hit), so the packets
            # reflection sees come from that request, and each accepted child's valset request is all instances.
            "acceptance_criterion": "strict_improvement", "cache_evaluation": False,
            "parallel": False, "max_workers": 1, "raise_on_exception": True},
            reflection={"reflection_minibatch_size": int(arm["minibatch"]), "batch_sampler": "epoch_shuffled",
                        "module_selector": "round_robin"},
            merge=None, refiner=None, verifier={"max_state_evals": int(arm["max_state_evals"]),
                                                "max_requests": int(arm["max_metric_calls"])})
    verifier = {"max_screen_evals": int(arm["max_screen_evals"]), "max_full_evals": int(arm["max_full_evals"])}
    if engine == "sequential":
        return dict(common, screen_threshold=float(cc["screen_threshold"]), verifier=verifier,
                    provider_seed_field=None)
    return dict(common, sky=sky_config_v3(cc, engine, seed, bc, rbc), verifier=verifier)


def gepa_metric_calls(n_instances, minibatch, iterations) -> int:
    return n_instances + (iterations + 1) * lb.gepa_metric_calls_per_proposal(minibatch, [None] * n_instances)


# ------------------------------------------------------------ proposer clients
class FirstPromptMismatch(ob.BrokerHalted):
    """The first request differs from the approved first-prompt hash."""


class EvalBudget(BaseException):
    """The trusted verifier refused with HTTP 429 (evaluation budget); escapes GEPA's exception handling."""


def _as_messages(request):
    return [{"role": "user", "content": request}] if isinstance(request, str) else [dict(m) for m in request]


class SortBrokerLMv3(ob.BrokerLM):
    """Flash proposer via the broker: sort preflight, packet-v2 receipts, first-prompt guard."""

    expected_first_sha256 = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.receipts = []

    @staticmethod
    def _preflight(content, finish_reason):
        sb.preflight_source(content, finish_reason)

    def __call__(self, request, guard_messages=None):
        messages = _as_messages(request)
        if self.calls == 0 and self.expected_first_sha256 and \
                lb.messages_sha256(guard_messages or messages) != self.expected_first_sha256:
            raise FirstPromptMismatch("first proposer prompt differs from the approved first-prompt hash")
        text = json.dumps(messages)
        receipt = {"call": self.calls + 1, "packet_seen": PACKET_MARK in text, "request_sha256": _sha(text.encode()),
                   "request_chars": len(text)}
        self.receipts.append(receipt)
        try:
            return super().__call__(messages)
        finally:
            receipt["finish_reason"] = self.last_finish_reason


class DiagnosisLM(ob.BrokerLM):
    """Reflection model via its own broker. Accepts any non-empty untruncated text; strips code."""

    max_chars = 4000

    @staticmethod
    def _preflight(content, finish_reason):
        if finish_reason in ("length", "max_tokens"):
            raise ValueError("diagnosis was truncated by the model output limit")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty diagnosis")

    def __call__(self, messages):
        try:
            text = super().__call__(messages)
        except HTTPError as exc:
            if exc.code >= 500:
                raise ob.BrokerHalted(f"reflection broker stopped: HTTP {exc.code}") from exc
            raise
        return strip_code(text)[:self.max_chars]


def strip_code(text) -> str:
    return re.sub(r"```.*?(?:```|\Z)", "[code removed]", text, flags=re.DOTALL).strip()


def diagnosis_messages(messages):
    return [{"role": "system", "content": REFLECT_SYSTEM},
            {"role": "user", "content": "\n\n".join(m["content"] for m in messages)}]


def with_diagnosis(messages, diagnosis):
    out = [dict(m) for m in messages]
    out[-1]["content"] = out[-1]["content"] + DIAGNOSIS_APPEND + diagnosis
    return out


def guard_view(messages):
    """The messages with any appended diagnosis text replaced by the placeholder (for first-prompt hashes)."""
    out = [dict(m) for m in messages]
    content = out[-1]["content"]
    if DIAGNOSIS_APPEND in content:
        out[-1]["content"] = content.rsplit(DIAGNOSIS_APPEND, 1)[0] + DIAGNOSIS_APPEND + DIAGNOSIS_PLACEHOLDER
    return out


class ReflectThenWriteLM:
    """Two calls per proposal: the reflection model diagnoses, then flash writes the program."""

    expected_diagnosis_sha256 = None

    def __init__(self, diagnose: DiagnosisLM, writer: SortBrokerLMv3):
        self.diagnose, self.writer, self.receipts = diagnose, writer, []

    @property
    def calls(self):
        return self.writer.calls

    def __call__(self, request):
        messages = _as_messages(request)
        d_messages = diagnosis_messages(messages)
        if self.diagnose.calls == 0 and self.expected_diagnosis_sha256 and \
                lb.messages_sha256(d_messages) != self.expected_diagnosis_sha256:
            raise FirstPromptMismatch("first diagnosis prompt differs from the approved hash")
        # A truncated or otherwise invalid diagnosis (SyntaxError/ValueError from DiagnosisLM._preflight,
        # e.g. hit max_tokens) is retried once, then the proposal falls back to no diagnosis, rather than
        # letting the exception reach GEPA's own per-task retry (which burns extra, unbounded broker
        # requests -- the actual cause of a reflection-budget BROKER_STOPPED seen in practice). A genuine
        # broker halt (ob.BrokerHalted: HTTP 429/5xx or a connection failure) always propagates immediately;
        # only a bad-response preflight failure gets the retry-then-fallback treatment.
        diagnosis, fallback_reason = None, None
        for attempt in (1, 2):
            try:
                diagnosis = self.diagnose(d_messages)
                break
            except (SyntaxError, ValueError) as exc:
                fallback_reason = f"attempt {attempt}: {exc}"
                if attempt == 2:
                    diagnosis = None
        receipt = {"call": len(self.receipts) + 1,
                   "diagnosis_sha256": _sha(diagnosis.encode()) if diagnosis is not None else None,
                   "diagnosis_chars": len(diagnosis) if diagnosis is not None else 0,
                   "diagnosis_finish_reason": self.diagnose.last_finish_reason,
                   "diagnosis_fallback": fallback_reason}
        self.receipts.append(receipt)
        if diagnosis is None:
            return self.writer(messages)
        full = with_diagnosis(messages, diagnosis)
        return self.writer(full, guard_messages=with_diagnosis(messages, DIAGNOSIS_PLACEHOLDER))


def make_lm(broker_url, model, max_tokens, timeout, effort, expected=None, *, reflection_url=None,
            reflection_model=None, reflection_max_tokens=None, reflection_timeout=None, reflection_effort=None,
            diagnosis_max_chars=4000, expected_diagnosis=None):
    writer = SortBrokerLMv3(broker_url, model, max_tokens, None, timeout, effort)
    writer.expected_first_sha256 = expected
    if not reflection_url:
        return writer
    diag = DiagnosisLM(reflection_url, reflection_model, reflection_max_tokens, None, reflection_timeout,
                       reflection_effort)
    diag.max_chars = diagnosis_max_chars
    lm = ReflectThenWriteLM(diag, writer)
    lm.expected_diagnosis_sha256 = expected_diagnosis
    return lm


def _lm_from_args(args):
    return make_lm(args.broker_url, args.model, args.max_tokens, args.llm_timeout, args.reasoning_effort,
                   args.expected_first_prompt_sha256, reflection_url=args.reflection_url,
                   reflection_model=args.reflection_model, reflection_max_tokens=args.reflection_max_tokens,
                   reflection_timeout=args.reflection_timeout, reflection_effort=args.reflection_effort,
                   diagnosis_max_chars=args.diagnosis_max_chars, expected_diagnosis=args.expected_diagnosis_sha256)


# ------------------------------------------------------------ GEPA worker (inside the sandbox)
def _post(url, body, timeout):
    with urlopen(Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"}),
                 timeout=timeout) as response:
        return json.load(response)


def _gepa_worker_v3(args) -> dict:
    from gepa.optimize_anything import EngineConfig, GEPAConfig, ReflectionConfig, optimize_anything

    knobs = _load(args.knobs)
    data = [{"id": i} for i in _load(args.dataset)["instances"]]
    lm = _lm_from_args(args)
    url = args.verifier_url.rstrip("/") + "/evaluate_instances"

    def batch_eval(pairs):
        groups = {}
        for index, (candidate, example) in enumerate(pairs):
            groups.setdefault(candidate, []).append((index, example["id"]))
        results = [None] * len(pairs)
        for candidate, items in groups.items():
            try:
                out = _post(url, {"source": candidate, "instances": sorted({i for _, i in items})}, args.eval_timeout)
            except HTTPError as exc:
                if exc.code == 429:
                    raise EvalBudget("verifier evaluation budget exhausted") from exc
                raise
            by = {r["instance"]: r for r in out["results"]}
            for index, iid in items:
                results[index] = (float(by[iid]["score"]), by[iid]["side_info"])
        return results

    summary = {"engine": "gepa", "upstream": ob.UPSTREAM["gepa"], "knobs": knobs, "status": "COMPLETE"}
    code = 0
    try:
        result = optimize_anything(
            seed_candidate=args.seed.read_text(), batch_evaluator=batch_eval, dataset=data, valset=data,
            objective=sb.OBJECTIVE, background=sb.SYSTEM,
            config=GEPAConfig(engine=EngineConfig(run_dir=str(args.run_dir / "gepa"), **knobs["engine"]),
                              reflection=ReflectionConfig(reflection_lm=lm, **knobs["reflection"]),
                              merge=None, refiner=None))
        best = result.best_candidate
        if not isinstance(best, str):
            raise TypeError("GEPA returned a non-source candidate")
        (args.run_dir / "best.py").write_text(best)
        candidates = [c if isinstance(c, str) else json.dumps(c) for c in getattr(result, "candidates", [])]
        summary.update(best_idx=getattr(result, "best_idx", None), best_sha256=_sha(best.encode()),
                       candidate_sha256=[_sha(c.encode()) for c in candidates],
                       lineage={k: getattr(result, k, None) for k in ("parents", "val_aggregate_scores",
                                                                     "discovery_eval_counts", "total_metric_calls",
                                                                     "num_full_val_evals")})
    except FirstPromptMismatch as exc:
        summary.update(status="FIRST_PROMPT_MISMATCH", reason=str(exc))
        code = 4
    except ob.BrokerHalted as exc:
        summary.update(status="BROKER_STOPPED", reason=str(exc))
        code = 3
    except EvalBudget as exc:
        summary.update(status="EVAL_BUDGET", reason=str(exc))
        code = 5
    writer = lm.writer if isinstance(lm, ReflectThenWriteLM) else lm
    d_receipts = lm.receipts if isinstance(lm, ReflectThenWriteLM) else []
    summary.update(reflection_calls=writer.calls, model_valid_responses=writer.valid_responses,
                   model_preflight_failures=writer.preflight_failures, reflection_receipts=writer.receipts,
                   diagnosis_calls=lm.diagnose.calls if isinstance(lm, ReflectThenWriteLM) else 0,
                   diagnosis_receipts=d_receipts,
                   diagnosis_fallback_count=sum(1 for r in d_receipts if r.get("diagnosis_fallback")),
                   diagnosis_missing_count=sum(1 for r in d_receipts if r.get("diagnosis_sha256") is None))
    (args.run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    if code:
        sys.exit(code)
    return summary


# ------------------------------------------------------------ setup / finish
def _configs(args):
    cc = _load(args.campaign_config)
    bc = _load(args.broker_config)
    rbc = _load(args.reflection_config) if args.reflection_config and Path(args.reflection_config).is_file() else None
    return cc, bc, rbc


def _setup_v3(args, cc, engine, knobs):
    from integrations.sort_evaluator import load_set

    frozen = ROOT / cc["frozen_manifest"]
    dev, dev_sha = lb.development_from_manifest(frozen)
    provenance = lb._verify_inputs(dev.resolve(), frozen.resolve())
    instances, screen_ids = load_frozen_v3(ROOT / cc["frozen_v3_manifest"], dev_sha)
    run_dir = args.run_dir.resolve()
    if run_dir.exists():
        raise FileExistsError(run_dir)
    (run_dir / "output" / "tmp").mkdir(parents=True)
    stage = run_dir / "stage"
    stage.mkdir()
    seed = stage / "initial_program.py"
    shutil.copyfile(ROOT / cc["seed_program"], seed)
    provenance = dict(provenance, seed_sha256=_sha(seed.read_bytes()),
                      frozen_v3_manifest_sha256=_sha((ROOT / cc["frozen_v3_manifest"]).read_bytes()))
    keys = sorted({(s["m"], s["r"]) for s in load_set(dev)})
    tables = None if args.no_tables else sb.tables_from_manifest(frozen, keys)
    verifier = SortVerifierV3(dev, run_dir, cache_dir=ROOT / cc["eval_cache"], engine=engine, instances=instances,
                              screen_ids=screen_ids, budgets=knobs["verifier"],
                              reveal_cap=cc["reveal_optimal_max_states"], jobs=args.jobs, tables=tables,
                              reveal_minibatch=(knobs.get("reflection") or {}).get("reflection_minibatch_size"))
    source = seed.read_text()
    seed_screen = verifier.evaluate(source, "screen", final=True, use_cache=False)
    # Only the sequential arm shows this packet (its first prompt); the engines evaluate the seed themselves.
    seed_full = verifier.evaluate(source, "full", final=True, use_cache=False, show=engine == "sequential")
    thr = float(cc["screen_threshold"])
    if abs(seed_screen["combined_score"] - float(cc["seed_screen_score"])) > 1e-9:
        raise RuntimeError(f"seed screen score {seed_screen['combined_score']!r} differs from seed_screen_score")
    if seed_screen["combined_score"] < thr:
        raise RuntimeError("seed screen score is below the screen threshold")
    if seed_screen["timeouts"] or seed_full["timeouts"]:
        raise RuntimeError("seed evaluation has TIMEOUT rows (machine load); refusing to start")
    (stage / "dataset.json").write_text(json.dumps({"instances": sorted(instances)}) + "\n")
    return run_dir, stage, seed, verifier, provenance, seed_screen, seed_full


_RESULT_KEYS = sb._RESULT_KEYS


def _finish_v3(manifest, run_dir, verifier, seed_full):
    from tools.orchestrator import trusted_status

    best = verifier.best_full()
    source = Path(best["candidate_path"]).read_text()
    final = verifier.evaluate(source, "full", final=True)
    st = verifier.state
    manifest.update({
        "verifier_usage": dict(verifier.used), "verifier_failures": st["failures"],
        "evaluation_trace": st["evaluations"],
        "proposal_hashes": [h for h in st["distinct_source_hashes"] if h != seed_full["candidate_hash"]],
        "seed_result": {k: seed_full[k] for k in _RESULT_KEYS},
        "seed_screen_result": {k: verifier.seed["screen"][k] for k in _RESULT_KEYS},
        "verified_best_ordinal": best["ordinal"], "verified_best_hash": final["candidate_hash"],
        "verified_best_result": {k: final[k] for k in _RESULT_KEYS},
        "revealed_ids": list(verifier.reveal.ids), "reveal_cap": verifier.reveal.cap,
        "trusted_status_after": trusted_status()})
    (run_dir / "verified").mkdir(exist_ok=True)
    (run_dir / "verified" / "best.py").write_text(source)
    manifest["research_status"] = sb._research_status(manifest["seed_result"], manifest["verified_best_result"],
                                                      manifest["proposal_hashes"])
    _write(run_dir, manifest)
    return manifest


def _write(run_dir, manifest):
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")


def evox_leak(ledger, mechanism) -> str | None:
    """None when EvoX made no strategy/variation call and wrote no strategy code, else the reason."""
    share = ob._evox_meta_search_share(ledger)
    if share["evox_meta_search_calls"] is None:
        return "no ledger receipts to verify the EvoX meta-search count"
    if share["evox_meta_search_calls"]:
        return f"{share['evox_meta_search_calls']} strategy/variation calls in the ledger"
    if mechanism.get("generated_strategy_artifacts"):
        return "generated strategy code under search/iteration_*"
    return None


def sky_records_without_full_score(run_dir) -> list:
    """Program records of the last checkpoint that lack full_score (would fall back to averaging)."""
    cps = sorted((Path(run_dir) / "output" / "sky" / "checkpoints").glob("checkpoint_*"),
                 key=lambda p: int(p.name.split("_")[1]))
    if not cps:
        return []
    bad = []
    for path in sorted((cps[-1] / "programs").glob("*.json")):
        try:
            metrics = _load(path).get("metrics") or {}
        except ValueError:
            continue
        if "full_score" not in metrics:
            bad.append(path.name)
    return bad


def _reflection_argv(cc, rbc, engine, args):
    if reflection_cap(cc, engine) <= 0 or engine not in ("gepa", "sequential"):
        return {}
    return {"reflection_url": args.reflection_url, "reflection_model": rbc["model"],
            "reflection_max_tokens": rbc["max_tokens"], "reflection_timeout": _llm_timeout(rbc),
            "reflection_effort": rbc.get("reasoning_effort"),
            "diagnosis_max_chars": cc["reflection"]["diagnosis_max_chars"]}


def _launch_v3(args) -> dict:
    from integrations.program_sandbox import sandbox_command, sandbox_profile

    cc, bc, rbc = _configs(args)
    engine, seed_value = args.engine, args.seed
    knobs = engine_knobs(cc, engine, seed_value, bc, rbc)
    args.broker_url = ob._broker_url(args.broker_url)
    needs_reflection = reflection_cap(cc, engine) > 0 and engine in ("gepa", "adaevolve")
    if needs_reflection:
        args.reflection_url = ob._broker_url(args.reflection_url or "")
    routing = _reflection_argv(cc, rbc, engine, args)
    python = args.python.absolute()
    upstream = ob._installed_identity(python, engine)
    run_dir, stage, seed, verifier, provenance, seed_screen, seed_full = _setup_v3(args, cc, engine, knobs)
    for mod in (ob, lb, sb):
        shutil.copyfile(Path(mod.__file__), stage / Path(mod.__file__).name)
    shutil.copyfile(Path(__file__), stage / "sort_loop3_worker.py")
    server, verifier_url = verifier.serve()
    env = (ob._worker_environment(stage, run_dir, args.broker_url) if engine == "gepa"
           else sky_worker_environment(stage, run_dir, args.broker_url))
    if engine == "gepa":
        (stage / "knobs.json").write_text(json.dumps(knobs, indent=2) + "\n")
        command = [str(python), str(stage / "sort_loop3_worker.py"), "_gepa_worker",
                   "--seed", str(seed), "--dataset", str(stage / "dataset.json"), "--knobs", str(stage / "knobs.json"),
                   "--run-dir", str(run_dir / "output"), "--broker-url", args.broker_url, "--model", bc["model"],
                   "--verifier-url", verifier_url, "--max-tokens", str(bc["max_tokens"]),
                   "--llm-timeout", str(_llm_timeout(bc)), "--eval-timeout", str(cc["eval_timeout"])]
        if bc.get("reasoning_effort"):
            command += ["--reasoning-effort", bc["reasoning_effort"]]
        for flag, value in (("--expected-first-prompt-sha256", args.expected_first_prompt_sha256),
                            ("--expected-diagnosis-sha256", args.expected_diagnosis_sha256)):
            if value:
                command += [flag, value]
        for key, value in routing.items():
            if value is not None:
                command += ["--" + key.replace("_", "-"), str(value)]
    else:
        config = stage / "sky-config.yaml"  # JSON is valid YAML
        config.write_text(json.dumps(knobs["sky"], indent=2) + "\n")
        evaluator = stage / "evaluator.py"
        evaluator.write_text(sky_evaluator_source(verifier_url, int(cc["eval_timeout"]) - 30))
        command = [str(python), "-m", "skydiscover", "optimize", str(seed), str(evaluator), "--config", str(config),
                   "--search", engine, "--iterations", str(knobs["iterations"]),
                   "--output", str(run_dir / "output" / "sky"), "--log-level", "INFO"]
    base_python = Path(os.path.realpath(python))
    read_paths = ["/System", "/usr", "/Library", "/opt/homebrew", "/private/etc", "/dev",
                  str(python.parent.parent), str(base_python.parent.parent), str(stage)]
    ports = [urlparse(args.broker_url).port, urlparse(verifier_url).port]
    if needs_reflection:
        ports.append(urlparse(args.reflection_url).port)
    profile = run_dir / "worker.sb"
    profile.write_text(sandbox_profile(read_paths=read_paths, write_paths=[run_dir / "output"], loopback_ports=ports,
                                       allow_python_multiprocessing=True))
    wrapped = sandbox_command(command, profile)
    manifest = {"engine": engine, "seed": seed_value, "task": TASK, "upstream": upstream, **provenance,
                "knobs": knobs, "seed_result": {k: seed_full[k] for k in _RESULT_KEYS},
                "seed_screen_result": {k: seed_screen[k] for k in _RESULT_KEYS},
                "broker_url": args.broker_url, "reflection_url": args.reflection_url if needs_reflection else None,
                "model": bc["model"], "reflection_model": rbc["model"] if (rbc and needs_reflection) else None,
                "verifier_url": verifier_url, "command": command, "sandbox_command": wrapped,
                "sandbox_profile": str(profile), "run_dir": str(run_dir), "evox_note": EVOX_NOTE}
    _write(run_dir, manifest)
    start = time.monotonic()
    try:
        with (run_dir / "console.log").open("w") as log:
            proc = subprocess.Popen(wrapped, cwd=run_dir / "output", env=env, stdout=log, stderr=subprocess.STDOUT,
                                    text=True, start_new_session=True)
            try:
                returncode = proc.wait(timeout=knobs["wall_seconds"])
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
    manifest.update(returncode=returncode, engine_seconds=time.monotonic() - start)
    manifest["mechanism_evidence"] = ob._mechanism_evidence(run_dir, engine, knobs["iterations"], args.ledger)
    console = (run_dir / "console.log").read_text(errors="replace")
    manifest["console_flags"] = {"stage1_failed": console.count("Stage 1 failed"),
                                 "timed_out": console.count("timed out")}
    if engine == "gepa" and (run_dir / "output" / "summary.json").is_file():
        s = _load(run_dir / "output" / "summary.json")
        manifest["mechanism_evidence"].update({k: s.get(k) for k in (
            "lineage", "best_idx", "best_sha256", "candidate_sha256", "reflection_receipts", "diagnosis_calls",
            "diagnosis_receipts", "reflection_calls", "model_valid_responses", "model_preflight_failures")})
    status = "COMPLETE"
    if engine in ("adaevolve", "evox"):
        check = sb.verify_first_solution_prompt(args.ledger, args.expected_first_prompt_sha256)
        manifest["first_solution_prompt_check"] = (None if check is None else
                                                   {"actual_sha256": check[0], "matches": check[1]})
        manifest["records_without_full_score"] = sky_records_without_full_score(run_dir)
        if check is not None and not check[1]:
            status = "FIRST_PROMPT_MISMATCH"
    if engine == "evox":
        manifest["strategy_evolution_leak"] = evox_leak(args.ledger, manifest["mechanism_evidence"])
        if manifest["strategy_evolution_leak"]:
            status = "STRATEGY_EVOLUTION_LEAK"
    if returncode and status == "COMPLETE":
        status = STATUS_EXIT.get(returncode, "INCOMPLETE") if engine == "gepa" else "INCOMPLETE"
    manifest["status"] = status
    if status in EXCLUDED:
        manifest.update(research_status=status, best_full_row=verifier.best_full(),
                        evaluation_trace=verifier.state["evaluations"], revealed_ids=list(verifier.reveal.ids))
        _write(run_dir, manifest)
        return manifest
    if engine == "gepa":
        s = _load(run_dir / "output" / "summary.json")
        rows = [r for r in verifier.state["evaluations"] if r["candidate_hash"] == s.get("best_sha256")
                and r["scope"] == "full"]
        manifest["gepa_best_idx_full_score"] = rows[0]["combined_score"] if rows else None
    elif status == "COMPLETE":
        engine_best = ob._snapshot_best(run_dir / "output" / "sky" / "best" / "best_program.py",
                                        run_dir / "output", run_dir / "verified" / "engine-best")
        manifest["engine_best_sha256"] = _sha(engine_best.read_bytes())
    return _finish_v3(manifest, run_dir, verifier, seed_full)


# ------------------------------------------------------------ sequential control
def _sequential_v3(args) -> dict:
    cc, bc, rbc = _configs(args)
    knobs = engine_knobs(cc, "sequential", args.seed, bc, rbc)
    args.broker_url = ob._broker_url(args.broker_url)
    routing = _reflection_argv(cc, rbc, "sequential", args)
    if routing:
        routing["reflection_url"] = ob._broker_url(routing["reflection_url"] or "")
    lm = make_lm(args.broker_url, bc["model"], bc["max_tokens"], _llm_timeout(bc), bc.get("reasoning_effort"),
                 args.expected_first_prompt_sha256, expected_diagnosis=args.expected_diagnosis_sha256, **routing)
    run_dir, stage, seed, verifier, provenance, seed_screen, seed_full = _setup_v3(args, cc, "sequential", knobs)
    thr = knobs["screen_threshold"]
    best_source, best = seed.read_text(), seed_full
    manifest = {"engine": "sequential", "seed": args.seed, "task": TASK, **provenance, "knobs": knobs,
                "broker_url": args.broker_url, "reflection_url": routing.get("reflection_url"),
                "model": bc["model"], "reflection_model": routing.get("reflection_model"), "run_dir": str(run_dir)}
    status, trace, history, last = "COMPLETE", [], [], None
    for step in range(1, knobs["iterations"] + 1):
        user = (sb.OBJECTIVE + "\n\n" + lb.rejection_note(history) + "Current program:\n```python\n" + best_source
                + "\n```\n\n" + "Evaluator feedback:\n" + best["packet"])
        request_sha256 = _sha(user.encode())
        messages = [{"role": "system", "content": sb.SYSTEM}, {"role": "user", "content": user}]
        row = {"step": step, "packet_seen": PACKET_MARK in user, "request_sha256": request_sha256}
        trace.append(row)
        if request_sha256 == last:
            row["outcome"], status = "guard: refusing to resend an identical consecutive prompt", "GUARD_STOPPED"
            break
        last = request_sha256
        try:
            content = lm(messages)
        except FirstPromptMismatch as exc:
            row["outcome"], status = f"guard: {exc}", "FIRST_PROMPT_MISMATCH"
            break
        except ob.BrokerHalted as exc:
            row["outcome"], status = f"broker stopped: {exc}", "BROKER_STOPPED"
            break
        except (SyntaxError, ValueError) as exc:
            writer = lm.writer if isinstance(lm, ReflectThenWriteLM) else lm
            row["finish_reason"] = writer.last_finish_reason
            reason = f"invalid proposal: {exc}"
            row["outcome"] = reason
            history.append({"step": step, "reason": reason})
            continue
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            row["outcome"], status = f"broker stopped: {exc}", "BROKER_STOPPED"
            break
        writer = lm.writer if isinstance(lm, ReflectThenWriteLM) else lm
        row["finish_reason"] = writer.last_finish_reason
        source = sb.preflight_source(content, writer.last_finish_reason)
        try:
            screen = verifier.evaluate(source, "screen")
            row.update(candidate_hash=screen["candidate_hash"], screen_score=screen["combined_score"])
            if screen["combined_score"] < thr:
                first = next((b for b in screen["artifacts"].get("worst_states", "").split("\n- ") if b), "")
                reason = f"screen {screen['combined_score']:.4f} < threshold {thr}; " + first[:300]
                row.update(outcome=reason, accepted=False)
                history.append({"step": step, "reason": reason})
                continue
            result = verifier.evaluate(source, "full")
        except PermissionError as exc:
            row["outcome"], status = str(exc), "EVAL_BUDGET"
            break
        accepted = result["combined_score"] > best["combined_score"]
        row.update(score=result["combined_score"], within_budget=result["within_budget"], accepted=accepted)
        if accepted:
            best_source, best = source, result
        else:
            reason = (f"rejected: combined {result['combined_score']:.4f} (within {result['within_budget']}, "
                      f"invalid {result['invalid']}) did not beat {best['combined_score']:.4f}")
            row["outcome"] = reason
            history.append({"step": step, "reason": reason})
    (run_dir / "sequential-trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in trace))
    writer = lm.writer if isinstance(lm, ReflectThenWriteLM) else lm
    manifest.update(status=status, steps=trace, mechanism_evidence={
        "accepted_steps": [r["step"] for r in trace if r.get("accepted")],
        "packet_seen_steps": [r["step"] for r in trace if r["packet_seen"]],
        "truncated_steps": [r["step"] for r in trace if r.get("finish_reason") in ("length", "max_tokens")],
        "model_calls": writer.calls, "diagnosis_calls": lm.diagnose.calls if isinstance(lm, ReflectThenWriteLM) else 0,
        "reflection_receipts": writer.receipts,
        "diagnosis_receipts": lm.receipts if isinstance(lm, ReflectThenWriteLM) else []})
    if status in EXCLUDED:
        manifest.update(research_status=status, evaluation_trace=verifier.state["evaluations"],
                        revealed_ids=list(verifier.reveal.ids))
        _write(run_dir, manifest)
        return manifest
    return _finish_v3(manifest, run_dir, verifier, seed_full)


# ------------------------------------------------------------ first prompts
def first_prompt_files(camp, engine, seed):
    return Path(camp) / f"first-prompt-{engine}-s{seed}.sha256", Path(camp) / f"first-prompt-{engine}-s{seed}-diagnosis.sha256"


def _read_hash(path):
    return Path(path).read_text().split()[0] if Path(path).is_file() else None


def captured_first_prompts(capture_dir, reflection_capture_dir=None) -> dict:
    """First solution request (diagnosis text replaced by the placeholder) and first diagnosis request."""
    out = {"solution": None, "diagnosis": None}
    for path in sorted(Path(capture_dir).glob("request-*.json")):
        messages = _load(path)["body"].get("messages", [])
        if sb.is_solution_request(messages) and REFLECT_SYSTEM not in json.dumps(messages):
            out["solution"] = lb.messages_sha256(guard_view(messages))
            break
    if reflection_capture_dir and Path(reflection_capture_dir).is_dir():
        for path in sorted(Path(reflection_capture_dir).glob("request-*.json")):
            messages = _load(path)["body"].get("messages", [])
            if messages and messages[0].get("content") == REFLECT_SYSTEM:
                out["diagnosis"] = lb.messages_sha256(messages)
                break
    return out


def write_first_prompt_v3(capture_dir, reflection_capture_dir, engine, seed, camp=CAMP) -> dict:
    """Write first-prompt-{engine}-s{seed}.{md,sha256} (and -diagnosis.sha256) from an offline mock capture."""
    found = {}
    for path in sorted(Path(capture_dir).glob("request-*.json")):
        messages = _load(path)["body"].get("messages", [])
        if sb.is_solution_request(messages) and REFLECT_SYSTEM not in json.dumps(messages):
            found["solution"] = (path, guard_view(messages))
            break
    if reflection_capture_dir and Path(reflection_capture_dir).is_dir():
        for path in sorted(Path(reflection_capture_dir).glob("request-*.json")):
            messages = _load(path)["body"].get("messages", [])
            if messages and messages[0].get("content") == REFLECT_SYSTEM:
                found["diagnosis"] = (path, messages)
                break
    if "solution" not in found:
        raise FileNotFoundError(f"no captured first {engine} solution request")
    sol_file, diag_file = first_prompt_files(camp, engine, seed)
    md = sol_file.with_suffix(".md")
    fence, lines, out = "`" * 6, [f"# First {engine} prompts, seed {seed} ({TASK})", "",
                                  "Captured offline through the mock (no provider call) with the frozen development "
                                  "set; only development states appear. The solution request is hashed with any "
                                  f"appended diagnosis replaced by `{DIAGNOSIS_PLACEHOLDER}`.", ""], {}
    for kind in ("solution", "diagnosis"):
        if kind not in found:
            continue
        path, messages = found[kind]
        digest = lb.messages_sha256(messages)
        out[kind] = digest
        target = sol_file if kind == "solution" else diag_file
        target.write_text(f"{digest}  first {kind} request of {engine} s{seed} (canonical JSON of messages)\n")
        lines += [f"## {kind} request: `{digest}` (from {Path(path).parent.parent.name}/{Path(path).name})", ""]
        for i, m in enumerate(messages, 1):
            lines += [f"### Message {i}: {m['role']}", "", fence + "text", m["content"], fence, ""]
    md.write_text("\n".join(lines))
    return out


def solution_prompt_hashes(capture_dir) -> list:
    return [lb.messages_sha256(guard_view(_load(p)["body"]["messages"]))
            for p in sorted(Path(capture_dir).glob("request-*.json"))
            if sb.is_solution_request(_load(p)["body"].get("messages", []))]


# ------------------------------------------------------------ approval
_GEPA_FILES = ("gepa/optimize_anything.py", "gepa/adapters/optimize_anything_adapter/optimize_anything_adapter.py",
               "gepa/proposer/reflective_mutation/reflection_lm.py")
_SKY_FILES = tuple("skydiscover/optimize/" + p for p in (
    "config.py", "evaluation/evaluator.py", "utils/metrics.py", "utils/pareto.py", "search/base_database.py",
    "search/adaevolve/database.py", "search/adaevolve/controller.py", "context_builder/adaevolve/builder.py",
    "context_builder/utils.py"))


def _engine_identity(python: Path) -> dict:
    venv = python.parent.parent
    site = next(iter(sorted(venv.glob("lib/python*/site-packages"))), None)
    cfg = venv / "pyvenv.cfg"
    out = {"interpreter": str(python), "interpreter_realpath": os.path.realpath(python) if python.exists() else None,
           "pyvenv_cfg": cfg.read_text() if cfg.is_file() else None}

    def files(names):
        return {n: (_sha((site / n).read_bytes()) if site and (site / n).is_file() else None) for n in names}

    def version(dist):
        meta = next(iter(sorted(site.glob(f"{dist}-*.dist-info")))) if site else None
        return meta.name if meta else None

    out["gepa"] = {"dist": version("gepa"), "files": files(_GEPA_FILES)}
    out["skydiscover"] = {"dist": version("skydiscover"), "files": files(_SKY_FILES)}
    return out


def approval_material_v3(camp=CAMP) -> dict:
    from integrations.research_budget import _dry_run_payload
    from integrations.sort_evaluator import CONTRACT, VERSION, evaluator_hash

    camp = Path(camp)
    cc, bc = _load(camp / "campaign-config.json"), _load(camp / "broker-config.json")
    rpath = camp / cc["reflection"]["broker_config"]
    rbc = _load(rpath) if rpath.is_file() else None
    frozen = ROOT / cc["frozen_manifest"]
    _, dev_sha = lb.development_from_manifest(frozen)
    v3 = ROOT / cc["frozen_v3_manifest"]
    v3m = _load(v3)
    knobs, prompts = {}, {}
    for engine in ARMS:
        for seed in cc["seeds"]:
            knobs[f"{engine}/s{seed}"] = engine_knobs(cc, engine, seed, bc, rbc)
            sol, diag = first_prompt_files(camp, engine, seed)
            prompts[f"{engine}/s{seed}"] = {"solution": _read_hash(sol),
                                            "diagnosis": _read_hash(diag) if engine in ("gepa", "sequential")
                                            else None}
    brokers = {"flash": {"upstream_endpoint": bc["upstream_url"].rstrip("/") + "/chat/completions",
                         "dry_run_payload": _dry_run_payload(bc)}}
    if rbc:
        brokers["reflection"] = {"upstream_endpoint": rbc["upstream_url"].rstrip("/") + "/chat/completions",
                                 "dry_run_payload": _dry_run_payload(rbc)}
    code = {n: _sha(Path(f).read_bytes()) for n, f in (("sort_loop3", __file__), ("sort_backends", sb.__file__),
                                                        ("lift_backends", lb.__file__),
                                                        ("official_backends", ob.__file__))}
    code["research_budget"] = _sha((ROOT / "integrations" / "research_budget.py").read_bytes())
    return {"broker_config": bc, "reflection_broker_config": rbc, "campaign_config": cc, "engine_knobs": knobs,
            "first_prompts": prompts, "brokers": brokers,
            "prompts": {"system": sb.SYSTEM, "objective": sb.OBJECTIVE, "reflect_system": REFLECT_SYSTEM,
                        "diagnosis_append": DIAGNOSIS_APPEND, "diagnosis_placeholder": DIAGNOSIS_PLACEHOLDER,
                        "sky_evaluator_stub": sky_evaluator_source("<VERIFIER>", int(cc["eval_timeout"]) - 30)},
            "packet_format": dict(PACKET_FORMAT, reveal_optimal_max_states=cc["reveal_optimal_max_states"]),
            "instance_score": INSTANCE_SCORE_TEXT, "screen_threshold": cc["screen_threshold"],
            "seed_screen_score": cc["seed_screen_score"], "evox_note": EVOX_NOTE,
            "data": {"seed_sha256": _sha((ROOT / cc["seed_program"]).read_bytes()),
                     "frozen_manifest_sha256": _sha(frozen.read_bytes()), "development_sha256": dev_sha,
                     "frozen_v3_manifest_sha256": _sha(v3.read_bytes()),
                     "instances_sha256": _sha((v3.parent / "instances.json").read_bytes()),
                     "screen_sha256": _sha((v3.parent / "screen-ids.json").read_bytes()),
                     "frozen_v3_recorded": {k: v3m[k] for k in ("instances_sha256", "screen_sha256",
                                                                "development_sha256")}},
            "evaluator": {"version": VERSION, "contract": CONTRACT, "hash": evaluator_hash()},
            "code_sha256": code, "engines": _engine_identity(ROOT / cc["python"])}


def approval_hash_v3(camp=CAMP) -> str:
    return _sha(lb._canonical(approval_material_v3(camp)).encode())


def check_approval_v3(camp=CAMP) -> str:
    camp = Path(camp)
    computed = approval_hash_v3(camp)
    approved = camp / "payload-approved.sha256"
    if not approved.is_file():
        raise SystemExit(f"refusing to start: {approved} is missing (created only after user approval)")
    token = approved.read_text().split()
    if not token or token[0] != computed:
        raise SystemExit(f"refusing to start: payload hash {computed} does not match {approved}")
    cc = _load(camp / "campaign-config.json")
    for path in (camp / "broker-config.json", camp / cc["reflection"]["broker_config"]):
        stored = _load(path).get("dry_run_payload_sha256") if path.is_file() else None
        if stored is not None and stored != computed:
            raise SystemExit(f"refusing to start: {path.name} dry_run_payload_sha256 disagrees")
    return computed


# ------------------------------------------------------------ live
def ledger_paths(camp, engine, seed):
    """(flash, reflection) ledger paths of one live (arm, seed) run; sort_loop3_finalize falls back to these."""
    tag = f"{engine}-s{seed}"
    return Path(camp) / f"broker-ledger-v3.{tag}.json", Path(camp) / f"broker-ledger-v3-reflection.{tag}.json"


def v3_ledgers(camp=CAMP):
    return sorted(Path(camp).glob("broker-ledger-v3*.json"))


def campaign_spend(camp=CAMP) -> float:
    return sum(a.get("charged_usd") or 0.0 for p in v3_ledgers(camp) for a in _load(p).get("attempts", []))


def _broker_command(cfg, ledger, max_requests, port):
    return [sys.executable, "-m", "integrations.research_budget", "serve", "--upstream-url", cfg["upstream_url"],
            "--model", cfg["model"], "--api-key-env", cfg["api_key_env"], "--ledger", str(ledger),
            "--max-requests", str(max_requests), "--max-usd", str(cfg["max_usd_per_run"]),
            "--input-usd-per-million", str(cfg["input_usd_per_million"]),
            "--output-usd-per-million", str(cfg["output_usd_per_million"]), "--port", str(port),
            "--max-tokens", str(cfg["max_tokens"]), "--reasoning-reserve", str(cfg["reasoning_cap_tokens"]),
            "--reasoning-effort", cfg["reasoning_effort"], "--reasoning-cap-tokens", str(cfg["reasoning_cap_tokens"]),
            "--timeout", str(cfg["timeout"])] + (["--upstream-stream"] if cfg.get("upstream_stream") else [])


def _wait_ready(port):
    for _ in range(100):
        try:
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                if r.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise SystemExit(f"local research broker on port {port} did not become ready")


def _live_v3(args):
    camp = getattr(args, "campaign_dir", None) or CAMP
    cc = _load(camp / "campaign-config.json")
    if cc.get("evox_strategy_evolution") is not False:
        raise SystemExit("refusing: evox_strategy_evolution must be false")
    if cc.get("campaign_max_usd") is None:
        raise SystemExit("refusing: campaign_max_usd is null until the scale and reflection model are decided")
    if args.seed not in cc["seeds"]:
        raise SystemExit(f"refusing: seed {args.seed} is not in campaign-config seeds")
    bc = _load(camp / "broker-config.json")
    rpath = camp / cc["reflection"]["broker_config"]
    rbc = _load(rpath) if rpath.is_file() else None
    cap = reflection_cap(cc, args.engine)
    for cfg in [bc] + ([rbc] if cap else []):
        if cfg is None or not os.environ.get(cfg["api_key_env"]):
            raise SystemExit("provider keys must be supplied through the environment")
    digest = check_approval_v3(camp)
    per_run = bc["max_usd_per_run"] + (rbc["max_usd_per_run"] if cap else 0)
    if campaign_spend(camp) + per_run > cc["campaign_max_usd"]:
        raise SystemExit("refusing: campaign spend plus this run's caps would exceed campaign_max_usd")
    stamp = time.strftime("%y%m%d-%H%M%S")
    tag = f"{args.engine}-s{args.seed}"
    run_dir = camp / f"live-v3-{tag}-{stamp}"
    ledger, rledger = ledger_paths(camp, args.engine, args.seed)
    logs = [camp / f"broker-v3-{tag}-{stamp}.log", camp / f"broker-v3-reflection-{tag}-{stamp}.log"]
    if run_dir.exists() or ledger.exists() or (cap and rledger.exists()) or any(p.exists() for p in logs):
        raise SystemExit("fresh run, ledger or broker log path already exists")
    procs = []
    try:
        with logs[0].open("w") as log:
            procs.append(subprocess.Popen(_broker_command(bc, ledger, cc["engines"][args.engine]["max_requests"],
                                                          cc["broker_port"]), cwd=ROOT, stdout=log,
                                          stderr=subprocess.STDOUT))
        _wait_ready(cc["broker_port"])
        if cap:
            with logs[1].open("w") as log:
                procs.append(subprocess.Popen(_broker_command(rbc, rledger, cap, cc["reflection"]["broker_port"]),
                                              cwd=ROOT, stdout=log, stderr=subprocess.STDOUT))
            _wait_ready(cc["reflection"]["broker_port"])
        sol, diag = first_prompt_files(camp, args.engine, args.seed)
        argv = ["--engine", args.engine, "--seed", str(args.seed), "--run-dir", str(run_dir),
                "--campaign-config", str(camp / "campaign-config.json"),
                "--broker-config", str(camp / "broker-config.json"), "--reflection-config", str(rpath),
                "--broker-url", f"http://127.0.0.1:{cc['broker_port']}/v1", "--ledger", str(ledger),
                "--python", str(ROOT / cc["python"])]
        if cap:
            argv += ["--reflection-url", f"http://127.0.0.1:{cc['reflection']['broker_port']}/v1",
                     "--reflection-ledger", str(rledger)]
        for flag, path in (("--expected-first-prompt-sha256", sol), ("--expected-diagnosis-sha256", diag)):
            if _read_hash(path):
                argv += [flag, _read_hash(path)]
        run_args = _parser().parse_args(["run"] + argv)
        out = _sequential_v3(run_args) if args.engine == "sequential" else _launch_v3(run_args)
        out["approved_payload_sha256"] = digest
        # finalize reads the ledgers from here (paths relative to the repository root)
        out.update(ledger=str(Path(ledger).resolve().relative_to(ROOT.resolve())),
                   reflection_ledger=str(Path(rledger).resolve().relative_to(ROOT.resolve())) if cap else None)
        _write(run_dir, out)
        return out
    finally:
        for proc in procs:
            proc.terminate()
            proc.wait()


# ------------------------------------------------------------ CLI
def _parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("run", help="one (arm, seed) run from explicit configs (offline smokes; live uses `live`)")
    p.add_argument("--engine", required=True, choices=ARMS)
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--run-dir", required=True, type=Path)
    p.add_argument("--campaign-config", type=Path, default=CAMP / "campaign-config.json")
    p.add_argument("--broker-config", type=Path, default=CAMP / "broker-config.json")
    p.add_argument("--reflection-config", type=Path, default=CAMP / "broker-config-reflection.json")
    p.add_argument("--broker-url", required=True)
    p.add_argument("--reflection-url")
    p.add_argument("--ledger", type=Path, help="flash ledger (receipts drive the Sky prompt and EvoX leak checks)")
    p.add_argument("--reflection-ledger", type=Path)
    p.add_argument("--python", type=Path, default=ROOT / ".venv-official" / "bin" / "python")
    p.add_argument("--jobs", type=int, default=8)
    p.add_argument("--no-tables", action="store_true")
    p.add_argument("--expected-first-prompt-sha256")
    p.add_argument("--expected-diagnosis-sha256")
    w = sub.add_parser("_gepa_worker")
    for flag in ("seed", "dataset", "knobs", "run-dir"):
        w.add_argument("--" + flag, required=True, type=Path)
    for flag in ("broker-url", "verifier-url", "model"):
        w.add_argument("--" + flag, required=True)
    for flag in ("max-tokens", "llm-timeout", "eval-timeout"):
        w.add_argument("--" + flag, required=True, type=int)
    w.add_argument("--reasoning-effort")
    w.add_argument("--expected-first-prompt-sha256")
    w.add_argument("--expected-diagnosis-sha256")
    w.add_argument("--reflection-url")
    w.add_argument("--reflection-model")
    w.add_argument("--reflection-max-tokens", type=int)
    w.add_argument("--reflection-timeout", type=int)
    w.add_argument("--reflection-effort")
    w.add_argument("--diagnosis-max-chars", type=int, default=4000)
    fp = sub.add_parser("first-prompt", help="hashes of the first solution and diagnosis requests of a capture")
    fp.add_argument("--capture-dir", required=True, type=Path)
    fp.add_argument("--reflection-capture-dir", type=Path)
    fp.add_argument("--all-solutions", action="store_true")
    fp.add_argument("--write", nargs=2, metavar=("ENGINE", "SEED"),
                    help="write first-prompt-ENGINE-sSEED.{md,sha256} into the campaign directory")
    for name in ("approval-hash", "check-approval", "campaign-spend"):
        a = sub.add_parser(name)
        a.add_argument("--campaign-dir", type=Path, default=CAMP,
                       help="directory holding campaign-config.json/broker-config.json (default: the "
                            "production sort-m9-v3-260925 campaign)")
        if name == "approval-hash":
            a.add_argument("--write-material", type=Path)
    lv = sub.add_parser("live")
    lv.add_argument("--engine", required=True, choices=ARMS)
    lv.add_argument("--seed", required=True, type=int)
    lv.add_argument("--campaign-dir", type=Path, default=CAMP,
                    help="directory holding campaign-config.json/broker-config.json/broker-config-reflection.json "
                         "(default: the production sort-m9-v3-260925 campaign); the approval hash is computed "
                         "from this same directory, so a reduced check config here is covered by its own hash")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.action == "approval-hash":
        if args.write_material:
            args.write_material.write_text(
                json.dumps(approval_material_v3(args.campaign_dir), indent=2, sort_keys=True) + "\n")
        print(approval_hash_v3(args.campaign_dir))
        return
    if args.action == "check-approval":
        print(check_approval_v3(args.campaign_dir))
        return
    if args.action == "campaign-spend":
        print(json.dumps({"charged_usd": campaign_spend(args.campaign_dir),
                          "ledgers": [p.name for p in v3_ledgers(args.campaign_dir)]}))
        return
    if args.action == "first-prompt":
        out = captured_first_prompts(args.capture_dir, args.reflection_capture_dir)
        if args.write:
            out["written"] = write_first_prompt_v3(args.capture_dir, args.reflection_capture_dir, args.write[0],
                                                   int(args.write[1]))
        if args.all_solutions:
            out["all_solutions"] = solution_prompt_hashes(args.capture_dir)
        print(json.dumps(out))
        return
    if args.action == "_gepa_worker":
        return _gepa_worker_v3(args)
    if args.action == "run":
        result = _sequential_v3(args) if args.engine == "sequential" else _launch_v3(args)
    else:
        result = _live_v3(args)
    keep = ("engine", "seed", "status", "research_status", "run_dir", "seed_result", "verified_best_result")
    print(json.dumps({k: result.get(k) for k in keep}, default=str))


if __name__ == "__main__":
    main()
