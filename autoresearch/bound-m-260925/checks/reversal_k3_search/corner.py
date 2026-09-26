"""Corner sub-band {0,g1,g2}, g1 small, r2 = m-g2 small: rank fit-hits tuples by corner coverage at m = 9..11,
then evaluate the top tuples as single words (lrx_m.Profile + criterion (7)) at m = 9..MAX over g1, r2 <= LIM.
Search side only. Output: corner-eval.json."""
import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_k3_search')
import json, time
from multiprocessing import Pool
import gen3
from harvest import absolute
from integrations import lrx_m as C

LIM, MAX = 6, 24


def evalt(tup):
    tup = tuple(tup)
    cov = []
    for m in range(9, MAX + 1):
        for g1 in range(1, LIM + 1):
            for r2 in range(0, LIM + 1):
                g2 = m - r2
                if g2 <= g1:
                    continue
                a = absolute(m, g1, g2, tup)
                if a is None:
                    continue
                t, cores, fin = a
                st = C.base_vector(list(range(m, 0, -1)), 1 | 1 << g1 | 1 << g2)
                w = gen3.word3(st, cores, fin)
                if not w:
                    continue
                p = C.Profile(st, w)
                ok, B, beta = C.mixture_criterion([(p.base, p.beta)], [1], 3, m=m)
                if ok:
                    cov.append((m, g1, r2, p.base - C.budget(m, 3), list(p.beta)))
    return list(tup), cov


if __name__ == '__main__':
    d = {tuple(json.loads(k)): v for k, v in json.load(open('fit-hits.json')).items()}
    sc = {t: sum(1 for m, a, b in v if a <= 3 and m - b <= 3) for t, v in d.items()}
    top = [t for t, c in sorted(sc.items(), key=lambda x: -x[1]) if c >= 2][:int(sys.argv[1])]
    print('candidates', len(top), flush=True)
    t0 = time.time()
    with Pool(int(sys.argv[2])) as pool:
        res = pool.map(evalt, top, chunksize=4)
    json.dump(res, open('corner-eval.json', 'w'))
    res.sort(key=lambda x: -len(x[1]))
    for t, cov in res[:15]:
        print(len(cov), t)
    print('wall', round(time.time() - t0, 1))
