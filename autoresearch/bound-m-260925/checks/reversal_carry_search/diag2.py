import sys
from common import *
from diag import diag
from explore2 import run
m, g = int(sys.argv[1]), int(sys.argv[2])
items, _ = run(m, g)
fr = pareto(items); T = C.budget(m, 2)
for k in sorted(fr)[:int(sys.argv[3]) if len(sys.argv) > 3 else 3]:
    w, p, q, s1, seed, s2, fin = fr[k]
    print('B-T', k[0] - T, 'beta', k[1:], 'p', p, 'q', q, 's1', s1, 'seed', seed, 's2', s2, fin)
    print(' ', w)
    diag(state(m, g), w)
