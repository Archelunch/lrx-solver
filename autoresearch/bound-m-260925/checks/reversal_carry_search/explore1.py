"""Design D1: core 2 = zigzag on [A_2] Zg [B_2] first, then core 1 = zero-core at Z0 carrying A_c (m..m-q+1)
leftwards and B_c (1..p) rightwards, growing into Zg after B_c. Cut t = p. Scan (p, q, seed2, schedules)."""
import sys, time, itertools
from functools import lru_cache
from common import *


@lru_cache(None)
def scheds(nl, nr, D):
    """Strings with nl 'l', nr 'r' and at most D adjacent equal pairs."""
    out = []
    def rec(s, l, r, d):
        if l == 0 and r == 0:
            out.append(s); return
        for ch, rem in (('l', l), ('r', r)):
            if rem == 0: continue
            nd = d + (1 if s and s[-1] == ch else 0)
            if nd > D: continue
            rec(s + ch, l - (ch == 'l'), r - (ch == 'r'), nd)
    rec('', nl, nr, 0)
    return tuple(out)


def run(m, g, D2=1, D1=1, extra_l=(0, 1, 2)):
    st = state(m, g); T = C.budget(m, 2); items = {}
    cnt = 0
    for p in range(0, m - g + 1):
        for q in range(0, g + 1):
            lo2, hi2 = q + 1, m + 1 - p
            for seed in range(lo2, hi2 + 1):
                nl2, nr2 = seed - lo2, hi2 - seed
                for s2 in scheds(nl2, nr2, D2):
                    for xl in extra_l:
                        for s1 in scheds(p + xl, q, D1):
                            w = sched_word(st, p, [(seed, s2), (0, s1)], 'R') 
                            for fin in 'LR':
                                w = sched_word(st, p, [(seed, s2), (0, s1)], fin)
                                if w is None: continue
                                cnt += 1
                                k = price(st, w)
                                if k is None: continue
                                key = (k[0],) + k[1]
                                if key not in items or len(w) < len(items[key][0]):
                                    items[key] = (w, p, q, seed, s2, s1, fin)
    return items, cnt


if __name__ == '__main__':
    for m in range(int(sys.argv[1]), int(sys.argv[2]) + 1):
        j = m // 4
        for g in range(j + 1, m - j):
            t0 = time.time()
            items, cnt = run(m, g)
            fr = pareto(items)
            T = C.budget(m, 2); s = m - 2
            r = root_lp(m, list(fr))
            feas = [(k[0] - T, k[1:]) for k in fr if max(k[1:]) <= s]
            print(m, g, 'words', cnt, 'front', len(fr), r['status'], 'lhs', r.get('value'), 'gap', r['gap'],
                  'best feasible single', min(feas) if feas else None, '%.1fs' % (time.time() - t0), flush=True)
            print('   front', sorted((k[0] - T, k[1], k[2]) for k in fr)[:12])
