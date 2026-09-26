"""Refined-origin tree search over carry pools (search side only)."""
import sys, json, time
from common import *
from pools import pool
from integrations.bound3_evaluator import score_output
from integrations.bound3_audit import audit_claim
from integrations.bound_task import make_family


def fronts(m, g, origins, gens=('F2', 'D1', 'F3', 'S'), **kw):
    """-> {o: [(pk_within, [(B, beta, word, params)])]}"""
    out = {}
    for o in origins:
        P = pool(m, g, o, gens, **kw)
        out[o] = [((a, b - o[0]), [(k[0], k[1:], v[0], v[1]) for k, v in fr.items()]) for (a, b), fr in P.items()]
    return out


class TreeSearch:
    def __init__(self, m, F, maxdepth=3, tmax=4):
        self.m, self.F, self.maxdepth, self.tmax = m, F, maxdepth, tmax
        self.leaf_memo, self.memo = {}, {}

    def leaf(self, box):
        key = tuple(box)
        if key in self.leaf_memo:
            return self.leaf_memo[key]
        node = None
        l = [a for a, _ in box]
        for o in sorted(self.F, key=lambda o: -sum(o)):
            if any(o[j] > l[j] for j in range(2)):
                continue
            for pk, fr in self.F[o]:
                if not fr: continue
                costs = [(b + sum(x * (li - oi) for x, li, oi in zip(bt, l, o)), list(bt)) for b, bt, _, _ in fr]
                res = leaf_lp(costs, box, self.m - 2, C.budget(self.m, sum(l)))
                if res['status'] == 'CERTIFIED':
                    sup = [i for i, x in enumerate(res['weights']) if x]
                    node = {'words': [fr[i][2] for i in sup], 'origins': list(o), 'picks': list(pk),
                            '_params': [fr[i][3] for i in sup], '_lhs': str(res['value'])}
                    break
            if node: break
        self.leaf_memo[key] = node
        return node

    def run(self, box=None, depth=0):
        box = box or [(1, None), (1, None)]
        key = (tuple(box), depth)
        if key in self.memo: return self.memo[key]
        node = self.leaf(box)
        if node is None and depth < self.maxdepth:
            for j in range(2):
                l, h = box[j]
                hi = min(self.tmax, h - 1) if h is not None else self.tmax
                for t in range(l, hi + 1):
                    left = list(box); left[j] = (l, t)
                    right = list(box); right[j] = (t + 1, h)
                    a = self.run(left, depth + 1)
                    if a is None: continue
                    b = self.run(right, depth + 1)
                    if b is None: continue
                    node = {'j': j, 't': t, 'le': a, 'ge': b}
                    break
                if node: break
        self.memo[key] = node
        return node


def strip(node):
    if node is None: return None
    if 'words' in node:
        return {k: v for k, v in node.items() if not k.startswith('_')}
    return {'j': node['j'], 't': node['t'], 'le': strip(node['le']), 'ge': strip(node['ge'])}


def check(m, g, node):
    fam = make_family(list(range(m, 0, -1)), 1 | 1 << g)
    out = {'tree': strip(node)}
    if 'words' in node and node['origins'] == [1, 1] and node['picks'] == [0, 0]:
        out = {'words': node['words']}
    r = score_output(fam, out)
    au = audit_claim(fam, r['output'], r['certificate']) if r['status'] == 'CERTIFIED' else None
    return r, au, out


if __name__ == '__main__':
    m = int(sys.argv[1]); gs = [int(x) for x in sys.argv[2].split(',')]
    origins = [tuple(int(y) for y in x.split('.')) for x in sys.argv[3].split(',')]
    maxdepth = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    tmax = int(sys.argv[5]) if len(sys.argv) > 5 else 4
    for g in gs:
        t0 = time.process_time()
        F = fronts(m, g, origins)
        t1 = time.process_time()
        node = TreeSearch(m, F, maxdepth=maxdepth, tmax=tmax).run()
        if node is None:
            print(m, g, 'NOT_FOUND', 'pools %.0fs tree %.0fs' % (t1 - t0, time.process_time() - t1), flush=True)
            continue
        r, au, out = check(m, g, node)
        print(m, g, r['status'], 'leaves', r['n_leaves'], 'audit', au, [(x['box'], x['origins'], x['lhs']) for x in r['leaves']],
              'pools %.0fs tree %.0fs' % (t1 - t0, time.process_time() - t1), flush=True)
