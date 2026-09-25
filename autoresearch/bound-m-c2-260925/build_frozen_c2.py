"""Freeze the bound-m campaign 2 sets. Stdlib only; refuses to overwrite frozen/.

- development: campaign 1's frozen/development.json, by reference (path and sha256; the
  30-family screen inside it is unchanged). Engines load that file directly.
- validation: campaign 1's 165 m=11 holdout families, copied verbatim into
  frozen/validation.json (checked equal to the c1 holdout records). Never shown to an
  engine; used only by finalize to pick each (arm, seed) finalist. Stored with
  "set": "holdout" so bound_evaluator.load_set and guard_not_holdout refuse it anywhere
  except an explicit allow_holdout load.
- holdout: 165 fresh m=12 families (k = 2..12, 15 per k, classes 4/3/2/3/2/1 as c1 m=11)
  plus 60 fresh m=11 families (the same class totals x4, dealt over k = 2..12), seed
  260925, disjoint from every c1 family. Evaluated once, after finalist freeze.

The draw helpers (draw_order, draw_mask, meta) are campaign 1's build_frozen.py, loaded
read-only without writing bytecode into the campaign 1 directory.

    python autoresearch/bound-m-c2-260925/build_frozen_c2.py
"""
import hashlib
import importlib.util
import json
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C1 = ROOT / 'autoresearch' / 'bound-m-260925'
FROZEN = HERE / 'frozen'
SEED = 260925
M12_PER_K = 15
M12_K = range(2, 13)          # c1 m=11 k range 2..12; k = 13 (single all-gaps mask) not drawn
M11_FRESH = 60
CLASSES = (('rev_rot', 4), ('near_rev', 3), ('refl', 2), ('high_inv', 3), ('uniform', 2), ('easy', 1))

sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('c1_build_frozen', C1 / 'build_frozen.py')
c1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c1)
from integrations.bound_task import SCHEMA, check_family  # noqa: E402


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def draw(rng, m, k, cls, want, taken, force_zero=False):
    for _ in range(1000):
        labels = c1.draw_order(rng, cls, m, force_zero=force_zero)
        mask = c1.draw_mask(rng, m, k, want)
        if (tuple(labels), mask) not in taken:
            taken.add((tuple(labels), mask))
            return c1.meta(labels, mask, cls)
        force_zero = False
    raise RuntimeError('no fresh family m=%d k=%d %s' % (m, k, cls))


def stratum(rng, m, k, slots, taken, rev_zero):
    """One (m, k) stratum; the first slots carry the 'both' / 'neither' mask conditions (c1 rule)."""
    wants = ['both'] + (['neither'] if k <= m - 1 else [])
    fams = []
    for i, cls in enumerate(slots):
        force = rev_zero[0] and cls == 'rev_rot'
        fams.append(draw(rng, m, k, cls, wants[i] if i < len(wants) else None, taken, force))
        if force:
            rev_zero[0] = False
    return fams


def main():
    if FROZEN.exists():
        raise SystemExit('refusing to overwrite %s' % FROZEN)
    c1_manifest = json.loads((C1 / 'frozen' / 'manifest.json').read_text())
    c1_sets = {n: json.loads((C1 / 'frozen' / (n + '.json')).read_text()) for n in ('development', 'holdout', 'edge')}
    for n, body in c1_sets.items():
        if _sha((C1 / 'frozen' / (n + '.json')).read_bytes()) != c1_manifest['files'][n + '.json']:
            raise SystemExit('campaign 1 %s.json differs from its manifest' % n)
    taken = {(tuple(f['labels']), f['mask']) for b in c1_sets.values() for f in b['families']}
    validation = [f for f in c1_sets['holdout']['families'] if f['m'] == 11]
    assert len(validation) == 165

    base = [c for c, n in CLASSES for _ in range(n)]
    rng12 = random.Random('%d:m12' % SEED)
    rev_zero = [True]
    m12 = []
    for k in M12_K:
        m12 += stratum(rng12, 12, k, list(base), taken, rev_zero)
    rng11 = random.Random('%d:m11' % SEED)
    slots = base * (M11_FRESH // len(base))
    rng11.shuffle(slots)
    sizes = [M11_FRESH // len(M12_K) + (i < M11_FRESH % len(M12_K)) for i in range(len(M12_K))]
    m11, rev_zero, at = [], [True], 0
    for k, size in zip(M12_K, sizes):
        m11 += stratum(rng11, 11, k, slots[at:at + size], taken, rev_zero)
        at += size
    holdout = m12 + m11
    for f in validation + holdout:
        check_family(f)
    keys = [(tuple(f['labels']), f['mask']) for f in holdout]
    assert len(keys) == len(set(keys))
    assert not set(keys) & {(tuple(f['labels']), f['mask']) for b in c1_sets.values() for f in b['families']}

    FROZEN.mkdir()
    files, counts = {}, {}
    for name, fams, role in (('validation', validation, 'validation'), ('holdout', holdout, 'holdout')):
        body = {'schema': SCHEMA, 'set': 'holdout', 'role': role, 'families': fams}
        data = (json.dumps(body, indent=1) + '\n').encode()
        (FROZEN / (name + '.json')).write_bytes(data)
        files[name + '.json'] = _sha(data)
        for f in fams:
            key = '%s m%d k%d %s' % (name, f['m'], f['k'], f['class'])
            counts[key] = counts.get(key, 0) + 1
    dev_path = C1 / 'frozen' / 'development.json'
    manifest = {
        'schema': 'lrx-bound-c2-manifest-v1', 'task': 'bound-m-c2-260925',
        'development': {'path': str(dev_path.relative_to(ROOT)), 'sha256': c1_manifest['files']['development.json'],
                        'c1_manifest': str((C1 / 'frozen' / 'manifest.json').relative_to(ROOT)),
                        'c1_manifest_sha256': _sha((C1 / 'frozen' / 'manifest.json').read_bytes()),
                        'families': 303, 'screen': 30},
        'validation_source': {'c1_holdout_sha256': c1_manifest['files']['holdout.json'], 'filter': 'm == 11',
                              'records_identical': True},
        'seeds': {'holdout m12': SEED, 'holdout m11': SEED}, 'rng': "random.Random('260925:m<m>')",
        'files': files,
        'families': {'development': 303, 'validation': len(validation), 'holdout': len(holdout)},
        'per_m': {'validation': {'11': len(validation)}, 'holdout': {'11': len(m11), '12': len(m12)}},
        'counts': counts,
        'mask_flags': {'holdout': {'both_0_and_m': sum(f['bit0'] and f['bitm'] for f in holdout),
                                   'neither': sum(not f['bit0'] and not f['bitm'] for f in holdout)}},
        'stratification': 'm=12: k = 2..12, 15 per k, classes rev_rot 4, near_rev 3, refl 2, high_inv 3, uniform 2, '
                          'easy 1 (c1 m=11 counts; k = 13 has one mask and is not drawn). m=11 fresh: the same 15 '
                          'classes x4, shuffled, dealt over k = 2..12 as 6,6,6,6,6,5,5,5,5,5,5. Each k >= 2 stratum '
                          'forces one mask with bits 0 and m and (k <= m-1) one with neither; one plain reversal per m.',
        'disjoint': 'holdout disjoint from every c1 development, holdout and edge family on (labels, mask); '
                    'validation = c1 holdout m=11, disjoint from development (different m)',
        'protocol': 'development: engines and packets. validation: finalize only, to pick one finalist per '
                    '(arm, seed) among its accepted candidates; never in a packet, prompt or trainset. holdout: '
                    'evaluated once per frozen finalist after freeze, by the human-run finalize.'}
    (FROZEN / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    print(json.dumps({'files': files, 'families': manifest['families'], 'per_m': manifest['per_m'],
                      'manifest_sha256': _sha((FROZEN / 'manifest.json').read_bytes())}))


if __name__ == '__main__':
    main()
