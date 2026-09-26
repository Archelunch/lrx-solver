"""Asymmetric core 1 (nl left, nr right steps, orders 'a'/'b'), core 2 alternating near the complement middle.
Collects single-word certificates and the best (base, beta) front for masks {0,g}. Search side only."""
import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search')  # added when copied from the scratch run directory, which held identical copies of fast.py, gen.py, engine.py, survey.py
import sys, json, time
from multiprocessing import Pool
from fast import _grow, is_sorted, finals, ranks, fast_profile, pareto, C
from k2gen import sides
from integrations.bound_task import make_family
from integrations.lift_evaluator import mixture_lp


def scan(m, mask, s2rad=2, slack=6):
    fam = make_family(list(range(m, 0, -1)), mask)
    st = fam['unit_base']; T = fam['budget_unit']; n = len(st)
    zs = [i for i, x in enumerate(st) if x == 0]
    seeds1 = sorted({(z + d) % n for z in zs for d in (-2, -1, 0, 1, 2)})
    items = {}
    for t in range(m + 1):
        rk = ranks(m, t)
        for s1 in seeds1:
            for nl in range(n - 1):
                for nr in range(n - 1 - nl):
                    if nl + nr == 0:
                        continue
                    for first in 'rl':
                        for mode in 'ab':
                            if mode == 'b' and nl == nr:
                                continue
                            if (nl == 0 or nr == 0) and (first == 'l') != (nl > 0):
                                continue
                            cell, c, w = list(st), 0, []
                            lo = hi = s1
                            ok = True
                            for ln, sd in enumerate(sides(nl, nr, first, mode), 1):
                                c, lo, hi = _grow(cell, c, w, rk, n, lo, hi, ln, sd)
                                if len(w) and sum(map(len, w)) > T + slack:
                                    ok = False
                                    break
                            if not ok:
                                continue
                            pre = ''.join(w)
                            ln1 = nl + nr + 1
                            mid = (hi + 1 + (n - ln1) // 2) % n
                            for s2 in sorted({(mid + d) % n for d in range(-s2rad, s2rad + 1)}):
                                for d2 in 'rl':
                                    cl2, c2, w2 = list(cell), c, [pre]
                                    lo2 = hi2 = s2
                                    sd = d2
                                    ln = 1
                                    while ln < n and not is_sorted(cl2, m):
                                        c2, lo2, hi2 = _grow(cl2, c2, w2, rk, n, lo2, hi2, ln, sd)
                                        sd = 'l' if sd == 'r' else 'r'
                                        ln += 1
                                    if not is_sorted(cl2, m):
                                        continue
                                    body = ''.join(w2)
                                    if len(body) > T + slack:
                                        continue
                                    for fin, tail in finals(cl2, c2, n).items():
                                        wd = body + tail
                                        if len(wd) > T + slack or wd in items:
                                            continue
                                        r = fast_profile(st, wd, list(range(len(zs))))
                                        if r:
                                            items[wd] = (r[0], r[1], (t, s1, nl, nr, first, mode,
                                                                      (s2 - mid + n // 2) % n - n // 2, d2, fin))
    fr = pareto([(b, bt, wd) for wd, (b, bt, _) in items.items()])
    sing = [[items[wd][2], b - T, list(bt)] for wd, (b, bt, _) in items.items() if b <= T and max(bt) <= m - 2]
    if fr:
        w, B, sl, tt = mixture_lp([(b, list(bt)) for b, bt, _ in fr], len(zs), m - 2)
        sup = [(str(x), b - T, list(bt), items[wd][2]) for x, (b, bt, wd) in zip(w, fr) if x]
    else:
        B, tt, sup = None, None, []
    return {'m': m, 'mask': mask, 'minB': None if B is None else str(B - T), 't': str(tt), 'sup': sup,
            'singles': sing, 'front': [(b - T, list(bt), items[wd][2]) for b, bt, wd in fr]}


def job(a):
    t0 = time.process_time()
    r = scan(*a)
    r['cpu'] = round(time.process_time() - t0, 1)
    return r


if __name__ == '__main__':
    jobs = json.loads(sys.argv[1])
    with Pool(int(sys.argv[3])) as pool, open(sys.argv[2], 'a') as fo:
        for r in pool.imap_unordered(job, [tuple(j) for j in jobs]):
            fo.write(json.dumps(r) + '\n'); fo.flush()
            print(r['m'], r['mask'], 'singles', len(r['singles']), 'minB-T', r['minB'], 't', r['t'], 'cpu', r['cpu'], flush=True)
