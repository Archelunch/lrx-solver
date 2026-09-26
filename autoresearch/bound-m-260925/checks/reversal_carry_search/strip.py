import sys, time
from tree import *
m, g = int(sys.argv[1]), int(sys.argv[2])
ax = int(sys.argv[3]) if len(sys.argv) > 3 else 0
K = int(sys.argv[4]) if len(sys.argv) > 4 else 4
t0 = time.process_time()
os_ = [(1, 1)] + [((k, 1) if ax == 0 else (1, k)) for k in range(2, K + 1)]
F = fronts(m, g, os_)
print('pools %.0fs' % (time.process_time() - t0))
T = C.budget(m, 2); s = m - 2
for o in os_:
    for pk, fr in F[o]:
        print(o, pk, sorted((b - C.budget(m, sum(o)), bt) for b, bt, _, _ in fr)[:10])
ts = TreeSearch(m, F, 4, 8)
for k in range(1, K + 2):
    for box in ([(k, k), (1, 1)], [(k, None), (1, 1)]) if ax == 0 else ([(1, 1), (k, k)], [(1, 1), (k, None)]):
        nd = ts.leaf(box)
        # best gap
        best = None
        l = [a for a, _ in box]
        for o in F:
            if any(o[j] > l[j] for j in range(2)): continue
            for pk, fr in F[o]:
                costs = [(b + sum(x * (li - oi) for x, li, oi in zip(bt, l, o)), list(bt)) for b, bt, _, _ in fr]
                r = leaf_lp(costs, box, s, C.budget(m, sum(l)))
                v = r['value'] if r['status'] == 'CERTIFIED' else 1 + r['gap'] if r['gap'] else r.get('gap_value')
                if best is None or v < best[0]: best = (v, o, pk)
        print(box, 'ok' if nd else 'FAIL', 'best lhs/1+gap', best)
