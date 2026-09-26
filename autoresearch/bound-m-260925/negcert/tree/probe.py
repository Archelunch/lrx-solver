#!/usr/bin/env python3
"""One lrxtree call on a refined base:  probe.py M G o0,o1 p0,p1 wB,w0,w1 K 'classes' [--omega b/a ...]
[--wcap N] [--cap N] [--exact] [--anytime] [--mem GB].  Prints the parsed result (JSON)."""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import treeoracle as TO
NG = TO.NG
ap = argparse.ArgumentParser()
for x in ('m', 'g', 'origin', 'picks', 'W', 'K', 'classes'):
    ap.add_argument(x)
ap.add_argument('--omega', action='append', default=[])
ap.add_argument('--wcap', type=int)
ap.add_argument('--cap', type=int)
ap.add_argument('--exact', action='store_true')
ap.add_argument('--anytime', action='store_true')
ap.add_argument('--no-search', action='store_true')
ap.add_argument('--mem', type=float, default=5.0)
a = ap.parse_args()
m, g = int(a.m), int(a.g)
o = [int(x) for x in a.origin.split(',')]
pk = [int(x) for x in a.picks.split(',')]
vec = NG.refine(NG.base_vector(list(range(m, 0, -1)), 1 | (1 << g)), o)
cls = [[[int(x) for x in p.split(',')] for p in c.split('|')] for c in a.classes.split(';')]
r = TO.run(vec, tuple(int(x) for x in a.W.split(',')), cls, [pk[0], o[0] + pk[1]], K=int(a.K), cap=a.cap,
           mem_gb=a.mem, omega=a.omega or None, wcap=a.wcap, then_exact=a.exact, anytime=a.anytime,
           no_search=a.no_search)
r.pop('lines', None)
print(json.dumps(r))
