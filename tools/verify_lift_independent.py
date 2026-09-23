"""Independent pure-Python recomputation of A_q(v) for chosen vectors.

Shares no code with src/lrx/lifting_fast.py (numpy, ranked arrays). Uses the
tuple state model of src/lrx/exact_dp.py: marked state (u, j) with u the
vector after deleting the marked zero, transitions from
exact_dp.compute_marked_transitions, and the same "projection changes iff u
changes" rule. H_q is built layer by layer over ALL smaller-graph states
(enumerated by reference_bfs), keeping only two layers in memory.

    python tools/verify_lift_independent.py M R --q Q --v 2,1,0,0,0,7,8,6,5,4,3 [--v ...]

Prints A_q(v) and every H_q(v\\j, j). Slow by design (tens of minutes at n=11).
"""

import argparse
import json
import sys
import time
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.lrx.exact_dp import compute_marked_transitions  # noqa: E402
from src.lrx.reference_bfs import bfs_visible  # noqa: E402
from src.lrx.state import smaller_root  # noqa: E402

INF = 30000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("m", type=int)
    ap.add_argument("r", type=int)
    ap.add_argument("--q", type=int, required=True)
    ap.add_argument("--v", action="append", required=True)
    args = ap.parse_args()
    m, r, q = args.m, args.r, args.q
    n = m + r
    t0 = time.time()
    smaller = bfs_visible(m, r - 1, max_vertices=10**9)
    if smaller.status != "COMPLETE":
        raise SystemExit("smaller enumeration incomplete")
    states = sorted(smaller.distances)
    index = {u: i for i, u in enumerate(states)}
    size = len(states) * n
    print(
        f"{len(states)} smaller states, {size} marked states, {time.time() - t0:.0f}s",
        file=sys.stderr,
        flush=True,
    )
    # Precompute transitions: for each marked cell, 3 (target cell, changes_u).
    tgt = array("i", [0]) * (3 * size)
    chg = bytearray(3 * size)
    for ui, u in enumerate(states):
        for j in range(n):
            cell = ui * n + j
            for k, (tu, tj) in enumerate(compute_marked_transitions(u, j, n).values()):
                tgt[3 * cell + k] = index[tu] * n + tj
                chg[3 * cell + k] = 1 if tu != u else 0
    print(f"transitions {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    root = index[smaller_root(m, r)]
    init = array("h", [INF]) * size
    for j in range(m, n):
        init[root * n + j] = 0

    def closure(values):
        # u-preserving moves: marked zero among positions {0, 1, n-1}.
        for _ in range(3):
            for ui in range(len(states)):
                for j in (0, 1, n - 1):
                    cell = ui * n + j
                    best = values[cell]
                    for k in range(3):
                        if not chg[3 * cell + k]:
                            t = tgt[3 * cell + k]
                            if t != cell and values[t] + 1 < best:
                                best = values[t] + 1
                    values[cell] = best
        return values

    layer = closure(array("h", init))
    for level in range(1, q + 1):
        nxt = array("h", init)
        for cell in range(size):
            best = nxt[cell]
            base = 3 * cell
            for k in range(3):
                if chg[base + k]:
                    val = layer[tgt[base + k]] + 1
                    if val < best:
                        best = val
            nxt[cell] = best if best < INF else INF
        layer = closure(nxt)
        print(f"layer {level}/{q} {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    out = []
    for text in args.v:
        v = tuple(int(x) for x in text.split(","))
        per_zero = {}
        for j, x in enumerate(v):
            if x == 0:
                u = v[:j] + v[j + 1 :]
                per_zero[j] = int(layer[index[u] * n + j])
        out.append(
            {
                "v": list(v),
                "q": q,
                "H_by_zero_position": per_zero,
                "A": min(per_zero.values()),
            }
        )
    print(
        json.dumps(
            {
                "m": m,
                "r": r,
                "q": q,
                "results": out,
                "seconds": round(time.time() - t0, 1),
                "method": "pure-Python tuple DP, independent of lifting_fast",
            }
        )
    )


if __name__ == "__main__":
    main()
