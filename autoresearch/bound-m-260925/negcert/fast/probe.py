#!/usr/bin/env python3
"""Single C oracle call: python3 probe.py M G wB w0 w1 [--K K] [--classes 'a,b|c|..']... [--cap N] [--mem GB] [--omega a/b]"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fastoracle as FO
ap = argparse.ArgumentParser()
for x in ('m', 'g', 'wB', 'w0', 'w1'):
    ap.add_argument(x, type=int)
ap.add_argument('--K', type=int)
ap.add_argument('--classes', action='append')
ap.add_argument('--cap', type=int)
ap.add_argument('--mem', type=float, default=10)
ap.add_argument('--omega')
ap.add_argument('--threads', type=int, default=6)
ap.add_argument('--no-search', action='store_true')
a = ap.parse_args()
vec = FO.NG.base_vector(list(range(a.m, 0, -1)), 1 | (1 << a.g))
cls = [[[int(x) for x in p.split(',')] for p in c.split('|')] for c in a.classes]
T, s = FO.NG.budget(a.m, 2), a.m - 2
W = (a.wB, a.w0, a.w1)
print('m=%d g=%d W=%s K=%s T=%d s=%d threshold %d classes %s' % (a.m, a.g, W, a.K, T, s, W[0] * (T + 1) + s * (W[1] + W[2]), cls), flush=True)
r = FO.run(vec, W, cls, K=a.K, cap=a.cap, mem_gb=a.mem, threads=a.threads, omega=a.omega, log=lambda x: print(x, flush=True), no_search=a.no_search)
print('returncode', r.get('returncode'), 'result', r.get('result'))
if r.get('result') == 'FOUND':
    print('re-priced: F=%d B=%d beta=%s' % (r['Fw'], r['B'], r['beta']))
