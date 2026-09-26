#!/usr/bin/env python3
"""Column generation for the root-leaf LP of (m..1){0,g} with the C oracle (exploration; every positive is
re-checked by fast_positive_check.py, every refutation by fast_check.py and, where feasible, negcert_general.py).

    python3 fast_colgen.py M G --classes 'a,b|c|..' [--classes ...] [--omega 2/1 ...] [--wcap N] [--cap N]
                           [--mem GB] [--budget S] [--mode refute|exact] [--out DIR]

Loop (as midband_colgen.py): pool P -> exact pool LP (Fractions) -> multipliers l_P, value V_P.
  refute mode: V_P < T+1 -> the pool certifies the root (mixture reported); else one C call at l_P with
    K = wB(T+1) + s(w0+w1): optional weighted A* passes (capped at --wcap; a column generator, never a bound),
    then the exact bounded A* on the same tables.  'NONE' -> refutation at l_P; a word -> joins P.
  exact mode: K = wB V_P + s(w0+w1); 'NONE' -> exact root LP value V_P.
"""
import argparse
import json
import os
import sys
import time
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fastoracle as FO  # noqa: E402
sys.path.insert(0, os.path.dirname(HERE))
import midband_colgen as MC  # noqa: E402  (pool_lp, primal_mixture, scale: exact Fraction LP helpers)

NG = FO.NG
SEEDS = [os.path.join(os.path.dirname(HERE), 'midband-runs', f) for f in ('pool-seeds.json', 'pool-seeds-2.json')]


def parse_classes(spec):
    return [[int(x) for x in p.split(',')] for p in spec.split('|')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('m', type=int)
    ap.add_argument('g', type=int)
    ap.add_argument('--classes', action='append', required=True)
    ap.add_argument('--omega', action='append', default=[])
    ap.add_argument('--wcap', type=int, default=20_000_000)
    ap.add_argument('--cap', type=int, default=0)
    ap.add_argument('--anytime', action='store_true')
    ap.add_argument('--mem', type=float, default=10.0)
    ap.add_argument('--budget', type=float, default=3600)
    ap.add_argument('--mode', choices=('refute', 'exact'), default='refute')
    ap.add_argument('--extra-words', help='file with extra seed words, one per line')
    ap.add_argument('--out', default=os.path.join(HERE, 'runs'))
    a = ap.parse_args()
    m, g = a.m, a.g
    vec = NG.base_vector(list(range(m, 0, -1)), 1 | (1 << g))
    T, s = NG.budget(m, 2), m - 2
    classes = [parse_classes(c) for c in a.classes]
    t_start = time.time()
    pool, words, calls = [], [], []

    def add(word):
        B, beta = NG.profile_cost(vec, word)
        pt = (B, beta[0], beta[1])
        if pt in pool:
            return False
        pool.append(pt)
        words.append(word)
        return True

    def log(x):
        print(x, flush=True)

    log('m=%d g=%d T=%d s=%d mode=%s classes=%s omega=%s wcap=%d' % (m, g, T, s, a.mode, classes, a.omega, a.wcap))
    for f in SEEDS:
        if os.path.exists(f):
            for pt, w in json.load(open(f)).get('%d,%d' % (m, g), []):
                add(w)
    if a.extra_words:
        for w in open(a.extra_words).read().split():
            try:
                add(w)
            except ValueError:
                pass
    log('  %d seed words' % len(pool))
    verdict = None
    it = 0
    while True:
        if time.time() - t_start > a.budget:
            verdict = ['BUDGET']
            break
        it += 1
        V, l0, l1 = MC.pool_lp(pool, s)
        mix = MC.primal_mixture(pool, s)
        log('iter %d: pool %d, pool LP value %s (T+1 = %d) at lambda = (%s, %s); best <=3-mixture %s  [%.0f s]'
            % (it, len(pool), V, T + 1, l0, l1, mix and mix[0], time.time() - t_start))
        if a.mode == 'refute' and V < T + 1:
            verdict = ['POOL CERTIFIES ROOT', str(V)]
            break
        W = MC.scale(Fr(l0), Fr(l1))
        K = W[0] * (T + 1) + s * (W[1] + W[2]) if a.mode == 'refute' else int(W[0] * V + s * (W[1] + W[2]))
        r = FO.run(vec, W, classes, K=K, cap=a.cap or None, mem_gb=a.mem, omega=a.omega, wcap=a.wcap,
                   then_exact=True, anytime=a.anytime)
        rec = {'lambda': [str(l0), str(l1)], 'W': list(W), 'K': K, 'result': r['result'],
               'exact_pass': r['result'] != 'FOUND' or r.get('exact_pass'), 'weighted': r.get('weighted'),
               'wstats': r.get('wstats'), 'stats': r.get('stats'), 'tables': r['tables'],
               'start_bound': r.get('start_bound'), 'reason': r.get('reason'),
               'returncode': r.get('returncode')}
        if r['result'] == 'FOUND':
            rec.update(F=r['Fw'], B=r['B'], beta=r['beta'], word=r['word'])
        log('  oracle %s' % json.dumps(rec))
        calls.append(rec)
        if r['result'] == 'NONE':
            if a.mode == 'exact':
                verdict = ['EXACT LP', str(V), 'certifiable' if V < T + 1 else 'REFUTED', str(l0), str(l1), list(W), K]
            else:
                verdict = ['REFUTED', str(l0), str(l1), list(W), K]
            break
        if r['result'] != 'FOUND':
            verdict = ['INCOMPLETE', r.get('reason'), str(V), str(l0), str(l1), list(W), K]
            break
        word = r['word']
        if not add(word):
            verdict = ['ERROR: oracle returned a pool point below K']
            break
    V, l0, l1 = MC.pool_lp(pool, s)
    mix = MC.primal_mixture(pool, s)
    mixture = None
    if mix:
        mixture = {'Bbar': str(mix[0]), 'words': [words[i] for _, i in mix[1]], 'weights': [str(x) for x, _ in mix[1]],
                   'points': [pool[i] for _, i in mix[1]]}
    log('verdict %s; pool LP %s at (%s, %s); best mixture %s; total %.0f s' % (verdict, V, l0, l1,
                                                                               mix and mix[0], time.time() - t_start))
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, 'colgen-m%d-g%d-%s.json' % (m, g, time.strftime('%H%M%S')))
    with open(path, 'w') as fh:
        json.dump({'m': m, 'g': g, 'T': T, 's': s, 'mode': a.mode, 'classes': classes,
                   'pool': pool, 'words': words, 'calls': calls, 'verdict': verdict, 'pool_lp': [str(V), str(l0), str(l1)],
                   'mixture': mixture, 'total_s': round(time.time() - t_start)}, fh, indent=1)
    log('wrote %s' % path)


if __name__ == '__main__':
    main()
