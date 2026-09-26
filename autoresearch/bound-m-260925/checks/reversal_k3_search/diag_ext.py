"""Diagnostic: root min base excess and CPU per extended sub-pool (added to the two-core front)."""
import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_k3_search')
import time, gen3
from integrations.bound_task import make_family
from integrations.lift_evaluator import mixture_lp
for m, mask in [(9, 35), (9, 529), (9, 1 | 2 | 64)]:
    fam = make_family(list(range(m, 0, -1)), mask); st = fam['unit_base']; T = fam['budget_unit']; zc = [i for i, x in enumerate(st) if x == 0]
    def val(F):
        fr = gen3.confirm(st, F.pareto(), [0, 1, 2])
        w, B, sl, t = mixture_lp([(b, list(bt)) for b, bt, _, _ in fr], 3, m - 2)
        return str(B - T), str(t)
    base = gen3.pool(st, [0, 1, 2])
    for name, kw in [('zfree', dict(zfree=(True,))), ('percore', dict(seeds1=zc, percore=True)),
                     ('three', dict(seeds1=zc, seeds2=zc, three=True))]:
        F = gen3.Front(); F.best = dict(base.best)
        t0 = time.process_time(); gen3.pool(st, [0, 1, 2], front=F, **kw)
        print(m, fam['gaps'], name, val(F), round(time.process_time() - t0, 1), flush=True)
