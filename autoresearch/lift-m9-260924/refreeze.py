"""Merge the tree stratum into the v1 parent lists and regenerate
development.json/holdout.json/manifest.json. Stdlib only.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FROZEN = os.path.join(HERE, 'frozen')
sys.path.insert(0, ROOT)

from integrations import lift_task as LT  # noqa: E402


def sha256_path(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    raw = json.load(open(os.path.join(FROZEN, 'parents_raw.v1.json')))
    dev_v1 = json.load(open(os.path.join(FROZEN, 'development.v1.json')))
    hold_v1 = json.load(open(os.path.join(FROZEN, 'holdout.v1.json')))
    tree = json.load(open(os.path.join(FROZEN, 'tree_stratum.json')))

    # recover the 200/100 parent objects from parents_raw.v1 using the ids
    # already present in the v1 instance files (unique per parent)
    def parent_ids_from_instances(doc):
        return sorted({inst['parent']['id'] for inst in doc['instances']})

    dev_ids = set(parent_ids_from_instances(dev_v1))
    hold_ids = set(parent_ids_from_instances(hold_v1))
    by_id = {f['id']: f for f in raw['families']}
    dev_parents = [by_id[i] for i in sorted(dev_ids)]
    hold_parents = [by_id[i] for i in sorted(hold_ids)]
    assert len(dev_parents) == 200 and len(hold_parents) == 100

    dev_parents = dev_parents + tree['dev_new']
    hold_parents = hold_parents + tree['hold_new']
    assert len(dev_parents) == 210 and len(hold_parents) == 105

    dev_ids2 = {(tuple(f['labels']), f['mask']) for f in dev_parents}
    hold_ids2 = {(tuple(f['labels']), f['mask']) for f in hold_parents}
    assert len(dev_ids2) == 210 and len(hold_ids2) == 105
    assert not (dev_ids2 & hold_ids2)

    def instances_for(parent_list, set_name):
        insts = []
        for p in parent_list:
            insts.extend(LT.build_instances(p))
        return dict(schema='lrx-lift-instances-v1', set=set_name, instances=insts)

    dev_doc = instances_for(dev_parents, 'development')
    hold_doc = instances_for(hold_parents, 'holdout')
    print('dev instances', len(dev_doc['instances']), 'holdout instances', len(hold_doc['instances']))

    with open(os.path.join(FROZEN, 'development.json'), 'w') as fh:
        json.dump(dev_doc, fh, indent=1, sort_keys=True)
    with open(os.path.join(FROZEN, 'holdout.json'), 'w') as fh:
        json.dump(hold_doc, fh, indent=1, sort_keys=True)

    all_parents_raw = raw['families'] + tree['dev_new'] + tree['hold_new']
    with open(os.path.join(FROZEN, 'parents_raw.json'), 'w') as fh:
        json.dump(dict(seed=raw['seed'], count=len(all_parents_raw), families=all_parents_raw), fh)

    counts_per_k = {}
    for f in dev_parents + hold_parents:
        counts_per_k.setdefault(f['k'], {}).setdefault(f['route'], 0)
        counts_per_k[f['k']][f['route']] += 1

    manifest = dict(
        seed=raw['seed'], m_parent=8, m_child=9,
        development_parents=len(dev_parents), holdout_parents=len(hold_parents),
        development_instances=len(dev_doc['instances']), holdout_instances=len(hold_doc['instances']),
        counts_per_k=counts_per_k,
        routes_included=['direct_mixture', 'projection_from_N', 'direct_tree', 'reverse_tree_transfer'],
        tree_stratum_note=('15 tree-route parents added on top of the 300 mixture-route parents '
                            '(10 -> development, 5 -> holdout): 7 direct_tree, 8 reverse_tree_transfer. '
                            'Their certificate.kind is "tree" with weights_placeholder=true and every '
                            'row weight forced to "0": the evaluator solves its own exact LP over the '
                            'words the candidate program returns (parent weights are never used by '
                            'scoring), so these stored weights carry no information and must not be '
                            'read as real mixture coefficients. Only unit-origin (all-1 block length) '
                            'leaf rows are included, since only those are literal words that sort the '
                            'parent UNIT base directly; non-unit-origin leaf rows were used to verify '
                            'criterion (8) here but are not emitted.'),
        v1_note='development.v1.json / holdout.v1.json / manifest.v1.json / parents_raw.v1.json are the pre-tree-stratum freeze, kept for the record.',
        files={name: sha256_path(os.path.join(FROZEN, name)) for name in
               ('development.json', 'holdout.json', 'parents_raw.json')},
    )
    with open(os.path.join(FROZEN, 'manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    print(json.dumps(manifest, indent=1))


if __name__ == '__main__':
    main()
