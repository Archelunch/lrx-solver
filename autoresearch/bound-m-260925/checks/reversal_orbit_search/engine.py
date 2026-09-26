from gen import core_word, C, make_family, Fr, time
from integrations.bound3_evaluator import leaf_lp, score_output
from integrations.bound3_audit import audit_claim
from integrations.lift_evaluator import mixture_lp


def near_zero_cells(state, rad=1):
    n = len(state)
    z = [i for i, x in enumerate(state) if x == 0]
    return sorted({(i + d) % n for i in z for d in range(-rad, rad + 1)})


def pool(state, seeds1=None, seeds2=None, cuts=None, fins='RL', one_core=True):
    n = len(state)
    m = sum(1 for x in state if x)
    cuts = range(m + 1) if cuts is None else cuts
    seeds1 = near_zero_cells(state) if seeds1 is None else seeds1
    seeds2 = range(n) if seeds2 is None else seeds2
    out = {}
    for t in cuts:
        for s1 in seeds1:
            for d1 in 'rl':
                if one_core:
                    for fin in fins:
                        w = core_word(state, t, [(s1, None, d1)], fin)
                        if w and w not in out:
                            out[w] = [t, [s1, None, d1], fin]
                for k1 in range(1, n - 1):
                    for s2 in seeds2:
                        for d2 in 'rl':
                            for fin in fins:
                                w = core_word(state, t, [(s1, k1, d1), (s2, None, d2)], fin)
                                if w and w not in out:
                                    out[w] = [t, [s1, k1, d1], [s2, None, d2], fin]
    return out


def front(state, words, picks=None):
    """Pareto front of (base, beta) over words that pass Profile. -> [(base, beta, word)]"""
    best = {}
    for w in words:
        try:
            p = C.Profile(state, w, picks)
        except C.CheckError:
            continue
        key = tuple(p.beta)
        if key not in best or p.base < best[key][0]:
            best[key] = (p.base, w)
    items = sorted((b, bt, w) for bt, (b, w) in best.items())
    fr = []
    for b, bt, w in items:
        if not any(b2 <= b and all(x <= y for x, y in zip(bt2, bt)) for b2, bt2, _ in fr):
            fr.append((b, bt, w))
    return fr


def leaf_eval(fr, box, o, m):
    """fr: front on the base refined at origin o. -> (status, value, gap, support indices, weights)."""
    k = len(box)
    l = [a for a, _ in box]
    costs = [(b + sum(x * (li - oi) for x, li, oi in zip(bt, l, o)), list(bt)) for b, bt, _ in fr]
    res = leaf_lp(costs, box, m - 2, C.budget(m, sum(l)))
    return res


def leaf_node(fr, res, o, k):
    sup = [i for i, x in enumerate(res['weights']) if x]
    node = {'words': [fr[i][2] for i in sup]}
    if list(o) != [1] * k:
        node['origins'] = list(o)
    return node


def search(fronts, box, m, depth, maxdepth, budget, tmax=12):
    """fronts: dict origin tuple -> front. Returns node or None. Greedy: leaf if any origin passes, else best split."""
    k = len(box)
    best = None
    for o, fr in fronts.items():
        if any(o[j] > box[j][0] for j in range(k)) or not fr:
            continue
        res = leaf_eval(fr, box, o, m)
        if res['status'] == 'CERTIFIED':
            return leaf_node(fr, res, o, k)
    if depth >= maxdepth or budget[0] <= 0:
        return None
    budget[0] -= 1
    for j in range(k):
        l, h = box[j]
        for t in range(l, min(tmax, (h - 1) if h is not None else tmax) + 1):
            left = list(box); left[j] = (l, t)
            right = list(box); right[j] = (t + 1, h)
            a = search(fronts, left, m, depth + 1, maxdepth, budget, tmax)
            if a is None:
                continue
            b = search(fronts, right, m, depth + 1, maxdepth, budget, tmax)
            if b is None:
                continue
            return {'j': j, 't': t, 'le': a, 'ge': b}
    return None


def certify(fam, fronts, maxdepth=3, budget=400):
    k, m = fam['k'], fam['m']
    node = search(fronts, [(1, None)] * k, m, 0, maxdepth, [budget])
    if node is None:
        return None
    return {'words': node['words']} if 'words' in node and 'origins' not in node else {'tree': node}


def check(fam, out):
    r = score_output(fam, out)
    row = {'status': r['status'], 'gap': r['gap'], 'n_leaves': r.get('n_leaves')}
    if r['status'] == 'CERTIFIED':
        row['audit'] = list(audit_claim(fam, r['output'], r['certificate']))
        row['certificate'] = r['certificate']
    return row, r


def refined_fronts(fam, origins, seeds1='all', picks_mode=('first', 'last')):
    """origin tuple -> front (with picks stored). Words generated on the refined base."""
    out = {}
    k = fam['k']
    for o in origins:
        st = C.refine(fam['unit_base'], list(o))
        n = len(st)
        p = pool(st, seeds1=range(n) if seeds1 == 'all' else None)
        best = []
        for pm in picks_mode:
            pk = [0 if pm == 'first' else oj - 1 for oj in o]
            gp = [sum(o[:j]) + pk[j] for j in range(k)]
            fr = front(st, p, gp)
            best.append((pk, fr))
            if all(oj == 1 for oj in o):
                break
        out[tuple(o)] = best
    return out


def search2(fronts, box, m, depth, maxdepth, budget, tmax=12):
    """fronts: origin -> [(picks, front)]."""
    k = len(box)
    for o, lst in fronts.items():
        if any(o[j] > box[j][0] for j in range(k)):
            continue
        for pk, fr in lst:
            if not fr:
                continue
            res = leaf_eval(fr, box, o, m)
            if res['status'] == 'CERTIFIED':
                node = leaf_node(fr, res, o, k)
                if any(pk):
                    node['picks'] = pk
                    node.setdefault('origins', list(o))
                return node
    if depth >= maxdepth or budget[0] <= 0:
        return None
    budget[0] -= 1
    for j in range(k):
        l, h = box[j]
        for t in range(l, min(tmax, (h - 1) if h is not None else tmax) + 1):
            left = list(box); left[j] = (l, t)
            right = list(box); right[j] = (t + 1, h)
            a = search2(fronts, left, m, depth + 1, maxdepth, budget, tmax)
            if a is None:
                continue
            b = search2(fronts, right, m, depth + 1, maxdepth, budget, tmax)
            if b is None:
                continue
            return {'j': j, 't': t, 'le': a, 'ge': b}
    return None


def certify2(fam, fronts, maxdepth=3, budget=2000):
    k, m = fam['k'], fam['m']
    node = search2(fronts, [(1, None)] * k, m, 0, maxdepth, [budget])
    if node is None:
        return None
    return {'words': node['words']} if 'words' in node and 'origins' not in node and 'picks' not in node \
        else {'tree': node}


class TreeSearch:
    def __init__(self, fam, fronts, maxdepth=3, tmax=6):
        self.fam, self.fronts, self.maxdepth, self.tmax = fam, fronts, maxdepth, tmax
        self.leaf_memo, self.memo = {}, {}
        self.m, self.k = fam['m'], fam['k']

    def leaf(self, box):
        key = tuple(box)
        if key in self.leaf_memo:
            return self.leaf_memo[key]
        node = None
        for o, lst in self.fronts.items():
            if any(o[j] > box[j][0] for j in range(self.k)):
                continue
            for pk, fr in lst:
                if not fr:
                    continue
                res = leaf_eval(fr, box, o, self.m)
                if res['status'] == 'CERTIFIED':
                    node = leaf_node(fr, res, o, self.k)
                    if any(pk):
                        node['picks'] = pk
                        node.setdefault('origins', list(o))
                    break
            if node:
                break
        self.leaf_memo[key] = node
        return node

    def run(self, box=None, depth=0):
        box = box or [(1, None)] * self.k
        key = (tuple(box), depth)
        if key in self.memo:
            return self.memo[key]
        node = self.leaf(box)
        if node is None and depth < self.maxdepth:
            for j in range(self.k):
                l, h = box[j]
                hi = min(self.tmax, h - 1) if h is not None else self.tmax
                for t in range(l, hi + 1):
                    left = list(box); left[j] = (l, t)
                    right = list(box); right[j] = (t + 1, h)
                    a = self.run(left, depth + 1)
                    if a is None:
                        continue
                    b = self.run(right, depth + 1)
                    if b is None:
                        continue
                    node = {'j': j, 't': t, 'le': a, 'ge': b}
                    break
                if node:
                    break
        self.memo[key] = node
        return node


def to_output(node):
    if node is None:
        return None
    if 'words' in node and 'origins' not in node and 'picks' not in node:
        return {'words': node['words']}
    return {'tree': node}
