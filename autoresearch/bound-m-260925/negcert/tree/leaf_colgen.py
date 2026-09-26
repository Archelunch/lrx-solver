#!/usr/bin/env python3
"""Column generation for ONE tree leaf of the unit base of (m..1){0,g}, with lrxtree as the exact pricing oracle.
Exploration; every positive is re-checked by ../../checks/midband_trees.py (evaluator + audit + replay).

    python3 leaf_colgen.py M G --origin o0,o1 --picks p0,p1 --box l0:h0,l1:h1 (h = inf allowed)
                          --classes 'a,b|c|..' [--omega b/a ...] [--wcap N] [--mem GB] [--budget S] [--seeds FILE]

Leaf LP (bound3_evaluator.leaf_lp, criterion (8)): costs C_i(l) = B_i + beta_i.(l - o), lhs = Cbar(l) - T(l)
  + sum_{bounded j} max(0, betabar_j - s)(h_j - l_j), betabar_j <= s on unbounded axes; the leaf passes iff lhs < 1.
Dual: max_lambda  min_i [C_i(l) + lambda.beta_i] - lambda.s,  0 <= lambda_j <= h_j - l_j (bounded), <= LMAX
  (unbounded; a cap only weakens the dual, never the refutation).  Weak duality: for every feasible mixture,
  lhs + T(l) >= min_i [C_i(l) + lambda.beta_i] - lambda.s.  Hence if EVERY accepted sorting word w of the refined
  base (picks fixed) has  F_W(w) = B + (l - o + lambda).beta >= T(l) + 1 + lambda.s,  no certificate exists at
  this leaf with this origin and these picks: LEAF REFUTED.  Pricing = lrxtree at W = den (1, l - o + lambda),
  K = ceil(den (T(l) + 1 + lambda.s)).
"""
import argparse
import itertools
import json
import math
import os
import sys
import time
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, ROOT)
import treeoracle as TO  # noqa: E402
from integrations import lrx_m as C  # noqa: E402
from integrations.bound3_evaluator import leaf_lp  # noqa: E402

NG = TO.NG
LMAX = Fr(16)


def solve3(rows, rhs):
    M = [[Fr(x) for x in r] + [Fr(b)] for r, b in zip(rows, rhs)]
    for c in range(3):
        p = next((r for r in range(c, 3) if M[r][c] != 0), None)
        if p is None:
            return None
        M[c], M[p] = M[p], M[c]
        for r in range(3):
            if r != c and M[r][c] != 0:
                f = M[r][c] / M[c][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    return [M[r][3] / M[r][r] for r in range(3)]


def dual(costs, caps, s):
    """costs [(C_i(l), beta_i)]; max t - s(l0+l1), t <= C + l.beta, 0 <= l_j <= caps_j.  -> (value, l0, l1)."""
    pts = sorted(set((c, b[0], b[1]) for c, b in costs))
    # drop dominated points (c, b0, b1 all >=)
    pts = [p for p in pts if not any(q != p and q[0] <= p[0] and q[1] <= p[1] and q[2] <= p[2] for q in pts)]
    cons = [((1, -b0, -b1), c) for c, b0, b1 in pts]
    box = [((0, -1, 0), 0), ((0, 0, -1), 0), ((0, 1, 0), caps[0]), ((0, 0, 1), caps[1])]
    allc = cons + box
    best = None
    for tri in itertools.combinations(range(len(allc)), 3):
        sol = solve3([allc[i][0] for i in tri], [allc[i][1] for i in tri])
        if sol is None:
            continue
        t, l0, l1 = sol
        if all(a[0] * t + a[1] * l0 + a[2] * l1 <= b for a, b in allc):
            val = t - s * (l0 + l1)
            if best is None or val > best[0] or (val == best[0] and (l0 + l1, l0) < (best[1] + best[2], best[1])):
                best = (val, l0, l1)
    return best


def parse_classes(spec):
    return [[int(x) for x in p.split(',')] for p in spec.split('|')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('m', type=int)
    ap.add_argument('g', type=int)
    ap.add_argument('--origin', required=True)
    ap.add_argument('--picks', default='0,0', help='atom index inside each block')
    ap.add_argument('--box', required=True, help='l0:h0,l1:h1 with h = inf for unbounded')
    ap.add_argument('--classes', action='append', required=True)
    ap.add_argument('--classes2', action='append', default=[], help='tables used when both multipliers are > 0')
    ap.add_argument('--omega', action='append', default=[])
    ap.add_argument('--wcap', type=int, default=20_000_000)
    ap.add_argument('--anytime', action='store_true')
    ap.add_argument('--mem', type=float, default=4.5)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--budget', type=float, default=2400)
    ap.add_argument('--seeds', action='append', default=[], help='file of words (one per line) on THIS refined base')
    ap.add_argument('--tag', default='')
    ap.add_argument('--out', default=os.path.join(HERE, 'runs'))
    a = ap.parse_args()
    m, g = a.m, a.g
    o = [int(x) for x in a.origin.split(',')]
    pk = [int(x) for x in a.picks.split(',')]
    box = []
    for part in a.box.split(','):
        lo, hi = part.split(':')
        box.append((int(lo), None if hi == 'inf' else int(hi)))
    l = [x for x, _ in box]
    assert all(o[j] <= l[j] for j in range(2)) and all(0 <= pk[j] < o[j] for j in range(2))
    base = NG.base_vector(list(range(m, 0, -1)), 1 | (1 << g))
    vec = NG.refine(base, o)
    picks = [pk[0], o[0] + pk[1]]
    Tl, s = C.budget(m, sum(l)), m - 2
    caps = [Fr(h - x) if h is not None else LMAX for x, h in box]
    classes = [parse_classes(c) for c in a.classes]
    classes2 = [parse_classes(c) for c in a.classes2] or classes
    t_start = time.time()
    pool, words, calls = [], [], []

    def log(x):
        print(x, flush=True)

    def add(word):
        B, beta = NG.profile_cost(vec, word, picks)
        pt = (B, beta[0], beta[1])
        if pt in pool:
            return False
        pool.append(pt)
        words.append(word)
        return True

    def costs():
        return [(B + b0 * (l[0] - o[0]) + b1 * (l[1] - o[1]), [b0, b1]) for B, b0, b1 in pool]

    log('m=%d g=%d origin=%s picks=%s (global %s) box=%s T(l)=%d s=%d n=%d classes=%s omega=%s wcap=%d'
        % (m, g, o, pk, picks, box, Tl, s, len(vec), classes, a.omega, a.wcap))
    for f in a.seeds:
        for w in open(f).read().split():
            try:
                add(w)
            except ValueError:
                pass
    log('  %d seed words' % len(pool))
    verdict, it = None, 0
    while True:
        if time.time() - t_start > a.budget:
            verdict = ['BUDGET']
            break
        it += 1
        if pool:
            res = leaf_lp(costs(), box, s, Tl)
            if res['status'] == 'CERTIFIED':
                verdict = ['CERTIFIED', str(res['value'])]
                log('iter %d: pool %d CERTIFIES the leaf, lhs %s' % (it, len(pool), res['value']))
                break
            V, l0, l1 = dual(costs(), caps, s)
        else:
            V, l0, l1 = None, Fr(0), Fr(0)
        log('iter %d: pool %d, dual value %s (need < T(l)+1 = %d) at lambda = (%s, %s)  [%.0f s]'
            % (it, len(pool), V, Tl + 1, l0, l1, time.time() - t_start))
        a0, a1 = Fr(l[0] - o[0]) + l0, Fr(l[1] - o[1]) + l1
        den = math.lcm(a0.denominator, a1.denominator)
        W = (den, int(a0 * den), int(a1 * den))
        thr = den * (Tl + 1 + s * (l0 + l1))
        K = math.ceil(thr)
        r = TO.run(vec, W, classes2 if W[1] and W[2] else classes, picks, K=K, mem_gb=a.mem, threads=a.threads, omega=a.omega, wcap=a.wcap,
                   then_exact=True, anytime=a.anytime)
        rec = {'lambda': [str(l0), str(l1)], 'W': list(W), 'K': K, 'threshold': str(thr), 'result': r['result'],
               'exact_pass': r['result'] != 'FOUND' or r.get('exact_pass'), 'weighted': r.get('weighted'),
               'wstats': r.get('wstats'), 'stats': r.get('stats'), 'tables': r['tables'],
               'start_bound': r.get('start_bound'), 'reason': r.get('reason'), 'returncode': r.get('returncode'),
               'dual_value': None if V is None else str(V)}
        if r['result'] == 'FOUND':
            rec.update(F=r['Fw'], B=r['B'], beta=r['beta'], word=r['word'])
        log('  oracle %s' % json.dumps({x: rec[x] for x in rec if x not in ('tables',)}))
        calls.append(rec)
        if r['result'] == 'NONE':
            verdict = ['REFUTED', str(l0), str(l1), list(W), K]
            break
        if r['result'] != 'FOUND':
            verdict = ['INCOMPLETE', r.get('reason'), None if V is None else str(V), str(l0), str(l1), list(W), K]
            break
        if not add(r['word']):
            verdict = ['ERROR: oracle returned a pool point below K']
            break
    out = {'m': m, 'g': g, 'origin': o, 'picks': pk, 'box': [[x, 'inf' if h is None else h] for x, h in box],
           'T': Tl, 's': s, 'classes': classes, 'pool': pool, 'words': words, 'calls': calls, 'verdict': verdict,
           'total_s': round(time.time() - t_start)}
    if pool:
        res = leaf_lp(costs(), box, s, Tl)
        out['leaf_lp'] = {'status': res['status'], 'value': str(res['value']), 'gap': str(res['gap']),
                          'gap_value': str(res.get('gap_value')),
                          'support': [[words[i], str(x)] for i, x in enumerate(res['weights']) if x]}
        log('leaf LP: %s' % json.dumps(out['leaf_lp']))
    log('verdict %s; total %.0f s' % (verdict, time.time() - t_start))
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, 'leaf-m%d-g%d-o%d%d-p%d%d-%s%s-%s.json' % (
        m, g, o[0], o[1], pk[0], pk[1], a.tag and a.tag + '-', a.box.replace(':', '').replace(',', '_'),
        time.strftime('%H%M%S')))
    if os.path.exists(path):
        raise SystemExit('refusing to overwrite %s' % path)
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    log('wrote %s' % path)


if __name__ == '__main__':
    main()
