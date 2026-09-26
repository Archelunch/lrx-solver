"""Word pools at a refined origin o = (o0, o1), priced for every pick pair.  Generators: F2 (zero-core at Z0 first,
then zigzag on the rest), D1 (rest first, then zero-core), word_S (reversal_midband_search/gen.py restricted pool)."""
import itertools
from common import *
from explore1 import scheds


def f2_words(m, g, o, D1=1, D2=2, dpq=3):
    st = state(m, g, o); n = len(st); o0, o1 = o
    for p in range(0, m - g + 1):
        for q in range(0, g + 1):
            if abs(p - q) > dpq: continue
            lo2, hi2 = q + o0, n - p - 1
            for s1 in scheds(p, q + o0 - 1, D1 + o0 - 1):
                for seed in range(lo2, hi2 + 1):
                    for s2 in scheds(seed - lo2, hi2 - seed + q, D2):
                        for fin in 'LR':
                            w = sched_word(st, p, [(0, s1), (seed, s2)], fin)
                            if w: yield w, ('F2', p, q, s1, seed, s2, fin)


def d1_words(m, g, o, D2=1, D1=1):
    st = state(m, g, o); n = len(st); o0, o1 = o
    for p in range(0, m - g + 1):
        for q in range(0, g + 1):
            if abs(p - q) > 3: continue
            lo2, hi2 = q + o0, n - p - 1
            for seed in range(lo2, hi2 + 1):
                for s2 in scheds(seed - lo2, hi2 - seed, D2):
                    for xl in (0, 1, 2):
                        for s1 in scheds(p + xl, q + o0 - 1, D1 + o0 - 1):
                            for fin in 'LR':
                                w = sched_word(st, p, [(seed, s2), (0, s1)], fin)
                                if w: yield w, ('D1', p, q, seed, s2, s1, fin)


def f3_words(m, g, o, D1=1, D2=2, dpq=3):
    """k=0: core 1 zero-core at Z0 (cut p), core 2 on [A_2] Zg [B_2] with cut m (Zg sorts to its left end),
    extended left over B_c.  Both core orders."""
    from sw2 import sched_word2
    st = state(m, g, o); n = len(st); o0, o1 = o
    for p in range(0, m - g + 1):
        for q in range(0, g + 1):
            if abs(p - q) > dpq: continue
            lo2, hi2 = q + o0, n - p - 1
            for s1 in scheds(p, q + o0 - 1, D1 + o0 - 1):
                for seed in range(lo2, hi2 + 1):
                    for s2 in scheds(seed - lo2 + p, hi2 - seed, D2):
                        for fin in 'LR':
                            w = sched_word2(st, [(0, s1, p), (seed, s2, m)], fin)
                            if w: yield w, ('F3', p, q, s1, seed, s2, fin)
            for seed in range(lo2, hi2 + 1):
                for s2 in scheds(seed - lo2, hi2 - seed, D2):
                    for xl in (0, 1):
                        for s1 in scheds(p, q + o0 - 1 + xl, D1 + o0 - 1):
                            for fin in 'LR':
                                w = sched_word2(st, [(seed, s2, m), (0, s1, p)], fin)
                                if w: yield w, ('F3r', p, q, seed, s2, s1, fin)


def ws_words(m, g, o):
    import sys as _s
    from pathlib import Path as _P
    _s.path.insert(0, str(_P(__file__).resolve().parents[1] / 'reversal_midband_search'))
    import gen
    for b in range(1, m - g + 1):
        a = m - g - b
        for sc1 in gen.scheds(g + a):
            for ds in (1, 2, 3):
                for fin in 'LR':
                    st, w = gen.word_S(m, g, b, ds, sc1, fin, o)
                    if w: yield w, ('S', b, ds, sc1, fin)


def picks_for(o):
    return [(a, o[0] + b) for a in range(o[0]) for b in range(o[1])]


def pool(m, g, o, gens=('F2', 'D1', 'F3', 'S')):
    """-> {pick_pair: pareto{(B,b0,b1): (word, params)}}"""
    st = state(m, g, o)
    out = {pk: {} for pk in picks_for(o)}
    src = []
    if 'F2' in gens: src.append(f2_words(m, g, o))
    if 'D1' in gens: src.append(d1_words(m, g, o))
    if 'F3' in gens: src.append(f3_words(m, g, o))
    if 'S' in gens: src.append(ws_words(m, g, o))
    seen = set()
    for w, par in itertools.chain(*src):
        if w in seen: continue
        seen.add(w)
        for pk in out:
            k = price(st, w, list(pk))
            if k is None: break
            key = (k[0],) + k[1]
            d = out[pk]
            if key not in d or len(w) < len(d[key][0]):
                d[key] = (w, par)
    return {pk: pareto(d) for pk, d in out.items()}


def leaf_value(m, fr, o, box):
    """fr: pareto dict for one pick pair. -> leaf_lp result."""
    l = [a for a, _ in box]
    costs = [(k[0] + sum(b * (x - y) for b, x, y in zip(k[1:], l, o)), list(k[1:])) for k in fr]
    return leaf_lp(costs, box, m - 2, C.budget(m, sum(l)))


def best_leaf(m, P, o, box):
    best = None
    for pk, fr in P.items():
        if not fr: continue
        r = leaf_value(m, fr, o, box)
        v = (0 if r['status'] == 'CERTIFIED' else 1, r['value'] if r['status'] == 'CERTIFIED' else r['gap'])
        if best is None or v < best[0]:
            best = (v, pk, r)
    return best
