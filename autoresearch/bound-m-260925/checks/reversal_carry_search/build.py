"""Assemble checks/reversal-carry-words.json from the search outputs in this directory. Refuses to overwrite."""
import json, sys
from fractions import Fraction as Fr
from pathlib import Path
from common import *
sys.path.insert(0, str(ROOT / 'autoresearch/bound-m-260925/checks'))
import reversal_carry as RC

DEST = RC.DATA
if DEST.exists():
    sys.exit('refusing to overwrite %s' % DEST)
HERE = Path(__file__).resolve().parent


def jl(name):
    p = HERE / name
    return [json.loads(l) for l in open(p)] if p.exists() else []


cert, seen = [], set()
cover = {}
for m in range(14, 61):
    cf = RC.closed_form_rows(m)
    cover[m] = {side: [x[0] for x in cf[side]] for side in cf}
    if m > 24:
        continue
    for side in ('lo', 'hi'):
        for g, bt, beta in cf[side]:
            if (m, g) in seen: continue
            p, q, s1, seed, first = RC.params_M(m, side)
            s2 = RC.core2_canon(side, m, g, p, q, seed, first)
            w = RC.word_M(m, g, side)
            cert.append({'source': 'word_M closed form (%s)' % side, 'm': m, 'g': g, 'mask': 1 | 1 << g,
                         'output': {'words': [w]}, 'params': [[side, p, q, s1, seed, s2, 'L']],
                         'base_minus_T': bt, 'beta': beta})
            seen.add((m, g))
for src, name in (('word_K root LP (v1 pool)', 'canon-root-14-24.jsonl'), ('word_K root LP (v2 pool)', 'extra2-14-24.jsonl')):
    for r in jl(name):
        if r['status'] != 'CERTIFIED' or (r['m'], r['g']) in seen: continue
        cert.append({'source': src, 'm': r['m'], 'g': r['g'], 'mask': 1 | 1 << r['g'], 'output': {'words': r['words']},
                     'params': [s[2] for s in r['support']],
                     'support': [{'base_minus_T': s[0], 'beta': s[1], 'weight': s[3]} for s in r['support']],
                     'lhs': r['lhs']})
        seen.add((r['m'], r['g']))
for r in jl('opentrees.jsonl'):
    if r['status'] == 'CERTIFIED' and (r['m'], r['g']) not in seen:
        cert.append({'source': 'carry pools, %s' % ('root' if r['n_leaves'] == 1 and 'words' in r['output'] else 'tree'),
                     'm': r['m'], 'g': r['g'], 'mask': 1 | 1 << r['g'], 'output': r['output'], 'params': None,
                     'leaves': r['leaves']})
        seen.add((r['m'], r['g']))

# not certified: best evaluator root gap over the pools run, and the minimum base excess with slopes feasible
best = {}
for name in ('canon-root-14-24.jsonl', 'extra2-14-24.jsonl'):
    for r in jl(name):
        k = (r['m'], r['g'])
        if k in seen: continue
        b = best.setdefault(k, {'m': r['m'], 'g': r['g'], 'root_gap': r['gap'], 'min_base_excess_slopes_feasible': None})
        if Fr(r['gap']) < Fr(b['root_gap']): b['root_gap'] = r['gap']
        if r.get('min_base_excess_slopes_feasible') is not None:
            b['min_base_excess_slopes_feasible'] = r['min_base_excess_slopes_feasible']
notc = [best[k] for k in sorted(best)]
for r in jl('opentrees.jsonl'):
    if r['status'] != 'CERTIFIED':
        notc.append({'m': r['m'], 'g': r['g'], 'tree_search': 'depth <= 4, thresholds <= 6, origins %s' % r['origins'],
                     'best_leaf_lhs': r.get('best_lhs')})

res = {
    'schema': 'lrx-reversal-carry/1', 'date': '2026-09-26',
    'semantics': 'Family (m..1) with zeros in gaps {0,g}, mask 1|1<<g. Outputs are bound-contract-3 outputs; a CERTIFIED '
                 'output proves d(v) <= T_m(n) for every state of the family, conditional on the group\'s Lemma 1 (with '
                 'refinement) and criteria (7)/(8) with m as a parameter.',
    'closed_form': {
        'rule': 'word_M(m, g, side) = word_K(m, g, side, p, q, s1, seed, core2_canon(side, m, g, p, q, seed, first), L) '
                'with (p, q, seed, first) from params_M by m mod 4 (reversal_carry.py). Single word, root leaf, unit origins.',
        'coverage_note': 'coverage[m][side] = band values g (floor(m/4) < g < m - floor(m/4)) where the single word meets '
                         'criterion (7): B < T+1 and both slopes <= m-2. Evaluator + audit for m <= 40, replay + criterion '
                         '(7) for 41..60.',
        'coverage': {str(m): cover[m] for m in cover}},
    'certified': cert,
    'not_certified': notc,
}
DEST.write_text(json.dumps(res, indent=1))
print('wrote', DEST, len(cert), 'certified rows', len(notc), 'not certified rows')
