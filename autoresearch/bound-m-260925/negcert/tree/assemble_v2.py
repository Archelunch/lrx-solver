#!/usr/bin/env python3
"""Refine the two open m = 12 leaves of checks/midband-trees-m12.json (v1) by one split each and score the trees
with the unchanged evaluator (integrations.bound3_evaluator.score_output).

  {0,5}: open leaf [4,inf) x {1} at origin (3,1)  ->  u0 <= 4 : point {4} x {1}   |  u0 >= 5 : [5,inf) x {1}
  {0,6}: open leaf [3,inf) x {1} at origin (3,1)  ->  u0 <= 3 : point {3} x {1}   |  u0 >= 4 : [4,inf) x {1}

The tail leaves reuse one stored origin-(3,1) word each ((111,(8,15)) resp. (109,(8,13)), slope 8 < s = 10).
The point leaves use the stored words, or --point5 / --point6 FILE (words at the given --o5 / --o6 origin, e.g. a
certifying word found by suffix_opt.py).  Prints per-family status and leaf lhs; with --output writes the
v2 data file (same format as v1; refuses to overwrite).
"""
import argparse, copy, json, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from integrations import lrx_m as C  # noqa: E402
from integrations.bound3_evaluator import score_output  # noqa: E402
from integrations.bound_task import make_family  # noqa: E402
from integrations.bound3_task import pick_indices  # noqa: E402

V1 = HERE.parents[1] / 'checks' / 'midband-trees-m12.json'


def pt(fam, o, w, pk=(0, 0)):
    st = C.refine(fam['unit_base'], list(o))
    p = C.Profile(st, w, pick_indices(list(o), list(pk)))
    return [p.base, list(p.beta)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--point5')
    ap.add_argument('--o5', default='3,1')
    ap.add_argument('--point6')
    ap.add_argument('--o6', default='3,1')
    ap.add_argument('--output')
    a = ap.parse_args()
    d = json.loads(V1.read_text())
    out = {'about': 'Middle-band trees v2 (MIDBAND-TREES-M12-V2.md): v1 with the open m = 12 leaves split at one point; '
                    're-check with checks/midband_trees_v2.py', 'families': [], 'refutations': d['refutations']}
    for row in d['families']:
        row = copy.deepcopy(row)
        fam = make_family(row['labels'], row['mask'])
        if row['m'] == 12:
            g = row['gaps'][1]
            tree = row['output']['tree']
            node = tree['ge']['le']                      # u0 >= 2, u1 <= 1 subtree
            if g == 5:
                parent, key = node['ge'], 'ge'           # [4,inf) x {1}
                open_leaf = node[key]
                tpoint, tail_B = 4, (111, [8, 15])
                pfile, po = a.point5, [int(x) for x in a.o5.split(',')]
            else:
                parent, key = node, 'ge'                  # [3,inf) x {1}
                open_leaf = node[key]
                tpoint, tail_B = 3, (109, [8, 13])
                pfile, po = a.point6, [int(x) for x in a.o6.split(',')]
            words = open_leaf['words']
            tail = [w for w in words if pt(fam, (3, 1), w) == [tail_B[0], tail_B[1]]]
            assert len(tail) == 1, (g, [pt(fam, (3, 1), w) for w in words])
            if pfile:
                pw = open(pfile).read().split()
                point = {'words': pw, 'origins': po, 'picks': [0, 0]}
            else:
                point = {'words': words, 'origins': [3, 1], 'picks': [0, 0]}
            node[key] = {'j': 0, 't': tpoint, 'le': point,
                         'ge': {'words': tail, 'origins': [3, 1], 'picks': [0, 0], 'weights': ['1']}}
            row['output'] = {'tree': tree, 'note': 'v1 tree with the open leaf split at u0 = %d (point leaf and a '
                                                   'tail at origin (3,1))' % tpoint}
        r = score_output(fam, row['output'])
        row['status'] = r['status']
        row['lhs'] = [x['lhs'] for x in r.get('leaves', [])]
        row['leaves'] = r.get('leaves')
        row.pop('tree_with_points', None)
        row.pop('audit', None)
        print('%s: %s gap %s, leaves %d, lhs %s' % (row['family'], r['status'], r.get('gap'), r.get('n_leaves'), row['lhs']))
        for x in r.get('leaves', []):
            if x['status'] != 'CERTIFIED':
                print('   open leaf box %s origin %s lhs %s' % (x['box'], x['origins'], x['lhs']))
        out['families'].append(json.loads(json.dumps(row, default=str)))
    if a.output:
        p = Path(a.output)
        if p.exists():
            raise SystemExit('refusing to overwrite %s' % p)
        p.write_text(json.dumps(out, indent=1, default=str) + '\n')
        print('wrote', p)


if __name__ == '__main__':
    main()
