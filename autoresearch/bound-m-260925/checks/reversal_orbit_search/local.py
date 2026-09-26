import sys, time
from gen import core_word, C, make_family
from fast import pareto, fast_profile
from integrations.lift_evaluator import mixture_lp

def local_pool(st, ts, s1s, k1s, d1s, s2s, d2s, fins='RL'):
    out = {}
    for t in ts:
        for s1 in s1s:
            for k1 in k1s:
                for d1 in d1s:
                    for s2 in s2s:
                        for d2 in d2s:
                            for fin in fins:
                                w = core_word(st, t, [(s1, k1, d1), (s2, None, d2)], fin)
                                if w:
                                    out.setdefault(w, (t, s1, k1, d1, s2, d2, fin))
    return out

def front_lp(fam, pool):
    st = fam['unit_base']; k = fam['k']; m = fam['m']
    items = []
    for w, p in pool.items():
        r = fast_profile(st, w, list(range(k)))
        if r:
            items.append((r[0], r[1], (w, p)))
    fr = pareto(items)
    w, B, sl, t = mixture_lp([(b, list(bt)) for b, bt, _ in fr], k, m - 2)
    return fr, w, B, sl, t
