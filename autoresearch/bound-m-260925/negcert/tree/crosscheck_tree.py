#!/usr/bin/env python3
"""Cross-check of lrxtree against the pure-Python reference on small refined origins (m = 5, 6):
exact minimum = negcert_general.raw_dijkstra (uncompressed cz, no table) = Python table-guided A* = the
returned word's price (negcert_general.price and integrations.lrx_m.Profile), bounded search NONE at K = F and
F at K = F + 1; unit origins included as a regression against lrxfast."""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', '..')))
import treeoracle as TO
from integrations import lrx_m as C
NG = TO.NG
t0 = time.time()
bad = n = 0
for m, g in [(5, 2), (5, 3), (6, 3), (6, 2)]:
    base = NG.base_vector(list(range(m, 0, -1)), 1 | (1 << g))
    for o in ((1, 1), (2, 1), (1, 2), (2, 2), (3, 1)):
        vec = NG.refine(base, list(o))
        for pk in {(0, 0), (o[0] - 1, 0), (0, o[1] - 1), (o[0] - 1, o[1] - 1)}:
            picks = [pk[0], o[0] + pk[1]]
            for W in ((1, 3, 0), (1, 0, 3), (2, 3, 1), (3, 4, 5), (1, 0, 0)):
                cl = [list(range(m, m // 2, -1)), list(range(m // 2, 0, -1))]
                r = TO.run(vec, W, [cl], picks, threads=2, mem_gb=1)
                G = NG.raw_dijkstra(vec, W, picks)
                u0 = NG.encode(vec, W, picks)
                tab = NG.PatternTable(u0, cl, W)
                tab.verify()
                Fp = NG.astar(u0, [tab], W)[0]
                prof = C.Profile(vec, r['word'], picks)
                Fl = W[0] * prof.base + W[1] * prof.beta[0] + W[2] * prof.beta[1]
                r1 = TO.run(vec, W, [cl], picks, K=G, threads=2, mem_gb=1)
                r2 = TO.run(vec, W, [cl], picks, K=G + 1, threads=2, mem_gb=1)
                ok = r['F'] == G == Fp == r['Fw'] == Fl and r1['result'] == 'NONE' and r2.get('F') == G
                n += 1
                bad += not ok
                if not ok or n % 10 == 0:
                    print('m=%d g=%d o=%s picks=%s W=%s: C %s raw %s A* %s Profile %s K=F %s K=F+1 %s -> %s'
                          % (m, g, o, picks, W, r['F'], G, Fp, Fl, r1['result'], r2.get('F'), 'ok' if ok else 'MISMATCH'),
                          flush=True)
print('%d cases, %d mismatches, %.0f s' % (n, bad, time.time() - t0))
print('CROSSCHECK OK' if not bad else 'CROSSCHECK FAILED')
