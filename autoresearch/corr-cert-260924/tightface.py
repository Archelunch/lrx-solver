"""Rows tight on the whole optimal face {epsilon <= 0} (approximated by averaging random optimal vertices).
Prints pair-row tightness by (b-a, q) and triple-row tightness summary. Search side (scipy)."""
import sys, json
from collections import defaultdict
from math import comb
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import vstack, coo_matrix
import corrcert as cc, search_lp as sl, structure as st

def face_average(m, support, n=12, seed=0):
    A, bb = sl.constraints(m); j = sl.j_vector(m)
    A2 = vstack([A, coo_matrix(-j[None, :])]).tocsr()
    b2 = np.append(bb, 4.0 * m * comb(m, 3) + 1e-9)
    bnds = st.bounds_for(m, support)
    bnds = [(lo if lo is not None else -1e4, hi if hi is not None else 1e4) for lo, hi in bnds]
    rng = np.random.default_rng(seed)
    slacks = []
    for _ in range(n):
        c = rng.normal(size=A.shape[1])
        r = linprog(c, A_ub=A2, b_ub=b2, bounds=bnds, method="highs-ds")
        if r.x is not None:
            slacks.append(bb - A @ r.x)
    return np.mean(slacks, axis=0), len(slacks)

def rows(m):
    out = []
    for t in cc.triples(m):
        for q in range(1, m):
            for s in range(1, m):
                if q + s != m:
                    out.append(("T", t, q, s))
    for p in cc.pairs(m):
        for q in range(1, m):
            out.append(("P", p, q, None))
    return out

if __name__ == "__main__":
    sup = {"all": lambda t: True, "T1": lambda t: t[1] - t[0] == 1}[sys.argv[1]]
    res = {}
    for m in [int(x) for x in sys.argv[2:]]:
        sl_avg, n = face_average(m, sup)
        R = rows(m)
        tight = [r for r, s in zip(R, sl_avg) if s < 1e-7]
        P = [r for r in tight if r[0] == "P"]
        T = [r for r in tight if r[0] == "T"]
        grid = defaultdict(lambda: [0, 0])
        for (a, b) in cc.pairs(m):
            for q in range(1, m):
                grid[(b - a, q)][1] += 1
        for r in P:
            a, b = r[1]; grid[(b - a, r[2])][0] += 1
        forcedP = sum(1 for r in P if r[2] == m - (r[1][1] - r[1][0]))
        forcedT = sum(1 for r in T if r[2] == m - (r[1][1] - r[1][0]) and r[3] == m - (r[1][2] - r[1][1]))
        supT = sum(1 for r in R if r[0] == "T" and sup(r[1]))
        print(f"m={m} vertices={n} tight pair rows {len(P)}/{len(cc.pairs(m))*(m-1)} (forced {forcedP}); "
              f"tight triple rows {len(T)}/{supT} in support (forced {forcedT})")
        print("  pair rows tight on whole face, by d=b-a (rows) and q (cols): fraction tight")
        for d in range(1, m):
            print("   d=%d " % d + " ".join("%4s" % (f"{grid[(d,q)][0]}/{grid[(d,q)][1]}" if grid[(d,q)][0] else ".") for q in range(1, m)))
        # triple rows beyond forced: by (q - (m-(b-a)), t - (m-(c-b)))
        extra = defaultdict(int)
        for r in T:
            a, b, c = r[1]
            if not (r[2] == m - (b - a) and r[3] == m - (c - b)):
                extra[("wrap" if r[2] + r[3] > m else "nowrap", r[2] == m - (b - a), r[3] == m - (c - b))] += 1
        print("  extra tight triple rows (wrap?, q at eq-order?, t at eq-order?):", dict(extra))
        res[m] = {"P": [[list(r[1]), r[2]] for r in P], "T": [[list(r[1]), r[2], r[3]] for r in T]}
    json.dump(res, open(f"tightface-{sys.argv[1]}.json", "w"))
