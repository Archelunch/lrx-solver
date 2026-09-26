"""Exact-table sanity checks of the general-m Lemma 1 pricing and criterion (7).

Read-only.  Uses the complete one-byte BFS distance tables (distance from the
root; the Cayley graph is undirected) under datasets/generated/ and the
repository's parametric reading of Lemma 1 in integrations/lrx_m.py.

Part 0  the manuscript's worked example (section 8, m = 8) priced by lrx_m.
Part A  random (family, word) pairs at m = 9, 10: for every block-length vector
        within table range, check  d(v(z)) <= F_W(z) <= B + sum beta_j z_j,
        the lifted word literally sorts v(z) and has length F_W(z).
        Includes refined bases (o_j = 2 zeros in a block, one picked atom, (6)).
Part B  families certified at the root at m = 9 (bound-campaign finalist rows):
        recompute costs, re-check (7), then check d(v(u)) <= T_9(n) and
        min_i F_i(u) <= T_9(n) for every u >= 1 with sum u <= 6.

Usage:  python autoresearch/checks-lemma1/lemma1_tables_check.py [--seed 260926]
"""
import argparse
import collections
import glob
import itertools
import json
import mmap
import os
import random
import sys
from fractions import Fraction as Fr

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from integrations import lrx_m as C  # noqa: E402
from src.lrx.table_bfs import Ranker  # noqa: E402

TABLE_DIRS = ['datasets/generated', 'datasets/generated/outer-layer-260925',
              'datasets/generated/sort-m9-260925', 'datasets/generated/m10-r2-260926']
RMAX = {9: 6, 10: 3}


class Tables:
    def __init__(self):
        self.maps, self.rankers = {}, {}

    def _open(self, m, r):
        for d in TABLE_DIRS:
            p = os.path.join(ROOT, d, 'dist_m%d_r%d.bin' % (m, r))
            meta = p[:-4] + '.json'
            if os.path.exists(p) and os.path.exists(meta):
                info = json.load(open(meta))
                if not info.get('complete') or info['states'] != os.path.getsize(p):
                    raise SystemExit('table %s incomplete' % p)
                f = open(p, 'rb')
                self.maps[m, r] = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                self.rankers[m, r] = Ranker(m, r)
                return
        raise KeyError('no table for (%d,%d)' % (m, r))

    def dist(self, v):
        v = tuple(0 if C.is_zero(x) else x for x in v)
        m = sum(1 for x in v if x)
        r = len(v) - m
        if (m, r) not in self.maps:
            self._open(m, r)
        rk = self.rankers[m, r]
        d = self.maps[m, r][rk.rank(rk.positions(v))]
        if d == 255:
            raise SystemExit('unreached state in complete table')
        return d


def step(v, ch):
    return tuple(C.run_naive(v, ch))


def geodesic(tab, v, rng):
    """A shortest sorting word, ties broken at random (never swaps two zeros)."""
    word = []
    d = tab.dist(v)
    while d:
        opts = [ch for ch in 'LRX' if tab.dist(step(v, ch)) == d - 1]
        ch = rng.choice(opts)
        word.append(ch)
        v = step(v, ch)
        d -= 1
    return ''.join(word)


def z_vectors(k, budget):
    """All z in N^k with sum z <= budget."""
    for s in range(budget + 1):
        for c in itertools.combinations_with_replacement(range(k), s):
            z = [0] * k
            for j in c:
                z[j] += 1
            yield tuple(z)


def random_family(m, k, rng):
    labels = list(range(1, m + 1))
    rng.shuffle(labels)
    gaps = sorted(rng.sample(range(m + 1), k))
    mask = sum(1 << g for g in gaps)
    return labels, mask


def check_pair(tab, state, word, picks, extra_budget, stats, tag):
    """Lemma 1 / (4) / (5) / (6) on one priced word; returns number of z tested."""
    prof = C.Profile(state, word, picks)
    tested = 0
    for z in z_vectors(prof.k, extra_budget):
        v = C.stretch(state, prof.picks, z)
        d = tab.dist(v)
        F = prof.exact_len(z)
        A = prof.affine(z)
        w = prof.lift(z)
        if not C.is_root(C.run(v, w)) or len(w) != F:
            stats['lift_fail'].append((tag, state, word, z))
        if d > F:
            stats['violation_F'].append((tag, state, word, z, d, F))
        if F > A:
            stats['violation_affine_vs_F'].append((tag, state, word, z, F, A))
        if d > A:
            stats['violation_affine'].append((tag, state, word, z, d, A))
        if any(z):
            stats['slack_affine'][A - d] += 1
            stats['slack_F'][F - d] += 1
            stats['affine_minus_F'][A - F] += 1
        tested += 1
    stats['same_sign'][prof.same_sign] += 1
    return tested


def part0():
    v = [0, 5, 0, 8, 7, 0, 6, 4, 3, 2, 1, 0]
    W1 = 'XLLXLXRRXRRXLXLLXRXRXRRRXRXRXRXLXLXLXLXRRXRXLXRR'
    W2 = 'LXLLLXLLXRXLLXRXRXRRXRXLLXLXLLXLXRXRXRXRXRXLXLXLLXLXLXRXRXRXRXRXRX'
    p1, p2 = C.Profile(v, W1), C.Profile(v, W2)
    got = [(p1.base, p1.beta), (p2.base, p2.beta)]
    want = [(48, [9, 6, 0, 8]), (66, [1, 2, 8, 0])]
    ok, B, beta = C.mixture_criterion(got, [Fr(5, 8), Fr(3, 8)], 4, m=8)
    print('Part 0  manuscript section 8 example (m=8):')
    print('  W1 base %d slopes %s, W2 base %d slopes %s ; manuscript: 48 (9,6,0,8), 66 (1,2,8,0) -> %s'
          % (p1.base, p1.beta, p2.base, p2.beta, 'MATCH' if got == want else 'MISMATCH'))
    print('  weights 5/8,3/8: Bbar = %s (manuscript 219/4), betabar = %s, criterion (7) at m=8: %s'
          % (B, [str(x) for x in beta], ok))
    return got == want and ok and B == Fr(219, 4)


def part_a(tab, rng):
    stats = {'lift_fail': [], 'violation_F': [], 'violation_affine': [], 'violation_affine_vs_F': [],
             'slack_affine': collections.Counter(), 'slack_F': collections.Counter(),
             'affine_minus_F': collections.Counter(), 'same_sign': collections.Counter()}
    pairs = collections.Counter()
    zs = collections.Counter()
    plan = ([('geo', 9, k) for k in (1, 2, 3, 4, 5) for _ in range(40)]
            + [('pre', 9, k) for k in (1, 2, 3, 4, 5) for _ in range(12)]
            + [('geo', 10, 2) for _ in range(40)]
            + [('ref', 9, k) for k in (1, 2, 3) for _ in range(20)]
            + [('ref', 10, 1) for _ in range(20)])
    for kind, m, k in plan:
        labels, mask = random_family(m, k, rng)
        base = C.base_vector(labels, mask)
        origin = [1] * k
        if kind == 'ref':  # refine one block (two if room) to o_j = 2 zero atoms, keep >= 1 extra zero
            idx = rng.sample(range(k), 2 if k >= 2 and RMAX[m] - k >= 3 and rng.random() < 0.5 else 1)
            for j in idx:
                origin[j] = 2
        state = C.refine(base, origin)
        _, _, blocks = C.parse_state(state)
        picks = [rng.choice(b) for b in blocks]
        if kind == 'pre':
            while True:
                ch = rng.choice('LRX')
                if ch == 'X' and C.is_zero(state[0]) and C.is_zero(state[1]):
                    continue
                break
            word = ch + geodesic(tab, step(tuple(state), ch), rng)
        else:
            word = geodesic(tab, tuple(state), rng)
        extra = RMAX[m] - sum(origin)
        zs[kind, m] += check_pair(tab, state, word, picks, extra, stats, (kind, m, k))
        pairs[kind, m] += 1
    return stats, pairs, zs


def load_certified(m):
    rows = {}
    pats = ['autoresearch/bound-m-260925/finalists/*-arms/*.json',
            'autoresearch/bound-m-c2-260925/finalists/*-arms/*.json',
            'autoresearch/bound-m-c3-260926/finalists/*-arms/*.json']
    for pat in pats:
        for f in sorted(glob.glob(os.path.join(ROOT, pat))):
            for x in json.load(open(f))['result'].get('rows', []):
                if x.get('status') == 'CERTIFIED' and x['m'] == m and x['id'] not in rows:
                    rows[x['id']] = x
    return rows


def parse_id(fid):
    _, mask, lab = fid.split('-')
    s = lab[len('labels'):]
    labels = [int(t) for t in (s.split('.') if '.' in s else s)]
    return labels, int(mask[len('mask'):])


def part_b(tab):
    rows = load_certified(9)
    fams = sorted((x for x in rows.values() if x['k'] <= RMAX[9]), key=lambda x: (x['k'], x['id']))
    res = {'families': 0, 'crit_fail': [], 'viol_d': [], 'viol_minF': [], 'lift_fail': [],
           'z_tested': 0, 'slack_T_d': collections.Counter(), 'slack_T_minF': collections.Counter(),
           'per_k': collections.Counter(), 'Bbar_gap': collections.Counter()}
    for x in fams:
        labels, mask = parse_id(x['id'])
        k = x['k']
        base = C.base_vector(labels, mask)
        cert = x['certificate']
        profs = [C.Profile(base, w) for w in cert['words']]
        costs = [(p.base, p.beta) for p in profs]
        ok, B, beta = C.mixture_criterion(costs, [Fr(w) for w in cert['weights']], k, m=9)
        if not ok:
            res['crit_fail'].append(x['id'])
            continue
        res['families'] += 1
        res['per_k'][k] += 1
        res['Bbar_gap'][str(C.budget(9, k) + 1 - B)] += 1
        for z in z_vectors(k, RMAX[9] - k):
            T = C.budget(9, k + sum(z))
            v = C.stretch(base, profs[0].picks, z)
            d = tab.dist(v)
            Fs = [p.exact_len(z) for p in profs]
            i = min(range(len(Fs)), key=Fs.__getitem__)
            w = profs[i].lift(z)
            if not C.is_root(C.run(v, w)) or len(w) != Fs[i]:
                res['lift_fail'].append((x['id'], z))
            if d > T:
                res['viol_d'].append((x['id'], z, d, T))
            if Fs[i] > T:
                res['viol_minF'].append((x['id'], z, Fs[i], T))
            res['slack_T_d'][T - d] += 1
            res['slack_T_minF'][T - Fs[i]] += 1
            res['z_tested'] += 1
    return res


def hist(c):
    return ' '.join('%s:%d' % (k, c[k]) for k in sorted(c, key=lambda t: Fr(t)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=260926)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    tab = Tables()
    ok0 = part0()

    stats, pairs, zs = part_a(tab, rng)
    print('\nPart A  Lemma 1 / (4)-(6) against exact distances (seed %d)' % args.seed)
    for key in sorted(pairs):
        print('  %-4s m=%-2d pairs %3d  block-length vectors tested %5d' % (key[0], key[1], pairs[key], zs[key]))
    print('  total pairs %d, total (pair, z) points %d' % (sum(pairs.values()), sum(zs.values())))
    print('  same-sign condition of (5) holds for %d words, fails for %d'
          % (stats['same_sign'][True], stats['same_sign'][False]))
    print('  lifted word fails to sort or length != F_W(z): %d' % len(stats['lift_fail']))
    print('  violations d(v(z)) > F_W(z): %d ; F_W(z) > B + beta.z: %d ; d(v(z)) > B + beta.z: %d'
          % (len(stats['violation_F']), len(stats['violation_affine_vs_F']), len(stats['violation_affine'])))
    print('  slack (B + beta.z) - d(v(z)) over z != 0:  ' + hist(stats['slack_affine']))
    print('  slack F_W(z) - d(v(z)) over z != 0:        ' + hist(stats['slack_F']))
    print('  (B + beta.z) - F_W(z) over z != 0:         ' + hist(stats['affine_minus_F']))
    for key in ('lift_fail', 'violation_F', 'violation_affine'):
        for item in stats[key][:5]:
            print('  EXAMPLE %s: %s' % (key, item))

    res = part_b(tab)
    print('\nPart B  criterion (7) at m=9 against exact distances')
    print('  certified families re-checked by (7): %d (per k: %s); criterion failures on recompute: %d'
          % (res['families'], dict(sorted(res['per_k'].items())), len(res['crit_fail'])))
    print('  T_9(unit)+1 - Bbar distribution: ' + hist(res['Bbar_gap']))
    print('  block-length vectors u >= 1 with sum u <= 6 tested: %d' % res['z_tested'])
    print('  violations d(v(u)) > T_9(n): %d ; min_i F_i(u) > T_9(n): %d ; lift failures: %d'
          % (len(res['viol_d']), len(res['viol_minF']), len(res['lift_fail'])))
    print('  slack T_9(n) - d(v(u)):        ' + hist(res['slack_T_d']))
    print('  slack T_9(n) - min_i F_i(u):   ' + hist(res['slack_T_minF']))
    for key in ('viol_d', 'viol_minF', 'lift_fail', 'crit_fail'):
        for item in res[key][:5]:
            print('  EXAMPLE %s: %s' % (key, item))

    bad = (not ok0 or stats['lift_fail'] or stats['violation_F'] or stats['violation_affine']
           or stats['violation_affine_vs_F'] or res['viol_d'] or res['viol_minF'] or res['lift_fail']
           or res['crit_fail'])
    print('\nRESULT: %s' % ('FAIL' if bad else 'PASS (0 violations)'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
