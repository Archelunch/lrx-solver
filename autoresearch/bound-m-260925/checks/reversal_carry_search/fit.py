"""Fit: single-word certificates from the canonical family without swaps; report parameters per (m, g)."""
import sys, json
from common import *
from canon import word_K
from canon2 import core2_canon
out = open(sys.argv[3], 'w') if len(sys.argv) > 3 else None
for m in range(int(sys.argv[1]), int(sys.argv[2]) + 1):
    s, T, n = m - 2, C.budget(m, 2), m + 2
    for g in range(m // 4 + 1, m - m // 4):
        best = None
        for side in ('lo', 'hi'):
            for small in range(1, m // 4 + 3):
                for d in (1, 2, 3):
                    p, q = (small, small + d) if side == 'lo' else (small + d, small)
                    if p > m - g or q > g: continue
                    s1 = ('r' * d + 'lr' * p) if side == 'lo' else ('l' * d + 'rl' * q)
                    for seed in range(q + 1, n - p):
                        for first in 'lr':
                            s2 = core2_canon(side, m, g, p, q, seed, first)
                            for fin in 'L':
                                w = word_K(m, g, side, p, q, s1, seed, s2, fin)
                                if not w: continue
                                k = price(state(m, g), w)
                                if k and max(k[1]) <= s and k[0] - T < 1:
                                    v = (k[0] - T, side, p, q, seed, first, k[1])
                                    if best is None or v < best: best = v
        print(m, g, best, flush=True)
        if out: out.write(json.dumps([m, g, best]) + '\n')
