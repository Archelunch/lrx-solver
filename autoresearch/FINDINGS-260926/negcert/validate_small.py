#!/usr/bin/env python3
"""Validation of negcert_check.py against brute force priced by the REPOSITORY's lrx_m.Profile.

Run from the repository root:  python3 autoresearch/bound-m-260925/negcert/validate_small.py
(This script, unlike the checker, imports integrations/lrx_m.py on purpose: it compares the checker's
exact A* minimum with an exhaustive enumeration priced by the original Profile class.)

Part 1 (m = 5, 6): every REDUCED word (no LR, RL, XX) of length <= F* whose prefixes satisfy
    len(prefix) + d(prefix state) <= F*, where d is the exact BFS distance on the small (m, r) graph with
    distinguishable zeros built here.  For a reduced word B = length, so F >= length >= len(prefix) +
    d(state after prefix); the enumeration therefore contains every reduced sorting word with F <= F*.
    Each sorting word is priced by lrx_m.Profile.  Pass iff the brute-force minimum equals F*.
Part 2 (m = 3, 4): every word, reduced or not, of length <= Lmax, priced by lrx_m.Profile.  Pass iff the
    brute-force minimum is >= F* and equals F* whenever F* <= Lmax (this exercises Lemma R).
"""
import os
import sys
import time
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import negcert_check as NC  # noqa: E402
from integrations import lrx_m as C  # noqa: E402


def moves(u):
    yield 'L', u[1:] + u[:1]
    yield 'R', u[-1:] + u[:-1]
    if not (u[0] >= 100 and u[1] >= 100):
        yield 'X', bytes([u[1], u[0]]) + u[2:]


def dist_table(vec):
    m = sum(1 for x in vec if x)
    roots = NC.roots_of(m, len(vec) - m)
    d = {g: 0 for g in roots}
    dq = deque(roots)
    while dq:
        u = dq.popleft()
        for _, t in moves(u):          # moves are invertible (L/R, X self-inverse), so BFS is symmetric
            if t not in d:
                d[t] = d[u] + 1
                dq.append(t)
    return d, roots


def exact_min(vec, lam):
    m = sum(1 for x in vec if x)
    classes = [list(range(m, m // 2, -1)), list(range(m // 2, 0, -1))]
    tab = NC.PatternTable(m, len(vec) - m, classes, lam)
    tab.verify()
    F, w, _ = NC.astar(vec, [tab], lam)
    return F, w


def brute_reduced(vec, lam, bound):
    d, roots = dist_table(vec)
    best, count, sorters = None, 0, 0
    stack = [(NC.encode(vec), '')]
    visited = 0
    while stack:
        u, w = stack.pop()
        visited += 1
        if u in roots:
            sorters += 1
            try:
                p = C.Profile(vec, w)
            except C.CheckError:
                p = None
            if p is not None:
                F = p.base + lam * p.beta[0]
                if best is None or F < best:
                    best, count = F, 1
                elif F == best:
                    count += 1
        for ch, t in moves(u):
            if w and w[-1] + ch in ('LR', 'RL', 'XX'):
                continue
            if len(w) + 1 + d[t] <= bound:
                stack.append((t, w + ch))
    return best, count, sorters, visited


def brute_all(vec, lam, lmax):
    d, roots = dist_table(vec)
    best = None
    stack = [(NC.encode(vec), '')]
    n = 0
    while stack:
        u, w = stack.pop()
        if u in roots:
            n += 1
            try:
                p = C.Profile(vec, w)
                F = p.base + lam * p.beta[0]
                best = F if best is None else min(best, F)
            except C.CheckError:
                pass
        if len(w) < lmax:
            for ch, t in moves(u):
                if len(w) + 1 + d[t] <= lmax:
                    stack.append((t, w + ch))
    return best, n


def main():
    ok = True
    t0 = time.time()
    print('Part 1: reduced words, table-pruned, priced by lrx_m.Profile')
    for m, mask, lams in ((5, 1 | 4, (1, 3)), (5, 1 | 8, (1, 3)), (5, 1 | 16, (1, 3)), (5, 1 | 2 | 16, (3,)),
                          (5, 2 | 8, (3,)), (6, 1 | 4, (1, 3)), (6, 1 | 8, (1, 3)), (6, 1 | 16, (3,)),
                          (6, 1 | 32, (3,)), (6, 4 | 32, (3,))):
        vec = C.base_vector(list(range(m, 0, -1)), mask)
        for lam in lams:
            t1 = time.time()
            F, w = exact_min(vec, lam)
            p = C.Profile(vec, w)
            bm, cnt, sorters, visited = brute_reduced(vec, lam, F)
            good = bm == F and p.base + lam * p.beta[0] == F
            ok &= good
            print('  m=%d mask=%-9s lam=%d  checker %d  brute %s (%d optimal of %d sorting words, %d prefixes)'
                  '  %s  %.1fs' % (m, bin(mask), lam, F, bm, cnt, sorters, visited, 'ok' if good else 'MISMATCH',
                                  time.time() - t1))
    print('Part 2: all words (non-reduced included) up to Lmax, priced by lrx_m.Profile')
    for m, mask, lam, lmax in ((3, 1 | 4, 1, 16), (3, 1 | 4, 3, 16), (3, 1 | 2, 3, 16), (3, 2 | 8, 3, 16),
                               (4, 1 | 4, 1, 15), (4, 1 | 8, 3, 15)):
        vec = C.base_vector(list(range(m, 0, -1)), mask)
        t1 = time.time()
        F, w = exact_min(vec, lam)
        bm, n = brute_all(vec, lam, lmax)
        good = bm is not None and bm >= F and (F > lmax or bm == F)
        ok &= good
        print('  m=%d mask=%-7s lam=%d  checker %d (len %d)  brute min over %d sorting words of length <= %d: %s  %s'
              '  %.1fs' % (m, bin(mask), lam, F, len(w), n, lmax, bm, 'ok' if good else 'MISMATCH', time.time() - t1))
    print('total %.1f s' % (time.time() - t0))
    print('VALIDATED' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
