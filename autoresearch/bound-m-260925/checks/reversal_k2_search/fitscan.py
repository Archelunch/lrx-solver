"""Collect all single-word certificates (base <= T, slopes <= m-2) among two-core words with core-2 seed near the
middle of the complement arc, for masks {0,g}. Search side only."""
import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search')  # added when copied from the scratch run directory, which held identical copies of fast.py, gen.py, engine.py, survey.py
import sys, json, time
from multiprocessing import Pool
from fast import _grow, is_sorted, finals, ranks, fast_profile, C
from integrations.bound_task import make_family


def singles(m, g, s2rad=2):
    fam = make_family(list(range(m, 0, -1)), 1 | 1 << g)
    st = fam['unit_base']; T = fam['budget_unit']; n = len(st)
    out = []
    seeds1 = sorted({(z + d) % n for z in (0, g + 1) for d in (-2, -1, 0, 1, 2)})
    for t in range(m + 1):
        rk = ranks(m, t)
        for s1 in seeds1:
            for d1 in 'rl':
                cell, c, w = list(st), 0, []
                lo = hi = s1
                side = d1
                for k1 in range(1, n - 1):
                    c, lo, hi = _grow(cell, c, w, rk, n, lo, hi, k1, side)
                    side = 'l' if side == 'r' else 'r'
                    pre = ''.join(w)
                    if len(pre) > T + 2:
                        break
                    if is_sorted(cell, m):
                        break
                    ln1 = k1 + 1
                    mid = (hi + 1 + (n - ln1) // 2) % n
                    for s2 in sorted({(mid + d) % n for d in range(-s2rad, s2rad + 1)}):
                        for d2 in 'rl':
                            cl2, c2, w2 = list(cell), c, [pre]
                            lo2 = hi2 = s2
                            sd = d2
                            ln = 1
                            L = len(pre)
                            while ln < n and not is_sorted(cl2, m):
                                c2, lo2, hi2 = _grow(cl2, c2, w2, rk, n, lo2, hi2, ln, sd)
                                sd = 'l' if sd == 'r' else 'r'
                                ln += 1
                            if not is_sorted(cl2, m):
                                continue
                            body = ''.join(w2)
                            if len(body) > T + 2:
                                continue
                            for fin, tail in finals(cl2, c2, n).items():
                                wd = body + tail
                                if len(wd) > T + 2:
                                    continue
                                r = fast_profile(st, wd, [0, 1])
                                if r and r[0] <= T and max(r[1]) <= m - 2:
                                    out.append([t, s1, k1, d1, (s2 - mid + n // 2) % n - n // 2, d2, fin, r[0] - T, list(r[1])])
    return out


def job(a):
    m, g = a
    t0 = time.process_time()
    s = singles(m, g)
    return {'m': m, 'g': g, 'singles': s, 'cpu': round(time.process_time() - t0, 1)}


if __name__ == '__main__':
    jobs = json.loads(sys.argv[1])
    with Pool(int(sys.argv[3])) as pool, open(sys.argv[2], 'a') as fo:
        for r in pool.imap_unordered(job, [tuple(j) for j in jobs]):
            fo.write(json.dumps(r) + '\n'); fo.flush()
            print(r['m'], r['g'], len(r['singles']), r['cpu'], flush=True)
