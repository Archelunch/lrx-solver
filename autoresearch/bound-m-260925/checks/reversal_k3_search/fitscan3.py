"""Every single two-core word (full pool, gen3.pool) that meets criterion (7) alone on (m..1){0,g1,g2}, m = 9..11,
recorded in relative coordinates (harvest.rel). Output: fit-hits.json {tuple: [[m, g1, g2], ...]}.
Search side only; the fast pricer is used (pruning grade), final candidates are re-priced by lrx_m.Profile."""
import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_k3_search')
import json, time, collections
from multiprocessing import Pool
import gen3
from harvest import rel
from integrations import lrx_m as C


class Hits(gen3.Front):
    def __init__(self, T, s):
        super().__init__()
        self.T, self.s, self.hits = T, s, set()

    def emit(self, b, bt, st, params):
        if b < self.T + 1 and max(bt) <= self.s:
            zf, cores, fin = params
            if len(cores) == 2:
                self.hits.add((cores, fin))


def job(a):
    m, g1, g2 = a
    st = C.base_vector(list(range(m, 0, -1)), 1 | 1 << g1 | 1 << g2)
    H = Hits(C.budget(m, 3), m - 2)
    gen3.pool(st, [0, 1, 2], front=H)
    tups = set()
    for cores, fin in H.hits:
        tups.update(rel(m, g1, g2, cores[0][3], cores, fin))
    return (m, g1, g2), len(H.hits), sorted(tups)


if __name__ == '__main__':
    jobs = [(m, g1, g2) for m in (9, 10, 11) for g1 in range(1, m + 1) for g2 in range(g1 + 1, m + 1)]
    t0 = time.time()
    res = collections.defaultdict(list)
    with Pool(int(sys.argv[1])) as pool:
        for key, nh, tups in pool.imap_unordered(job, jobs):
            print(key, nh, len(tups), flush=True)
            for t in tups:
                res[t].append(list(key))
    json.dump({json.dumps(k): v for k, v in res.items()}, open('fit-hits.json', 'w'))
    print('tuples', len(res), 'wall', round(time.time() - t0, 1))
