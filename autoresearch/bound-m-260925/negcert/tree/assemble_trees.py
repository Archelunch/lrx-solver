#!/usr/bin/env python3
"""Assemble tree certificates from certified leaf runs (runs/leaf-*.json) and score them.

    python3 assemble_trees.py SPEC.json OUT.json      (refuses to overwrite OUT)

SPEC: {"families": [{"m", "g", "tree": NODE}], "refutations": [...]}, NODE = {"j", "t", "le", "ge"} or
{"leaf": "runs/leaf-....json", "open"?: true}; an open leaf
contributes its best pool mixture, and the family is then scored BOUNDARY or NO_CERTIFICATE, not CERTIFIED.  A leaf takes the support words and exact weights of the stored leaf LP
(bound3_evaluator.leaf_lp) and must match the box the tree gives it.  Each family is scored with
bound3_evaluator.score_output and audited with bound3_audit.audit_claim before it is written."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', '..')))
from integrations import lrx_m as C  # noqa: E402
from integrations.bound3_audit import audit_claim  # noqa: E402
from integrations.bound3_evaluator import score_output  # noqa: E402
from integrations.bound3_task import pick_indices  # noqa: E402
from integrations.bound_task import make_family  # noqa: E402


def build(node, box, fam):
    if 'leaf' in node:
        d = json.load(open(os.path.join(HERE, node['leaf'])))
        want = [[lo, 'inf' if hi is None else hi] for lo, hi in box]
        if d['box'] != want or (d['leaf_lp']['status'] != 'CERTIFIED' and not node.get('open')):
            raise SystemExit('leaf %s: box %s / status %s, tree box %s' % (node['leaf'], d['box'],
                                                                             d['leaf_lp']['status'], want))
        words = [w for w, _ in d['leaf_lp']['support']]
        o, pk = d['origin'], d['picks']
        state = C.refine(fam['unit_base'], o)
        pts = []
        for w in words:
            p = C.Profile(state, w, pick_indices(o, pk))
            pts.append([p.base, list(p.beta)])
        leaf = {'words': words, 'origins': o, 'picks': pk, 'points': pts, 'source': node['leaf']}
        if d['leaf_lp']['status'] == 'CERTIFIED':
            leaf['weights'] = [x for _, x in d['leaf_lp']['support']]
        else:
            leaf['open'] = True  # best pool mixture of an uncertified leaf (the evaluator re-solves it)
        return leaf
    j, t = node['j'], node['t']
    lo, hi = box[j]
    left, right = list(box), list(box)
    left[j], right[j] = (lo, t), (t + 1, hi)
    return {'j': j, 't': t, 'le': build(node['le'], left, fam), 'ge': build(node['ge'], right, fam)}


def strip(node):
    """Evaluator output: drop the bookkeeping keys 'points' and 'source' (not part of bound-contract-3)."""
    if 'j' in node:
        return {'j': node['j'], 't': node['t'], 'le': strip(node['le']), 'ge': strip(node['ge'])}
    return {x: node[x] for x in ('words', 'origins', 'picks', 'weights') if x in node}


def main():
    spec, out = sys.argv[1], sys.argv[2]
    if os.path.exists(out):
        raise SystemExit('refusing to overwrite existing %s' % out)
    spec = json.load(open(spec))
    rows = []
    for f in spec['families']:
        m, g = f['m'], f['g']
        fam = make_family(list(range(m, 0, -1)), 1 | (1 << g))
        full = build(f['tree'], [(1, None)] * 2, fam)
        output = {'tree': strip(full), 'note': 'm=%d zeros in gaps {0,%d}: tree certificate, leaves priced by the '
                  'exact oracle negcert/tree/lrxtree.c' % (m, g)}
        r = score_output(fam, output)
        agree = audit_claim(fam, r['output'], r['certificate']) if r['status'] == 'CERTIFIED' else (None, None)
        print('m=%d {0,%d}: %s, gap %s, leaves %s, lhs %s, audit %s' % (
            m, g, r['status'], r['gap'], r.get('n_leaves'), [x['lhs'] for x in r.get('leaves', [])], agree))
        rows.append({'family': fam['id'], 'm': m, 'gaps': [0, g], 'labels': fam['labels'], 'mask': fam['mask'],
                     'status': r['status'], 'lhs': [x['lhs'] for x in r.get('leaves', [])],
                     'leaves': [{'box': x['box'], 'origins': x['origins'], 'picks': x['picks'], 'T': x['T'],
                                 'lhs': x['lhs'], 'support': [{k: s[k] for k in ('word', 'weight', 'base', 'beta')}
                                                             for s in x['support']]} for x in r.get('leaves', [])],
                     'output': output, 'tree_with_points': full, 'audit': agree[0]})
    json.dump({'about': 'Middle-band tree certificates and leaf refutations (MIDBAND-TREES-M12.md); re-check '
                        'with checks/midband_trees.py', 'families': rows,
               'refutations': spec.get('refutations', [])}, open(out, 'w'), indent=1)
    print('wrote %s' % out)


if __name__ == '__main__':
    main()
