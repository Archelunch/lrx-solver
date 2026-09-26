"""Closed-form candidate word_M(m, g): canonical carry word with parameters fixed by m mod 4 and the side."""
import sys, json
from common import *
from canon import word_K
from canon2 import core2_canon


def params(m, side):
    j, r = m // 4, m % 4
    if side == 'lo':
        p, q, seed, first = {0: (j - 2, j, 2 * j + 2, 'r'), 1: (j - 1, j, 2 * j + 2, 'r'),
                             2: (j - 1, j, 2 * j + 3, 'l'), 3: (j - 2, j + 1, 2 * j + 4, 'r')}[r]
        s1 = 'r' * (q - p) + 'lr' * p
    else:
        p, q, seed, first = {0: (j, j - 2, 2 * j, 'l'), 1: (j, j - 1, 2 * j + 1, 'l'),
                             2: (j, j - 1, 2 * j + 1, 'r'), 3: (j + 1, j - 2, 2 * j + 1, 'l')}[r]
        s1 = 'l' * (p - q) + 'rl' * q
    return p, q, s1, seed, first


def word_M(m, g, side):
    p, q, s1, seed, first = params(m, side)
    if p < 0 or q < 0 or p > m - g or q > g: return None
    s2 = core2_canon(side, m, g, p, q, seed, first)
    return word_K(m, g, side, p, q, s1, seed, s2, 'L')


if __name__ == '__main__':
    res = {}
    for m in range(int(sys.argv[1]), int(sys.argv[2]) + 1):
        s, T = m - 2, C.budget(m, 2)
        row = []
        for side in ('lo', 'hi'):
            ok = []
            for g in range(1, m):
                w = word_M(m, g, side)
                if not w: continue
                st = state(m, g)
                if not (C.is_root(C.run_naive(st, w)) and C.is_root(C.run(st, w))): continue
                k = price(st, w)
                if k and k[0] - T < 1 and max(k[1]) <= s:
                    ok.append((g, k[0] - T, k[1]))
            row.append(ok)
        lo, hi = row
        j = m // 4
        print(m, 'lo', [x[0] for x in lo], 'hi', [x[0] for x in hi], 'band', (j + 1, m - j - 1))
