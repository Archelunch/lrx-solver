#!/usr/bin/env python3
"""Audit saved resource certificates without an optimizer.

Every proof inequality uses Fraction arithmetic. Base words and independent
macro expansions are literally executed. Certified parameter orthants are
justified by the zero-stretch lemma, not by extrapolating the sampled lengths.
"""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import hashlib
from itertools import product
import json
from pathlib import Path
from random import Random
import time

from multiset_zero_projection import literal_step
from multiset_zero_stretch import certificate


def replay(state, word):
    for letter in word:
        state = literal_step(state, letter)
    return state


def stretch_literal(state, word, lengths):
    """Independent literal block macros and rotation-only cancellation."""
    atoms, source, j = [], [], 0
    for x in state:
        if x:
            atoms.append((x, 1)); source.append(x)
        else:
            atoms.append((0, lengths[j])); source.extend([0] * lengths[j]); j += 1
    atoms = tuple(atoms)
    output = []

    def emit(piece):
        for letter in piece:
            if output and (output[-1], letter) in (('L', 'R'), ('R', 'L')):
                output.pop()
            else:
                output.append(letter)

    for letter in word:
        if letter == 'L':
            emit('L' * atoms[0][1])
        elif letter == 'R':
            emit('R' * atoms[-1][1])
        elif atoms[0][0] == 0:
            assert atoms[1][0] != 0
            z = atoms[0][1] - 1
            emit('L' * z + 'X' + 'RX' * z)
        elif atoms[1][0] == 0:
            z = atoms[1][1] - 1
            emit('X' + 'LX' * z + 'R' * z)
        else:
            assert letter == 'X'
            emit('X')
        atoms = literal_step(atoms, letter)
    return tuple(source), ''.join(output)


def shorter_rotations(word, n):
    pieces, shift = [], 0
    for letter in word + '!':
        if letter == 'L':
            shift += 1
        elif letter == 'R':
            shift -= 1
        else:
            forward = shift % n
            pieces.append('L' * forward if forward <= n-forward else 'R' * (n-forward))
            if letter == 'X':
                pieces.append(letter)
            shift = 0
    return ''.join(pieces)


def rational_check(state, rows):
    m, k = max(state), state.count(0)
    weights = [Fraction(row['weight']) for row in rows]
    assert weights and all(x >= 0 for x in weights) and sum(weights) == 1
    mean_base, mean_beta, data = Fraction(0), [Fraction(0)] * k, []
    for weight, row in zip(weights, rows):
        c = certificate(state, row['word'])
        assert replay(state, row['word']) == tuple(range(1, m+1)) + (0,) * k
        assert c['base_cost'] == row['base_cost'] and c['beta'] == tuple(row['beta'])
        base, beta, used = Fraction(c['base_cost']), list(map(Fraction, c['beta'])), set()
        for flip in row.get('flips', []):
            gap, probability = flip['gap'], Fraction(flip['probability'])
            assert gap not in used and 0 <= probability <= 1
            used.add(gap)
            constant, coefficients = c['gaps'][gap]
            assert abs(constant) < len(state) and all(abs(x) <= 1 for x in coefficients)
            base += probability * (len(state) - 2*abs(constant))
            for j, v in enumerate(coefficients):
                beta[j] += probability * (1-2*abs(v))
        mean_base += weight * base
        mean_beta = [a + weight*b for a, b in zip(mean_beta, beta)]
        data.append(c)
    target = (m-2)*len(state)-(m*m-3*m-4)//2
    assert mean_base < target+1 and all(x <= m-2 for x in mean_beta)
    return mean_base, tuple(mean_beta), data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', action='append', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert __debug__
    if args.output.exists():
        raise FileExistsError(args.output)
    started, counts, rng = time.monotonic(), Counter(), Random(2026092302)
    cases, supplied, fingerprints = {}, set(), {}
    for path in args.input:
        report = json.loads(path.read_text())
        assert report['status'] == 'COMPLETE_FINITE_SEARCH'
        for name, expected in report['source_sha256'].items():
            assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected, name
            fingerprints[name] = expected
        assert report['counts']['cases'] == len(report['cases'])
        assert report['counts']['certified'] == sum(c['result']['certified'] for c in report['cases'])
        for case in report['cases']:
            state = tuple(case['state'])
            supplied.add(state)
            if case['result']['certified']:
                if state not in cases or len(case['result']['rows']) < len(cases[state]['result']['rows']):
                    cases[state] = case
        fingerprints[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    checked_words = set()
    by_blocks = Counter()
    prefix_rows = []

    def literal_check(state, row, cert, lengths):
        source, word = stretch_literal(state, row['word'], lengths)
        price = cert['base_cost'] + sum(b*(l-1) for b, l in zip(cert['beta'], lengths))
        assert len(word) == price
        goal = tuple(range(1, 9)) + (0,) * sum(lengths)
        assert replay(source, word) == goal
        shorter = shorter_rotations(word, len(source))
        assert len(shorter) <= len(word) and replay(source, shorter) == goal
        counts['literal_expanded_words'] += 2
        counts['literal_expanded_letters'] += len(word) + len(shorter)
        return len(shorter)

    for state, case in sorted(cases.items()):
        k = state.count(0)
        assert sorted(x for x in state if x) == list(range(1, 9))
        rows = case['result']['rows']
        base, beta, certs = rational_check(state, rows)
        by_blocks[k] += 1
        counts['exact_rational_certificates'] += 1
        for row, cert in zip(rows, certs):
            key = state, row['word']
            if key in checked_words:
                continue
            checked_words.add(key)
            # Each independent slope is witnessed directly in the literal macros.
            for j in range(k):
                lengths = [1] * k; lengths[j] = 2
                literal_check(state, row, cert, lengths)
                counts['independent_slope_checks'] += 1
        configurations = [[1] * k, [rng.randrange(1, 8) for _ in range(k)]]
        prefix = state == tuple(x for label in range(8, 0, -1)
                               for x in ((label, 0) if label > 8-k else (label,)))
        if prefix and k in (6, 7, 8):
            configurations += list(product((1, 2), repeat=k))
            configurations += [[rng.randrange(1, 25) for _ in range(k)] for _ in range(50)]
            prefix_rows.append(dict(state=state, rows=rows, mean_base=str(base),
                                    mean_beta=list(map(str, beta)), certificates=certs))
        for lengths in configurations:
            prices = [literal_check(state, row, cert, lengths) for row, cert in zip(rows, certs)]
            average = sum(Fraction(row['weight'])*p for row, p in zip(rows, prices))
            affine = base + sum(b*(l-1) for b, l in zip(beta, lengths))
            target = 6*(8+sum(lengths))-18
            assert min(prices) <= target and average <= affine < target+1
            counts['tested_length_vectors'] += 1
        huge = [10**100+j for j in range(k)]
        assert base + sum(b*(l-1) for b, l in zip(beta, huge)) < 6*(8+sum(huge))-17
        counts['huge_symbolic_inequalities'] += 1

    assert len(prefix_rows) == 3
    for example in prefix_rows:
        state = tuple(example['state'])
        for mutation in ('weight', 'word', 'base'):
            bad = deepcopy(example['rows'])
            if mutation == 'weight':
                bad[0]['weight'] = str(Fraction(bad[0]['weight'])+1)
            elif mutation == 'word':
                bad[0]['word'] += 'X'
            else:
                bad[0]['base_cost'] += 1
            try:
                rational_check(state, bad)
            except AssertionError:
                counts['rejected_negative_controls'] += 1
            else:
                raise AssertionError('corrupt certificate was accepted')

    for p in (Path(__file__), Path('scripts/multiset_zero_projection.py'),
              Path('scripts/multiset_zero_stretch.py')):
        fingerprints[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    result = dict(status='PASS', supplied_distinct_states=len(supplied),
                  certified_distinct_states=len(cases), unresolved_in_supplied=len(supplied)-len(cases),
                  counts=dict(counts), certified_by_blocks=dict(sorted(by_blocks.items())),
                  prefix_families=prefix_rows, full_conjecture_proved=False,
                  all_reverse_orders_proved=len(supplied) == len(cases) == 4088,
                  source_sha256=fingerprints, seconds=time.monotonic()-started)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
    print(dict(status='PASS', counts=dict(counts), certified=len(cases),
               unresolved=result['unresolved_in_supplied'], seconds=result['seconds']), flush=True)


if __name__ == '__main__':
    main()
