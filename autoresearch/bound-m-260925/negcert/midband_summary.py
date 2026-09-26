#!/usr/bin/env python3
"""Summarise exact column-generation runs (midband-runs/small, midband-runs/exact) as a markdown table:
d = min B, F3 = min B + 3 beta_0, G3 = min B + 3 beta_1 (exact seeds), V = exact root LP value, dual lambda."""
import glob, json, os
from fractions import Fraction as Fr
HERE = os.path.dirname(os.path.abspath(__file__))
rows = {}
for f in glob.glob(os.path.join(HERE, 'midband-runs', '*', 'colgen-m*-g*.json')):
    d = json.load(open(f))
    if d.get('mode') != 'exact':
        continue
    seeds = {}
    for c in d['oracle_calls']:
        if c.get('K') is None and isinstance(c.get('F'), int):
            seeds[tuple(c['lambda'])] = c['F']
    rows[(d['m'], d['g'])] = (d['T'], seeds, d['verdict'])
print('| m | g | T | d - T | min B+3b0 - T | min B+3b1 - T | V - T | dual (l0, l1) | root |')
print('|---|---|---|---|---|---|---|---|---|')
for (m, g) in sorted(rows):
    T, seeds, v = rows[(m, g)]
    f = lambda k: (seeds[k] - T) if k in seeds else '-'
    if v and v[0] == 'EXACT LP':
        V = Fr(v[1]) - T
        print('| %d | %d | %d | %s | %s | %s | %s | (%s, %s) | %s |' % (m, g, T, f(('0', '0')), f(('3', '0')), f(('0', '3')), V, v[3], v[4], v[2]))
    else:
        print('| %d | %d | %d | %s | %s | %s | %s | | |' % (m, g, T, f(('0', '0')), f(('3', '0')), f(('0', '3')), v))
