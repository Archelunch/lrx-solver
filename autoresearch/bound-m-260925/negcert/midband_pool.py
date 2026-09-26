#!/usr/bin/env python3
"""Harvest seed words for the root LP: every [LRX]{16,} string in checks/**/*.json|jsonl|log and midband-runs/
that sorts the unit base of (m..1){0,g}, priced by negcert_general.profile_cost.  Writes midband-runs/pool-seeds.json.
Seeds only steer the multipliers; nothing here is a proof."""
import glob, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import negcert_general as NG
targets = [(m, g) for m in range(10, 17) for g in range(1, m)]
pat = re.compile(r'[LRX]{16,}')
words = set()
roots = [os.path.join(HERE, '..', 'checks'), os.path.join(HERE, 'midband-runs')]
for r in roots:
    for ext in ('json', 'jsonl', 'log', 'txt'):
        for f in glob.glob(os.path.join(r, '**', '*.' + ext), recursive=True):
            try:
                words.update(pat.findall(open(f, errors='ignore').read()))
            except OSError:
                pass
print(len(words), 'candidate strings')
out = {}
for m, g in targets:
    vec = NG.base_vector(list(range(m, 0, -1)), 1 | (1 << g))
    n = len(vec)
    pts = {}
    for w in words:
        if not (m * (m + 1) // 2 - 20 <= len(w) <= 3 * m * m):
            continue
        try:
            B, beta = NG.profile_cost(vec, w)
        except ValueError:
            continue
        key = (B, beta[0], beta[1])
        if key not in pts or len(w) < len(pts[key]):
            pts[key] = w
    # keep the Pareto-minimal points
    keys = sorted(pts)
    pareto = [k for k in keys if not any(o != k and all(a <= b for a, b in zip(o, k)) for o in keys)]
    out['%d,%d' % (m, g)] = [[list(k), pts[k]] for k in pareto]
    print(m, g, len(pts), 'sorting words,', len(pareto), 'pareto')
json.dump(out, open(os.path.join(HERE, 'midband-runs', 'pool-seeds.json'), 'w'))
