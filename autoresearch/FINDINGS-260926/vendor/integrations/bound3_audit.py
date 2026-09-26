"""Independent audit of CERTIFIED bound-eval-3 (tree) families from the evaluator's result file.

Deliberately does not import bound3_evaluator.py, bound3_task.py, bound_evaluator.py,
lrx_m.py or lift_evaluator.py. It loads the independent m=8 checker
(autoresearch/verify-m8-260924/checker/lrxm8.py) as a fresh module with M = m
(lift_audit.checker), rebuilds the unit base from (labels, mask), re-parses the raw
candidate output (stored in the row as "output") into the checker's tree form, walks it with
the checker's tree_leaves from the root box [1, inf)^k (complete coverage), and for each leaf
matches the claimed box, origins, picks and support words. Every claimed word is replayed on
the refined base (checker refine + Profile with picks), with literal lifted execution at
z = 0, e_j, 2e_j, e_j+e_{j+1}, (1..1) and at the box points u = l, l+e_j, l+2e_j. The claimed
weights are checked against criterion (8) twice: directly at m, and with the checker's own
leaf_criterion (hard-wired to m = 8) after the exact affine change
    beta' = beta - (m-8),  B' = B - (m(m+1)/2 - (m-2) - 30) - (m-8) sum(o),
which maps criterion (8) at m onto criterion (8) at 8 term by term. A witness suffices for a
claim; the audit does not search for certificates the scorer missed.

    python -m integrations.bound3_audit --families F --results R [R ...]
"""
import argparse
from fractions import Fraction as Fr
import json
from pathlib import Path

from integrations.lift_audit import checker


def budget(m, r):
    return m * (m + 1) // 2 + (r - 1) * (m - 2)


def _tree(node, k, depth=0):
    """Raw output node -> checker tree ({'kind': 'split'|'leaf', ...}); limits as bound-contract-3."""
    if 'le' in node or 'ge' in node:
        if depth >= 6 or type(node['j']) is not int or not 0 <= node['j'] < k \
                or type(node['t']) is not int or not 1 <= node['t'] <= 12:
            raise ValueError('bad split')
        return {'kind': 'split', 'axis': node['j'], 'cut': node['t'],
                'left': _tree(node['le'], k, depth + 1), 'right': _tree(node['ge'], k, depth + 1)}
    words = node['words']
    if not 1 <= len(words) <= 32 or any(type(w) is not str or len(w) > 4000 or set(w) - set('LRX') for w in words):
        raise ValueError('leaf violates word caps')
    return {'kind': 'leaf', 'words': words, 'origins': node.get('origins', [1] * k),
            'picks': node.get('picks', [0] * k)}


def criterion8(rows, box, m):
    """rows: (weight, B, beta, origin). -> (ok, excess). Direct at m."""
    k, s = len(box), m - 2
    Cl = sum(w * (b + sum(bt[j] * (box[j][0] - o[j]) for j in range(k))) for w, b, bt, o in rows)
    g = [sum(w * bt[j] for w, _, bt, _ in rows) for j in range(k)]
    T = budget(m, sum(l for l, _ in box))
    ex = Cl - T + sum(max(Fr(0), g[j] - s) * (box[j][1] - box[j][0]) for j in range(k) if box[j][1] is not None)
    return ex < 1 and all(g[j] <= s for j in range(k) if box[j][1] is None), ex


def audit_claim(family, output, claim):
    """-> (agree, reason)."""
    try:
        labels, mask = list(family['labels']), family['mask']
        m = len(labels)
        C = checker(m)
        base = C.base_vector(labels, mask)
        k = bin(mask).count('1')
        if base != family['unit_base'] or k != family['k'] or family['budget_unit'] != budget(m, k) \
                or family['slope_bound'] != m - 2:
            return False, 'family fields disagree with independent reconstruction'
        raw = output['tree'] if 'tree' in output else {'words': output['words']}
        leaves = list(C.tree_leaves(_tree(raw, k), [(1, None)] * k))
        if len(leaves) > 32 or len(leaves) != len(claim['leaves']):
            return False, 'claimed leaves do not match the raw tree'
        zs = C.z_samples(k, pairs=k - 1)
        zs.append(tuple([1] * k))
        for (leaf, box), cl in zip(leaves, claim['leaves']):
            if [[a, 'inf' if b is None else b] for a, b in box] != cl['box']:
                return False, 'claimed box %s differs from the raw tree box %s' % (cl['box'], box)
            o, p = leaf['origins'], leaf['picks']
            if cl['origins'] != o or cl['picks'] != p or any(w not in leaf['words'] for w in cl['words']):
                return False, 'claimed leaf differs from the raw output leaf'
            if any(type(x) is not int or not 1 <= x <= box[j][0] for j, x in enumerate(o)) or \
                    any(type(x) is not int or not 0 <= x < o[j] for j, x in enumerate(p)):
                return False, 'origins exceed the lower corner or picks outside their block'
            ws = [Fr(x) for x in cl['weights']]
            if len(ws) != len(cl['words']) or any(x < 0 for x in ws) or sum(ws) != 1:
                return False, 'claimed weights are not a probability vector'
            state = C.refine(base, o)
            picks = [sum(o[:j]) + p[j] for j in range(k)]
            zbox = [tuple(a - x for (a, _), x in zip(box, o))]
            for j in range(k):
                for d in (1, 2):
                    zbox.append(tuple(zbox[0][i] + d * (i == j) for i in range(k)))
            rows = []
            for w, x in zip(cl['words'], ws):
                prof = C.Profile(state, w, picks)  # raises unless it sorts without a zero-zero swap
                C.literal_lift_check(prof, zs + zbox)
                rows.append((x, prof.base, prof.beta, o))
            ok, ex = criterion8(rows, box, m)
            shift = m * (m + 1) // 2 - (m - 2) - 30
            moved = [(x, b - shift - (m - 8) * sum(oo), [t - (m - 8) for t in bt], oo) for x, b, bt, oo in rows]
            ok8, _, _, ex8 = C.leaf_criterion(moved, box)
            if (ok, ex) != (ok8, ex8):
                return False, 'direct criterion (8) and the checker leaf_criterion disagree'
            if not ok:
                return False, 'leaf %s fails criterion (8): excess %s' % (cl['box'], ex)
        return True, 'ok'
    except Exception as exc:  # checker errors are disagreements, never crashes
        return False, '%s: %s' % (type(exc).__name__, exc)


def audit_result(families, result):
    by_id = {f['id']: f for f in families}
    rows = [r for r in result['results'] if r['status'] == 'CERTIFIED']
    bad = []
    for r in rows:
        ok, why = audit_claim(by_id[r['id']], r['output'], r['certificate'])
        if not ok:
            bad.append({'id': r['id'], 'reason': why})
    return {'certified_claims': len(rows), 'agree': len(rows) - len(bad), 'disagreements': bad}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--families', required=True, nargs='+')
    ap.add_argument('--results', required=True, nargs='+')
    ap.add_argument('--output')
    a = ap.parse_args(argv)
    fams = [f for p in a.families for f in json.loads(Path(p).read_text())['families']]
    report = {p: audit_result(fams, json.loads(Path(p).read_text())) for p in a.results}
    if a.output:
        out = Path(a.output)
        if out.exists():
            raise SystemExit('refusing to overwrite existing %s' % out)
        out.write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({p: {x: v[x] for x in ('certified_claims', 'agree')} | {'disagreements': len(v['disagreements'])}
                      for p, v in report.items()}))


if __name__ == '__main__':
    main()
