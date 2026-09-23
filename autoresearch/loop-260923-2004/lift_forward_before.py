"""Independent forward check of H_q(u, j) for chosen vectors (Route B).

Shares no DP code with src/lrx/lifting_fast.py or tools/verify_lift_independent.py.
From one start it runs a breadth-first search in full word length over states
(w, j, e): w is the vector after deleting the marked zero, j its insertion
position, e the unspent projection slack. Moves follow the table in
research/problem.md. A move that changes w is a projection step and spends
c = 1 + d(w') - d(w) >= 0 (the c's telescope to projection length - d(u), so
e starts at q - d(u)); moves that only carry the marked zero between positions
1, 0 and n-1 are free. d is the trusted smaller-graph distance table.

The first terminal reached (w = smaller root, j >= m) is H_q(u, j) exactly: the
search is exhaustive over admissible words, so the value is also a lower
bound. Its parent chain is a witness word, replayed by
certificates.CertificateValidator.

    python autoresearch/lift_forward.py M R --q Q --v 2,1,0,0,0,9,8,7,6,5,4,3 --out PATH

--q defaults to P = E_{r-1}(n-1). A state cap turns an unfinished search into
INCOMPLETE, never into infinity.
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.lrx.certificates import CertificateValidator, replay_visible  # noqa: E402
from src.lrx.table_bfs import DistanceTable, Ranker, build_table  # noqa: E402

LETTERS = "LRX"


def smaller_table(m, r):
    """Distances of the smaller graph (m, r-1): registry table or a full BFS."""
    try:
        table = DistanceTable(ROOT / "datasets" / "generated", m, r - 1)
        return table.dist, table.radius, "registry"
    except FileNotFoundError:
        n1 = m + r - 1
        dist, meta = build_table(m, r - 1, workers=1 if n1 <= 10 else 8)
        if not meta["complete"]:
            raise RuntimeError(f"BFS incomplete for m={m} r={r - 1}")
        return dist, meta["radius"], "bfs"


def forward_h(m, r, u, j0, q, dist, max_states=30_000_000, witness=True, max_length=None):
    """Exact H_q(u, j0) by forward search. Returns a dict (H is None if no lift)."""
    n = m + r
    ranker = Ranker(m, r - 1)
    root = tuple(range(1, m + 1)) + (0,) * (r - 1)

    def code(w):
        pos = [0] * m
        for i, x in enumerate(w):
            if x:
                pos[x - 1] = i
        return ranker.rank(pos)

    u = tuple(u)
    cu = code(u)
    du = dist[cu]
    e0 = q - du
    out = {"d_small": du, "slack": e0, "status": "COMPLETE", "H": None, "states": 0}
    if e0 < 0:
        return out
    span = e0 + 1

    def pkey(c, j, e):
        return (c * n + j) * span + e

    best = {cu * n + j0: e0}
    parent = {}
    frontier = [(u, j0, e0, cu, du)]
    length = 0
    while frontier:
        for w, j, e, cw, _ in frontier:
            if j >= m and w == root:
                out.update(H=length, states=len(best))
                if witness:
                    letters = []
                    key = pkey(cw, j, e)
                    while key in parent:
                        key, letter = divmod(parent[key], 3)
                        letters.append(LETTERS[letter])
                    out["word"] = "".join(reversed(letters))
                return out
        if max_length is not None and length >= max_length:
            # No terminal through this full-word depth. This is a bounded
            # decision, NOT infinity and NOT an exact H value.
            out.update(status="COMPLETE_BOUND", H=None, states=len(best),
                       lower_bound=length + 1, length_cap=max_length)
            return out
        nxt = []
        for w, j, e, cw, dw in frontier:
            here = pkey(cw, j, e)
            moves = (
                (0, w, n - 1, False) if j == 0 else (0, w[1:] + w[:1], j - 1, True),
                (1, w, 0, False) if j == n - 1 else (1, w[-1:] + w[:-1], j + 1, True),
                (2, w, 1 - j, False)
                if j < 2
                else None
                if w[0] == w[1]  # two plain zeros: X is a self-loop
                else (2, (w[1], w[0]) + w[2:], j, True),
            )
            for move in moves:
                if move is None:
                    continue
                letter, w2, j2, projected = move
                if projected:
                    c2 = code(w2)
                    d2 = dist[c2]
                    spend = 1 + d2 - dw
                    if spend > e:
                        continue
                    e2 = e - spend
                else:
                    c2, d2, e2 = cw, dw, e
                key = c2 * n + j2
                if best.get(key, -1) >= e2:
                    continue
                best[key] = e2
                if witness:
                    parent[pkey(c2, j2, e2)] = here * 3 + letter
                nxt.append((w2, j2, e2, c2, d2))
        if len(best) > max_states:
            out.update(
                status="INCOMPLETE", reason=f"state cap {max_states}", states=len(best)
            )
            return out
        frontier = nxt
        length += 1
    out["states"] = len(best)
    return out


def decide_vector(m, r, v, q, bound, dist, max_states=30_000_000):
    """Decide A_q(v) <= bound, stopping at the first replayed witness.

    A negative answer needs every deletion resolved by complete search. A
    resource-limited deletion leaves the result INCOMPLETE unless another
    deletion supplies a positive witness. Does not claim the exact A value.
    """
    if type(bound) is not int or bound < 0:
        raise ValueError("bound must be a nonnegative integer")
    v = tuple(v)
    root = tuple(range(1, m + 1)) + (0,) * r
    if sorted(v) != sorted(root):
        raise ValueError("invalid visible vector")
    validator = CertificateValidator(m, r)
    rows = []
    for j, token in enumerate(v):
        if token:
            continue
        u = v[:j] + v[j + 1:]
        res = forward_h(m, r, u, j, q, dist, max_states, True, max_length=bound)
        res["j"] = j
        rows.append(res)
        if res["H"] is not None:
            cert = validator.replay_word(res["word"], start_state=(u, j))
            if not (cert.terminal and cert.replay_valid and cert.word_length <= bound
                    and cert.projection_length <= q and replay_visible(v, res["word"]) == root):
                raise AssertionError("bounded witness failed independent replay")
            return {"status": "COMPLETE", "within_bound": True,
                    "q": q, "bound": bound, "witness": res, "deletions": rows}
    incomplete = any(row["status"] == "INCOMPLETE" for row in rows)
    return {"status": "INCOMPLETE" if incomplete else "COMPLETE",
            "within_bound": None if incomplete else False,
            "q": q, "bound": bound, "deletions": rows}


def check_vector(m, r, v, q, dist, max_states, witness=True):
    """A_q(v) = min over zeros j of H_q(v\\j, j), with a replayed witness per j."""
    v = tuple(v)
    validator = CertificateValidator(m, r)
    root = tuple(range(1, m + 1)) + (0,) * r
    rows = []
    for j, x in enumerate(v):
        if x:
            continue
        u = v[:j] + v[j + 1 :]
        t0 = time.perf_counter()
        res = forward_h(m, r, u, j, q, dist, max_states, witness)
        res.update(j=j, seconds=round(time.perf_counter() - t0, 1))
        if res.get("word") is not None:
            cert = validator.replay_word(res["word"], start_state=(u, j))
            res["replay"] = {
                "terminal": cert.terminal,
                "valid": cert.replay_valid,
                "length": cert.word_length,
                "projection": cert.projection_length,
                "visible_root": replay_visible(v, res["word"]) == root,
            }
            if not (
                cert.terminal
                and cert.replay_valid
                and cert.word_length == res["H"]
                and cert.projection_length <= q
                and res["replay"]["visible_root"]
            ):
                raise AssertionError(f"witness failed replay for v={v} j={j}")
        rows.append(res)
    complete = all(x["status"] == "COMPLETE" for x in rows)
    finite = [x["H"] for x in rows if x["H"] is not None]
    return {
        "v": list(v),
        "q": q,
        "status": "COMPLETE" if complete else "INCOMPLETE",
        "A": (min(finite) if finite else None) if complete else None,
        "deletions": rows,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("m", type=int)
    ap.add_argument("r", type=int)
    ap.add_argument("--q", type=int, action="append", help="cap(s); default P")
    ap.add_argument("--v", action="append", required=True)
    ap.add_argument("--max-states", type=int, default=30_000_000)
    ap.add_argument("--no-witness", action="store_true")
    ap.add_argument("--out", required=True, help="new JSON file (never overwritten)")
    args = ap.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    t0 = time.perf_counter()
    dist, p, source = smaller_table(args.m, args.r)
    caps = args.q or [p]
    results = []
    for s in args.v:
        v = tuple(int(x) for x in s.split(","))
        for q in caps:
            res = check_vector(
                args.m, args.r, v, q, dist, args.max_states, not args.no_witness
            )
            print(
                json.dumps(
                    {"v": res["v"], "q": q, "A": res["A"], "status": res["status"]}
                ),
                flush=True,
            )
            results.append(res)
    rep = {
        "m": args.m,
        "r": args.r,
        "n": args.m + args.r,
        "P": p,
        "budget_P_m_2": p + args.m - 2,
        "smaller_table": source,
        "results": results,
        "method": "autoresearch/lift_forward.py (forward BFS with projection slack)",
        "scope": "finite: these vectors on this graph only",
        "seconds": round(time.perf_counter() - t0, 1),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
