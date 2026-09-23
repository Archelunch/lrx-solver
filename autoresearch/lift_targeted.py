"""Targeted lift check around the far layers of the smaller graph (Route B).

For every u at distance >= P - k in the smaller graph (m, r-1) and every
insertion position j of the marked zero, H_P(u, j) is computed exactly by
lift_forward.forward_h (exhaustive forward search, no shared DP code with the
trusted engines). A_P(v) <= H_P(u, j) for v = u with a zero inserted at j, so
only pairs with H_P(u, j) > P + m - 2 (or no admissible lift) need the full
A_P(v); lift_forward.check_vector computes it over all deletions and replays
every witness word.

Scope: exhaustive over the vectors v with at least one zero whose deletion is
at smaller-graph distance >= P - k; silent about every other vector. A state
cap makes a pair INCOMPLETE, which is reported and never counted as a lift.

    python autoresearch/lift_targeted.py M R --k 2 --out PATH [--table-cache DIR]
"""

import argparse
import hashlib
import json
import multiprocessing
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "autoresearch"))

from lift_forward import check_vector, forward_h, smaller_table  # noqa: E402
from src.lrx.table_bfs import Ranker, build_table  # noqa: E402

REGISTRY = ROOT / "datasets" / "generated"
_DIST = None


def load_table(m, r, cache):
    """Smaller-graph distances: registry table, else a cached or fresh full BFS."""
    if cache is None or (REGISTRY / f"dist_m{m}_r{r - 1}.bin").exists():
        return smaller_table(m, r)
    stem = Path(cache) / f"dist_m{m}_r{r - 1}"
    bin_path, meta_path = stem.with_suffix(".bin"), stem.with_suffix(".json")
    if bin_path.exists():
        meta = json.loads(meta_path.read_text())
        dist = bin_path.read_bytes()
        if (
            hashlib.sha256(dist).hexdigest() != meta["table_sha256"]
            or not meta["complete"]
        ):
            raise ValueError(f"cached table unusable: {bin_path}")
        return dist, meta["radius"], f"cache {bin_path}"
    dist, meta = build_table(m, r - 1, workers=8)
    if not meta["complete"]:
        raise RuntimeError(f"BFS incomplete for m={m} r={r - 1}")
    dist = bytes(dist)
    bin_path.parent.mkdir(parents=True, exist_ok=True)
    bin_path.write_bytes(dist)
    meta["table_sha256"] = hashlib.sha256(dist).hexdigest()
    meta_path.write_text(json.dumps(meta) + "\n")
    return dist, meta["radius"], "bfs"


def far_vectors(dist, m, r, lo, hi):
    """Smaller-graph vectors with lo <= distance <= hi, in rank order per layer."""
    ranker = Ranker(m, r - 1)
    out = []
    for t in range(hi, lo - 1, -1):
        byte = bytes([t])
        start = dist.find(byte)
        while start >= 0:
            out.append((t, ranker.vector(ranker.unrank(start))))
            start = dist.find(byte, start + 1)
    return out


def _pair(args):
    m, r, u, j, q, max_states = args
    res = forward_h(m, r, u, j, q, _DIST, max_states, witness=False)
    return u, j, res["H"], res["status"], res["states"]


def run(m, r, k, max_states, workers, cache, flag_max_states=None):
    global _DIST
    n = m + r
    t0 = time.perf_counter()
    _DIST, p, source = load_table(m, r, cache)
    budget = p + m - 2
    far = far_vectors(_DIST, m, r, p - k, p)
    layers = Counter(t for t, _ in far)
    jobs = [(m, r, u, j, p, max_states) for _, u in far for j in range(n)]
    if workers > 1:
        with multiprocessing.get_context("fork").Pool(workers) as pool:
            pairs = pool.map(_pair, jobs, chunksize=4)
    else:
        pairs = list(map(_pair, jobs))
    hist = Counter()
    incomplete, flagged = [], {}
    for u, j, h, status, states in pairs:
        if status != "COMPLETE":
            incomplete.append({"u": list(u), "j": j, "states": states})
            continue
        hist["INF" if h is None else h - budget] += 1
        if h is None or h > budget:
            v = u[:j] + (0,) + u[j:]
            flagged[v] = flagged.get(v, []) + [{"u": list(u), "j": j, "H": h}]
    over = []
    for v, hits in sorted(flagged.items()):
        res = check_vector(m, r, v, p, _DIST, flag_max_states or max_states)
        res["flagged_by"] = hits
        res["over_budget"] = res["status"] == "COMPLETE" and (
            res["A"] is None or res["A"] > budget
        )
        over.append(res)
    covered = {u[:j] + (0,) + u[j:] for _, u in far for j in range(n)}
    return {
        "m": m,
        "r": r,
        "n": n,
        "P": p,
        "budget_P_m_2": budget,
        "k": k,
        "smaller_table": source,
        "far_layer_sizes": {str(t): layers[t] for t in sorted(layers, reverse=True)},
        "pairs": len(jobs),
        "covered_vectors": len(covered),
        "hist_H_minus_budget": {
            str(x): hist[x]
            for x in sorted(hist, key=lambda x: (x == "INF", x if x != "INF" else 0))
        },
        "incomplete_pairs": incomplete,
        "flagged_vectors": over,
        "over_budget_vectors": [x["v"] for x in over if x["over_budget"]],
        "unresolved_vectors": [x["v"] for x in over if x["status"] != "COMPLETE"],
        "scope": (
            "finite: exhaustive over vectors with a zero whose deletion is at "
            f"smaller-graph distance >= P-{k} on this graph; silent elsewhere"
        ),
        "method": "autoresearch/lift_targeted.py (lift_forward.forward_h per pair)",
        "seconds": round(time.perf_counter() - t0, 1),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("m", type=int)
    ap.add_argument("r", type=int)
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--max-states", type=int, default=8_000_000)
    ap.add_argument("--flag-max-states", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--table-cache", default=None)
    ap.add_argument("--out", required=True, help="new JSON file (never overwritten)")
    args = ap.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    rep = run(
        args.m,
        args.r,
        args.k,
        args.max_states,
        args.workers,
        args.table_cache,
        args.flag_max_states,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1) + "\n")
    print(
        json.dumps(
            {
                k: rep[k]
                for k in (
                    "m",
                    "r",
                    "P",
                    "budget_P_m_2",
                    "k",
                    "far_layer_sizes",
                    "pairs",
                    "covered_vectors",
                    "hist_H_minus_budget",
                    "over_budget_vectors",
                    "unresolved_vectors",
                    "seconds",
                )
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
