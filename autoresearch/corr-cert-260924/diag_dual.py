"""Dual weights of the min-t ansatz LP: which (5)/(6) rows certify that t* > 0.
Usage: python3 diag_dual.py FAMILY DEG M  -> prints top rows and aggregates."""
import sys, json
from collections import Counter
import corrcert as cc
import ansatz_lp as al
fam, deg, m = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
an = al.Ansatz(fam, deg)
th, t, res = al.solve(an, [m])
y = -res.ineqlin.marginals          # >= 0 for <= rows in a minimisation
rows = []
for tr in cc.triples(m):
    for q in range(1, m):
        for s in range(1, m):
            if q + s != m:
                rows.append(("T", tr, q, s))
for pr in cc.pairs(m):
    for q in range(1, m):
        rows.append(("P", pr, q, None))
tot = sum(y[:len(rows)])
print(f"{fam} deg{deg} m={m} t*={t:.4f}  total dual mass on (5)+(6): {tot:.3f}; eps-row dual {y[len(rows)]:.3f}")
agg_tri, agg_pair, agg_gap, agg_pos = Counter(), Counter(), Counter(), Counter()
for w, r in zip(y, rows):
    if w <= 1e-9:
        continue
    if r[0] == "T":
        a, b, c = r[1]
        agg_tri[r[1]] += w
        agg_gap[(b - a, c - b)] += w
        eq = (r[2] == m - (b - a), r[3] == m - (c - b))
        agg_pos["T at equality-order q" if eq[0] else "T other q"] += w
        agg_pos["T wraps (q+t>m)" if r[2] + r[3] > m else "T no wrap"] += w
    else:
        agg_pair[r[1]] += w
        agg_pos["P at q=m-(b-a)" if r[2] == m - (r[1][1] - r[1][0]) else "P other q"] += w
print("mass split:", {k: round(v, 3) for k, v in agg_pos.items()})
print("top triples:", [(k, round(v, 3)) for k, v in agg_tri.most_common(10)])
print("mass by gaps (b-a,c-b):", sorted(((k, round(v, 3)) for k, v in agg_gap.items()), key=lambda x: -x[1])[:10])
print("top pairs:", [(k, round(v, 3)) for k, v in agg_pair.most_common(8)])
print("n rows with dual > 1e-6:", int(sum(y[:len(rows)] > 1e-6)), "of", len(rows))
out = {"family": fam, "deg": deg, "m": m, "t_star": t,
       "rows": [{"kind": r[0], "idx": list(r[1]), "q": r[2], "t": r[3], "dual": float(w)}
                for w, r in zip(y, rows) if w > 1e-9]}
import os
os.makedirs("ansatz", exist_ok=True)
with open(f"ansatz/dual-{fam}-d{deg}-m{m}.json", "w") as fh:
    json.dump(out, fh)
print("wrote", f"ansatz/dual-{fam}-d{deg}-m{m}.json")
