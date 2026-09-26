"""Evaluate the per-residue corner tuples of cornerscan.json on the rectangle g1 = 1..j+2, r2 = 0..j+2 (j = m//4),
m = 9..40, as single words (fast_profile, hits re-priced by lrx_m.Profile). Output: cornerfit.json."""
import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_k3_search')
import json, time
from collections import defaultdict
from multiprocessing import Pool
from cornerscan import cw, fast_profile, C


def job(args):
    r, tup = args
    tup = [tuple(tup[0])] + tup[1:]
    cov = []
    for m in range(9, 41):
        if m % 4 != r:
            continue
        j, T = m // 4, C.budget(m, 3)
        for g1 in range(1, j + 3):
            for r2 in range(0, j + 3):
                g2 = m - r2
                if g2 <= g1:
                    continue
                st, w = cw(m, g1, g2, tup)
                if not w:
                    continue
                x = fast_profile(st, w, [0, 1, 2])
                if x and x[0] < T + 1 and max(x[1]) <= m - 2:
                    p = C.Profile(st, w)
                    assert (p.base, tuple(p.beta)) == x
                    cov.append([m, g1, r2])
    return r, json.dumps(tup), cov


if __name__ == '__main__':
    res = json.load(open('cornerscan.json'))
    S = defaultdict(dict)
    for (m, g1, r2), h in res:
        S[(g1, r2)][m] = {json.dumps(x[0]) for x in h}
    jobs = set()
    for cell, d in S.items():
        for r in range(4):
            I = set.intersection(*[d[m] for m in range(9, 21) if m % 4 == r])
            jobs.update((r, t) for t in I)
    jobs = sorted(jobs)
    print('jobs', len(jobs), flush=True)
    t0 = time.time()
    with Pool(int(sys.argv[1])) as pool:
        out = pool.map(job, [(r, json.loads(t)) for r, t in jobs])
    json.dump(out, open('cornerfit.json', 'w'))
    for r in range(4):
        best = sorted([x for x in out if x[0] == r], key=lambda x: -len(x[2]))[:4]
        for _, t, cov in best:
            print(r, t, len(cov))
    print('wall', round(time.time() - t0, 1))
