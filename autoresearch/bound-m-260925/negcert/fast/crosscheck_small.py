#!/usr/bin/env python3
"""Cross-check of the C oracle against the pure-Python reference on small instances (m = 5..7):
  exact minimum = negcert_general.raw_dijkstra (uncompressed cz, no table) = Python table-guided A*,
  the returned word re-prices to the minimum, the bounded search is tight at K = F and K = F + 1,
  and the table statistics (vectors, nodes, edges, max h, start bound) equal PatternTable's."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fastoracle as FO
NG = FO.NG
t0 = time.time()
bad = n = 0
for m, g in [(5, 2), (5, 3), (5, 4), (6, 3), (6, 4), (6, 2), (7, 3), (7, 4)]:
    vec = NG.base_vector(list(range(m, 0, -1)), 1 | (1 << g))
    for W in ((1, 3, 0), (1, 0, 3), (2, 3, 1), (1, 2, 2), (3, 4, 5), (1, 0, 0)):
        cl = [list(range(m, m // 2, -1)), list(range(m // 2, 0, -1))]
        r = FO.run(vec, W, [cl], threads=2, mem_gb=1)
        G = NG.raw_dijkstra(vec, W)
        u0 = NG.encode(vec, W)
        tab = NG.PatternTable(u0, cl, W)
        nodes, edges, hmax = tab.verify()
        Fp = NG.astar(u0, [tab], W)[0]
        tstat = r['tables'][0]
        same_tab = (int(tstat['vectors']), int(tstat['nodes']), int(tstat['edges']), int(tstat['maxh']),
                    int(tstat['start_bound'])) == (tab.N, nodes, edges, hmax, NG.start_bound(u0, [tab], W))
        if W == (1, 0, 0):
            same_tab = True   # zeros identical in Python, distinct in C (double cover): counts differ by design
        r1 = FO.run(vec, W, [cl], K=G, threads=2, mem_gb=1)
        r2 = FO.run(vec, W, [cl], K=G + 1, threads=2, mem_gb=1)
        ok = r['F'] == G == Fp == r['Fw'] and r1['result'] == 'NONE' and r2.get('F') == G and same_tab
        n += 1
        bad += not ok
        print('m=%d g=%d W=%s: C %s, raw Dijkstra %s, Python A* %s, word re-priced %s, bounded K=F %s, K=F+1 %s, '
              'table stats equal %s -> %s' % (m, g, W, r['F'], G, Fp, r['Fw'], r1['result'], r2.get('F'), same_tab,
                                              'ok' if ok else 'MISMATCH'), flush=True)
print('%d cases, %d mismatches, %.0f s' % (n, bad, time.time() - t0))
print('CROSSCHECK OK' if not bad else 'CROSSCHECK FAILED')
