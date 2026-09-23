"""Route B sweep: A_q(v) for every visible v over a window of projection caps.

One pass of the layer loop of src/lrx/lifting_fast.h_layers (its transitions,
terminal mask and closure, reproduced step for step) yields
A_q(v) = min_j H_q(v\\j, j) after every layer q in [qmin, qmax]. The marked
rank is visible_rank * r + (index of the marked zero among v's zeros), because
the marked zero is the last token of the Lehmer code; so A_q is a reshape-min.

Counts use the FIXED lifting budget P + m - 2 with P = E_{r-1}(n-1), so rows
with q > P answer "does a larger projection cap bring every lift within the
budget?". At q = P the histogram must equal `python -m src.lrx.cli lift M R`.

    python autoresearch/lift_sweep.py M R --qmin Q0 --qmax Q1 --out PATH [--v 2,1,0,0,0,7,8,6,5,4,3]

Finite and exhaustive on this graph only. INF means no admissible lift after
the complete computation; memory refusals raise before any result is written.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.lrx.lifting_fast import INF, _terminal_mask, build_transitions  # noqa: E402
from src.lrx.table_bfs import DistanceTable, Ranker, build_table  # noqa: E402


def distances(m, r):
    """(uint8 numpy distances, radius): registry table if present, else full BFS."""
    try:
        table = DistanceTable(ROOT / "datasets" / "generated", m, r)
        return np.frombuffer(table.dist, dtype=np.uint8), table.radius, "registry"
    except FileNotFoundError:
        dist, meta = build_table(m, r, workers=1 if m + r <= 10 else 8)
        if not meta["complete"]:
            raise RuntimeError(f"BFS incomplete for m={m} r={r}")
        return np.frombuffer(bytes(dist), dtype=np.uint8), meta["radius"], "bfs"


def _describe(code, a, h, d, ranker, small, d_small, r):
    v = ranker.vector(ranker.unrank(int(code)))
    zeros = [i for i, x in enumerate(v) if x == 0]
    deletions = []
    for index, j in enumerate(zeros):
        u = v[:j] + v[j + 1 :]
        deletions.append(
            {
                "j": j,
                "d_small": int(d_small[small.rank(small.positions(u))]),
                "H": int(h[r * int(code) + index]),
            }
        )
    return {"v": list(v), "A": int(a[code]), "d": int(d[code]), "deletions": deletions}


def layer_iter(trans, m, r, qmax, log=None):
    """Yield (q, H_q over marked ranks) for q = 0..qmax, as lifting_fast.h_layers."""
    space, targets, changes, loops = trans
    terminal = _terminal_mask(space, m, r)
    init = np.where(terminal, np.int16(0), INF).astype(np.int16)
    free_edges = [(k, np.nonzero(~changes[k] & ~loops[k])[0]) for k in range(3)]

    def closure(values):
        for _ in range(2):
            for k, idx in free_edges:
                cand = values[targets[k, idx]] + 1
                values[idx] = np.minimum(values[idx], cand)
        return values

    current = closure(init.copy())
    yield 0, current
    for level in range(1, qmax + 1):
        t0 = time.perf_counter()
        nxt = init.copy()
        for k in range(3):
            idx = changes[k]
            cand = current[targets[k][idx]] + 1
            nxt[idx] = np.minimum(nxt[idx], cand)
        np.minimum(nxt, INF, out=nxt)
        current = closure(nxt)
        if log:
            log(f"m{m}r{r} layer {level}/{qmax} {time.perf_counter() - t0:.1f}s")
        yield level, current


def lift_min(h, r):
    """A over visible ranks: min over the r consecutive marked ranks of each v."""
    return h.reshape(-1, r).min(axis=1)


def family(m, r):
    """Candidate obstruction shapes (2,1,0^r,m,...,3) and (2,1,0^r,m-1,m,m-2,...,3)."""
    tail = list(range(m, 2, -1))
    swapped = [m - 1, m] + list(range(m - 2, 2, -1))
    return [tuple([2, 1] + [0] * r + tail), tuple([2, 1] + [0] * r + swapped)]


def sweep(m, r, qmin=None, qmax=None, vectors=(), listing=12, log=None, rel=(-3, 5)):
    start = time.perf_counter()
    d_small, p, small_src = distances(m, r - 1)
    d_big, radius, big_src = distances(m, r)
    qmin = max(0, p + rel[0]) if qmin is None else qmin
    qmax = p + rel[1] if qmax is None else qmax
    budget = p + m - 2
    d = d_big.astype(np.int16)
    ranker, small = Ranker(m, r), Ranker(m, r - 1)
    wanted = [(tuple(v), ranker.rank(ranker.positions(tuple(v)))) for v in vectors]

    trans = build_transitions(m, r)
    space = trans[0]
    if space.size != d.size * r:
        raise AssertionError("marked/visible rank layout mismatch")

    rows = []
    for level, current in layer_iter(trans, m, r, qmax, log):
        if level < qmin:
            continue
        a = lift_min(current, r)
        finite = a < INF
        over = finite & (a > budget)
        gt_d = finite & (a > d)
        vals, counts = np.unique(a[finite].astype(int) - budget, return_counts=True)
        row = {
            "q": level,
            "q_minus_P": level - p,
            "no_admissible_lift": int((~finite).sum()),
            "max_finite_A": int(a[finite].max()) if finite.any() else None,
            "over_budget": int(over.sum()),
            "A_gt_d": int(gt_d.sum()),
            "A_eq_d": int((finite & (a == d)).sum()),
            "A_below_d": int((finite & (a < d)).sum()),
            "hist_A_minus_budget": {
                str(k): int(c) for k, c in zip(vals, counts) if k >= -3
            },
        }
        over_codes = np.nonzero(over)[0]
        over_codes = over_codes[np.argsort(-a[over_codes], kind="stable")][:listing]
        row["over_budget_examples"] = [
            _describe(c, a, current, d, ranker, small, d_small, r) for c in over_codes
        ]
        gt_codes = np.nonzero(gt_d)[0]
        gt_codes = gt_codes[np.argsort(-(a[gt_codes] - d[gt_codes]), kind="stable")]
        row["A_gt_d_examples"] = [
            _describe(c, a, current, d, ranker, small, d_small, r)
            for c in gt_codes[:listing]
        ]
        row["requested"] = [
            _describe(code, a, current, d, ranker, small, d_small, r)
            for _, code in wanted
        ]
        rows.append(row)
        if log:
            log(
                f"m{m}r{r} q={level} max_A={row['max_finite_A']} over={row['over_budget']}"
                f" inf={row['no_admissible_lift']} A>d={row['A_gt_d']}"
            )
        if level >= p and row["A_eq_d"] == d.size:
            break  # A_q is non-increasing in q and >= d: nothing changes above.

    def first(pred):
        return next((row["q"] for row in rows if pred(row)), None)

    q_budget = first(lambda x: x["over_budget"] == 0 and x["no_admissible_lift"] == 0)
    q_eq = first(lambda x: x["A_eq_d"] == d.size)
    return {
        "m": m,
        "r": r,
        "n": m + r,
        "P": p,
        "budget_P_m_2": budget,
        "true_radius": radius,
        "conjectured_T": m * (m + 1) // 2 + (r - 1) * (m - 2),
        "conjecture_domain": m >= 8 and r >= 2,
        "visible_states": int(d.size),
        "marked_states": int(space.size),
        "window": [qmin, qmax],
        "rows": rows,
        "q_budget": q_budget,
        "q_budget_note": None
        if q_budget is not None or rows[0]["q"] > qmin
        else "not reached in window",
        "q_all_equal_d": q_eq,
        "tables": {"smaller": small_src, "visible": big_src},
        "status": "COMPLETE",
        "scope": "finite: this graph only",
        "method": "autoresearch/lift_sweep.py (layer loop of lifting_fast.h_layers)",
        "seconds": round(time.perf_counter() - start, 1),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("m", type=int)
    ap.add_argument("r", type=int)
    ap.add_argument("--qmin", type=int, help="first cap (default P - below)")
    ap.add_argument("--qmax", type=int, help="last cap (default P + above)")
    ap.add_argument("--below", type=int, default=3)
    ap.add_argument("--above", type=int, default=5)
    ap.add_argument("--v", action="append", default=[], help="vector to report")
    ap.add_argument("--family", action="store_true", help="also report family()")
    ap.add_argument("--listing", type=int, default=12)
    ap.add_argument("--out", required=True, help="new JSON file (never overwritten)")
    args = ap.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    vectors = [tuple(int(x) for x in s.split(",")) for s in args.v]
    if args.family:
        vectors += [v for v in family(args.m, args.r) if v not in vectors]
    rep = sweep(
        args.m,
        args.r,
        args.qmin,
        args.qmax,
        vectors,
        args.listing,
        log=lambda s: print(s, file=sys.stderr, flush=True),
        rel=(-args.below, args.above),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1) + "\n")
    brief = {
        k: rep[k]
        for k in (
            "m",
            "r",
            "P",
            "budget_P_m_2",
            "true_radius",
            "q_budget",
            "q_all_equal_d",
        )
    }
    brief["rows"] = [
        {
            k: row[k]
            for k in (
                "q",
                "max_finite_A",
                "over_budget",
                "no_admissible_lift",
                "A_gt_d",
            )
        }
        for row in rep["rows"]
    ]
    print(json.dumps(brief))
    return 0


if __name__ == "__main__":
    sys.exit(main())
