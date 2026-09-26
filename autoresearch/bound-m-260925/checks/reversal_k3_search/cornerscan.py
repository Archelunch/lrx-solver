"""Direct single-word scan on the corner {0,g1,m-r2}, g1 in {1,2}, r2 in {0,1}, m = 9..20, word_G-style coordinates:
cut ('j', dt) = (m-3)//4 + dt or ('m', dt) = m + dt; core 1 at cell s1 with m//2 + dk sweeps, first side d1; core 2
seeded at the complement middle + ds2 (as word_G, n = m+3), grown until sorted, first side d2; final walk fin.
fast_profile prices (pruning grade); every hit is re-priced by lrx_m.Profile. Output: cornerscan.json."""
import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks')
import json, itertools, time
from multiprocessing import Pool
from fast import fast_profile
from reversal_orbit import core_word
from integrations import lrx_m as C

CUTS = [('j', d) for d in range(-2, 4)] + [('m', d) for d in (-3, -2, -1)]


def cw(m, g1, g2, tup):
    (ca, dt), s1, dk, d1, ds2, d2, fin = tup
    n = m + 3
    t = ((m - 3) // 4 if ca == 'j' else m) + dt
    k1 = m // 2 + dk
    if not 0 <= t <= m:
        return None, None
    nr = (k1 + 1) // 2 if d1 == 'r' else k1 // 2
    mid = s1 + nr + 1 + (n - k1 - 1) // 2
    st = C.base_vector(list(range(m, 0, -1)), 1 | 1 << g1 | 1 << g2)
    return st, core_word(st, t, [(s1 % n, k1, d1), ((mid + ds2) % n, None, d2)], fin)


def job(a):
    m, g1, r2 = a
    g2 = m - r2
    T = C.budget(m, 3)
    hits = []
    for tup in itertools.product(CUTS, range(-2, 3), range(-2, 2), 'rl', range(-2, 3), 'rl', 'RL'):
        st, w = cw(m, g1, g2, tup)
        if not w:
            continue
        r = fast_profile(st, w, [0, 1, 2])
        if r and r[0] < T + 1 and max(r[1]) <= m - 2:
            p = C.Profile(st, w)
            assert (p.base, tuple(p.beta)) == r
            hits.append([list(tup), p.base - T, list(p.beta)])
    return [m, g1, r2], hits


if __name__ == '__main__':
    jobs = [(m, g1, r2) for m in range(9, 21) for g1 in (1, 2) for r2 in (0, 1) if m - r2 > g1]
    t0 = time.time()
    with Pool(int(sys.argv[1])) as pool:
        res = pool.map(job, jobs)
    json.dump(res, open('cornerscan.json', 'w'))
    for k, h in res:
        print(k, len(h))
    print('wall', round(time.time() - t0, 1))
