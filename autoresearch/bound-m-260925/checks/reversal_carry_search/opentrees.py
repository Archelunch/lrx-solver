"""Open leaves m = 10..13: root (full pools), then refined-origin trees (depth <= 4, thresholds <= 6)."""
import sys, json, time
from tree import *
CASES = [(10, 5), (11, 4), (11, 5), (11, 6), (12, 5), (12, 6), (13, 5), (13, 6), (13, 7)]
ORIG = [(1, 1), (2, 1), (1, 2), (2, 2), (3, 1), (1, 3), (4, 1), (3, 2)]
out = open(sys.argv[1], 'a')
for m, g in CASES:
    t0 = time.process_time()
    F = fronts(m, g, ORIG)
    t1 = time.process_time()
    node = TreeSearch(m, F, maxdepth=4, tmax=6).run()
    row = {'m': m, 'g': g, 'origins': ORIG, 'pool_cpu': round(t1 - t0, 1)}
    if node is None:
        row['status'] = 'NOT_FOUND'
        # diagnostics: best value per simple leaf
        diag = {}
        for name, o, box in [('root', (1, 1), [(1, None), (1, None)]), ('u0=3', (3, 1), [(3, 3), (1, None)]),
                             ('u0=4', (4, 1), [(4, 4), (1, None)]), ('u0>=2', (2, 1), [(2, None), (1, None)]),
                             ('u1=1', (1, 1), [(1, None), (1, 1)]), ('u0=1', (1, 1), [(1, 1), (1, None)])]:
            best = None
            l = [a for a, _ in box]
            for oo in F:
                if any(oo[j] > l[j] for j in range(2)): continue
                for pk, fr in F[oo]:
                    costs = [(b + sum(x * (li - oi) for x, li, oi in zip(bt, l, oo)), list(bt)) for b, bt, _, _ in fr]
                    r = leaf_lp(costs, box, m - 2, C.budget(m, sum(l)))
                    v = r['value'] if r['status'] == 'CERTIFIED' else 1 + r['gap']
                    if best is None or v < best: best = v
            diag[name] = str(best)
        row['best_lhs'] = diag
    else:
        r, au, o = check(m, g, node)
        row.update(status=r['status'], audit=au, n_leaves=r['n_leaves'], output=o,
                   leaves=[(x['box'], x['origins'], x['picks'], x['lhs']) for x in r['leaves']])
    row['cpu'] = round(time.process_time() - t0, 1)
    out.write(json.dumps(row) + '\n'); out.flush()
    print(m, g, row['status'], row.get('audit'), row.get('n_leaves'), row.get('best_lhs'), 'cpu', row['cpu'], flush=True)
