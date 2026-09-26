"""Single-word certificates on interior masks (all zeros in gaps 1..m-1) of the reversal m..1.
Search side only: records every two-core pool word (gen3.pool, cuts t0-2..t0+2, or all cuts with CUTS=all) that meets criterion (7) alone
(base - T <= 0, every beta <= m-2), in relative coordinates.
    python fitscan.py K M1 M2 OUT.jsonl WORKERS"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab')
sys.path.insert(0, os.path.join(HERE, '..', 'reversal_k3_search'))
import json, time, itertools
from multiprocessing import Pool
import gen3
from integrations import lrx_m as C


class Hits:
    def __init__(self, T, s):
        self.T, self.s, self.hits = T, s, {}

    def emit(self, b, bt, st, params):
        if b - self.T <= 0 and max(bt) <= self.s:
            if params not in self.hits or b < self.hits[params]:
                self.hits[params] = b


def job(args):
    m, k, gaps = args
    t0 = time.process_time()
    mask = sum(1 << g for g in gaps)
    st = C.base_vector(list(range(m, 0, -1)), mask)
    T = C.budget(m, k)
    tc = (m - 3) // 4
    H = Hits(T, m - 2)
    gen3.pool(st, list(range(k)), cuts=(range(m + 1) if os.environ.get('CUTS') == 'all' else
                                            [t for t in range(tc - 2, tc + 3) if 0 <= t <= m]), front=H)
    hits = [[b - T, p[1], p[2]] for p, b in H.hits.items()]
    return {'m': m, 'k': k, 'gaps': list(gaps), 'n_hits': len(hits), 'hits': hits,
            'cpu': round(time.process_time() - t0, 1)}


if __name__ == '__main__':
    k, m1, m2 = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    jobs = [(m, k, g) for m in range(m1, m2 + 1) for g in itertools.combinations(range(1, m), k)]
    t0 = time.time()
    with Pool(int(sys.argv[5])) as pool, open(sys.argv[4], 'w') as fo:
        for r in pool.imap_unordered(job, jobs):
            fo.write(json.dumps(r) + '\n'); fo.flush()
            print(r['m'], r['gaps'], r['n_hits'], r['cpu'], flush=True)
    print('wall', round(time.time() - t0, 1))
