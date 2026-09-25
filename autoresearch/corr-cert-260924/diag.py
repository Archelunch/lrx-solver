"""Bottleneck diagnosis: free one component per m, keep the rest on the ansatz."""
import sys, time, json
import ansatz_lp as al
fam, deg = sys.argv[1], int(sys.argv[2]); ms = [int(x) for x in sys.argv[3:]]
an = al.Ansatz(fam, deg)
for free in [(), ("tri",), ("mu",), ("lam",), ("mu", "lam"), ("tri", "lam"), ("tri", "mu")]:
    t0 = time.time()
    th, t, r = al.solve(an, ms, free=free)
    print(json.dumps({"fam": fam, "deg": deg, "ms": ms, "free": free, "t_star": t, "s": round(time.time()-t0, 1)}), flush=True)
