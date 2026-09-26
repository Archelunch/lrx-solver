#!/usr/bin/env python3
"""Lift words from a refined base (origin o, picks p) by z (Lemma 1): lift_refined.py M G o0,o1 p0,p1 z0,z1 FILE...
Prints the lifted words (words on refine(base, o + z) with the stretched atom at the picked position).  Seeds only."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', '..')))
from integrations import lrx_m as C
m, g = int(sys.argv[1]), int(sys.argv[2])
o, p, z = ([int(x) for x in a.split(',')] for a in sys.argv[3:6])
state = C.refine(C.base_vector(list(range(m, 0, -1)), 1 | (1 << g)), o)
picks = [p[0], o[0] + p[1]]
out = set()
for f in sys.argv[6:]:
    for w in open(f).read().split():
        try:
            out.add(C.Profile(state, w, picks).lift(tuple(z)))
        except C.CheckError:
            pass
print('\n'.join(sorted(out)))
