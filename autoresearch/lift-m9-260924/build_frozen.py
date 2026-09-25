"""Build the frozen m=8 -> m=9 lift development/holdout instance sets.

Stdlib only. Uses two already-existing pieces of OUR code, unmodified:
  - autoresearch/verify-m8-260924/checker/{lrxm8,union}.py: independent m=8
    package checker, used here only to classify each (labels, mask) family's
    certificate route (direct_mixture / projection_from_N) exactly as
    union.do_order does, and to verify criterion (7).
  - integrations/{lrx_m,lift_task}.py: the shared lift-task library (already
    built by the lift-eval worker per autoresearch/lift-m9-260924/TASK.md's
    "Schema decisions" section). Its build_instances()/check_instance() are
    the actual contract the evaluator uses, so instances are built with it
    directly rather than re-derived here.

Never touches package/. Deterministic given SEED.

LIMITATION discovered while building this: integrations/lift_task.py's
check_instance() and integrations/lift_evaluator.py both read
parent['certificate']['rows'] as a flat list unconditionally; neither
handles a tree/leaf structure. The m=8 package's tree-route families
(direct_tree, reverse_tree_transfer -- only 21 + ~38k families out of
~19.8M respectively, see autoresearch/verify-m8-260924/checker/results/
union.json) cannot be flattened into a single global mixture without
losing their per-box conditional weights, so they are NOT evaluator-usable
today. This build therefore only samples direct_mixture and
projection_from_N routes (2 of the 4 routes asked for); tree routes are
excluded and documented, not silently dropped.
"""
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CHECKER = os.path.join(ROOT, 'autoresearch', 'verify-m8-260924', 'checker')
FROZEN = os.path.join(HERE, 'frozen')
sys.path.insert(0, CHECKER)
sys.path.insert(0, ROOT)

import lrxm8  # noqa: E402
import union  # noqa: E402
from lrxm8 import CheckError, base_vector, parse_state  # noqa: E402
from integrations import lrx_m as C  # noqa: E402
from integrations import lift_task as LT  # noqa: E402

SEED = 20260924
M = 8


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


def classify(oi, S, direct, want):
    """Mixture-only subset of union.do_order's priority chain (direct then
    smallest-popcount-first projection); tree branches skipped (see module
    docstring). Returns (route, parent_mask, rows) or None."""
    labels = union.PERMS[oi]
    if S in direct:
        stage, rows = direct[S]
        if union.verify_mix(labels, S, S, rows, {'alternative_cut': 0, 'literal_letters': 0}, False):
            return ('direct_mixture', S, rows) if want in (None, 'direct_mixture') else None
        return None
    if (oi, S) in union.TREES:
        return None  # a direct_tree would win here in the real priority chain; excluded (see docstring)
    parents = sorted(direct, key=popcount)
    for Mm in parents:
        if Mm != S and Mm & S == S:
            stage, rows = direct[Mm]
            try:
                ok = union.verify_mix(labels, Mm, S, rows, {'alternative_cut': 0, 'literal_letters': 0}, False)
            except CheckError:
                ok = False
            if ok:
                return ('projection_from_%d' % popcount(Mm), Mm, rows) if want in (None, 'projection') else None
    return None


def materialize_rows(oi, parent_mask, S, rows):
    """Literal words on the (labels, S) unit base, via Lemma 4 deletion
    (lrxm8.project, same primitive union.py uses) + Lemma 3 comparison
    transfer (integrations.lift_task.comparison_word, the evaluator's own
    transfer builder). base/slopes recomputed by integrations.lrx_m.Profile
    inside lift_task.plain_row, never copied from the package."""
    labels = union.PERMS[oi]
    gaps = [g for g in range(9) if (parent_mask >> g) & 1]
    delete = tuple(j for j, g in enumerate(gaps) if not (S >> g) & 1)
    Pp = base_vector(labels, parent_mask)
    out_rows = []
    for src, cut, w in rows:
        state, word = union.cat(src)
        if delete:
            child_state, child_word, keep = lrxm8.project(state, word, set(delete))
        else:
            child_state, child_word, keep = state, word, list(range(len(state)))
        P = [Pp[p] for p in keep]
        kept = set(keep)
        n0 = len(Pp)
        p = cut
        while p not in kept:
            p = (p + 1) % n0
        ccut = keep.index(p)
        ref_labels = parse_state(state)[0]
        try:
            plain = LT.comparison_word(P, child_state, child_word, ccut)
        except lrxm8.CheckError:
            ok_cut = None
            ref = lrxm8.Reference(child_state, child_word)
            for c2 in range(ref.n):
                if c2 != ccut and ref.cut_ok(c2):
                    try:
                        plain = LT.comparison_word(P, child_state, child_word, c2)
                        ok_cut = c2
                        break
                    except lrxm8.CheckError:
                        continue
            if ok_cut is None:
                raise
            ccut = ok_cut
        row = LT.plain_row(list(labels), S, plain, weight=w, reference_labels=list(ref_labels), cut=ccut)
        out_rows.append(row)
    costs = [(r['base'], r['slopes']) for r in out_rows]
    ok, B, beta = lrxm8.mixture_criterion(costs, [r['weight'] for r in out_rows], popcount(S))
    if not ok:
        raise CheckError('materialized mixture fails criterion (7): B=%s beta=%s' % (B, beta))
    return out_rows


def build_parent(oi, S, route, parent_mask, rows):
    labels = union.PERMS[oi]
    k = popcount(S)
    out_rows = materialize_rows(oi, parent_mask, S, rows)
    return dict(id='k%d-mask%d-order%d' % (k, S, oi), m=M, labels=list(labels), mask=S, k=k,
                order_index=oi, route=route,
                unit_base=base_vector(labels, S),
                certificate=dict(kind='mixture', rows=out_rows))


TARGETS = {
    4: dict(direct_mixture=25, projection=25),
    5: dict(direct_mixture=25, projection=25),
    6: dict(direct_mixture=25, projection=25),
    7: dict(direct_mixture=25, projection=25),
    8: dict(direct_mixture=25, projection=25),
    9: dict(direct_mixture=50),
}


def masks_of_popcount(k):
    return [m for m in range(1, 512) if popcount(m) == k]


def sample():
    rng = random.Random(SEED)
    picks = []
    seen = set()
    for k, want in sorted(TARGETS.items()):
        masks = masks_of_popcount(k)
        for route_name, target in sorted(want.items()):
            got, attempts = 0, 0
            max_attempts = target * 500 + 3000
            while got < target and attempts < max_attempts:
                attempts += 1
                oi = rng.randrange(len(union.PERMS))
                S = rng.choice(masks)
                if (oi, S) in seen:
                    continue
                direct = order_direct(oi)
                result = classify(oi, S, direct, want=route_name)
                if result is None:
                    continue
                route, parent_mask, rows = result
                picks.append((oi, S, route, parent_mask, rows, k))
                seen.add((oi, S))
                got += 1
            print('k=%d route=%s: got %d/%d in %d attempts' % (k, route_name, got, target, attempts), flush=True)
    return picks


def main():
    t0 = time.time()
    union.load_all(lambda m: print('[load]', m, flush=True))
    print('loaded in %.1fs' % (time.time() - t0), flush=True)

    picks = sample()
    print('sampled %d parents in %.1fs' % (len(picks), time.time() - t0), flush=True)

    built, errors = [], []
    for oi, S, route, parent_mask, rows, k in picks:
        try:
            built.append(build_parent(oi, S, route, parent_mask, rows))
        except CheckError as e:
            errors.append(dict(order_index=oi, mask=S, route=route, error=str(e)))
        except Exception as e:
            errors.append(dict(order_index=oi, mask=S, route=route, error='%s: %s' % (type(e).__name__, e)))
    print('built %d families, %d errors' % (len(built), len(errors)), flush=True)
    if errors:
        print('ERRORS (first 10):', json.dumps(errors[:10], indent=1), flush=True)

    os.makedirs(FROZEN, exist_ok=True)
    with open(os.path.join(FROZEN, 'parents_raw.json'), 'w') as fh:
        json.dump(dict(seed=SEED, targets=TARGETS, count=len(built), errors=errors, families=built), fh)
    print('wrote parents_raw.json (%.1fs total)' % (time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
