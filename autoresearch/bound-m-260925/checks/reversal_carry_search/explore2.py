"""Design F2: core 1 = zero-core at Z0 (cell 0) carrying A_c = m..m-q+1 leftwards and B_c = 1..p rightwards
(word_C core 1 with one zero); core 2 = zigzag on [A_2] Zg [B_2], extended right over A_c (each passes Zg only).
Cut t = p.  Scan p, q, core-1 schedule, core-2 seed and schedule (<= D adjacent repeats)."""
import sys, time
from common import *
from explore1 import scheds


def run(m, g, o=(1, 1), D1=1, D2=2):
    st = state(m, g, o); n = len(st); o0, o1 = o
    items = {}; cnt = 0
    picks = [0, o0]
    for p in range(0, m - g + 1):
        for q in range(0, g + 1):
            if abs(p - q) > 3: continue
            # after core 1 (seed 0, grows into the zero block for free) cells: n-p .. q+o0-1
            lo2, hi2 = q + o0, n - p - 1          # A_2 .. Zg block .. B_2
            for s1 in scheds(p, q + o0 - 1, D1 + o0 - 1):
                for seed in range(lo2, hi2 + 1):
                    nl2, nr2 = seed - lo2, hi2 - seed + q
                    for s2 in scheds(nl2, nr2, D2):
                        for fin in 'LR':
                            w = sched_word(st, p, [(0, s1), (seed, s2)], fin)
                            if w is None: continue
                            cnt += 1
                            k = price(st, w, picks)
                            if k is None: continue
                            key = (k[0],) + k[1]
                            if key not in items or len(w) < len(items[key][0]):
                                items[key] = (w, p, q, s1, seed, s2, fin)
    return items, cnt


if __name__ == '__main__':
    D2 = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    for m in range(int(sys.argv[1]), int(sys.argv[2]) + 1):
        j = m // 4
        for g in range(j + 1, m - j):
            t0 = time.time()
            items, cnt = run(m, g, D2=D2)
            fr = pareto(items)
            T = C.budget(m, 2); s = m - 2
            r = root_lp(m, list(fr))
            feas = [(k[0] - T, k[1:]) for k in fr if max(k[1:]) <= s]
            print(m, g, 'words', cnt, 'front', len(fr), r['status'], 'lhs', r.get('value'), 'gap', r['gap'],
                  'best feasible single', min(feas) if feas else None, '%.1fs' % (time.time() - t0), flush=True)
            print('   front', sorted((k[0] - T, k[1], k[2]) for k in fr)[:14])
