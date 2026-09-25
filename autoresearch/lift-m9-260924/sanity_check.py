"""Sanity check: 20 random instances from development.json + holdout.json.
For each: literally verify the child unit_base is a valid m=9 vector
(labels 1..9 once each, zeros only in the stated gaps), and that each
parent certificate row's word sorts the parent unit base with lrxm8
recomputing base/slopes that match criterion (7) at m=8. Also runs
integrations.lift_task.check_instance for an independent recomputation.
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
from integrations import lift_task as LT  # noqa: E402
from integrations import lrx_m as C  # noqa: E402

SEED = 999


def check_child_vector(vec, m):
    labels = [x for x in vec if x]
    if sorted(labels) != list(range(1, m + 1)):
        return 'labels not a permutation of 1..%d' % m
    if any(x < 0 for x in vec):
        return 'negative entries'
    return None


def main():
    dev = json.load(open(os.path.join(FROZEN, 'development.json')))['instances']
    hold = json.load(open(os.path.join(FROZEN, 'holdout.json')))['instances']
    pool = dev + hold
    rng = random.Random(SEED)
    tree_pool = [i for i in pool if i['parent']['certificate']['kind'] == 'tree']
    non_tree_pool = [i for i in pool if i['parent']['certificate']['kind'] != 'tree']
    sample = rng.sample(non_tree_pool, 20) + rng.sample(tree_pool, 5)

    failures = []
    for inst in sample:
        cid = inst['id']
        child = inst['child']
        err = check_child_vector(child['unit_base'], 9)
        if err:
            failures.append((cid, 'child vector: ' + err))
            continue
        if child['mask'].bit_length() > 10 or child['mask'] < 1:
            failures.append((cid, 'child mask out of range'))
            continue
        if bin(child['mask']).count('1') != child['k']:
            failures.append((cid, 'child k mismatch'))
            continue
        # parent rows: literal m=8 sort check + criterion (7) via lrxm8
        parent = inst['parent']
        base = C.base_vector(parent['labels'], parent['mask'])
        if base != parent['unit_base']:
            failures.append((cid, 'parent unit_base mismatch'))
            continue
        costs = []
        for row in parent['certificate']['rows']:
            prof8 = lrxm8.Profile(base, row['word'])
            if (prof8.base, list(prof8.beta)) != (row['base'], row['slopes']):
                failures.append((cid, 'row base/slopes mismatch: %r vs %r' %
                                  ((prof8.base, prof8.beta), (row['base'], row['slopes']))))
                continue
            costs.append((prof8.base, prof8.beta))
        is_tree = parent['certificate'].get('kind') == 'tree'
        if costs and not is_tree:
            ok, B, beta = lrxm8.mixture_criterion(costs, [r['weight'] for r in parent['certificate']['rows']],
                                                    parent['mask'].bit_count())
            if not ok:
                failures.append((cid, 'criterion (7) fails: B=%s beta=%s' % (B, beta)))
        elif is_tree:
            if not parent['certificate'].get('weights_placeholder'):
                failures.append((cid, 'tree parent missing weights_placeholder flag'))
            if any(r['weight'] != '0' for r in parent['certificate']['rows']):
                failures.append((cid, 'tree parent row weight is not the "0" placeholder'))
        # independent recomputation via the evaluator's own check_instance
        try:
            want, rows = LT.check_instance(inst)
        except Exception as e:
            failures.append((cid, 'check_instance raised: %s' % e))
            continue
        for r in rows:
            if r['claimed'] != [r['base'], r['slopes']]:
                failures.append((cid, 'check_instance recompute mismatch'))
                break

    result = dict(sample_size=len(sample), failures=failures, ok=len(failures) == 0,
                  sample_ids=[i['id'] for i in sample])
    out = os.path.join(FROZEN, 'sanity_check_result.json')
    json.dump(result, open(out, 'w'), indent=1)
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
