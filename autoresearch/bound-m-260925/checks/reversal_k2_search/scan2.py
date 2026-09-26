import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search')  # added when copied from the scratch run directory, which held identical copies of fast.py, gen.py, engine.py, survey.py
import sys, json, time
from multiprocessing import Pool
from k2gen import core_word2, sides, C, make_family
from fast import fast_profile, pareto
from integrations.lift_evaluator import mixture_lp


def pool2(st, seeds1=None, s2rad=2, tfull=False):
    n = len(st); m = n - 2
    z = [i for i, x in enumerate(st) if x == 0]
    seeds1 = seeds1 if seeds1 is not None else sorted({(zz + d) % n for zz in z for d in (-1, 0, 1)})
    out = {}
    for s1 in seeds1:
        for nl in range(0, n - 1):
            for nr in range(0, n - 1 - nl):
                if nl + nr == 0:
                    continue
                lo, hi = (s1 - nl) % n, (s1 + nr) % n
                mid = (hi + 1 + ((lo - 1 - hi - 1) % n) // 2) % n  # middle of complement
                s2s = sorted({(mid + d) % n for d in range(-s2rad, s2rad + 1)})
                ts = range(m + 1) if tfull else sorted({x for x in (0, m, nl - 1, nl, nl + 1, m - nr - 1, m - nr, m - nr + 1, m - nr + 2) if 0 <= x <= m})
                for first in 'rl':
                    for mode in 'ab':
                        if mode == 'b' and nl == nr:
                            continue
                        sd = sides(nl, nr, first, mode)
                        for t in ts:
                            for s2 in s2s:
                                for d2 in 'rl':
                                    for fin in 'RL':
                                        w = core_word2(st, t, [(s1, sd), (s2, None, d2)], fin)
                                        if w and w not in out:
                                            out[w] = (t, s1, nl, nr, first, mode, s2, d2, fin)
    return out


def job(args):
    m, mask = args
    t0 = time.process_time()
    fam = make_family(list(range(m, 0, -1)), mask)
    st = fam['unit_base']; T = fam['budget_unit']
    p = pool2(st)
    items = []
    for w, par in p.items():
        r = fast_profile(st, w, [0, 1])
        if r:
            items.append((r[0], r[1], w))
    fr = pareto(items)
    w, B, sl, t = mixture_lp([(b, list(bt)) for b, bt, _ in fr], 2, m - 2)
    sup = [(str(x), b - T, list(bt), p[wd]) for x, (b, bt, wd) in zip(w, fr) if x]
    return dict(m=m, mask=mask, minB=str(B - T), t=str(t), sup=sup, front=[(b - T, list(bt), p[wd]) for b, bt, wd in fr],
                npool=len(p), cpu=round(time.process_time() - t0, 1))


if __name__ == '__main__':
    jobs = json.loads(sys.argv[1])
    with Pool(int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool, open(sys.argv[2], 'a') as fo:
        for r in pool.imap_unordered(job, [tuple(j) for j in jobs]):
            fo.write(json.dumps(r) + '\n'); fo.flush()
            print(r['m'], r['mask'], 'minB-T', r['minB'], 't', r['t'], 'pool', r['npool'], 'cpu', r['cpu'], flush=True)
            for s in r['sup']:
                print('    ', s, flush=True)
