"""Canonical carry words (stdlib + sched_word2).  word_K(m, g, side, p, q, s1, seed, s2, fin):
side 'lo' (F3, k=0: Zg sorts to the left end of core 2, cut m) or 'hi' (F2, k=1: Zg to the right end, cut p).
Core 1 = zero-core at cell 0 (cut p): q large labels cross Z0 leftwards, p small ones rightwards.
Core 2 = zigzag over [A_2] Zg [B_2], extended over B_c ('lo') or A_c ('hi')."""
import sys, time, itertools
from common import *
from sw2 import sched_word2
from explore1 import scheds


def word_K(m, g, side, p, q, s1, seed, s2, fin='L'):
    st = state(m, g)
    t2 = m if side == 'lo' else p
    return sched_word2(st, [(0, s1, p), (seed, s2, t2)], fin)


def alt(nl, nr, first):
    """Alternating string with nl 'l', nr 'r', starting with `first`, one-sided tail at the end."""
    s, l, r, cur = '', nl, nr, first
    while l or r:
        if cur == 'l' and l: s += 'l'; l -= 1
        elif cur == 'r' and r: s += 'r'; r -= 1
        else:
            s += 'l' if l else 'r'; l -= (s[-1] == 'l'); r -= (s[-1] == 'r')
        cur = 'r' if cur == 'l' else 'l'
    return s


def one_defect(nl, nr):
    """All strings with nl 'l', nr 'r' and at most one adjacent repeat beyond what the counts force."""
    return scheds(nl, nr, max(1, abs(nl - nr)))


def family(m, g, sides=('lo', 'hi'), dpq=(1, 2), D2=1):
    n = m + 2
    for side in sides:
        for big in range(1, m // 2 + 2):
            for d in dpq:
                if side == 'lo':
                    p, q = big, big + d          # q = p + d, schedule 'r'*d... (rr(lr)*)
                    s1s = ['r' * d + 'lr' * p, 'r' * (d - 1) + 'rl' * p + 'r']
                else:
                    q, p = big, big + d
                    s1s = ['l' * d + 'rl' * q, 'l' * (d - 1) + 'lr' * q + 'l']
                if p > m - g or q > g: continue
                lo2, hi2 = q + 1, n - p - 1
                for s1 in s1s:
                    for seed in range(lo2, hi2 + 1):
                        if side == 'lo':
                            nl, nr = seed - lo2 + p, hi2 - seed
                        else:
                            nl, nr = seed - lo2, hi2 - seed + q
                        if abs(nl - nr) > 3: continue
                        for s2 in scheds(nl, nr, max(D2, abs(nl - nr))):
                            for fin in 'LR':
                                w = word_K(m, g, side, p, q, s1, seed, s2, fin)
                                if w: yield w, (side, p, q, s1, seed, s2, fin)


def front(m, g, **kw):
    st = state(m, g); items = {}
    for w, par in family(m, g, **kw):
        k = price(st, w)
        if k is None: continue
        key = (k[0],) + k[1]
        if key not in items or len(w) < len(items[key][0]):
            items[key] = (w, par)
    return pareto(items)


if __name__ == '__main__':
    import json
    out = open(sys.argv[3], 'a') if len(sys.argv) > 3 else None
    for m in range(int(sys.argv[1]), int(sys.argv[2]) + 1):
        row = []
        for g in range(m // 4 + 1, m - m // 4):
            t0 = time.process_time()
            fr = front(m, g); keys = list(fr)
            r = root_lp(m, keys); T = C.budget(m, 2)
            sup = [(keys[i][0] - T, keys[i][1:], fr[keys[i]][1], str(x)) for i, x in enumerate(r['weights']) if x]
            row.append('%d:%s' % (g, ('C%s' % r['value']) if r['status'] == 'CERTIFIED' else ('gap%s' % r['gap'])))
            if out:
                out.write(json.dumps({'m': m, 'g': g, 'status': r['status'], 'lhs': str(r.get('value')),
                                      'gap': str(r['gap']), 'support': [[x[0], list(x[1]), list(x[2]), x[3]] for x in sup],
                                      'words': [fr[keys[i]][0] for i, x in enumerate(r['weights']) if x],
                                      'cpu': round(time.process_time() - t0, 1)}) + '\n'); out.flush()
        print(m, ' '.join(row), flush=True)
