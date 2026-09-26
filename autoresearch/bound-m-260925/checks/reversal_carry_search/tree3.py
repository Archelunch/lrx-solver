import sys, time
from common import *
from pools import pool, best_leaf
LEAVES = [('root', (1, 1), [(1, None), (1, None)]),
          ('u0=1', (1, 1), [(1, 1), (1, None)]),
          ('u1=1', (1, 1), [(1, None), (1, 1)]),
          ('u0>=2,u1=1', (2, 1), [(2, None), (1, 1)]),
          ('u0=1,u1>=2', (1, 2), [(1, 1), (2, None)]),
          ('u0>=2,u1>=2', (2, 2), [(2, None), (2, None)]),
          ('u0>=2', (2, 1), [(2, None), (1, None)]),
          ('u1>=2', (1, 2), [(1, None), (2, None)])]
if __name__ == '__main__':
    gens = tuple(sys.argv[3].split(',')) if len(sys.argv) > 3 else ('F2', 'D1', 'F3', 'S')
    for m in range(int(sys.argv[1]), int(sys.argv[2]) + 1):
        j = m // 4
        for g in range(j + 1, m - j):
            t0 = time.time()
            P = {o: pool(m, g, o, gens) for o in [(1, 1), (2, 1), (1, 2), (2, 2)]}
            out = []
            for name, o, box in LEAVES:
                v, pk, r = best_leaf(m, P[o], o, box)
                fr = P[o][pk]
                keys = list(fr)
                sup = sorted({fr[keys[i]][1][0] for i, x in enumerate(r['weights']) if x}) if v[0] == 0 else []
                out.append('%s:%s%s' % (name, ('ok %s' % v[1]) if v[0] == 0 else ('gap %s' % v[1]), '/'.join(sup)))
            print(m, g, ' '.join(out), '%.0fs' % (time.time() - t0), flush=True)
