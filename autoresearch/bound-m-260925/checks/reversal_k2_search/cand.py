import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search')  # added when copied from the scratch run directory, which held identical copies of fast.py, gen.py, engine.py, survey.py
import json, sys, time
from collections import defaultdict
from multiprocessing import Pool
from fast import fast_profile, C
from gen import core_word
rows = {(r['m'], r['g']): r['singles'] for r in map(json.loads, open('fit-a.jsonl'))}


def rel(m, x):
    n = m + 2
    return (x[0] - (m - 3) // 4, (x[1] + n // 2) % n - n // 2, x[2] - m // 2, x[3], x[4], x[5], x[6])


def word(m, g, tup):
    dt, s1, dk, d1, ds2, d2, fin = tup
    n = m + 2
    t = (m - 3) // 4 + dt
    k1 = m // 2 + dk
    if not (0 <= t <= m and 1 <= k1 <= n - 2):
        return None, None
    st = C.base_vector(list(range(m, 0, -1)), 1 | 1 << g)
    s1 %= n
    nr = (k1 + 1) // 2 if d1 == 'r' else k1 // 2
    hi = (s1 + nr) % n
    mid = (hi + 1 + (n - k1 - 1) // 2) % n
    return st, core_word(st, t, [(s1, k1, d1), ((mid + ds2) % n, None, d2)], fin)


def good(m, g, tup):
    st, w = word(m, g, tup)
    if not w:
        return None
    T = C.budget(m, 2)
    r = fast_profile(st, w, [0, 1])
    if r and r[0] <= T and max(r[1]) <= m - 2:
        return r[0] - T
    return None


cands = set()
for rho in range(4):
    cov = defaultdict(set)
    for m in range(9, 25):
        if m % 4 != rho:
            continue
        for g in range(1, m + 1):
            for x in rows[(m, g)]:
                cov[rel(m, x)].add((m, g))
    for k, v in sorted(cov.items(), key=lambda kv: -len(kv[1]))[:25]:
        cands.add(k)
cands = sorted(cands)


def job(m):
    return m, {g: [i for i, c in enumerate(cands) if good(m, g, c) is not None] for g in range(1, m + 1)}


if __name__ == '__main__':
    t0 = time.time()
    with Pool(6) as p:
        res = dict(p.map(job, range(9, 41)))
    json.dump({'cands': cands, 'res': res}, open('cand-res.json', 'w'))
    print(len(cands), 'cands', time.time() - t0)
    for m in range(9, 41):
        print(m, ''.join('#' if res[m][g] else '.' for g in range(1, m + 1)))
