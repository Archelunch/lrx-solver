#!/usr/bin/env python3
"""Write a negcert_general-format refutation certificate from a fast_colgen.py result JSON whose verdict is
REFUTED:  python3 make_cert.py runs/colgen-mM-gG-*.json OUT.json"""
import json, os, sys
from fractions import Fraction as Fr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fastoracle as FO
NG = FO.NG
d = json.load(open(sys.argv[1]))
assert d['verdict'][0] == 'REFUTED', d['verdict']
_, l0, l1, W, K = d['verdict']
m, g = d['m'], d['g']
vec = NG.base_vector(list(range(m, 0, -1)), 1 | (1 << g))
T, s = NG.budget(m, 2), m - 2
W = tuple(W)
need = W[0] * (T + 1) + s * (W[1] + W[2])
assert K == need
wits = sorted((NG.price(vec, w, W)[0], w) for w in d['words'])
exact = wits[0][0] == K
lp = Fr(K - s * (W[1] + W[2]), W[0])
cert = {'family': 'reversal (%d..1) with zeros in gaps {0,%d}, unit base, root leaf' % (m, g), 'm': m,
        'labels': list(range(m, 0, -1)), 'mask': 1 | (1 << g), 'base': vec, 'T': T, 's': s, 'weights': list(W),
        'lambda': [l0, l1], 'claim_min': K, 'exact': exact, 'refutation_threshold': need, 'kind': 'root',
        'abstractions': d['classes'], 'witnesses': []}
if exact:
    cert['lp_value'] = str(lp)
for F, w in wits:
    if F == K or (not exact and len(cert['witnesses']) < 3):
        _, B, beta = NG.price(vec, w, W)
        cert['witnesses'].append({'word': w, 'B': B, 'beta': beta, 'F': F})
tail = ('; witnesses attain %d, so the minimum is exact and the root LP value is exactly %s' % (K, lp)
        if exact else '; witnesses are upper-bound evidence only')
cert['consequence'] = ('every accepted sorting word has %d B + %d beta_0 + %d beta_1 >= %d = %d (T+1) + s (%d + %d), '
                       'so no mixture has Bbar < %d and betabar_j <= %d: no root-leaf certificate for m = %d {0,%d}%s'
                       % (W[0], W[1], W[2], K, W[0], W[1], W[2], T + 1, s, m, g, tail))
cert['assumed'] = 'only the Lemma 1 bookkeeping definitions (integrations/lrx_m.Profile, transcribed in negcert_general.profile_cost)'
cert['verifier'] = 'fast/fast_check.py (C search lrxfast); the pure-Python negcert_general.py is infeasible at this size (see README)'
if os.path.exists(sys.argv[2]):
    sys.exit('refusing to overwrite ' + sys.argv[2])
json.dump(cert, open(sys.argv[2], 'w'), indent=1)
print('wrote', sys.argv[2], 'W', W, 'K', K, 'exact', exact, 'LP', lp, 'witnesses', [(x['B'], x['beta']) for x in cert['witnesses']])
