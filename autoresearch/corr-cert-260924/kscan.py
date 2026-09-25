"""Smallest k such that triples with b-a <= k suffice for LP epsilon ~ 0 (search side)."""
import sys, time, json
import structure as st
for m in [int(x) for x in sys.argv[1:]]:
    for k in range(1, m):
        t0 = time.time()
        e, r = st.min_eps(m, (lambda kk: (lambda t: t[1] - t[0] <= kk))(k))   # 1-arg support (bounds_for dispatches on arity)
        print(json.dumps({"m": m, "k": k, "lp_eps": e, "s": round(time.time() - t0, 1)}), flush=True)
        if e is not None and e < 1e-6:
            break
