"""Independently rebuild the k>=4 coverage table of the m=8 package.

For every label order a (8! lexicographic) and every mask S (9 bits, |S|>=4):
  1. direct mixture record for (a,S) in a stage file 4..9  -> verify transfer + (7)
  2. direct tree (repairs / reverse fallback) for (a,S)     -> verify leaves (8)
  3. projection (Lemma 4) of any direct mixture record (a,M), M strictly contains S:
     project each reference word, rebuild the child reference from scratch,
     verify transfer (Lemma 3, (11)) on the child and criterion (7) with the child budget
  4. whole-tree comparison transfer of one of the 8 reverse-order trees with mask S
     (every row of every leaf transferred with some valid cut, then (8))
The first success counts.  Nothing from the package's coverage tables is read.

usage: python union.py [--orders A:B] [--workers W] [--literal-every P]
"""
import argparse
import itertools
import json
import multiprocessing as mp
import os
import sys
import time
from array import array

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lrxm8 import (CheckError, Reference, base_vector, leaf_criterion, literal_lift_check,  # noqa: E402
                   mixture_criterion, parse_state, project, refine, tree_leaves, z_samples)

HERE = os.path.dirname(os.path.abspath(__file__))
LIT = os.path.join(HERE, '..', 'package', 'literature')
STAGE_FILES = [
    (9, 'multiset_nine_gap_complete_certificates_20260924.json', None),
    (8, 'multiset_eight_gap_complement_certificates_20260924.json', None),
    (7, 'multiset_seven_gap_complement_certificates_20260924.json', None),
    (6, 'multiset_six_gap_bounded_search_20260924.json', 'multiset_six_gap_bounded_repairs_final_20260924.json'),
    (5, 'multiset_five_gap_bounded_search_20260924.json', 'multiset_five_gap_bounded_repairs_final_20260924.json'),
    (4, 'multiset_four_gap_bounded_search_20260924.json', 'multiset_four_gap_bounded_repairs_final_20260924.json'),
]
REVERSE_FILE = 'multiset_reverse_m8_complete_certificates_20260923.json'
EXPECTED = {4: 5080320, 5: 5080320, 6: 3386880, 7: 1451520, 8: 362880, 9: 40320}

PERMS = None
# compact shared store (filled before fork)
W_BLOB = bytearray()
W_OFF = array('Q', [0])
S_BLOB = bytearray()
S_OFF = array('Q', [0])
R_ORDER = array('I')
R_MASK = array('H')
R_ROW0 = array('I')
R_NROW = array('B')
R_STAGE = array('B')
ROW_SRC = array('I')
ROW_CUT = array('B')
ROW_W = array('I')
WEIGHTS = []
ORDER_START = None
TREES = {}      # (order_index, mask) -> (base, tree, tag)
REV_BY_MASK = {}  # mask -> list of (tree_id, base, tree)


def popcount(x):
    return bin(x).count('1')


def load_all(log):
    global PERMS, ORDER_START
    PERMS = list(itertools.permutations(range(1, 9)))
    pidx = {p: i for i, p in enumerate(PERMS)}
    widx = {}
    recs = []
    for k, fn, rep in STAGE_FILES:
        t = time.time()
        d = json.load(open(os.path.join(LIT, fn)))
        base_id = len(W_OFF) - 1
        for c in d['catalog']:
            W_BLOB.extend(c['word'].encode())
            W_OFF.append(len(W_BLOB))
            S_BLOB.extend(bytes(c['state']))
            S_OFF.append(len(S_BLOB))
        repairs = {}
        if rep:
            for res in json.load(open(os.path.join(LIT, rep)))['results']:
                repairs[(res['mask'], tuple(res['labels']))] = res['result']
        for rec in d['records']:
            mask = rec.get('mask', 511)
            oi = rec['order_index']
            if PERMS[oi] != tuple(rec['labels']):
                raise SystemExit('order_index mismatch')
            mix = rec.get('mixture')
            if rec.get('method') == 'unresolved' or mix is None:
                key = (mask, tuple(rec['labels']))
                if key in repairs:
                    TREES[(oi, mask)] = (tuple(repairs[key]['base']), repairs[key]['tree'], 'repair%d' % k)
                else:
                    TREES[(oi, mask)] = (None, None, 'reverse_fallback%d' % k)
                continue
            rows = []
            for m in mix:
                w = widx.setdefault(m['weight'], len(widx))
                rows.append((base_id + m['source'], m['cut'], w))
            recs.append((oi, mask, k, rows))
        del d
        log('loaded stage %d in %.1fs' % (k, time.time() - t))
    WEIGHTS.extend(sorted(widx, key=widx.get))
    recs.sort(key=lambda r: r[0])
    ORDER_START = array('I', [0] * (len(PERMS) + 1))
    for oi, mask, k, rows in recs:
        R_ORDER.append(oi)
        R_MASK.append(mask)
        R_STAGE.append(k)
        R_ROW0.append(len(ROW_SRC))
        R_NROW.append(len(rows))
        for s, c, w in rows:
            ROW_SRC.append(s)
            ROW_CUT.append(c)
            ROW_W.append(w)
        ORDER_START[oi + 1] += 1
    for i in range(len(PERMS)):
        ORDER_START[i + 1] += ORDER_START[i]
    rev = json.load(open(os.path.join(LIT, REVERSE_FILE)))
    for tid, fam in enumerate(rev['families']):
        labels, mask, _ = parse_state(fam['base'])
        REV_BY_MASK.setdefault(mask, []).append((tid, tuple(fam['base']), fam['tree']))
        key = (pidx[tuple(labels)], mask)
        if key in TREES and TREES[key][2].startswith('reverse_fallback'):
            TREES[key] = (tuple(fam['base']), fam['tree'], TREES[key][2])
    log('records %d rows %d catalog %d trees %d' % (len(R_ORDER), len(ROW_SRC), len(W_OFF) - 1, len(TREES)))


def cat(src):
    w = W_BLOB[W_OFF[src]:W_OFF[src + 1]].decode()
    s = list(S_BLOB[S_OFF[src]:S_OFF[src + 1]])
    return s, w


# ------------------------------------------------------------------ worker side
_CREF = {}
_RREF = {}


def child_reference(src, delete_blocks):
    key = (src, delete_blocks)
    hit = _CREF.get(key)
    if hit is None:
        if len(_CREF) > 40000:
            _CREF.clear()
        state, word = cat(src)
        if delete_blocks:
            child, cw, keep = project(state, word, set(delete_blocks))
        else:
            child, cw, keep = state, word, list(range(len(state)))
        hit = (Reference(child, cw), keep)
        _CREF[key] = hit
    return hit


def verify_mix(labels, parent_mask, child_mask, rows, st, literal):
    """rows: list of (src, cut, weight_str). parent_mask==child_mask means direct."""
    gaps = [g for g in range(9) if (parent_mask >> g) & 1]
    delete = tuple(j for j, g in enumerate(gaps) if not (child_mask >> g) & 1)
    Pp = base_vector(labels, parent_mask)
    k = popcount(child_mask)
    costs = []
    for src, cut, w in rows:
        cref, keep = child_reference(src, delete)
        P = [Pp[p] for p in keep]
        kept = set(keep)
        n0 = len(Pp)
        p = cut
        while p not in kept:
            p = (p + 1) % n0
        ccut = keep.index(p)
        try:
            b, bt, _ = cref.transfer(P, ccut)
        except CheckError:
            got = None
            for c2 in range(cref.n):
                if c2 != ccut and cref.cut_ok(c2):
                    try:
                        got = cref.transfer(P, c2)
                        ccut = c2
                        break
                    except CheckError:
                        pass
            if got is None:
                return False
            st['alternative_cut'] += 1
            b, bt, _ = got
        if literal:
            zs = z_samples(k)
            st['literal_letters'] += literal_lift_check(cref.prof, zs)
            st['literal_letters'] += cref.literal_transfer(P, ccut, zs, b, bt)
        costs.append((b, bt))
    ok, _, _ = mixture_criterion(costs, [w for _, _, w in rows], k)
    return ok


def verify_tree(labels, mask, base, tree, st, literal, transfer_from=None):
    """Direct tree (transfer_from None) or whole-tree comparison transfer from a reverse tree id."""
    k = popcount(mask)
    P = base_vector(labels, mask)
    zs = z_samples(k)
    for leaf, box in tree_leaves(tree, [(1, None)] * k):
        rows = []
        for ri, row in enumerate(leaf['rows']):
            Qr = refine(list(base), row['origin'])
            if transfer_from is None:
                if list(base) != P:
                    return False
                from lrxm8 import Profile
                prof = Profile(Qr, row['word'], row['picks'])
                if literal:
                    st['literal_letters'] += literal_lift_check(prof, zs)
                rows.append((row['weight'], prof.base, prof.beta, row['origin']))
                continue
            if row['weight'] in ('0', 0):
                rows.append((row['weight'], 0, [0] * k, row['origin']))
                continue
            key = (transfer_from, id(leaf), ri)
            ref = _RREF.get(key)
            if ref is None:
                ref = Reference(Qr, row['word'], row['picks'])
                _RREF[key] = ref
            Pr = refine(P, row['origin'])
            got = None
            for c in range(ref.n):
                if ref.cut_ok(c):
                    try:
                        got = ref.transfer(Pr, c)
                        if literal:
                            st['literal_letters'] += ref.literal_transfer(Pr, c, zs, got[0], got[1])
                        break
                    except CheckError:
                        pass
            if got is None:
                return False
            rows.append((row['weight'], got[0], got[1], row['origin']))
        ok, _, _, _ = leaf_criterion(rows, box)
        if not ok:
            return False
    return True


MASKS = [m for m in range(1, 512) if popcount(m) >= 4]
MASKS.sort(key=lambda m: (-popcount(m), m))


def do_order(oi, literal_every, st):
    labels = PERMS[oi]
    direct = {}
    for r in range(ORDER_START[oi], ORDER_START[oi + 1]):
        r0, nr = R_ROW0[r], R_NROW[r]
        rows = [(ROW_SRC[i], ROW_CUT[i], WEIGHTS[ROW_W[i]]) for i in range(r0, r0 + nr)]
        direct[R_MASK[r]] = (R_STAGE[r], rows)
    parents = sorted(direct, key=popcount)
    for S in MASKS:
        k = popcount(S)
        literal = literal_every and (oi * 512 + S) % literal_every == 0
        if literal:
            st['literal_families'] += 1
        how = None
        try:
            if S in direct:
                if verify_mix(labels, S, S, direct[S][1], st, literal):
                    how = 'direct_mixture'
                else:
                    st['direct_failed'].append([oi, S])
            elif (oi, S) in TREES:
                base, tree, tag = TREES[(oi, S)]
                if tree is not None and verify_tree(labels, S, base, tree, st, literal):
                    how = 'direct_tree'
                else:
                    st['direct_failed'].append([oi, S, tag])
            if how is None:
                for M in parents:
                    if M != S and M & S == S:
                        if verify_mix(labels, M, S, direct[M][1], st, literal):
                            how = 'projection_from_%d' % popcount(M)
                            break
            if how is None:
                for tid, base, tree in REV_BY_MASK.get(S, []):
                    if verify_tree(labels, S, base, tree, st, literal, transfer_from=tid):
                        how = 'reverse_tree_transfer'
                        break
        except CheckError as e:
            st['errors'].append([oi, S, str(e)])
        key = '%d:%s' % (k, how or 'UNCOVERED')
        st['table'][key] = st['table'].get(key, 0) + 1
        if how is None:
            st['uncovered'].append([oi, S])


def new_st():
    return {'table': {}, 'uncovered': [], 'direct_failed': [], 'errors': [], 'alternative_cut': 0,
            'literal_families': 0, 'literal_letters': 0, 'orders': 0}


def work(args):
    lo, hi, literal_every = args
    st = new_st()
    for oi in range(lo, hi):
        do_order(oi, literal_every, st)
        st['orders'] += 1
    return st


def merge(a, b):
    for key, v in b.items():
        if isinstance(v, list):
            a[key].extend(v)
        elif isinstance(v, dict):
            for kk, vv in v.items():
                a[key][kk] = a[key].get(kk, 0) + vv
        else:
            a[key] += v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--orders', default='0:40320')
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--chunk', type=int, default=40)
    ap.add_argument('--literal-every', type=int, default=97)
    ap.add_argument('--out', default=os.path.join(HERE, 'results', 'union.json'))
    args = ap.parse_args()
    try:
        os.nice(10)
    except OSError:
        pass
    t0 = time.time()

    def log(msg):
        print('[%7.1fs] %s' % (time.time() - t0, msg), flush=True)

    load_all(log)
    lo, hi = map(int, args.orders.split(':'))
    tasks = [(a, min(a + args.chunk, hi), args.literal_every) for a in range(lo, hi, args.chunk)]
    st = new_st()
    done = 0
    ctx = mp.get_context('fork')
    with ctx.Pool(args.workers) as pool:
        for s in pool.imap_unordered(work, tasks):
            merge(st, s)
            done += 1
            if done % 25 == 0 or done == len(tasks):
                unc = len(st['uncovered'])
                log('orders %d/%d uncovered so far %d' % (st['orders'], hi - lo, unc))
    per_k = {}
    for key, v in st['table'].items():
        k, how = key.split(':', 1)
        per_k.setdefault(int(k), {})[how] = v
    summary = {}
    for k in sorted(per_k):
        tot = sum(per_k[k].values())
        summary[k] = {'families': tot, 'expected_if_all_orders': EXPECTED[k],
                      'uncovered': per_k[k].get('UNCOVERED', 0), 'by_source': per_k[k]}
    out = {'orders': [lo, hi], 'literal_every': args.literal_every, 'per_k': summary,
           'uncovered_count': len(st['uncovered']), 'uncovered': st['uncovered'][:5000],
           'direct_failed_count': len(st['direct_failed']), 'direct_failed': st['direct_failed'][:5000],
           'errors': st['errors'][:2000], 'alternative_cut_rows': st['alternative_cut'],
           'literal_families': st['literal_families'], 'literal_letters': st['literal_letters'],
           'seconds': round(time.time() - t0, 1), 'workers': args.workers}
    path = args.out
    if os.path.exists(path):
        b, e = os.path.splitext(path)
        path = '%s_%d%s' % (b, int(time.time()), e)
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    log('wrote %s' % path)
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
