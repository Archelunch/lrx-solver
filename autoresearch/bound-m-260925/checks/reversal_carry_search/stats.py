import sys, time, collections
from common import *
from pools import pool
m = int(sys.argv[1])
j = m // 4
for g in range(j + 1, m - j):
    for o in [(1, 1)]:
        t0 = time.time()
        P = pool(m, g, o)
        fr = P[(0, o[0])]
        T = C.budget(m, 2)
        r = root_lp(m, list(fr))
        keys = list(fr)
        sup = [keys[i] for i, x in enumerate(r['weights']) if x]
        print(m, g, r['status'], r.get('value'), r['gap'], '%.0fs' % (time.time() - t0))
        for k in sorted(fr)[:8]:
            print('   ', k[0] - T, k[1:], fr[k][1], '*' if k in sup else '')
