import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search')  # added when copied from the scratch run directory, which held identical copies of fast.py, gen.py, engine.py, survey.py
import sys, json, time
sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search')
from multiprocessing import Pool
from fast import gen_pool, front_fast, C
from engine import make_family, mixture_lp

def job(args):
    m, g = args
    t0 = time.process_time()
    fam = make_family(list(range(m, 0, -1)), 1 | 1 << g)
    st = fam['unit_base']; T = fam['budget_unit']
    p = gen_pool(st)
    f = front_fast(st, p, [0, 1])
    w, B, sl, t = mixture_lp([(b, list(bt)) for b, bt, _ in f], 2, m - 2)
    sup = [(str(x), b - T, list(bt), p[wd]) for x, (b, bt, wd) in zip(w, f) if x]
    # also all single words with base<=T and slopes<=m-2
    singles = [(b - T, list(bt), p[wd]) for b, bt, wd in f if b <= T and max(bt) <= m - 2]
    return dict(m=m, g=g, minB=str(B - T), t=str(t), sup=sup, singles=singles, front=[(b - T, list(bt), p[wd]) for b, bt, wd in f], cpu=time.process_time() - t0)

if __name__ == '__main__':
    ms = [int(x) for x in sys.argv[1].split(',')]
    jobs = [(m, g) for m in ms for g in range(1, m + 1)]
    with Pool(6) as pool, open(sys.argv[2], 'w') as fo:
        for r in pool.imap_unordered(job, jobs):
            fo.write(json.dumps(r) + '\n'); fo.flush()
            print(r['m'], r['g'], r['minB'], r['t'], len(r['singles']), round(r['cpu'], 1), flush=True)
