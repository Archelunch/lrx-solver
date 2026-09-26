#!/usr/bin/env python3
"""C-backed checker for negcert_general.py certificates (same JSON format, same statement, same proof).

    python3 fast_check.py CERT.json [...] [--mem GB] [--threads T]

Performs every step of negcert_general.check_certificate, with the table build, the table verification and the
bounded A* delegated to lrxfast (C port; see lrxfast.c and README.md for the completeness argument):
  - recomputes the base vector, T = T_m(m+2), s = m-2 from (m, labels, mask) and compares with the certificate;
  - builds each abstraction table and verifies consistency on every abstract node and letter (C, independent of
    the build); any failure -> FAILED;
  - bounded A* pruning at f >= claim_min; 'no terminal below claim_min' proves claim_min; INCOMPLETE -> FAILED;
  - re-prices every witness with negcert_general.profile_cost (pure Python) and checks exactness;
  - root-leaf consequence: claim_min >= wB(T+1) + s(w0+w1) and the implied LP bound, as negcert_general.
The pure-Python checker remains the reference; this program is the verifier where it is too slow (m >= 12).
"""
import argparse
import json
import os
import sys
import time
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fastoracle as FO  # noqa: E402

NG = FO.NG


def check(path, mem, threads, log=print):
    cert = json.load(open(path))
    t0 = time.time()
    m, labels, mask = cert['m'], cert['labels'], cert['mask']
    W = tuple(cert['weights'])
    if cert.get('origin') or cert.get('picks'):
        return ['refined origins / picks are not supported by the C checker; use negcert_general.py']
    vec = NG.base_vector(labels, mask)
    problems = []
    if vec != cert['base']:
        problems.append('state vector %s != certificate %s' % (vec, cert['base']))
    T, s = NG.budget(m, len(vec) - m), m - 2
    if [T, s] != [cert['T'], cert['s']]:
        problems.append('T, s mismatch')
    K = cert['claim_min']
    log('statement: m=%d state=%s  min over accepted sorting words of %d*B + %d*beta_0 + %d*beta_1 >= %d'
        % (m, vec, W[0], W[1], W[2], K))
    r = FO.run(vec, W, cert['abstractions'], K=K, mem_gb=mem, threads=threads, log=log)
    if r.get('inconsistent') or r['result'] in ('ERROR', None):
        problems.append('table verification or run failed: %s' % r.get('reason'))
    elif r['result'] == 'INCOMPLETE':
        problems.append('search INCOMPLETE (%s): no bound' % r.get('reason'))
    elif r['result'] == 'FOUND':
        problems.append('found a word with F = %d < claimed %d: %s' % (r['Fw'], K, r['word']))
    else:
        log('bounded A* (prune f >= %d): no sorting word below %d; %s expansions (%s s)'
            % (K, K, r['stats']['expanded'], r['stats']['search_s']))
    attained = False
    for wit in cert.get('witnesses', []):
        Fw, B, beta = NG.price(vec, wit['word'], W)
        good = [B, beta] == [wit['B'], wit['beta']]
        log('witness %s: B=%d beta=%s F=%d %s' % (wit['word'], B, beta, Fw, 'ok' if good else 'BAD'))
        if not good:
            problems.append('witness mismatch')
        if Fw < K:
            problems.append('witness F %d < claim_min %d' % (Fw, K))
        attained = attained or Fw == K
    if cert.get('exact'):
        if not attained:
            problems.append('exact claimed but no witness attains claim_min %d' % K)
        else:
            log('exact minimum %d (lower bound by search, attained by a witness)' % K)
    if cert.get('kind', 'root') == 'root':
        need = W[0] * (T + 1) + s * (W[1] + W[2])
        verdict = K >= need
        log('root mixture needs Bbar < T+1 = %d and betabar_j <= s = %d, so %d Bbar + %d betabar_0 + %d betabar_1 '
            '< %d; every word, hence every mixture, has >= %d: %s'
            % (T + 1, s, W[0], W[1], W[2], need, K, 'NO ROOT-LEAF CERTIFICATE' if verdict else 'not refuted'))
        lpb = Fraction(K - s * (W[1] + W[2]), W[0])
        log('implied lower bound on the root LP value min{Bbar : betabar_j <= s}: %s (T+1 = %d)' % (lpb, T + 1))
        if 'lp_value' in cert and Fraction(cert['lp_value']) != lpb:
            problems.append('lp_value %s != implied bound %s' % (cert['lp_value'], lpb))
        if cert.get('refutes', True) and not verdict:
            problems.append('bound does not refute the root leaf')
    log('total %.1f s' % (time.time() - t0))
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('certs', nargs='+')
    ap.add_argument('--mem', type=float, default=11.0)
    ap.add_argument('--threads', type=int, default=6)
    a = ap.parse_args()
    ok = True
    for p in a.certs:
        probs = check(p, a.mem, a.threads)
        for pr in probs:
            print('PROBLEM:', pr)
        ok &= not probs
    print('VERIFIED' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
