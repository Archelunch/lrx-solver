import sys, json, time
from multiprocessing import Pool
from fast import gen_pool, front_fast, C, fast_profile
from engine import make_family, mixture_lp

def rel(par, state):
    """Express params relative to zero cells: seed as (nearest zero index j, offset)."""
    n = len(state)
    z = [i for i, x in enumerate(state) if x == 0]
    def r(s):
        best = min(((s - p) % n if (s - p) % n <= n // 2 else (s - p) % n - n, j) for j, p in enumerate(z))
        return 'z%d%+d' % (best[1], best[0])
    t, cores, fin = par
    return [t, [[r(s), k, d] for s, k, d in cores], fin]

def job(args):
    labels, mask = args
    fam = make_family(labels, mask)
    st = fam['unit_base']; k = fam['k']; m = fam['m']
    p = gen_pool(st)
    f = front_fast(st, p, list(range(k)))
    w, B, sl, t = mixture_lp([(b, list(bt)) for b, bt, _ in f], k, m - 2)
    ok = t == 0 and B < fam['budget_unit'] + 1
    sup = [(str(x), b - fam['budget_unit'], bt, p[wd], rel(p[wd], st)) for x, (b, bt, wd) in zip(w, f) if x]
    return m, mask, [g for g in range(m + 1) if mask >> g & 1], ok, sup

if __name__ == '__main__':
    m = int(sys.argv[1])
    jobs = [(list(range(m, 0, -1)), (1 << a) | (1 << b)) for a in range(m + 1) for b in range(a + 1, m + 1)]
    with Pool(10) as pool:
        for r in pool.imap(job, jobs):
            print(r[:4])
            for s in r[4]:
                print('     ', s)
