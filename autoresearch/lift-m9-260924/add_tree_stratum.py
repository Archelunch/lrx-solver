"""Add a small tree-route stratum (direct_tree + reverse_tree_transfer) to
the already-frozen v1 parent sets, per team-lead decision: 15 new parents
(10 -> development, 5 -> holdout), disjoint from the existing 300 and from
each other. Tree weights are placeholders ("0", certificate.weights_placeholder
= true): the evaluator solves its own exact LP over whatever words the
candidate returns, so parent weights are hints only (see lift-eval's note).
Stdlib only; package/ untouched; old v1 files kept as-is.
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CHECKER = os.path.join(ROOT, 'autoresearch', 'verify-m8-260924', 'checker')
FROZEN = os.path.join(HERE, 'frozen')
sys.path.insert(0, CHECKER)
sys.path.insert(0, ROOT)

import lrxm8  # noqa: E402
import union  # noqa: E402
from lrxm8 import CheckError, base_vector, parse_state, refine, Profile, Reference, tree_leaves, leaf_criterion  # noqa: E402
from integrations import lift_task as LT  # noqa: E402
from integrations import lrx_m as C  # noqa: E402

SEED = 20260924


def popcount(x):
    return bin(x).count('1')


def order_direct(oi):
    direct = {}
    for r in range(union.ORDER_START[oi], union.ORDER_START[oi + 1]):
        r0, nr = union.R_ROW0[r], union.R_NROW[r]
        rows = [(union.ROW_SRC[i], union.ROW_CUT[i], union.WEIGHTS[union.ROW_W[i]])
                for i in range(r0, r0 + nr)]
        direct[union.R_MASK[r]] = (union.R_STAGE[r], rows)
    return direct


def literal_transfer(vec, word, R, cut):
    n = len(vec)
    rk = [R[(p - cut) % n] for p in range(n)]
    val = list(vec)
    c, out = 0, []
    for ch in word:
        if ch == 'X':
            j = c + 1 if c + 1 < n else 0
            if j == cut:
                raise CheckError('swap across the cut')
            if rk[c] > rk[j]:
                rk[c], rk[j] = rk[j], rk[c]
                val[c], val[j] = val[j], val[c]
                out.append('X')
        elif ch == 'L':
            c = c + 1 if c + 1 < n else 0
            out.append('L')
        else:
            c = c - 1 if c else n - 1
            out.append('R')
    return ''.join(out), (val[c:] + val[:c])


def materialize_tree_flat(oi, mask, base, tree, transfer_from):
    """Verify the real leaf criterion (8) with the package's own weights,
    then flatten all leaf rows into one list with placeholder weight '0'."""
    labels = union.PERMS[oi]
    k = popcount(mask)
    P = base_vector(labels, mask)
    flat = []
    for leaf, box in tree_leaves(tree, [(1, None)] * k):
        rows_check = []
        for row in leaf['rows']:
            Qr = refine(list(base), row['origin'])
            if transfer_from is None:
                if list(base) != P:
                    raise CheckError('direct tree base mismatch')
                prof = Profile(Qr, row['word'], row['picks'])
                word, ref_labels, cut = row['word'], list(parse_state(base)[0]), None
                b, bt = prof.base, list(prof.beta)
            elif row['weight'] in ('0', 0):
                word, ref_labels, cut, b, bt = '', [], None, 0, [0] * k
            else:
                ref = Reference(Qr, row['word'], row['picks'])
                Pr = refine(P, row['origin'])
                got = None
                for c in range(ref.n):
                    if ref.cut_ok(c):
                        try:
                            bb, btt, _ = ref.transfer(Pr, c)
                            wtxt = LT.comparison_word(Pr, Qr, row['word'], c)
                            fin = lrxm8.run(Pr, wtxt)
                            if not lrxm8.is_root(fin):
                                continue
                            prof = Profile(Pr, wtxt)
                            if (prof.base, list(prof.beta)) != (bb, list(btt)):
                                continue
                            got = (bb, btt, wtxt, c)
                            break
                        except (CheckError, lrxm8.CheckError):
                            continue
                if got is None:
                    raise CheckError('no valid cut for tree row transfer')
                b, bt, word, cut = got
                ref_labels = list(parse_state(base)[0])
            rows_check.append((row['weight'], b, bt, row['origin']))
            if list(row['origin']) != [1] * k or not word:
                continue  # only unit-origin, non-placeholder rows are literal words on the parent UNIT base
            flat.append(dict(word=word, reference_labels=ref_labels, cut=cut,
                              base=b, slopes=list(bt), origin=list(row['origin']),
                              real_weight=row['weight'], weight='0'))
        ok, C_, g, ex = leaf_criterion(rows_check, box)
        if not ok:
            raise CheckError('leaf criterion (8) fails on box %s' % (box,))
    if not flat:
        raise CheckError('no unit-origin literal rows found for this tree')
    return flat


def classify_tree(oi, S, direct):
    """Return ('direct_tree'|'reverse_tree_transfer', base, tree, transfer_from) or None,
    for masks NOT already covered by a direct/projection mixture route (so this
    genuinely exercises the tree path, matching union.do_order's own priority)."""
    labels = union.PERMS[oi]
    if S in direct:
        return None
    if (oi, S) in union.TREES:
        base, tree, tag = union.TREES[(oi, S)]
        if tree is not None and list(base) == base_vector(labels, S):
            try:
                if union.verify_tree(labels, S, base, tree, {'literal_letters': 0}, False):
                    return ('direct_tree', base, tree, None)
            except CheckError:
                pass
    for tid, base, tree in union.REV_BY_MASK.get(S, []):
        try:
            if union.verify_tree(labels, S, base, tree, {'literal_letters': 0}, False, transfer_from=tid):
                return ('reverse_tree_transfer', base, tree, tid)
        except CheckError:
            continue
    return None


def main():
    raw = json.load(open(os.path.join(FROZEN, 'parents_raw.v1.json')))
    existing = {(tuple(f['labels']), f['mask']) for f in raw['families']}

    t0 = __import__('time').time()
    union.load_all(lambda m: print('[load]', m, flush=True))
    print('loaded', __import__('time').time() - t0, flush=True)

    rng = random.Random(SEED)
    want_direct_tree = {4: 3, 5: 2, 6: 1, 7: 1}   # 7 total (out of 21 that exist)
    want_reverse = {4: 3, 5: 3, 6: 2}              # 8 total
    built = []
    seen = set(existing)
    skipped = []

    def try_build(oi, S, route, base, tree, transfer_from, k):
        labels = union.PERMS[oi]
        try:
            flat_rows = materialize_tree_flat(oi, S, base, tree, transfer_from)
        except CheckError as e:
            skipped.append(dict(order_index=oi, mask=S, route=route, error=str(e)))
            return None
        return dict(id='k%d-mask%d-order%d' % (k, S, oi), m=8, labels=list(labels), mask=S, k=k,
                    order_index=oi, route=route, unit_base=base_vector(labels, S),
                    certificate=dict(kind='tree', weights_placeholder=True, rows=flat_rows))

    # direct_tree: exhaustively scan the 21 candidates (deterministic order)
    need = dict(want_direct_tree)
    for (oi, S), (base, tree, tag) in sorted(union.TREES.items()):
        k = popcount(S)
        if need.get(k, 0) <= 0 or (oi, S) in seen:
            continue
        direct = order_direct(oi)
        r = classify_tree(oi, S, direct)
        if r and r[0] == 'direct_tree':
            fam = try_build(oi, S, *r, k)
            seen.add((oi, S))
            if fam is not None:
                built.append(fam)
                need[k] -= 1

    # reverse_tree_transfer: random search restricted to k with available REV_BY_MASK masks
    need = dict(want_reverse)
    masks_by_k = {k: [m for m in range(1, 512) if popcount(m) == k] for k in need}
    attempts = 0
    while any(v > 0 for v in need.values()) and attempts < 200000:
        attempts += 1
        k = rng.choice([k for k, v in need.items() if v > 0])
        S = rng.choice(masks_by_k[k])
        oi = rng.randrange(len(union.PERMS))
        if (oi, S) in seen:
            continue
        direct = order_direct(oi)
        r = classify_tree(oi, S, direct)
        if r and r[0] == 'reverse_tree_transfer':
            fam = try_build(oi, S, *r, k)
            seen.add((oi, S))
            if fam is not None:
                built.append(fam)
                need[k] -= 1
    print('picked %d tree parents in %d attempts, %d skipped (materialize failed)' %
          (len(built), attempts, len(skipped)), flush=True)
    if skipped:
        print('skipped sample:', json.dumps(skipped[:5], indent=1))
    assert len(built) == 15, len(built)

    rng.shuffle(built)
    dev_new, hold_new = built[:10], built[10:15]
    print('dev_new', [f['id'] for f in dev_new])
    print('hold_new', [f['id'] for f in hold_new])

    with open(os.path.join(FROZEN, 'tree_stratum.json'), 'w') as fh:
        json.dump(dict(dev_new=dev_new, hold_new=hold_new), fh, indent=1)
    print('wrote tree_stratum.json')


if __name__ == '__main__':
    main()
