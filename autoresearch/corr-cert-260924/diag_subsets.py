"""Which triples does the ansatz fail to express? Free one class of triples per run."""
import sys, time, json
import ansatz_lp as al
fam, deg = sys.argv[1], int(sys.argv[2]); ms = [int(x) for x in sys.argv[3:]]
an = al.Ansatz(fam, deg)
classes = {
    "none": lambda m, t: False,
    "a==0": lambda m, t: t[0] == 0,
    "c==m-1": lambda m, t: t[2] == m - 1,
    "a==0 or c==m-1": lambda m, t: t[0] == 0 or t[2] == m - 1,
    "interior (a>0,c<m-1)": lambda m, t: t[0] > 0 and t[2] < m - 1,
    "b-a==1 or c-b==1": lambda m, t: t[1] - t[0] == 1 or t[2] - t[1] == 1,
    "b-a>1 and c-b>1": lambda m, t: t[1] - t[0] > 1 and t[2] - t[1] > 1,
    "c-a <= m/2": lambda m, t: 2 * (t[2] - t[0]) <= m,
    "c-a > m/2": lambda m, t: 2 * (t[2] - t[0]) > m,
    "a+c < m-1": lambda m, t: t[0] + t[2] < m - 1,
    "a+c == m-1": lambda m, t: t[0] + t[2] == m - 1,
    "a+c > m-1": lambda m, t: t[0] + t[2] > m - 1,
}
for name, fn in classes.items():
    t0 = time.time()
    th, t, r = al.solve(an, ms, free=(("pred", fn),))
    print(json.dumps({"fam": fam, "deg": deg, "ms": ms, "freed": name, "t_star": None if t is None else round(t, 4),
                      "s": round(time.time() - t0, 1)}), flush=True)
