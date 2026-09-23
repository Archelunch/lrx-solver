"""Tiered deterministic evaluator for v2 JSON candidates.

sanity -> train -> heldout. A candidate that fails sanity never reaches train.
Heldout results are recorded with feedback=False and must not be shown to a
proposer. Scores are finite-sample evidence only: a zero-failure score on
probes is not a certificate for the whole graph (use `certify` for that) and
never a universal statement.
"""

import hashlib
import json
import os
import random
import time
from pathlib import Path

from .candidates import Candidate, CandidateError, run_beam, run_rules
from .certificates import replay_visible
from .dsl import Env, EvalError, budget, features
from .table_bfs import DistanceTable, Ranker

ROOT_DIR = Path(__file__).resolve().parents[2]
REGISTRY = ROOT_DIR / "datasets" / "registry.json"
LOCK = ROOT_DIR / "datasets" / "tables.lock.json"
TABLE_DIR = ROOT_DIR / "datasets" / "generated"


def paths():
    """(registry, lock, table_dir), overridable by LRX_REGISTRY / LRX_TABLES_LOCK /
    LRX_TABLE_DIR so spawned evaluation workers and tests see the same data."""
    env = os.environ
    return (
        Path(env.get("LRX_REGISTRY", REGISTRY)),
        Path(env.get("LRX_TABLES_LOCK", LOCK)),
        Path(env.get("LRX_TABLE_DIR", TABLE_DIR)),
    )


SPLITS = {
    "sanity": ("sanity",),
    "train": ("sanity", "train"),
    "heldout": ("sanity", "train", "heldout"),
}
FAIL_WEIGHT = 1000.0
EXCESS_WEIGHT = 10.0


def evaluator_hash():
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    for path in paths()[:2]:
        if path.exists():
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def load_registry(path=None):
    return json.loads(Path(path or paths()[0]).read_text())


_TABLES = {}
_PROBES = {}


def get_table(m, r, table_dir=None, lock_path=None):
    _, lock_default, dir_default = paths()
    table_dir = table_dir or dir_default
    lock_path = lock_path or lock_default
    key = (m, r, str(table_dir))
    if key not in _TABLES:
        table = DistanceTable(table_dir, m, r)
        lock = (
            json.loads(Path(lock_path).read_text()) if Path(lock_path).exists() else {}
        )
        expected = lock.get(f"m{m}_r{r}")
        if expected is None:
            raise ValueError(f"table m={m} r={r} missing from tables.lock.json")
        if expected != table.meta["table_sha256"]:
            raise ValueError(f"table m={m} r={r} does not match tables.lock.json")
        _TABLES[key] = table
    return _TABLES[key]


def _structured(m, r):
    n = m + r
    root = tuple(range(1, m + 1)) + (0,) * r
    rev = tuple(range(m, 0, -1)) + (0,) * r
    spread = [0] * n
    step = n / m
    slots = sorted({int(i * step) for i in range(m)})
    if len(slots) == m:
        for token, slot in zip(range(m, 0, -1), slots):
            spread[slot] = token
    out = [root, root[n // 2 :] + root[: n // 2], rev, rev[1:] + rev[:1]]
    if len(slots) == m:
        out.append(tuple(spread))
    return out


def probe_states(graph, probe, table=None, exhaustive_sanity=True):
    """Deterministic probe set: exhaustive for sanity, else hard + random."""
    m, r = graph["m"], graph["r"]
    exhaustive = exhaustive_sanity and graph["role"] == "sanity"
    key = (m, r, exhaustive, json.dumps(probe, sort_keys=True), table is not None)
    if key in _PROBES:
        return _PROBES[key]
    ranker = Ranker(m, r)
    if exhaustive:
        states = [ranker.vector(ranker.unrank(c)) for c in range(ranker.size)]
        # Fixed shuffle: a fail-fast stop then leaves a uniform sample, so the
        # failure rate can be estimated from the states actually checked.
        random.Random(f"lrx-sanity-order-v1:{m}:{r}").shuffle(states)
    else:
        rng = random.Random(f"lrx-probe-v1:{m}:{r}")
        seen = set()
        states = []

        def add(v):
            if v not in seen:
                seen.add(v)
                states.append(v)

        for v in _structured(m, r):
            add(v)
        if table is not None:
            layers = probe["hard_layers"]
            per_layer = max(1, probe["hard"] // layers)
            hard = []
            for d in range(table.radius, table.radius - layers, -1):
                hard.extend(table.spread_at(d, per_layer))
            for v in hard:
                add(v)
        for _ in range(probe["random"]):
            add(ranker.vector(ranker.unrank(rng.randrange(ranker.size))))
    _PROBES[key] = states
    return states


def _neighbours(v):
    return (v[1:] + v[:1], v[-1:] + v[:-1], (v[1], v[0]) + v[2:])


def _check_state(cand, v, m, r, d, limits):
    """Return (ok, value, gap, reason). value is the quantity compared with T."""
    kind = cand.kind
    root = tuple(range(1, m + 1)) + (0,) * r
    if kind == "bound":
        f = cand.fn(Env(v, m, r))
        if d is not None and f < d:
            return False, f, None, f"f={f} < d={d}"
        return True, f, None if d is None else f - d, None
    if kind == "potential":
        phi = cand.fn(Env(v, m, r))
        if phi < 0:
            return False, phi, None, f"phi={phi} < 0"
        if v != root:
            best = min(cand.fn(Env(u, m, r)) for u in _neighbours(v))
            if best > phi - 1:
                return False, phi, None, f"no descent: phi={phi}, min neighbour {best}"
        if d is not None and phi < d:
            return False, phi, None, f"phi={phi} < d={d}"
        return True, phi, None if d is None else phi - d, None
    if kind == "rules":
        word, reason = run_rules(cand, v, m, r, limits["max_steps"](m + r))
    else:
        word, reason = run_beam(cand, v, m, r, limits["max_expansions"])
    if word is None:
        return False, None, None, f"UNSOLVED ({reason})"
    if replay_visible(v, word, max_steps=len(word) + 1) != root:
        return False, None, None, "replay mismatch"
    length = len(word)
    if d is not None and length < d:
        return (
            False,
            length,
            None,
            f"word shorter than exact distance {d}: evaluator bug",
        )
    return True, length, None if d is None else length - d, None


def evaluate_graph(cand, graph, probe, limits, keep_worst=4):
    m, r = graph["m"], graph["r"]
    n = m + r
    T = budget(m, r)
    t_applies = m >= 8
    table = get_table(m, r) if graph.get("table") else None
    out = {
        "graph": f"m{m}r{r}",
        "m": m,
        "r": r,
        "n": n,
        "role": graph["role"],
        "T": T,
        "T_applies": t_applies,
        "radius": table.radius if table else None,
    }
    if cand.kind == "radius":
        f = cand.radius_value(m, r)
        fails = int(table is not None and f < table.radius)
        excess = f - T if t_applies else None
        gap = f - table.radius if table else 0
        out.update(
            checked=1,
            failures=fails,
            value_max=f,
            excess_T=excess,
            gap_mean=gap,
            worst=[]
            if not fails
            else [{"reason": f"predicted {f} < radius {table.radius}"}],
        )
        out["score"] = _score(out)
        return out
    # Beam search is too slow for exhaustive sanity; it gets sampled probes.
    states = probe_states(graph, probe, table, exhaustive_sanity=cand.kind != "beam")
    fails, gaps, values, worst = 0, [], [], []
    reasons = {}
    skipped = 0
    slow = cand.kind in ("rules", "beam")
    deadline = time.perf_counter() + limits["max_seconds_per_graph"]
    incomplete = 0
    for index, v in enumerate(states):
        if time.perf_counter() > deadline:
            incomplete = len(states) - index
            break
        if slow and fails >= limits["max_failures_per_graph"]:
            # Fail fast: unchecked states are scored as failures, reported apart.
            skipped = len(states) - index
            break
        d = table.distance(v) if table else None
        try:
            ok, value, gap, reason = _check_state(cand, v, m, r, d, limits)
        except (EvalError, ZeroDivisionError, OverflowError, RecursionError) as exc:
            ok, value, gap, reason = False, None, None, f"eval error: {exc}"
        if value is not None:
            values.append(value)
        if gap is not None:
            gaps.append(gap)
        if not ok:
            fails += 1
            tag = reason.split(":")[0].split(" (")[0].split("=")[0]
            reasons[tag] = reasons.get(tag, 0) + 1
            if len(worst) < keep_worst:
                worst.append({"v": list(v), "d": d, "reason": reason})
    vmax = max(values) if values else None
    out.update(
        checked=len(states) - incomplete - skipped,
        incomplete=incomplete,
        skipped_after_failures=skipped,
        failures=fails,
        failure_kinds=reasons,
        value_max=vmax,
        excess_T=(vmax - T) if (t_applies and vmax is not None) else None,
        gap_mean=round(sum(gaps) / len(gaps), 3) if gaps else None,
        gap_max=max(gaps) if gaps else None,
        worst=worst,
    )
    if not fails and not incomplete and values:
        top = sorted(zip(values, range(len(states))), reverse=True)[:2]
        out["largest"] = [
            {
                "v": list(states[i]),
                "value": val,
                "d": table.distance(states[i]) if table else None,
            }
            for val, i in top
        ]
    out["score"] = _score(out)
    return out


def _score(g):
    incomplete = g.get("incomplete", 0)
    if g.get("skipped_after_failures"):
        # Fail-fast stop on a shuffled probe list: estimate the failure rate
        # from the checked prefix. The graph is failed either way.
        rate = g["failures"] / max(1, g["checked"])
        g["fail_rate_estimated"] = True
    else:
        # INCOMPLETE (time cap) is ranked like a failure but reported
        # separately; it is never a counterexample or a lower bound.
        rate = (g["failures"] + incomplete) / max(1, g["checked"] + incomplete)
    g["fail_rate"] = round(rate, 4)
    score = -FAIL_WEIGHT * rate
    if g.get("excess_T") is not None and g["excess_T"] > 0:
        score -= EXCESS_WEIGHT * g["excess_T"]
    if g.get("gap_mean"):
        score -= g["gap_mean"]
    return round(score, 4)


DEFAULT_LIMITS = {
    "max_steps": lambda n: 4 * n * n,
    "max_expansions": 3_000,
    "max_seconds_per_graph": 20.0,
    "max_failures_per_graph": 25,
}


def evaluate(spec, split="train", registry=None, graphs=None):
    """Evaluate a candidate spec. Returns a JSON-serialisable result dict."""
    start = time.perf_counter()
    registry = registry or load_registry()
    base: dict = {"split": split, "evaluator_sha256": evaluator_hash()}
    try:
        cand = Candidate(spec)
    except CandidateError as exc:
        return dict(
            base,
            valid=False,
            error=str(exc),
            score=-1e6,
            feasible=False,
            graphs=[],
            instances={},
        )
    base.update(candidate_hash=cand.hash, kind=cand.kind, valid=True, error=None)
    roles = SPLITS[split]
    probe = registry["probe"]
    results = []
    stopped = None
    for role in roles:
        tier = [g for g in registry["graphs"] if g["role"] == role]
        if graphs and role != "sanity":
            tier = [g for g in tier if f"m{g['m']}r{g['r']}" in graphs]
        tier_results = [evaluate_graph(cand, g, probe, DEFAULT_LIMITS) for g in tier]
        for g in tier_results:
            g["feedback"] = role != "heldout"
        results.extend(tier_results)
        if role == "sanity" and any(
            g["failures"] or g.get("incomplete") for g in tier_results
        ):
            stopped = "sanity failure; later tiers skipped"
            break
    visible = [g for g in results if g["feedback"]]
    score = sum(g["score"] for g in visible) / max(1, len(visible))
    if stopped:
        score -= FAIL_WEIGHT
    feasible = not stopped and all(
        g["failures"] == 0 and not g.get("incomplete") and (g.get("excess_T") or 0) <= 0
        for g in results
    )
    return dict(
        base,
        score=round(score, 4),
        feasible=feasible,
        stopped=stopped,
        instances={g["graph"]: g["score"] for g in visible},
        heldout={g["graph"]: g["score"] for g in results if not g["feedback"]},
        graphs=results,
        seconds=round(time.perf_counter() - start, 3),
    )


def certify(spec, m, r):
    """Exhaustive check of a bound/potential candidate on one complete table.

    A pass is a finite statement about graph (m, r) only.
    """
    cand = Candidate(spec)
    if cand.kind not in ("bound", "potential"):
        raise CandidateError("certify supports bound and potential kinds")
    table = get_table(m, r)
    ranker = table.ranker
    failures, worst, vmax = 0, [], None
    for code in range(ranker.size):
        v = ranker.vector(ranker.unrank(code))
        d = table.dist[code]
        try:
            ok, value, _, reason = _check_state(cand, v, m, r, d, DEFAULT_LIMITS)
        except (EvalError, ZeroDivisionError, OverflowError) as exc:
            ok, value, reason = False, None, f"eval error: {exc}"
        if value is not None:
            vmax = value if vmax is None else max(vmax, value)
        if not ok:
            failures += 1
            if len(worst) < 10:
                worst.append({"v": list(v), "d": d, "reason": reason})
    T = budget(m, r)
    return {
        "candidate_hash": cand.hash,
        "m": m,
        "r": r,
        "states": ranker.size,
        "complete": True,
        "failures": failures,
        "value_max": vmax,
        "T": T,
        "radius": table.radius,
        "holds_on_graph": failures == 0,
        "within_T": vmax is not None and vmax <= T,
        "worst": worst,
        "evaluator_sha256": evaluator_hash(),
        "scope": "finite: this graph only",
    }


def feature_dump(v, m, r):
    return features(v, m, r)


def build_registry_tables(
    workers=1,
    max_bytes=4 * 1024**3,
    registry=None,
    table_dir=None,
    lock_path=None,
    log=None,
):
    """Build missing tables named in the registry and record their hashes."""
    from .table_bfs import build_table, table_paths, write_table

    registry = registry or load_registry()
    _, lock_default, dir_default = paths()
    table_dir = table_dir or dir_default
    lock_path = lock_path or lock_default
    lock = json.loads(Path(lock_path).read_text()) if Path(lock_path).exists() else {}
    report = []
    for g in registry["graphs"]:
        if not g.get("table"):
            continue
        m, r = g["m"], g["r"]
        bin_path, meta_path = table_paths(table_dir, m, r)
        if bin_path.exists():
            meta = json.loads(meta_path.read_text())
            status = "existing"
        else:
            dist, meta = build_table(m, r, workers=workers, max_bytes=max_bytes)
            if not meta["complete"]:
                raise RuntimeError(f"INCOMPLETE table m={m} r={r}")
            meta = write_table(table_dir, m, r, dist, meta)
            status = "built"
        key = f"m{m}_r{r}"
        if key in lock and lock[key] != meta["table_sha256"]:
            raise ValueError(f"{key}: rebuilt table differs from locked hash")
        lock[key] = meta["table_sha256"]
        row = {
            "graph": key,
            "status": status,
            "radius": meta["radius"],
            "states": meta["states"],
            "seconds": meta["seconds"],
        }
        report.append(row)
        if log:
            log(row)
    Path(lock_path).write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    return report
