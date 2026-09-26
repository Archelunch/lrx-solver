#!/usr/bin/env python3
"""Validation on the stored m = 9..11 certificates: bounded C search at K = claim_min (must prove no word below K,
with the same expansion count as the Python checker's log when given) and at K + 1 (must return a word of
value exactly K when the certificate is exact)."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fastoracle as FO
NG = FO.NG
PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY_EXPANSIONS = {'negcert-m11-05.json': 23907926, 'lpcert-m11-06.json': 9477482}
bad = 0
for name in sys.argv[1:] or ['lpcert-m10-05.json', 'lpcert-m11-06.json', 'negcert-m11-05.json']:
    c = json.load(open(os.path.join(PARENT, name)))
    vec = NG.base_vector(c['labels'], c['mask'])
    W, K = tuple(c['weights']), c['claim_min']
    t0 = time.time()
    r1 = FO.run(vec, W, c['abstractions'], K=K, mem_gb=8, threads=6)
    line = '%s: W=%s K=%d: bounded search %s, %s expansions (Python: %s)' % (
        name, W, K, r1['result'], r1['stats']['expanded'], PY_EXPANSIONS.get(name, 'not logged'))
    ok = r1['result'] == 'NONE' and (name not in PY_EXPANSIONS or int(r1['stats']['expanded']) == PY_EXPANSIONS[name])
    if c.get('exact'):
        r2 = FO.run(vec, W, c['abstractions'], K=K + 1, mem_gb=8, threads=6)
        line += '; K+1: %s F=%s (B=%s beta=%s)' % (r2['result'], r2.get('F'), r2.get('B'), r2.get('beta'))
        ok &= r2.get('F') == K == r2.get('Fw')
    line += '; tables %s; %.0f s -> %s' % ([(t['vectors'], t['start_bound']) for t in r1['tables']], time.time() - t0,
                                           'ok' if ok else 'MISMATCH')
    bad += not ok
    print(line, flush=True)
print('VALIDATION OK' if not bad else 'VALIDATION FAILED')
