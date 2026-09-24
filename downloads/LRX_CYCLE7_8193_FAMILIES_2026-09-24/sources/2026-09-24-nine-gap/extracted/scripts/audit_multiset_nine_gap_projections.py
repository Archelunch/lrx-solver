#!/usr/bin/env python3
"""Recheck every projected word cost and all exact projected inequalities."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from math import lcm
from pathlib import Path
import subprocess
import time

import numpy as np
from audit_multiset_nine_gap_cover import geometry, inversions, ranks, state_for, universe, zero_crossings
from multiset_bruhat_transfer import clause_bitsets, tree_domain
from multiset_zero_stretch import certificate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', type=Path, default=Path('literature/multiset_nine_gap_complete_certificates_20260924.json'))
    parser.add_argument('--search', type=Path, default=Path('literature/multiset_nine_gap_projection_search_20260924.json'))
    parser.add_argument('--reverse-bundle', type=Path, default=Path('literature/multiset_reverse_m8_complete_certificates_20260923.json'))
    parser.add_argument('--binary', type=Path, default=Path('/tmp/lrx_verify_projection_table_20260924'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert __debug__
    if args.output.exists():
        raise FileExistsError(args.output)
    started, counts = time.monotonic(), Counter()
    bundle, search = json.loads(args.bundle.read_text()), json.loads(args.search.read_text())
    universe(bundle['records'])
    table_path = args.search.with_suffix('.npz')
    with np.load(table_path) as archive:
        costs = archive['base_costs'].astype(np.int64)
        claimed = archive['directly_covered']
        claimed_union = archive['union_covered']
    catalog = bundle['catalog']
    assert costs.shape == (len(catalog), 512) and claimed.shape == claimed_union.shape == (40320, 512)
    infos = []
    with subprocess.Popen([str(args.binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, bufsize=1) as process:
        for i, source in enumerate(catalog):
            process.stdin.write(','.join(map(str, source['state']))+'|'+source['word']+'|'+','.join(map(str, costs[i]))+'\n')
            process.stdin.flush()
            result = process.stdout.readline().strip()
            if result != 'PASS 511':
                raise RuntimeError('Independent projection check failed: '+process.stderr.read())
            c = certificate(tuple(source['state']), source['word'])
            finish, _ = geometry(17, source['word'])
            infos.append((c, finish))
            counts['independent_projected_words'] += 511
            if (i+1) % 1000 == 0:
                print(dict(source_words=i+1, seconds=time.monotonic()-started), flush=True)
        process.stdin.close(); assert process.wait() == 0
    sizes = np.asarray([mask.bit_count() for mask in range(512)], dtype=np.int64)
    erased = np.asarray([[not (mask >> j & 1) for mask in range(512)] for j in range(9)], dtype=np.int64)
    original_x = np.asarray([c['x_count'] for c, _ in infos], dtype=np.int64)
    original_zero_swaps = np.asarray([c['zero_swaps'] for c, _ in infos], dtype=np.int64)
    rotation_cost = costs-original_x[:, None]+original_zero_swaps @ erased
    assert np.min(rotation_cost[:, 1:]) >= 0
    checked = np.zeros((40320, 512), dtype=bool)
    max_cost = int(costs.max())
    for record in bundle['records']:
        state, index = state_for(record['labels']), record['order_index']
        weights = [Fraction(row['weight']) for row in record['mixture']]
        denominator = lcm(*(w.denominator for w in weights))
        nums = [int(w*denominator) for w in weights]
        assert min(nums) > 0 and sum(nums) == denominator
        assert denominator*(max_cost+400) < 2**62
        total_rotation = np.zeros(512, dtype=np.int64)
        mean_inv, mean_zero = 0, np.zeros(9, dtype=np.int64)
        pure = []
        for row, num in zip(record['mixture'], nums):
            source, cut = row['source'], row['cut']
            c, finish = infos[source]
            p = ranks(state, cut, finish)
            inv, sigma = inversions(p), zero_crossings(p, state, cut)
            total_rotation += num*rotation_cost[source]
            mean_inv += num*inv
            mean_zero += num*np.asarray(sigma, dtype=np.int64)
            pure.append((source, inv, sigma))
        exact_price = total_rotation+mean_inv-mean_zero @ erased
        result = exact_price < denominator*(31+6*sizes)
        result[0] = False
        assert np.array_equal(result, claimed[index])
        checked[index] = result
        if index % 4096 == 0:
            for mask in range(1, 512):
                value = Fraction(0)
                for w, (source, inv, sigma) in zip(weights, pure):
                    removed_inv = sum(sigma[j] for j in range(9) if not (mask >> j & 1))
                    value += w*(int(rotation_cost[source, mask])+inv-removed_inv)
                assert value*denominator == int(exact_price[mask])
                counts['scalar_fraction_cross_checks'] += 1
        counts['projected_family_inequalities'] += 511
        if counts['projected_family_inequalities'] % (5000*511) == 0:
            print(dict(orders=counts['projected_family_inequalities']//511, seconds=time.monotonic()-started), flush=True)
    union = checked.copy()
    union[:, (sizes > 0) & (sizes <= 3)] = True
    orders, bits = clause_bitsets(8); all_bits = (1 << len(orders))-1
    reverse = json.loads(args.reverse_bundle.read_text())
    for family in reverse['families']:
        base = tuple(family['base']); named = mask = 0
        for x in base:
            if x:
                named += 1
            else:
                mask |= 1 << named
        domain = tree_domain(base, family['tree'], bits, all_bits)
        union[:, mask] |= np.unpackbits(np.frombuffer(domain.to_bytes(5040, 'little'), dtype=np.uint8), bitorder='little').astype(bool)
    assert np.array_equal(union, claimed_union)
    assert int((~union[:, 1:]).sum()) == search['remaining'] == 4495529
    source = catalog[0]; wrong = costs[0].copy(); wrong[1] += 1
    line = ','.join(map(str, source['state']))+'|'+source['word']+'|'+','.join(map(str, wrong))+'\n'
    result = subprocess.run([str(args.binary)], input=line, text=True, capture_output=True)
    assert result.returncode != 0 and 'Wrong projected word cost' in result.stderr
    counts['negative_controls_rejected'] += 1
    paths = [Path(__file__), args.bundle, args.search, table_path, args.reverse_bundle, args.binary,
        Path('scripts/verify_multiset_projection_table.cpp'), Path('scripts/audit_multiset_nine_gap_cover.py'),
        Path('scripts/multiset_zero_stretch.py'), Path('scripts/multiset_bruhat_transfer.py')]
    report = dict(status='PASS', counts=dict(counts),
        direct_families=int(checked[:, 1:].sum()), union_families=int(union[:, 1:].sum()),
        remaining=int((~union[:, 1:]).sum()), full_m8_proved=False, full_conjecture_proved=False,
        source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        seconds=time.monotonic()-started)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
    print(dict(status='PASS', counts=dict(counts), direct=report['direct_families'], union=report['union_families'],
               remaining=report['remaining'], seconds=report['seconds']), flush=True)


if __name__ == '__main__':
    main()
