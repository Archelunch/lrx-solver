import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search')  # added when copied from the scratch run directory, which held identical copies of fast.py, gen.py, engine.py, survey.py
import json, time
from multiprocessing import Pool
from fractions import Fraction as Fr
from cand import cands, word, fast_profile, C
from integrations.lift_evaluator import mixture_lp


def job(m):
    out = {}
    T = C.budget(m, 2)
    for g in range(1, m + 1):
        costs = {}
        for i, c in enumerate(cands):
            st, w = word(m, g, c)
            if not w:
                continue
            r = fast_profile(st, w, [0, 1])
            if r and (r[0], r[1]) not in costs:
                costs[(r[0], r[1])] = i
        items = sorted(costs)
        w, B, sl, t = mixture_lp([(b, list(bt)) for b, bt in items], 2, m - 2)
        ok = t == 0 and B < T + 1
        out[g] = [ok, str(B - T), str(t), [[str(x), items[j][0] - T, list(items[j][1]), costs[items[j]]] for j, x in enumerate(w) if x]]
    return m, out


if __name__ == '__main__':
    t0 = time.time()
    with Pool(6) as p:
        res = dict(p.map(job, range(9, 41)))
    json.dump(res, open('candlp-res.json', 'w'))
    print(time.time() - t0)
    for m in range(9, 41):
        print(m, ''.join('#' if res[m][g][0] else '.' for g in range(1, m + 1)), ' '.join(res[m][g][1] for g in range(1, m + 1) if not res[m][g][0]))
