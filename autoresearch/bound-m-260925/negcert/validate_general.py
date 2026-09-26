#!/usr/bin/env python3
"""Cross-check negcert_general.profile_cost against the REPOSITORY's lrx_m.Profile (imports it on purpose).
Run from the repository root: python3 autoresearch/bound-m-260925/negcert/validate_general.py"""
import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import negcert_general as NG
from integrations import lrx_m as C
rng = random.Random(7)
n = bad = rej = 0
states = []
for m in (4, 5, 6):
    for g in range(1, m):
        base = NG.base_vector(list(range(m, 0, -1)), 1 | 1 << g)
        for origin in ([1, 1], [2, 1], [1, 2], [3, 1]):
            states.append(NG.refine(base, origin))
for st in states:
    blocks = NG.blocks_of(st)
    for _ in range(40):
        picks = [rng.choice(b) for b in blocks]
        pre = ''.join(rng.choice('LRXX') for _ in range(rng.randint(0, 25)))
        u = NG._apply(NG.encode(st, (1, 1, 1)), pre)
        if u is None:
            continue
        w = pre + NG._sorter(u)
        try:
            mine = NG.profile_cost(st, w, picks)
        except ValueError:
            mine = None
        try:
            p = C.Profile(st, w, picks=picks)
            theirs = (p.base, p.beta)
        except C.CheckError:
            theirs = None
        n += 1
        rej += mine is None
        if mine != theirs:
            bad += 1
            print('MISMATCH', st, picks, w, mine, theirs)
print('%d words (%d rejected by both), %d mismatches with lrx_m.Profile: %s' % (n, rej, bad, 'VALIDATED' if bad == 0 else 'FAILED'))
