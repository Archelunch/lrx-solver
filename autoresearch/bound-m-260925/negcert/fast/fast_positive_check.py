#!/usr/bin/env python3
"""Re-check positive root certificates found by fast_colgen.py (midband-m12-14-certified.json), exactly as
midband_positive_check.py: bound3_evaluator.score_output must return CERTIFIED, bound3_audit.audit_claim
(True, 'ok'), every word replays to the root under lrx_m.run and run_naive, and lrx_m.mixture_criterion accepts
the stored weights.  Run from the repository root:
    PYTHONPATH=. python3 autoresearch/bound-m-260925/negcert/fast/fast_positive_check.py [FILE]"""
import json, os, sys
from fractions import Fraction as Fr
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', '..')))
from integrations import lrx_m as C
from integrations.bound3_audit import audit_claim
from integrations.bound3_evaluator import score_output
from integrations.bound_task import make_family
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'midband-m12-14-certified.json')
rows = json.load(open(path))['certified']
bad = 0
for row in rows:
    m, g, ws = row['m'], row['g'], row['words']
    fam = make_family(list(range(m, 0, -1)), 1 | 1 << g)
    r = score_output(fam, {'words': ws})
    au = tuple(audit_claim(fam, r['output'], r['certificate'])) if r['status'] == 'CERTIFIED' else None
    rep = all(C.is_root(C.run_naive(fam['unit_base'], w)) and C.is_root(C.run(fam['unit_base'], w)) for w in ws)
    costs = [(C.Profile(fam['unit_base'], w).base, C.Profile(fam['unit_base'], w).beta) for w in ws]
    mc = C.mixture_criterion(costs, [Fr(x) for x in row['weights']], 2, m=m)
    ok = r['status'] == 'CERTIFIED' and au == (True, 'ok') and rep and mc[0]
    bad += not ok
    print('m=%d {0,%d}: score %s lhs %s, audit %s, replay %s, stored weights: Bbar %s betabar %s -> %s'
          % (m, g, r['status'], r['leaves'][0]['lhs'] if r.get('leaves') else None, au, rep, mc[1],
             [str(x) for x in mc[2]], 'ok' if ok else 'FAIL'))
print('problems: none' if not bad else 'problems: %d' % bad)
