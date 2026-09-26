#!/usr/bin/env python3
"""Search driver for MIDBAND-LOWERBOUND.md (exploration; certificates are checked by negcert_general.py).

    python3 midband_driver.py M G W_B W_0 W_1 [--bound K] [--classes 'a,b|c,d|...'] [--cap N]
            [--origin o0,o1] [--picks p0,p1] [--write CERT.json]

Runs the exact A* of negcert_general.py on the unit base of (M..1){0,G} (or a refined origin) for
F = W_B*B + W_0*beta_0 + W_1*beta_1.  Without --bound: exact minimum and an optimal word.  With --bound K:
either a word with F < K (the optimum) or a proof that F >= K.  --write stores a certificate for the
proven bound (claim_min = exact minimum if found, else K) with the witness when available.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import negcert_general as NG  # noqa: E402


def default_classes(m, size):
    labs = list(range(m, 0, -1))
    return [labs[i:i + size] for i in range(0, m, size)]


def parse_classes(spec):
    return [[int(x) for x in part.split(',')] for part in spec.split('|')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('m', type=int)
    ap.add_argument('g', type=int)
    ap.add_argument('wB', type=int)
    ap.add_argument('w0', type=int)
    ap.add_argument('w1', type=int)
    ap.add_argument('--bound', type=int)
    ap.add_argument('--classes', action='append')
    ap.add_argument('--cap', type=int, default=40_000_000)
    ap.add_argument('--origin')
    ap.add_argument('--picks')
    ap.add_argument('--write')
    ap.add_argument('--witness', action='append', default=[])
    a = ap.parse_args()
    m, g, W = a.m, a.g, (a.wB, a.w0, a.w1)
    vec = NG.base_vector(list(range(m, 0, -1)), 1 | (1 << g))
    origin = [int(x) for x in a.origin.split(',')] if a.origin else None
    if origin:
        vec = NG.refine(vec, origin)
    picks = [int(x) for x in a.picks.split(',')] if a.picks else None
    r = len(vec) - m
    T, s = NG.budget(m, r), m - 2
    need = W[0] * (T + 1) + s * (W[1] + W[2])
    u0 = NG.encode(vec, W, picks)
    classes = [parse_classes(c) for c in a.classes] if a.classes else [default_classes(m, 3)]
    print('m=%d g=%d origin=%s picks=%s W=%s T=%d s=%d root-refutation threshold %d' % (m, g, origin, picks, W, T, s, need),
          flush=True)
    tabs = []
    for cl in classes:
        t0 = time.time()
        tab = NG.PatternTable(u0, cl, W)
        nodes, edges, hmax = tab.verify()
        tabs.append(tab)
        print('  table %s: %d vectors, verified, start bound %d (%.1f s)'
              % (cl, tab.N, NG.start_bound(u0, [tab], W), time.time() - t0), flush=True)
    t0 = time.time()
    try:
        F, word, exp, stored = NG.astar(u0, tabs, W, bound=a.bound, node_cap=a.cap,
                                        log=lambda x: print(x, flush=True))
    except NG.Incomplete as e:
        print('  INCOMPLETE: %s (%.1f s)' % (e, time.time() - t0))
        return
    dt = time.time() - t0
    if F is None:
        print('  PROVED: every word has F >= %d  (%d expansions, %d stored, %.1f s)' % (a.bound, exp, stored, dt))
        claim = a.bound
    else:
        Fw, B, beta = NG.price(vec, word, W, picks)
        print('  EXACT MIN F = %d  word %s  B=%d beta=%s re-priced F=%d  (%d expansions, %d stored, %.1f s)'
              % (F, word, B, beta, Fw, exp, stored, dt))
        claim = F
    print('  verdict: min %s %d vs threshold %d -> %s' % ('>=' if F is None else '=', claim, need,
                                                          'NO ROOT-LEAF CERTIFICATE' if claim >= need else 'not refuted'),
          flush=True)
    if a.write:
        wits = []
        for w in ([word] if word else []) + a.witness:
            Fw, B, beta = NG.price(vec, w, W, picks)
            wits.append({'word': w, 'B': B, 'beta': beta, 'F': Fw})
        cert = {'family': 'reversal (%d..1) with zeros in gaps {0,%d}' % (m, g), 'm': m,
                'labels': list(range(m, 0, -1)), 'mask': 1 | (1 << g), 'base': vec, 'T': T, 's': s,
                'weights': list(W), 'claim_min': claim, 'exact': F is not None, 'kind': 'root' if not origin else 'origin',
                'abstractions': classes, 'witnesses': wits}
        if origin:
            cert['origin'] = origin
        if picks:
            cert['picks'] = picks
        with open(a.write, 'x') as fh:
            json.dump(cert, fh, indent=1)
        print('  wrote', a.write)


if __name__ == '__main__':
    main()
