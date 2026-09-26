"""All two-zero masks of m..1 at one m: full two-core pool (reversal_orbit_search/fast.gen_pool), root-leaf LP only.
Search side only; every CERTIFIED output is re-verified by reversal_k2.py."""
import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search')  # added when copied from the scratch run directory, which held identical copies of fast.py, gen.py, engine.py, survey.py
import sys, json, time
from multiprocessing import Pool
from fast import gen_pool, front_fast, C
from engine import make_family, mixture_lp


def job(args):
    m, mask = args
    t0 = time.process_time()
    fam = make_family(list(range(m, 0, -1)), mask)
    st, T = fam['unit_base'], fam['budget_unit']
    p = gen_pool(st)
    f = front_fast(st, p, [0, 1])
    w, B, sl, t = mixture_lp([(b, list(bt)) for b, bt, _ in f], 2, m - 2)
    ok = t == 0 and B < T + 1
    row = {'m': m, 'mask': mask, 'gaps': fam['gaps'], 'status': 'ROOT_OK' if ok else 'ROOT_FAIL',
           'root_minB_minus_T': str(B - T), 'root_slope_excess': str(t),
           'support': [[str(x), b - T, list(bt), list(p[wd][:1]) + [p[wd][1], p[wd][2]]] for x, (b, bt, wd) in zip(w, f) if x]}
    if ok:
        row['output'] = {'words': [wd for x, (b, bt, wd) in zip(w, f) if x]}
    row['cpu'] = round(time.process_time() - t0, 1)
    return row


if __name__ == '__main__':
    m = int(sys.argv[1])
    jobs = [(m, (1 << a) | (1 << b)) for a in range(m + 1) for b in range(a + 1, m + 1)]
    if len(sys.argv) > 4 and sys.argv[4] == 'outer':  # masks with a zero in gap 0 or gap m only
        jobs = [(m, x) for _, x in jobs if x & 1 or x >> m & 1]
    t0 = time.time()
    with Pool(int(sys.argv[3])) as pool, open(sys.argv[2], 'w') as fo:
        for r in pool.imap_unordered(job, jobs):
            fo.write(json.dumps(r) + '\n'); fo.flush()
            print(r['m'], r['mask'], r['gaps'], r['status'], r['root_minB_minus_T'], r['root_slope_excess'], r['cpu'], flush=True)
    print('wall', round(time.time() - t0, 1))
