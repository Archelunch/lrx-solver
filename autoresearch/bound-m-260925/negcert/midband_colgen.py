#!/usr/bin/env python3
"""Column generation for the root-leaf LP of (m..1){0,g} with the exact oracle of negcert_general.py.

    python3 midband_colgen.py M G [--classes 'a,b|c|...'] [--cap N] [--budget SECONDS] [--out DIR]

Root LP:  V = min Bbar  s.t.  betabar_j <= s (j = 0, 1), a mixture of accepted sorting words of the unit base.
Dual:     V = max over l >= 0 of  phi(l) = min_w [B + l0 beta_0 + l1 beta_1] - s (l0 + l1).
Loop: pool P -> exact small LP (vertex enumeration in Fractions) -> multipliers l_P and V_P.
  If V_P < T + 1: the pool itself certifies the root leaf (reported, mixture printed).
  Else run the oracle at l_P with bound K = wB (T+1) + s (w0 + w1) (integer scaling of l_P):
    'no word below K'  -> refutation with multipliers l_P (certificate written);
    else the optimal word (F < K) joins P, repeat.
Exploration only: the certificate it writes is re-checked by negcert_general.py.
"""
import argparse
import itertools
import json
import math
import os
import sys
import time
from fractions import Fraction as Fr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import negcert_general as NG  # noqa: E402

LMAX = Fr(12)


def solve3(rows, rhs):
    """Solve a 3x3 system in Fractions; None if singular."""
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


def pool_lp(pool, s):
    """max t - s(l0 + l1) s.t. t <= B + l0 b0 + l1 b1 (pool), 0 <= l_j <= LMAX.  Returns (value, l0, l1)."""
    cons = [((1, -b0, -b1), B) for B, b0, b1 in pool]           # t - l0 b0 - l1 b1 <= B
    box = [((0, -1, 0), 0), ((0, 0, -1), 0), ((0, 1, 0), LMAX), ((0, 0, 1), LMAX)]
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


def primal_mixture(pool, s):
    """Best mixture of <= 3 pool words (min Bbar s.t. betabar <= s) by enumeration; for reporting."""
    best = None
    n = len(pool)
    for k in (1, 2, 3):
        for tri in itertools.combinations(range(n), k):
            pts = [pool[i] for i in tri]
            # grid over simplex vertices of the feasible region: solve with active constraints
            cands = []
            if k == 1:
                cands = [[Fr(1)]]
            elif k == 2:
                cands = [[Fr(1), Fr(0)], [Fr(0), Fr(1)]]
                for j in (1, 2):
                    a, b = pts[0][j], pts[1][j]
                    if a != b:
                        x = Fr(s - b, a - b)
                        if 0 <= x <= 1:
                            cands.append([x, 1 - x])
            else:
                A = [[Fr(p[1]) for p in pts], [Fr(p[2]) for p in pts], [Fr(1)] * 3]
                sol = solve3(A, [Fr(s), Fr(s), Fr(1)])
                if sol and all(x >= 0 for x in sol):
                    cands.append(sol)
            for mu in cands:
                b0 = sum(x * p[1] for x, p in zip(mu, pts))
                b1 = sum(x * p[2] for x, p in zip(mu, pts))
                if b0 <= s and b1 <= s:
                    B = sum(x * p[0] for x, p in zip(mu, pts))
                    if best is None or B < best[0]:
                        best = (B, [(x, tri[i]) for i, x in enumerate(mu) if x])
    return best


def scale(l0, l1):
    den = math.lcm(l0.denominator, l1.denominator)
    return (den, int(l0 * den), int(l1 * den))


def wastar(u0, tables, W, K, omega, cap):
    """Weighted A* (priority g + omega*h, prune g + h >= K): returns the first word with F < K, or None.
    Not optimal and not a proof; a column generator only."""
    import heapq
    step = NG.make_step(W)
    roots = NG.roots_of(u0)
    tabs = [(t.tr, t.idx, t.h) for t in tables]

    def H(u, c):
        return max(h[idx[u.translate(tr)] * 16 + c] for tr, idx, h in tabs)
    par = {u0 + b'\x00': None}
    best = {u0 + b'\x00': 0}
    heap = [(0, 0, u0, 0)]
    n = 0
    while heap and n < cap:
        _, g, u, c = heapq.heappop(heap)
        key = u + bytes([c])
        if best[key] < g:
            continue
        n += 1
        if u in roots and g + NG.final_cost(c, W) < K:
            w = []
            while par[key] is not None:
                key, ch = par[key]
                w.append(ch)
            return ''.join(reversed(w)), n
        for ch in 'LRX':
            st = step(u, c, ch)
            if st is None:
                continue
            t, c2, wt = st
            ng = g + wt
            k2 = t + bytes([c2])
            if best.get(k2, 1 << 30) > ng:
                hv = H(t, c2)
                if ng + hv >= K:
                    continue
                best[k2] = ng
                par[k2] = (key, ch)
                heapq.heappush(heap, (ng + omega * hv, ng, t, c2))
    return None, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('m', type=int)
    ap.add_argument('g', type=int)
    ap.add_argument('--classes', action='append')
    ap.add_argument('--cap', type=int, default=30_000_000)
    ap.add_argument('--budget', type=float, default=1200)
    ap.add_argument('--out', default='.')
    ap.add_argument('--mode', choices=('refute', 'exact'), default='refute')
    ap.add_argument('--seeds', help='pool-seeds.json from midband_pool.py')
    ap.add_argument('--no-exact-seeds', action='store_true')
    ap.add_argument('--omega', type=float, action='append', default=[])
    ap.add_argument('--wcap', type=int, default=3_000_000)
    a = ap.parse_args()
    m, g = a.m, a.g
    vec = NG.base_vector(list(range(m, 0, -1)), 1 | (1 << g))
    T, s = NG.budget(m, 2), m - 2
    if a.classes:
        classes = [[[int(x) for x in part.split(',')] for part in c.split('|')] for c in a.classes]
    else:
        classes = [[list(range(m, 0, -1))[i:i + 3] for i in range(0, m, 3)]]
    t_start = time.time()
    pool, words, log = [], [], []

    def add(word):
        B, beta = NG.profile_cost(vec, word)
        pt = (B, beta[0], beta[1])
        if pt in pool:
            return False
        pool.append(pt)
        words.append(word)
        return True

    def oracle(l0, l1, K_of_W):
        W = scale(Fr(l0), Fr(l1))
        u0 = NG.encode(vec, W)
        t0 = time.time()
        tabs = [NG.PatternTable(u0, cl, W) for cl in classes]
        for t in tabs:
            t.verify()
        tt = time.time() - t0
        K = K_of_W(W) if K_of_W else None
        sb = NG.start_bound(u0, tabs, W)
        t1 = time.time()
        if K is not None:
            for om in a.omega:
                wd, n = wastar(u0, tabs, W, K, om, a.wcap)
                Fw = NG.price(vec, wd, W)[0] if wd else None
                rec = {'lambda': [str(Fr(l0)), str(Fr(l1))], 'W': list(W), 'K': K, 'weighted_astar': om,
                       'expansions': n, 'F': Fw, 'search_s': round(time.time() - t1, 1)}
                if wd:
                    _, B, beta = NG.price(vec, wd, W)
                    rec.update(B=B, beta=beta)
                print('  heuristic %s' % json.dumps(rec), flush=True)
                log.append(dict(rec, word=wd))
                if wd:
                    return W, K, Fw, wd
                t1 = time.time()
        rec = {'lambda': [str(Fr(l0)), str(Fr(l1))], 'W': list(W), 'K': K, 'start_bound': sb,
               'table_s': round(tt, 1)}
        try:
            F, word, exp, stored = NG.astar(u0, tabs, W, bound=K, node_cap=a.cap)
        except NG.Incomplete:
            rec.update(F='INCOMPLETE', search_s=round(time.time() - t1, 1))
            print('  oracle %s' % json.dumps(rec), flush=True)
            log.append(rec)
            raise
        rec.update(F=F, word=word, expansions=exp, stored=stored, search_s=round(time.time() - t1, 1))
        if word:
            Fw, B, beta = NG.price(vec, word, W)
            assert Fw == F
            rec.update(B=B, beta=beta)
        print('  oracle %s' % json.dumps(rec), flush=True)
        log.append(rec)
        return W, K, F, word

    print('m=%d g=%d T=%d s=%d mode=%s classes=%s' % (m, g, T, s, a.mode, classes), flush=True)
    if a.seeds:
        for pt, w in json.load(open(a.seeds)).get('%d,%d' % (m, g), []):
            add(w)
        print('  %d seed words from %s' % (len(pool), a.seeds), flush=True)
    if not a.no_exact_seeds:
        for l0, l1 in ((0, 0), (3, 0), (0, 3)):
            add(oracle(l0, l1, None)[3])
    verdict, it, cert_W = None, 0, None
    try:
        while time.time() - t_start < a.budget:
            it += 1
            V, l0, l1 = pool_lp(pool, s)
            mix = primal_mixture(pool, s)
            print('iter %d: pool %d, pool LP value %s (T+1 = %d) at lambda = (%s, %s); best <=3-mixture %s'
                  % (it, len(pool), V, T + 1, l0, l1, mix and mix[0]), flush=True)
            if a.mode == 'refute':
                if V < T + 1:
                    verdict = ['POOL CERTIFIES ROOT', str(V), str(mix)]
                    break
                Kf = lambda W: W[0] * (T + 1) + s * (W[1] + W[2])
            else:
                Kf = lambda W, V=V: int(W[0] * V + s * (W[1] + W[2]))
            W, K, F, word = oracle(l0, l1, Kf)
            if F is None:
                if a.mode == 'exact':
                    verdict = ['EXACT LP', str(V), 'certifiable' if V < T + 1 else 'REFUTED', str(l0), str(l1)]
                    print('  exact root LP value %s at lambda (%s, %s): %s' % (V, l0, l1, verdict[2]), flush=True)
                    if V >= T + 1:
                        cert_W = (l0, l1, W, K)
                else:
                    verdict = ['REFUTED', str(l0), str(l1)]
                    cert_W = (l0, l1, W, K)
                break
            if not add(word):
                verdict = ['ERROR: oracle returned a pool point below K']
                break
        else:
            verdict = ['BUDGET', str(pool_lp(pool, s))]
    except NG.Incomplete:
        verdict = ['INCOMPLETE (node cap)', str(pool_lp(pool, s))]
    if cert_W:
        l0, l1, W, K = cert_W
        need = W[0] * (T + 1) + s * (W[1] + W[2])
        print('  REFUTED: every word has %d B + %d beta_0 + %d beta_1 >= %d >= %d = wB(T+1) + s(w0+w1)'
              % (W + (K, need)), flush=True)
        wits = sorted((NG.price(vec, w, W)[0], w) for w in words)
        exact = wits[0][0] == K
        if not exact:
            try:
                _, _, Fx, wx = oracle(l0, l1, None)
                add(wx)
                wits = sorted((NG.price(vec, w, W)[0], w) for w in words)
                K, exact = Fx, True
            except NG.Incomplete:
                print('  exact minimum at the refuting multipliers: INCOMPLETE (cap)', flush=True)
        cert = {'family': 'reversal (%d..1) with zeros in gaps {0,%d}, unit base, root leaf' % (m, g),
                'm': m, 'labels': list(range(m, 0, -1)), 'mask': 1 | (1 << g), 'base': vec, 'T': T, 's': s,
                'weights': list(W), 'lambda': [str(l0), str(l1)], 'claim_min': K, 'exact': exact,
                'refutation_threshold': need, 'kind': 'root', 'abstractions': classes, 'witnesses': []}
        for Fw, w in wits[:3]:
            _, B, beta = NG.price(vec, w, W)
            cert['witnesses'].append({'word': w, 'B': B, 'beta': beta, 'F': Fw})
        path = os.path.join(a.out, 'negcert-m%d-0%d.json' % (m, g))
        if not os.path.exists(path):
            with open(path, 'w') as fh:
                json.dump(cert, fh, indent=1)
            print('  wrote', path, flush=True)
    print('verdict', verdict, 'total %.0f s' % (time.time() - t_start), flush=True)
    with open(os.path.join(a.out, 'colgen-m%d-g%d.json' % (m, g)), 'w') as fh:
        json.dump({'m': m, 'g': g, 'T': T, 's': s, 'mode': a.mode, 'classes': classes, 'pool': pool,
                   'words': words, 'oracle_calls': log, 'verdict': verdict}, fh, indent=1)


if __name__ == '__main__':
    main()
