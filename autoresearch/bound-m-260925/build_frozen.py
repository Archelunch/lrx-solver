"""Freeze the bound-m family sets (TASK.md, Sets; SPEC-track2.md section 5). Stdlib only.

Writes frozen/development.json (m=9, 10; with the 30-family screen), frozen/holdout.json
(m=9, 10, 11), frozen/edge.json (k=1, unscored) and frozen/manifest.json (seeds, counts per
(set, m, k, class), mask flags, sha256 of every file, reversed-direction rebuild check).
Each (set, m) draws from random.Random('<seed>:m<m>'). Sets are built in the order
development, holdout, edge and are disjoint on (labels, mask). Refuses to overwrite frozen/.

    python autoresearch/bound-m-260925/build_frozen.py
"""
import hashlib
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from integrations import lrx_m as C  # noqa: E402
from integrations.bound_task import SCHEMA, check_family, family_of_state, inversions, make_family  # noqa: E402

HERE = Path(__file__).resolve().parent
FROZEN = HERE / 'frozen'
SEEDS = {('development', 9): 2609251, ('development', 10): 2609251, ('holdout', 9): 2609252,
         ('holdout', 10): 2609252, ('holdout', 11): 2609253, ('edge', 9): 2609254, ('edge', 10): 2609254}
PER_K = {9: 17, 10: 15, 11: 15}
CLASSES = {9: (('rev_rot', 5), ('near_rev', 3), ('refl', 2), ('high_inv', 3), ('uniform', 3), ('easy', 1)),
           10: (('rev_rot', 4), ('near_rev', 3), ('refl', 2), ('high_inv', 3), ('uniform', 2), ('easy', 1)),
           11: (('rev_rot', 4), ('near_rev', 3), ('refl', 2), ('high_inv', 3), ('uniform', 2), ('easy', 1))}
EDGE_PER_M = 10
SUBSTITUTED = []
CLASS_NOTE = ('refl = uniform rotations of (2,1,m,...,3), which is itself the rotation by m-2 of the reversal '
              '(m,...,1): as TASK.md defines it, refl draws from the same cyclic orbit and distribution as rev_rot. '
              'Kept as a separate label; together they give 7 (m=9) or 6 (m=10, 11) reversal-orbit slots per stratum. '
              'At k = m+1 (one mask) the orbit has only m orders, so exhausted slots are drawn as near_rev.')
TIGHT_M9 = {  # TASK.md, derived from outer-layer argmax_cls and asserted below
    ((2, 1, 7, 9, 8, 6, 5, 4, 3), 12), ((2, 1, 9, 8, 7, 6, 5, 4, 3), 68), ((2, 1, 9, 8, 7, 6, 5, 4, 3), 38),
    ((4, 3, 2, 1, 9, 8, 7, 6, 5), 272), ((5, 4, 3, 2, 1, 9, 8, 7, 6), 33), ((7, 6, 5, 4, 3, 2, 1, 9, 8), 132),
    ((9, 8, 7, 6, 5, 4, 3, 2, 1), 17)}
TIGHT_M9_K1 = {((2, 1, 9, 8, 7, 6, 5, 4, 3), 4), ((9, 8, 7, 6, 5, 4, 3, 2, 1), 1), ((4, 1, 3, 2, 9, 8, 7, 6, 5), 16),
               ((2, 3, 1, 9, 8, 7, 6, 5, 4), 8), ((3, 2, 1, 8, 9, 7, 6, 5, 4), 8)}


def rot(a, s):
    return list(a[s:]) + list(a[:s])


def draw_order(rng, cls, m, force_zero=False):
    rev = list(range(m, 0, -1))
    quarter = math.comb(m, 2) / 4
    if cls == 'rev_rot':
        return rot(rev, 0 if force_zero else rng.randrange(m))
    if cls == 'near_rev':
        i = rng.randrange(m - 1)
        a = list(rev)
        a[i], a[i + 1] = a[i + 1], a[i]
        return rot(a, rng.randrange(m))
    if cls == 'refl':
        return rot([2, 1] + list(range(m, 2, -1)), rng.randrange(m))
    if cls == 'uniform':
        a = list(range(1, m + 1))
        rng.shuffle(a)
        return a
    if cls == 'easy' and rng.random() < 0.5:
        return rot(list(range(1, m + 1)), rng.randrange(m))
    for _ in range(10 ** 4):
        a = list(range(1, m + 1))
        rng.shuffle(a)
        inv = inversions(a)
        if (cls == 'high_inv' and inv >= math.ceil(3 * quarter)) or (cls == 'easy' and inv <= quarter):
            return a
    raise RuntimeError('rejection sampling ran out for class %s m=%d' % (cls, m))


def draw_mask(rng, m, k, want=None):
    """Uniform k-subset of {0..m}; want='both' / 'neither' conditions on bits 0 and m."""
    for _ in range(10 ** 4):
        gaps = rng.sample(range(m + 1), k)
        both, neither = 0 in gaps and m in gaps, 0 not in gaps and m not in gaps
        if want is None or (want == 'both' and both) or (want == 'neither' and neither):
            return sum(1 << g for g in gaps)
    raise RuntimeError('no mask with %s for m=%d k=%d' % (want, m, k))


def tight_families():
    """(m, labels, mask, source) of states at d = T: outer-layer m=9 argmax_cls and (10,3) sort holdout."""
    out, seen = [], set()
    for r in range(1, 6):
        path = ROOT / 'autoresearch' / 'outer-layer-260925' / ('class_m9_r%d_full.json' % r)
        for x in json.loads(path.read_text())['argmax_cls']:
            labels, mask, lens = family_of_state(x['v'])
            assert C.refine(C.base_vector(labels, mask), lens) == x['v']
            if (tuple(labels), mask) not in seen:
                seen.add((tuple(labels), mask))
                out.append((9, labels, mask, '%s argmax_cls v=%s' % (path.name, x['v'])))
    got = {(tuple(a), s) for m, a, s, _ in out if m == 9}
    assert got == TIGHT_M9 | TIGHT_M9_K1, sorted(got ^ (TIGHT_M9 | TIGHT_M9_K1))
    missing = []
    hold = ROOT / 'autoresearch' / 'sort-m9-260925' / 'frozen' / 'holdout.json'
    if hold.is_file():
        for x in json.loads(hold.read_text())['states']:
            if x['m'] == 10 and x['r'] == 3 and x['d'] == x['budget']:
                labels, mask, lens = family_of_state(x['v'])
                assert C.refine(C.base_vector(labels, mask), lens) == x['v']
                if (tuple(labels), mask) not in seen:
                    seen.add((tuple(labels), mask))
                    out.append((10, labels, mask, 'sort-m9-260925 holdout %s d=T=%d' % (x['id'], x['d'])))
    else:
        missing.append('sort-m9-260925/frozen/holdout.json absent: no (10,3) tight families')
    return out, missing


def meta(labels, mask, cls, source=None):
    m = len(labels)
    return make_family(labels, mask, **{'class': cls, 'inv': inversions(labels),
                                        'bit0': bool(mask & 1), 'bitm': bool(mask >> m & 1),
                                        'tight_source': source})


def build_stratum(rng, m, k, taken, tight, rev_zero_needed):
    """17 or 15 families for one (m, k); tight families replace high_inv/uniform slots."""
    slots = [c for c, n in CLASSES[m] for _ in range(n)]
    fams = []
    for labels, mask, src in tight:
        i = next(i for i, c in enumerate(slots) if c in ('high_inv', 'uniform'))
        slots.pop(i)
        fams.append(meta(labels, mask, 'tight', src))
        taken.add((tuple(labels), mask))
    wants = []
    if k >= 2:
        if not any(f['bit0'] and f['bitm'] for f in fams):
            wants.append('both')
        if k <= m - 1 and not any(not f['bit0'] and not f['bitm'] for f in fams):
            wants.append('neither')
    for idx, cls in enumerate(slots):
        for attempt in range(1000):
            force = rev_zero_needed[0] and cls == 'rev_rot' and attempt == 0
            labels = draw_order(rng, cls, m, force_zero=force)
            mask = draw_mask(rng, m, k, wants[idx] if idx < len(wants) else None)
            if (tuple(labels), mask) not in taken:
                break
        else:
            if cls not in ('rev_rot', 'refl'):
                raise RuntimeError('could not draw a fresh family for m=%d k=%d class %s' % (m, k, cls))
            # k = m+1 has one mask and only m rotations: the class is exhausted across sets
            for _ in range(1000):
                labels, mask = draw_order(rng, 'near_rev', m), draw_mask(rng, m, k)
                if (tuple(labels), mask) not in taken:
                    break
            SUBSTITUTED.append('m%d k%d: %s exhausted, slot drawn as near_rev' % (m, k, cls))
            cls = 'near_rev'
        if force:
            rev_zero_needed[0] = False
        taken.add((tuple(labels), mask))
        fams.append(meta(labels, mask, cls))
    return fams


def pick_screen(dev, rng):
    """15 per m: one per k stratum, the rest from rev_rot, near_rev and tight (TASK.md, Screen)."""
    screen = []
    for m in (9, 10):
        fams = [f for f in dev if f['m'] == m]
        chosen = []
        for k in sorted({f['k'] for f in fams}):
            chosen.append(rng.choice([f for f in fams if f['k'] == k])['id'])
        rest = [f['id'] for f in fams if f['class'] in ('rev_rot', 'near_rev', 'tight') and f['id'] not in chosen]
        chosen += rng.sample(sorted(rest), 15 - len(chosen))
        screen += chosen
    return screen


def main():
    if FROZEN.exists():
        raise SystemExit('refusing to overwrite %s' % FROZEN)
    tight, missing = tight_families()
    taken, sets = set(), {}
    for name, ms in (('development', (9, 10)), ('holdout', (9, 10, 11))):
        fams = []
        for m in ms:
            rng = random.Random('%d:m%d' % (SEEDS[(name, m)], m))
            rev_zero = [True]
            for k in range(2, m + 2):
                tk = [(a, s, src) for mm, a, s, src in tight
                      if name == 'development' and mm == m and bin(s).count('1') == k]
                fams += build_stratum(rng, m, k, taken, tk, rev_zero)
        sets[name] = fams
    edge = []
    for m in (9, 10):
        rng = random.Random('%d:m%d' % (SEEDS[('edge', m)], m))
        tk = [(a, s, src) for mm, a, s, src in tight if mm == m and bin(s).count('1') == 1]
        for a, s, src in tk:
            taken.add((tuple(a), s))
            edge.append(meta(a, s, 'tight', src))
        root = (list(range(1, m + 1)), 1 << m)
        if (tuple(root[0]), root[1]) not in taken:
            taken.add((tuple(root[0]), root[1]))
            edge.append(meta(root[0], root[1], 'root'))
        classes = ['rev_rot', 'near_rev', 'refl', 'high_inv', 'uniform', 'easy'] * 3
        while sum(f['m'] == m for f in edge) < EDGE_PER_M:
            cls = classes.pop(0)
            labels, mask = draw_order(rng, cls, m), draw_mask(rng, m, 1)
            if (tuple(labels), mask) not in taken:
                taken.add((tuple(labels), mask))
                edge.append(meta(labels, mask, cls))
    sets['edge'] = edge
    screen = pick_screen(sets['development'], random.Random('%d:screen' % SEEDS[('development', 9)]))
    for fams in sets.values():
        for f in fams:
            check_family(f)
    keys = [(tuple(f['labels']), f['mask']) for fams in sets.values() for f in fams]
    assert len(keys) == len(set(keys)), 'sets are not disjoint on (labels, mask)'
    FROZEN.mkdir()
    files, counts = {}, {}
    for name, fams in sets.items():
        body = {'schema': SCHEMA, 'set': name, 'families': fams}
        if name == 'development':
            body['screen'] = screen
        data = (json.dumps(body, indent=1) + '\n').encode()
        (FROZEN / (name + '.json')).write_bytes(data)
        files[name + '.json'] = hashlib.sha256(data).hexdigest()
        for f in fams:
            key = '%s m%d k%d %s' % (name, f['m'], f['k'], f['class'])
            counts[key] = counts.get(key, 0) + 1
    manifest = {'schema': 'lrx-bound-manifest-v1', 'task': 'bound-m-260925',
                'seeds': {'%s m%d' % k: v for k, v in SEEDS.items()}, 'rng': "random.Random('<seed>:m<m>')",
                'files': files, 'families': {n: len(f) for n, f in sets.items()},
                'per_m': {n: {str(m): sum(f['m'] == m for f in fams) for m in (9, 10, 11)} for n, fams in sets.items()},
                'counts': counts, 'screen': screen, 'tight_missing': missing, 'class_substitutions': SUBSTITUTED,
                'class_note': CLASS_NOTE,
                'mask_flags': {n: {'both_0_and_m': sum(f['bit0'] and f['bitm'] for f in fams),
                                   'neither': sum(not f['bit0'] and not f['bitm'] for f in fams)}
                               for n, fams in sets.items()},
                'rebuild_check': 'every unit base parsed back to (labels, mask, 1^k) by bound_task.check_family',
                'disjoint': True, 'holdout_note': 'm=11 appears in no prompt, packet or trainset; holdout '
                                                  'evaluated once after finalist freeze by a human-run command'}
    (FROZEN / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    print(json.dumps({'files': files, 'families': manifest['families'], 'per_m': manifest['per_m'],
                      'tight_missing': missing, 'screen': len(screen), 'substitutions': SUBSTITUTED}))


if __name__ == '__main__':
    main()
