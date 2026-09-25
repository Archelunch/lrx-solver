"""Staircase tree constructor for bound-contract-3 (trusted control, hand-written, run in-process).

Mimics the research group's m=8 tree for (8..1){0,4} (theorem section 4; reverse
certificates file): short high-slope words on a finite box near the unit corner, and
refined-origin words (block j refined to o_j zero atoms) further out. For one axis j the
constructor walks l = 1, 2, ...: at lower corner l it uses origin o_j = min(l, largest
origin an exact table covers), tries the unbounded leaf [l, inf) and otherwise the widest
finite leaf [l, h], h <= 12, that passes criterion (8); the leaves form a right comb of
splits u_j <= h. Axes are tried in order; the first certified tree wins, else the tree
with the smallest gap.

Words per leaf: exact-table-guided search on the refined base (every word of length
<= d + SLACK_FREE, and words of length <= d + SLACK_LOW whose outer slope beta_j stays
<= m-2 - 2, with Lemma 1 costs tracked incrementally), plus the cyclic-sweep pool of
bound_control_sweep. Tables are the repository's exact BFS tables (datasets/generated,
datasets/generated/outer-layer-260925, datasets/generated/sort-m9-260925,
runs/lifting-check-260922-234448/tables), hash-checked on load. They are data used only to
find words; every word is replayed by bound3_evaluator. Without a table for (m, r) only
sweep words are used. This is a diagnostic control, not an m-uniform program.
"""
from pathlib import Path

from integrations import lrx_m as C
from integrations.bound3_evaluator import leaf_lp
from integrations.bound_control_sweep import pool

ROOT = Path(__file__).resolve().parent.parent
TABLE_DIRS = ('datasets/generated', 'datasets/generated/outer-layer-260925', 'datasets/generated/sort-m9-260925',
              'runs/lifting-check-260922-234448/tables')
SLACK_FREE, SLACK_LOW, NODE_LIMIT, MAX_H, MAX_LEAVES = 1, 2, 4_000_000, 12, 7
_TABLES = {}


def table(m, r):
    if (m, r) not in _TABLES:
        from src.lrx.table_bfs import DistanceTable
        _TABLES[(m, r)] = next((DistanceTable(ROOT / d, m, r) for d in TABLE_DIRS
                                if (ROOT / d / ('dist_m%d_r%d.bin' % (m, r))).exists()), None)
    return _TABLES[(m, r)]


def search(tb, v, picks, maxlen, caps, limit=NODE_LIMIT):
    """Words of length <= maxlen sorting v (pruned by the exact table), no zero-zero swap, no LR/RL/XX,
    whose Lemma 1 slopes stay <= caps (closed segments bound beta from below). -> {word: (B, beta)}."""
    rk, dist, n, k = tb.ranker, tb.dist, len(v), len(picks)
    m = n - sum(1 for x in v if x == 0)
    a, zi = [], 0
    for x in v:
        a.append(x if x else C.ZID + zi)
        zi += not x
    pb = {C.ZID + p: j for j, p in enumerate(picks)}
    cell = [0] * (m + 1)
    for i, x in enumerate(a):
        if x < C.ZID:
            cell[x] = i
    out, word, nodes = {}, [], [0]

    def rec(c, d, cz, cb, q, rot, left, last):
        nodes[0] += 1
        dd = dist[rk.rank(tuple((cell[x] - c) % n for x in range(1, m + 1)))]
        if dd > left or nodes[0] > limit:
            return
        if dd == 0:
            beta = [cb[j] + abs(cz[j]) for j in range(k)]
            if all(b <= cp for b, cp in zip(beta, caps)):
                out[''.join(word)] = (q + rot + abs(d), beta)
            return
        if last != 'R':
            j = pb.get(a[c])
            word.append('L')
            rec((c + 1) % n, d + 1, cz if j is None else [x + (i == j) for i, x in enumerate(cz)], cb, q, rot,
                left - 1, 'L')
            word.pop()
        if last != 'L':
            c2 = (c - 1) % n
            j = pb.get(a[c2])
            word.append('R')
            rec(c2, d - 1, cz if j is None else [x - (i == j) for i, x in enumerate(cz)], cb, q, rot, left - 1, 'R')
            word.pop()
        c2 = (c + 1) % n
        x, y = a[c], a[c2]
        if last != 'X' and (x < C.ZID or y < C.ZID):
            jx, jy = pb.get(x), pb.get(y)
            cz2 = [z + (i == jx) for i, z in enumerate(cz)]
            cb2 = [cb[i] + abs(cz2[i]) + 2 * (i == jx or i == jy) for i in range(k)]
            if all(b <= cp for b, cp in zip(cb2, caps)):
                a[c], a[c2] = y, x
                for t, p in ((x, c2), (y, c)):
                    if t < C.ZID:
                        cell[t] = p
                word.append('X')
                rec(c, 0, [-(i == jy) for i in range(k)], cb2, q + 1, rot + abs(d), left - 1, 'X')
                word.pop()
                a[c], a[c2] = x, y
                for t, p in ((x, c), (y, c2)):
                    if t < C.ZID:
                        cell[t] = p

    rec(0, 0, [0] * k, [0] * k, 0, 0, maxlen, None)
    return out


def columns(fam, origins, axis):
    """Pareto frontier [(word, B, beta)] of words for the refined base, picks = first atom of each block."""
    m, k = fam['m'], fam['k']
    v = C.refine(fam['unit_base'], origins)
    picks = [sum(origins[:j]) for j in range(k)]
    words = {}
    tb = table(m, len(v) - m)
    if tb is not None:
        d = tb.distance(v)
        words.update(search(tb, v, picks, d + SLACK_FREE, [10 ** 6] * k))
        caps = [10 ** 6] * k
        caps[axis] = m - 4
        words.update(search(tb, v, picks, d + SLACK_LOW, caps))
    for w in pool(v):
        try:
            p = C.Profile(v, w, picks)
        except C.CheckError:
            continue
        words.setdefault(w, (p.base, list(p.beta)))
    best = {}
    for w in sorted(words, key=lambda w: (len(w), w)):
        B, beta = words[w]
        best.setdefault((B,) + tuple(beta), w)
    keys = sorted(best)
    keep = [x for x in keys if not any(y != x and all(a <= b for a, b in zip(y, x)) for y in keys)]
    return [(best[x], x[0], list(x[1:])) for x in keep]


def max_origin(m, k):
    """Largest o such that an exact table covers origins (o, 1, ..., 1)."""
    o = 1
    while table(m, k + o) is not None:
        o += 1
    return o


def try_leaf(fam, axis, l, h, omax, cache):
    """-> (leaf node, leaf_lp result) for box [l, h] on `axis` ([1, inf) elsewhere)."""
    k, m = fam['k'], fam['m']
    o = min(l, omax)
    origins = [1] * k
    origins[axis] = o
    if o not in cache:
        cache[o] = columns(fam, origins, axis)
    cols = cache[o]
    box = [(1, None)] * k
    box[axis] = (l, h)
    lo = [a for a, _ in box]
    costs = [(B + sum(b * (x - y) for b, x, y in zip(beta, lo, origins)), beta) for _, B, beta in cols]
    res = leaf_lp(costs, box, m - 2, C.budget(m, sum(lo)))
    order = sorted(range(len(cols)), key=lambda i: -res['weights'][i])
    words = [cols[i][0] for i in order if res['weights'][i]][:32]
    return {'words': words, 'origins': origins}, res


def staircase(fam, axis):
    """-> (tree node, gap as Fraction, certified)."""
    omax = max_origin(fam['m'], fam['k'])
    cache, leaves, l = {}, [], 1
    while True:
        node, res = try_leaf(fam, axis, l, None, omax, cache)
        if res['status'] == 'CERTIFIED' or len(leaves) + 1 >= MAX_LEAVES or l > MAX_H:
            leaves.append((node, None, res))
            break
        h = next((h for h in range(MAX_H, l - 1, -1)
                  if try_leaf(fam, axis, l, h, omax, cache)[1]['status'] == 'CERTIFIED'), None)
        if h is None:  # even [l, l] fails: report the unbounded leaf (its gap bounds the family gap)
            leaves.append((node, None, res))
            break
        leaves.append((try_leaf(fam, axis, l, h, omax, cache)[0], h, None))
        l = h + 1
    tree = leaves[-1][0]
    for node, h, _ in reversed(leaves[:-1]):
        tree = {'j': axis, 't': h, 'le': node, 'ge': tree}
    last = leaves[-1][2]
    return tree, last['gap'], last['status'] == 'CERTIFIED'


def certify(family):
    best = None
    for axis in range(family['k']):
        tree, gap, ok = staircase(family, axis)
        if ok:
            return {'tree': tree, 'note': 'staircase on axis %d' % axis}
        if best is None or gap < best[1]:
            best = (tree, gap, axis)
    return {'tree': best[0], 'note': 'no certified staircase; best axis %d' % best[2]}
