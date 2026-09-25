"""Split the 300 sampled parents into 200 dev / 100 holdout (disjoint on
(labels, mask)) and enumerate every lift instance via integrations.lift_task
(the evaluator's own instance builder), writing development.json/holdout.json
in the schema TASK.md's "Schema decisions" section specifies.
"""
import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FROZEN = os.path.join(HERE, 'frozen')
sys.path.insert(0, ROOT)

from integrations import lift_task as LT  # noqa: E402
from integrations import lrx_m as C  # noqa: E402

SEED = 20260924


def sha256_path(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    raw = json.load(open(os.path.join(FROZEN, 'parents_raw.json')))
    families = raw['families']
    assert len(families) == len(set((tuple(f['labels']), f['mask']) for f in families)), 'duplicate parent'

    rng = random.Random(SEED)
    by_stratum = {}
    for f in families:
        by_stratum.setdefault((f['k'], f['route'].split('_from_')[0]), []).append(f)
    dev, holdout = [], []
    for key in sorted(by_stratum):
        group = by_stratum[key][:]
        rng.shuffle(group)
        n_hold = max(1, round(len(group) / 3)) if len(group) >= 3 else (1 if len(group) > 1 else 0)
        holdout.extend(group[:n_hold])
        dev.extend(group[n_hold:])
    rng.shuffle(dev)
    rng.shuffle(holdout)
    print('dev %d holdout %d (target 200/100)' % (len(dev), len(holdout)))

    # trim/pad to exactly 200/100 while keeping disjointness and stratum spread
    if len(dev) > 200:
        holdout.extend(dev[200:])
        dev = dev[:200]
    if len(holdout) > 100:
        dev.extend(holdout[100:])
        holdout = holdout[:100]
    dev.sort(key=lambda f: f['id'])
    holdout.sort(key=lambda f: f['id'])
    print('final dev %d holdout %d' % (len(dev), len(holdout)))

    dev_ids = {(tuple(f['labels']), f['mask']) for f in dev}
    hold_ids = {(tuple(f['labels']), f['mask']) for f in holdout}
    assert not (dev_ids & hold_ids), 'dev/holdout overlap'

    def instances_for(parent_list, set_name):
        insts = []
        for p in parent_list:
            insts.extend(LT.build_instances(p))
        return dict(schema='lrx-lift-instances-v1', set=set_name, instances=insts)

    dev_doc = instances_for(dev, 'development')
    hold_doc = instances_for(holdout, 'holdout')
    print('dev instances %d, holdout instances %d' % (len(dev_doc['instances']), len(hold_doc['instances'])))

    dev_path = os.path.join(FROZEN, 'development.json')
    hold_path = os.path.join(FROZEN, 'holdout.json')
    with open(dev_path, 'w') as fh:
        json.dump(dev_doc, fh, indent=1, sort_keys=True)
    with open(hold_path, 'w') as fh:
        json.dump(hold_doc, fh, indent=1, sort_keys=True)

    counts_per_k = {}
    for f in dev + holdout:
        counts_per_k.setdefault(f['k'], {}).setdefault(f['route'], 0)
        counts_per_k[f['k']][f['route']] += 1

    manifest = dict(
        seed=SEED,
        m_parent=8, m_child=9,
        development_parents=len(dev), holdout_parents=len(holdout),
        development_instances=len(dev_doc['instances']), holdout_instances=len(hold_doc['instances']),
        counts_per_k=counts_per_k,
        routes_included=['direct_mixture', 'projection_from_N'],
        routes_excluded=['direct_tree', 'reverse_tree_transfer'],
        routes_excluded_reason=('integrations/lift_task.check_instance and integrations/lift_evaluator.py '
                                 'read parent.certificate.rows as a flat list unconditionally; tree/leaf '
                                 'certificates cannot be flattened into one mixture without losing their '
                                 'per-box conditional weights, so they are not evaluator-usable yet.'),
        files={name: sha256_path(os.path.join(FROZEN, name)) for name in
               ('development.json', 'holdout.json', 'parents_raw.json')
               if os.path.exists(os.path.join(FROZEN, name))},
    )
    with open(os.path.join(FROZEN, 'manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    print(json.dumps(manifest, indent=1))


if __name__ == '__main__':
    main()
