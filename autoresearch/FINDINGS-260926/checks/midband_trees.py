#!/usr/bin/env python3
"""Re-check of the middle-band tree certificates in midband-trees-m12.json (MIDBAND-TREES-M12.md).

For every stored family (CERTIFIED trees, and partial trees whose open leaves carry their best pool):
  1. integrations.bound3_evaluator.score_output on the stored raw output must return the stored status, and
     every leaf lhs must equal the stored lhs;
  2. CERTIFIED only: integrations.bound3_audit.audit_claim (independent m=8 checker at M = m) must agree;
  3. replay: every leaf word is executed literally on its refined base (lrx_m.refine with the leaf origins)
     with lrx_m.run and must end at the root, never swap two zeros (lrx_m.Profile with the leaf picks), and
     re-price to the stored (B, beta).
Leaf refutations stored under "refutations" are negative statements proved by the exact oracle
(negcert/tree/lrxtree.c); with --refutations each is re-run (C oracle, minutes each, one at a time, nice 19).
Writes nothing unless --output is given, and refuses to overwrite an existing output file.

    python3 autoresearch/bound-m-260925/checks/midband_trees.py [--refutations] [--output FILE]
"""
import argparse
import json
import os
import sys
from fractions import Fraction as Fr
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from integrations import lrx_m as C  # noqa: E402
from integrations.bound3_audit import audit_claim  # noqa: E402
from integrations.bound3_evaluator import score_output  # noqa: E402
from integrations.bound3_task import pick_indices  # noqa: E402
from integrations.bound_task import make_family  # noqa: E402

DATA = HERE / 'midband-trees-m12.json'


def leaves_of(node, box):
    if 'le' in node:
        j, t = node['j'], node['t']
        lo, hi = box[j]
        left, right = list(box), list(box)
        left[j], right[j] = (lo, t), (t + 1, hi)
        yield from leaves_of(node['le'], left)
        yield from leaves_of(node['ge'], right)
    else:
        yield node, box


def check_family(row, log):
    fam = make_family(row['labels'], row['mask'])
    ok = True
    r = score_output(fam, row['output'])
    lhs = [x['lhs'] for x in r.get('leaves', [])]
    log('  score_output: %s, gap %s, %s leaves, lhs %s' % (r['status'], r.get('gap'), r.get('n_leaves'), lhs))
    if r['status'] != row['status'] or lhs != row['lhs']:
        log('  stored status %s / lhs %s differ -> FAIL' % (row['status'], row['lhs']))
        return False
    if r['status'] == 'CERTIFIED':
        agree, why = audit_claim(fam, r['output'], r['certificate'])
        log('  audit_claim: %s (%s)' % ('agree' if agree else 'DISAGREE', why))
        ok &= agree
    else:
        log('  not certified: open leaves %s (no audit; a miss proves nothing)'
            % [x['box'] for x in r['leaves'] if x['status'] != 'CERTIFIED'])
    n = 0
    for leaf, box in leaves_of(row['output']['tree'], [(1, None)] * fam['k']):
        o = leaf.get('origins', [1] * fam['k'])
        picks = pick_indices(o, leaf.get('picks', [0] * fam['k']))
        state = C.refine(fam['unit_base'], o)
        for i, w in enumerate(leaf['words']):
            fin = C.run(state, w)
            prof = C.Profile(state, w, picks)  # raises on a zero-zero swap or a non-sorting word
            want = leaf.get('points', [None] * len(leaf['words']))[i]
            if not C.is_root(fin) or (want is not None and [prof.base, prof.beta] != want):
                log('  replay FAIL leaf box %s word %d' % (box, i))
                ok = False
            n += 1
    log('  replay: %d leaf words sort their refined bases%s' % (n, '' if ok else ' (with failures)'))
    return ok


def check_refutation(ref, log):
    sys.path.insert(0, str(HERE.parent / 'negcert' / 'tree'))
    import treeoracle as TO
    base = C.base_vector(list(range(ref['m'], 0, -1)), 1 | (1 << ref['g']))
    vec = C.refine(base, ref['origin'])
    picks = pick_indices(ref['origin'], ref['picks'])
    r = TO.run(vec, ref['W'], ref['classes'], picks, K=ref['K'], mem_gb=ref.get('mem_gb', 5))
    good = r.get('stats', {}).get('expanded') == ref.get('expanded', r.get('stats', {}).get('expanded'))
    log('  expansions %s (stored %s)' % (r.get('stats', {}).get('expanded'), ref.get('expanded')))
    good &= r.get('result') == 'NONE'
    l = [b[0] for b in ref['box']]
    T = C.budget(ref['m'], sum(l))
    lam = [Fr(x) for x in ref['lambda']]
    s = ref['m'] - 2
    W = ref['W']
    good &= Fr(W[1], W[0]) == l[0] - ref['origin'][0] + lam[0] and Fr(W[2], W[0]) == l[1] - ref['origin'][1] + lam[1]
    good &= ref['K'] >= W[0] * (T + 1 + s * (lam[0] + lam[1]))
    log('  refutation %s origin %s picks %s box %s: oracle %s at W=%s K=%s -> %s'
        % (ref['family'], ref['origin'], ref['picks'], ref['box'], r.get('result'), W, ref['K'],
           'VERIFIED' if good else 'FAIL'))
    return good


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=str(DATA))
    ap.add_argument('--refutations', action='store_true')
    ap.add_argument('--output')
    a = ap.parse_args()
    lines = []

    def log(x):
        print(x, flush=True)
        lines.append(x)
    data = json.loads(Path(a.data).read_text())
    allok = True
    for row in data['families']:
        log('%s (m=%d, zeros in gaps %s): stored status %s' % (row['family'], row['m'], row['gaps'], row['status']))
        allok &= check_family(row, log)
    if a.refutations:
        for ref in data.get('refutations', []):
            allok &= check_refutation(ref, log)
    log('ALL OK' if allok else 'FAILURES')
    if a.output:
        out = Path(a.output)
        if out.exists():
            raise SystemExit('refusing to overwrite existing %s' % out)
        out.write_text('\n'.join(lines) + '\n')
    sys.exit(0 if allok else 1)


if __name__ == '__main__':
    main()
