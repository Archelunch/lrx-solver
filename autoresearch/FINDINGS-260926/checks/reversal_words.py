"""Shortest words for the reversal with two outer zeros, (0, m, m-1, ..., 1, 0), m = 4..11.

Read-only analysis over the exact (m,2) tables; writes reversal-words-m8-11.json (refuses to overwrite).
Words sort the state to the root (1..m,0,0) under lrx_m.run_naive semantics (L = left rotation of the
vector, R = L^-1, X swaps v1,v2). Every word below is replayed literally.

    PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_words.py
"""
import collections
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np

from integrations import lrx_m as C
from integrations.bound3_evaluator import score_output
from integrations.bound_task import make_family
from src.lrx.table_bfs import Ranker

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'reversal-words-m8-11.json'
DIRS = {m: 'datasets/generated' for m in range(4, 10)}
DIRS.update({10: 'datasets/generated/m10-r2-260926', 11: 'datasets/generated/m11-260925'})


# ---------------------------------------------------------------- generators (pure functions of m)
def zigzag(K, last):
    """Sweeps of 1, 2, ..., K swaps, alternating direction, the size-K sweep going `last` (L or R)."""
    other = 'R' if last == 'L' else 'L'
    return ''.join(((last if (K - s) % 2 == 0 else other) + 'X') * s for s in range(1, K + 1))


def zigzag_down(K):
    """Sweeps of K, K-1, ..., 1 swaps, alternating direction, the size-K sweep going L."""
    return ''.join((('L' if (K - s) % 2 == 0 else 'R') + 'X') * s for s in range(K, 0, -1))


def word_E(m):
    """m >= 8: L^p X, zigzag up to K1, long R sweep of m-2 swaps with one triple step, zigzag down from K2, R^t."""
    K1 = m // 2 - 1 if m % 2 == 0 else 2 * ((m - 2) // 4) + 1
    K2 = m - 2 - K1
    return ('L' * ((m + 2) // 4) + 'X' + zigzag(K1, 'L') + 'RX' * K1 + 'RRRX' + 'RX' * (K2 - 1)
            + zigzag_down(K2) + 'R' * (m // 4 - 2))


def word_A(m):
    """Merge the zeros, zigzag up to m-6, long R sweep through the zero block, (LX)^4. Slopes (9,8)."""
    K = m - 6
    return 'XRXRXLXLX' + 'L' * (m // 2) + 'X' + zigzag(K, 'L') + 'RX' * K + 'R' + 'RX' * 5 + 'LX' * 4


def word_B(m):
    """Merge the zeros, zigzag up to m-5, long L sweep (W_m of REVERSAL-OBSTACLE.md s.4). Slopes (7,6)."""
    K = m - 5
    return 'XRXRXLXLX' + 'L' * (m // 2) + 'X' + zigzag(K, 'R') + 'LX' * K + 'L' + 'LX' * 4


GENERATORS = {'E': word_E, 'A': word_A, 'B': word_B}


# ---------------------------------------------------------------- tables
def load(m):
    d = ROOT / DIRS[m]
    meta = json.loads((d / ('dist_m%d_r2.json' % m)).read_text())
    return Ranker(m, 2), np.memmap(d / ('dist_m%d_r2.bin' % m), dtype=np.uint8, mode='r'), meta


def verify(m, rk, dist, meta, samples=20000):
    h, sha = np.zeros(256, dtype=np.int64), hashlib.sha256()
    for s in range(0, len(dist), 1 << 26):
        blk = np.asarray(dist[s:s + (1 << 26)])
        h += np.bincount(blk, minlength=256)
        sha.update(blk.tobytes())
    rnd, bad = random.Random(20260926 + m), 0
    for _ in range(samples):
        c = rnd.randrange(len(dist))
        d = int(dist[c])
        nd = [int(dist[rk.rank(q)]) for q in rk.neighbours(rk.unrank(c))]
        bad += any(abs(x - d) > 1 for x in nd) or (d > 0 and min(nd) != d - 1)
    R = meta['radius']
    return {'path': DIRS[m], 'states': len(dist), 'radius': R, 'complete': meta['complete'],
            'table_sha256': meta['table_sha256'], 'sha256_matches': sha.hexdigest() == meta['table_sha256'],
            'histogram_equals_layer_sizes': [int(x) for x in h[:R + 1]] == meta['layer_sizes'],
            'bytes_above_radius': int(h[R + 1:].sum()), 'bytes_255': int(h[255]),
            'triangle_samples': samples, 'triangle_or_predecessor_violations': int(bad)}


def all_shortest(rk, dist, v):
    p0 = rk.positions(tuple(v))
    D = int(dist[rk.rank(p0)])
    out = []

    def rec(p, dd, w):
        if dd == 0:
            out.append(''.join(w))
            return
        for ch, q in zip('LRX', rk.neighbours(p)):
            if int(dist[rk.rank(q)]) == dd - 1:
                w.append(ch)
                rec(q, dd - 1, w)
                w.pop()
    rec(p0, D, [])
    return D, out


def sweeps(w):
    """'L4(1,1,5,1)' = a rightward sweep of 4 swaps whose rotation segments before each X have lengths 1,1,5,1.
    A trailing rotation after the last X is written as its own segment with a '~' suffix."""
    segs = w.split('X')
    out = []
    for i, s in enumerate(segs):
        if not s:
            continue
        d = s[0]
        tag = str(len(s)) + ('~' if i == len(segs) - 1 else '')
        if out and out[-1][0] == d:
            out[-1][1].append(tag)
        else:
            out.append([d, [tag]])
    return ' '.join('%s%d%s' % (d, sum(not t.endswith('~') for t in a),
                                '' if a == ['1'] * len(a) else '(' + ','.join(a) + ')') for d, a in out)


def main():
    if OUT.exists():
        sys.exit('refusing to overwrite %s' % OUT)
    res = {'schema': 'lrx-reversal-words-v1', 'date': '2026-09-26',
           'state': '(0, m, m-1, ..., 1, 0), family (m..1){0,m}, mask 1 | 1<<m',
           'semantics': 'word sorts the state to (1..m,0,0); L: (v1..vn)->(v2..vn,v1), R = L^-1, X swaps v1,v2 '
                        '(integrations/lrx_m.run_naive); replayed with run_naive and run',
           'canonical_rule': 'lexicographically least shortest word in L < R < X (greedy on the geodesic DAG)',
           'sweep_notation': sweeps.__doc__.strip(), 'tables': {}, 'm': {}}
    for m in range(4, 12):
        rk, dist, meta = load(m)
        res['tables'][m] = verify(m, rk, dist, meta)
        T, n = C.budget(m, 2), m + 2
        v = [0] + list(range(m, 0, -1)) + [0]
        D, W = all_shortest(rk, dist, v)
        for w in W:
            assert len(w) == D and C.is_root(C.run_naive(v, w)) and C.is_root(C.run(v, w))
        classes = collections.defaultdict(list)
        for w in W:
            p = C.Profile(v, w)
            classes[(p.base, tuple(p.beta), tuple(p.A))].append(w)
        dd = lambda x: int(dist[rk.rank(rk.positions(tuple(x)))])
        rot = [dd(v[i:] + v[:i]) for i in range(n)]
        adj = [0, 0] + list(range(m, 0, -1))
        rot_adj = [dd(adj[i:] + adj[:i]) for i in range(n)]
        R = meta['radius']
        at = {}
        for d in (R, R - 1):
            codes = []
            for s in range(0, len(dist), 1 << 26):
                codes += (np.flatnonzero(np.asarray(dist[s:s + (1 << 26)]) == d) + s).tolist()
            at[d] = [list(rk.vector(rk.unrank(c))) for c in codes]
        Wset = set(W)
        gens = {}
        for g, f in GENERATORS.items():
            x = f(m)
            ok = C.is_root(C.run_naive(v, x))
            gens[g] = {'word': x, 'length': len(x), 'sorts': ok, 'is_shortest': x in Wset}
            if ok:
                p = C.Profile(v, x)
                gens[g].update(base=p.base, beta=p.beta, A=p.A, sweeps=sweeps(x))
        lexmin = min(W)
        res['m'][m] = {
            'n': n, 'T': T, 'distance': D, 'distance_minus_T': D - T, 'n_shortest_words': len(W),
            'swaps_per_word': sorted({w.count('X') for w in W}), 'swaps_formula_floor((m+1)^2/4)-1': (m + 1) ** 2 // 4 - 1,
            'canonical_lexmin_LRX': lexmin, 'canonical_sweeps': sweeps(lexmin),
            'lemma1_classes': [{'base': b, 'beta': list(bt), 'A': list(a), 'count': len(ws), 'example': min(ws),
                                'example_sweeps': sweeps(min(ws))} for (b, bt, a), ws in sorted(classes.items())],
            'generators': gens,
            'rotations_of_state_distances': rot, 'rotations_of_(0,0,m..1)_distances': rot_adj,
            'radius': R, 'states_at_radius': at[R], 'states_at_radius_minus_1': at[R - 1],
            'shortest_words': sorted(W)}
        print('m', m, 'd', D, 'T', T, 'words', len(W), 'radius', R, 'tables ok',
              all(res['tables'][m][k] for k in ('sha256_matches', 'histogram_equals_layer_sizes'))
              and res['tables'][m]['bytes_255'] == 0 and res['tables'][m]['triangle_or_predecessor_violations'] == 0,
              flush=True)
    rep = []
    for m in range(8, 201):
        v = [0] + list(range(m, 0, -1)) + [0]
        x = word_E(m)
        rep.append([m, len(x), C.budget(m, 2), C.is_root(C.run_naive(v, x)) and C.is_root(C.run(v, x))])
    res['word_E_replay_m8_200'] = {'all_sort': all(r[3] for r in rep), 'all_length_T_minus_1': all(r[1] == r[2] - 1 for r in rep),
                                   'rows_[m,len,T,sorts]': rep}
    lift = {}
    for m in range(8, 17):
        fam = make_family(list(range(m, 0, -1)), 1 | 1 << m)
        v = fam['unit_base']
        ws = {g: f(m) for g, f in GENERATORS.items()}
        lift[m] = {'family': fam['id'], 'T': fam['budget_unit'], 's': fam['slope_bound'],
                   'words': {g: {'length': len(x), 'beta': C.Profile(v, x).beta} for g, x in ws.items()}, 'pools': {}}
        for name in ('E', 'A', 'B', 'A+B', 'A+E', 'A+B+E'):
            r = score_output(fam, {'words': [ws[g] for g in name.split('+')]})
            lf = r['leaves'][0]
            sup = [[s['weight'], s['base'], s['beta']] for s in lf['support']]
            crit = None
            if r['status'] == 'CERTIFIED':  # independent re-check with the group's criterion (7)
                crit = C.mixture_criterion([(b, bt) for _, b, bt in sup], [w for w, _, _ in sup], 2, m=m)[0]
            lift[m]['pools'][name] = {'status': r['status'], 'gap': r['gap'], 'lhs': lf['lhs'],
                                      'slope_excess': lf['slope_excess'], 'support': sup, 'criterion7_recheck': crit}
        print('lift m', m, {k: (p['status'], p['gap']) for k, p in lift[m]['pools'].items()}, flush=True)
    res['lift_bound3_evaluator'] = lift
    OUT.write_text(json.dumps(res, indent=1, default=str) + '\n')
    print('wrote', OUT.relative_to(ROOT))


if __name__ == '__main__':
    main()
