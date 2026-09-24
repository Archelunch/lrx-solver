#!/usr/bin/env python3
"""Verify all 4088 reverse-circle m=8 bases, independently of search.

Only exact rational arithmetic and explicit sorting words are proof inputs.
The standalone bundle does not require a solver, generator binary, previous
three-block theorem, or saved distance table. Literal tests corroborate the
implementation; the unbounded conclusion uses the affine-box inequalities.
"""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from random import Random
import sys
import time

from audit_multiset_projected_certificates import replay, stretch_literal
from multiset_box_certificate import verify_tree
from multiset_circle_materialization import materialize_circle_rows
from multiset_zero_stretch import certificate


def universe():
    result = set()
    for first in range(1, 9):
        labels = [1+(first-1-j) % 8 for j in range(8)]
        for mask in range(1, 1 << 9):
            state = []
            for j in range(9):
                if mask & (1 << j):
                    state.append(0)
                if j < 8:
                    state.append(labels[j])
            result.add(tuple(state))
    assert len(result) == 4088
    return result


def expand(base, lengths):
    result, j = [], 0
    for x in base:
        if x:
            result.append(x)
        else:
            result.extend([0]*lengths[j]); j += 1
    assert j == len(lengths)
    return tuple(result)


def tree_size(node):
    if node['kind'] == 'split':
        return 1 + tree_size(node['left']) + tree_size(node['right'])
    assert node['kind'] == 'affine'
    return 1 + len(node['rows'])


def check_leaf(base, rows, lower, upper):
    """A second exact verifier, independent of verify_leaf/row_profile."""
    k = base.count(0)
    total, mean, slopes, profiles = Fraction(0), Fraction(0), [Fraction(0)]*k, []
    assert rows
    for row in rows:
        weight = Fraction(row['weight']); assert weight >= 0; total += weight
        origin, picks = row['origin'], row['picks']
        assert len(origin) == len(picks) == k
        assert all(type(o) is int and 1 <= o <= lo for o, lo in zip(origin, lower))
        refined = expand(base, origin)
        word = row['word']; assert set(word) <= set('LRX')
        goal = tuple(range(1, 9)) + (0,)*sum(origin)
        assert replay(refined, word) == goal
        c = certificate(refined, word)
        assert type(row['base_cost']) is int and len(word) == c['base_cost'] == row['base_cost']
        selected, start = [], 0
        for o, pick in zip(origin, picks):
            assert type(pick) is int and start <= pick < start+o
            selected.append(c['beta'][pick]); start += o
        assert list(row['beta']) == selected
        mean += weight * (len(word) + sum(b*(lo-o) for b, lo, o in zip(selected, lower, origin)))
        slopes = [a+weight*b for a, b in zip(slopes, selected)]
        profiles.append((refined, c))
    assert total == 1
    worst = mean - (30 + 6*sum(lower))
    for slope, lo, hi in zip(slopes, lower, upper):
        if hi is None:
            assert slope <= 6
        else:
            assert type(hi) is int and hi >= lo
            worst += max(Fraction(0), (slope-6)*(hi-lo))
    assert worst < 1
    return profiles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', action='append', type=Path, default=[])
    parser.add_argument('--bundle-input', type=Path)
    parser.add_argument('--bundle-output', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert __debug__ and bool(args.input) != bool(args.bundle_input)
    for path in (args.output, args.bundle_output):
        if path is not None and path.exists():
            raise FileExistsError(path)
    started, counts, rng, families, origins = time.monotonic(), Counter(), Random(2026092304), {}, {}
    inputs = args.input if args.input else [args.bundle_input]
    if args.bundle_input:
        data = json.loads(args.bundle_input.read_text())
        assert data['format'] == 'lrx_reverse_m8_box_v1' and data['m'] == 8
        for row in data['families']:
            base = tuple(row['base']); assert base not in families
            families[base] = row['tree']; origins[base] = str(args.bundle_input)
    else:
        for path in args.input:
            data = json.loads(path.read_text())
            assert data['status'] in ('COMPLETE_FINITE_SEARCH', 'COMPLETE_CELL_SEARCH')
            assert data['counts']['cases'] == len(data['cases'])
            assert data['counts']['certified'] == sum(c['result']['certified'] for c in data['cases'])
            for case in data['cases']:
                result = case['result']
                if not result['certified']:
                    continue
                base = tuple(case['state']); k = base.count(0)
                if 'tree' in result:
                    tree = result['tree']
                else:
                    rows = materialize_circle_rows(base, result['rows'])
                    tree = dict(kind='affine', rows=[dict(r, origin=[1]*k, picks=list(range(k))) for r in rows])
                if base not in families or tree_size(tree) < tree_size(families[base]):
                    families[base] = tree; origins[base] = str(path)
    expected = universe()
    assert set(families) == expected, dict(missing=sorted(expected-set(families)), extra=sorted(set(families)-expected))
    by_blocks, checked_words, negative_example = Counter(), set(), None

    def literal_check(base, row, lengths):
        refined = expand(base, row['origin'])
        atom_lengths = [1]*sum(row['origin'])
        for pick, length, origin in zip(row['picks'], lengths, row['origin']):
            assert length >= origin
            atom_lengths[pick] += length-origin
        source, word = stretch_literal(refined, row['word'], atom_lengths)
        assert source == expand(base, lengths)
        price = row['base_cost'] + sum(b*(length-origin)
                    for b, length, origin in zip(row['beta'], lengths, row['origin']))
        assert len(word) == price
        assert replay(source, word) == tuple(range(1, 9))+(0,)*sum(lengths)
        counts['literal_words'] += 1; counts['literal_letters'] += len(word)
        return price

    for base, tree in sorted(families.items()):
        k = base.count(0); by_blocks[k] += 1
        reference = verify_tree(base, tree)
        local = Counter()

        def visit(node, lower, upper, depth):
            nonlocal negative_example
            local['nodes'] += 1
            counts['max_depth'] = max(counts['max_depth'], depth)
            assert depth <= 64
            if node['kind'] == 'split':
                axis, cut = node['axis'], node['cut']
                assert type(axis) is int and 0 <= axis < k
                assert type(cut) is int and lower[axis] <= cut
                assert upper[axis] is None or cut < upper[axis]
                left, right = list(upper), list(lower); left[axis] = cut; right[axis] = cut+1
                visit(node['left'], lower, left, depth+1)
                visit(node['right'], right, upper, depth+1)
                local['splits'] += 1
                return
            assert node['kind'] == 'affine'
            rows = node['rows']; check_leaf(base, rows, lower, upper)
            local['leaves'] += 1; local['words'] += len(rows)
            if negative_example is None:
                negative_example = base, rows, lower, upper
            for row in rows:
                key = (base, tuple(row['origin']), tuple(row['picks']), row['word'])
                if key in checked_words:
                    continue
                checked_words.add(key)
                for j in range(k):
                    lengths = list(row['origin']); lengths[j] += 1
                    literal_check(base, row, lengths)
                    counts['independent_slope_checks'] += 1
                counts['refined_word_profiles'] += any(x > 1 for x in row['origin'])
            configurations = [lower]
            configurations.append([rng.randint(lo, hi) if hi is not None else lo+rng.randrange(8)
                                   for lo, hi in zip(lower, upper)])
            for lengths in configurations:
                prices = [literal_check(base, row, lengths) for row in rows]
                average = sum(Fraction(row['weight'])*price for row, price in zip(rows, prices))
                target = 30 + 6*sum(lengths)
                assert min(prices) <= target and average < target+1
                counts['leaf_length_vectors'] += 1

        visit(tree, [1]*k, [None]*k, 0)
        for key in ('nodes', 'leaves', 'words'):
            assert local[key] == reference[key]
        assert local['splits'] == reference.get('splits', 0)
        counts.update(local); counts['families'] += 1

    base, rows, lower, upper = negative_example
    for mutation in ('word', 'weight', 'base_cost'):
        bad = deepcopy(rows)
        if mutation == 'word': bad[0]['word'] += 'X'
        elif mutation == 'weight': bad[0]['weight'] = str(Fraction(bad[0]['weight'])+1)
        else: bad[0]['base_cost'] += 1
        try:
            check_leaf(base, bad, lower, upper)
        except AssertionError:
            counts['rejected_negative_controls'] += 1
        else:
            raise AssertionError('corrupted certificate accepted')
    assert not any(name == 'scipy' or name.startswith('scipy.') for name in sys.modules)
    bundle = dict(format='lrx_reverse_m8_box_v1', m=8,
                  families=[dict(base=list(base), tree=tree) for base, tree in sorted(families.items())],
                  full_conjecture_proved=False)
    if args.bundle_output:
        with args.bundle_output.open('x') as stream:
            json.dump(bundle, stream, separators=(',', ':'))
    verifiers = ('audit_multiset_projected_certificates.py', 'multiset_zero_projection.py',
                 'multiset_zero_stretch.py', 'multiset_free_phase.py',
                 'multiset_box_certificate.py', 'multiset_circle_materialization.py')
    paths = [Path(__file__)] + inputs + [Path('scripts') / name for name in verifiers]
    if args.bundle_output: paths.append(args.bundle_output)
    report = dict(status='PASS', counts=dict(counts), families_by_blocks=dict(sorted(by_blocks.items())),
                  expected_bases=4088, checked_bases=len(families), missing_bases=[],
                  reverse_m8_theorem_proved=True, full_conjecture_proved=False,
                  optimizer_imported=False, literal_tests_do_not_replace_affine_proof=True,
                  source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                  seconds=time.monotonic()-started)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
    print(dict(status='PASS', counts=dict(counts), seconds=report['seconds']), flush=True)


if __name__ == '__main__':
    main()
