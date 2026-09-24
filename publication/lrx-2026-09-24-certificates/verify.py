#!/usr/bin/env python3
"""Portable, standard-library LRX certificate checker. Run beside certificates.json.

Reads JSON data only. No repository imports, candidate code, network, or API access.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def state_for(labels, mask):
    state = []
    for gap in range(9):
        if (mask >> gap) & 1:
            state.append(0)
        if gap < 8:
            state.append(labels[gap])
    return state


def replay(state, word):
    state = list(state)
    for letter in word:
        if letter == 'L':
            state = state[1:] + state[:1]
        elif letter == 'R':
            state = state[-1:] + state[:-1]
        elif letter == 'X':
            state[0], state[1] = state[1], state[0]
        else:
            raise ValueError('letter outside LRX')
    return state


def price(state, word):
    """Compute boundary-adjusted rotation-gap resources from the unit word."""
    atoms = []
    zero = 0
    for value in state:
        if value == 0:
            zero += 1
            atoms.append(-zero)
        else:
            atoms.append(value)
    count = len(atoms)
    at = 0
    swaps = [0] * zero
    gap = [0] * (zero + 1)
    gaps = []
    swap_count = 0
    for letter in word:
        if letter in 'LR':
            direction = 1 if letter == 'L' else -1
            carried = atoms[at if direction == 1 else (at - 1) % count]
            gap[0] += direction
            if carried < 0:
                gap[-carried] += direction
            at = (at + direction) % count
        elif letter == 'X':
            left, right = at, (at + 1) % count
            a, b = atoms[left], atoms[right]
            if a < 0 and b < 0:
                raise ValueError('zero-zero swap in a direct word')
            if a < 0:
                swaps[-a - 1] += 1
                gap[-a] += 1  # left block: macro prefix joins this gap
            elif b < 0:
                swaps[-b - 1] += 1
            gaps.append(gap)
            gap = [0] * (zero + 1)
            if b < 0:
                gap[-b] -= 1  # right block: macro suffix joins next gap
            atoms[left], atoms[right] = b, a
            swap_count += 1
        else:
            raise ValueError('letter outside LRX')
    gaps.append(gap)  # includes the terminal gap after the last X
    base = swap_count + sum(abs(g[0]) for g in gaps)
    beta = [2 * swaps[j] + sum(abs(g[j + 1]) for g in gaps)
            for j in range(zero)]
    if base != len(word):
        raise ValueError('unit rotations not reduced')
    return base, beta


def lift(state, word, lengths):
    """Literal atomic zero-block macro expansion, independently replayed."""
    atoms = []
    start = []
    zeros = iter(lengths)
    for value in state:
        width = 1 if value else next(zeros)
        atoms.append((value, width))
        start.extend([value] * width)
    parts = []
    for letter in word:
        if letter == 'L':
            parts.append('L' * atoms[0][1])
            atoms = atoms[1:] + atoms[:1]
        elif letter == 'R':
            parts.append('R' * atoms[-1][1])
            atoms = atoms[-1:] + atoms[:-1]
        elif letter == 'X':
            left, right = atoms[:2]
            if left[0] == right[0] == 0:
                raise ValueError('zero-zero macro')
            if left[0] == 0:
                q = left[1] - 1
                parts.extend(('L' * q, 'X', 'RX' * q))
            elif right[0] == 0:
                q = right[1] - 1
                parts.extend(('X', 'LX' * q, 'R' * q))
            else:
                parts.append('X')
            atoms[0], atoms[1] = right, left
        else:
            raise ValueError('letter outside LRX')
    reduced = []
    for letter in ''.join(parts):
        if reduced and (reduced[-1], letter) in (('L', 'R'), ('R', 'L')):
            reduced.pop()
        else:
            reduced.append(letter)
    if replay(start, reduced) != list(range(1, 9)) + [0] * sum(lengths):
        raise ValueError('lift does not sort expanded state')
    return len(reduced)


def check_profile(state, profile):
    word = profile['word']
    assert isinstance(word, str) and word and set(word) <= set('LRX')
    assert replay(state, word) == list(range(1, 9)) + [0] * state.count(0)
    base, gamma = price(state, word)
    assert (profile['base'], profile['gamma']) == (base, gamma)
    assert profile['base'] == len(word)


def exact_mixture(support, blocks):
    weights = [Fraction(item['weight']) for item in support]
    assert all(w > 0 for w in weights) and sum(weights) == 1
    base = sum(w * item['base'] for w, item in zip(weights, support))
    slopes = [sum(w * item['gamma'][j] for w, item in zip(weights, support))
              for j in range(blocks)]
    return base, slopes


def verify_case(case):
    labels, mask = case['labels'], case['mask']
    assert sorted(labels) == list(range(1, 9))
    assert 0 < mask < 512
    state = state_for(labels, mask)
    blocks = state.count(0)
    assert blocks in (5, 6)
    support, pool = case['support'], case['old_pool']
    key = lambda p: (p['word'], p['base'], tuple(p['gamma']))
    for profile in support:
        assert len(profile['gamma']) == blocks
        check_profile(state, profile)
    for profile in pool:
        assert len(profile['gamma']) == blocks
        check_profile(state, profile)
    base, slopes = exact_mixture(support, blocks)
    mu = [Fraction(x) for x in case['dual']['mu']]
    nu = Fraction(case['dual']['nu'])
    assert all(x >= 0 for x in mu)
    assert len(mu) == (blocks if blocks == 6 else blocks - 1)
    if blocks == 6:
        assert len(pool) == 29 and len(support) == 3
        assert all(key(p) in {key(q) for q in pool} for p in support[:2])
        assert key(support[2]) not in {key(q) for q in pool}
        assert base == Fraction(1255, 19) < 67
        assert slopes == [Fraction(110, 19), Fraction(110, 19), 6, 6,
                          Fraction(108, 19), Fraction(102, 19)]
        assert all(g <= 6 for g in slopes)
        costs = [Fraction(p['base']) + sum(x * g for x, g in zip(mu, p['gamma'])) - nu
                 for p in pool]
        assert min(costs) == 0
        assert nu - 6 * sum(mu) == Fraction(case['dual']['old_pool_lower_bound']) == Fraction(135, 2) > 67
        new = support[-1]
        new_cost = Fraction(new['base']) + sum(x * g for x, g in zip(mu, new['gamma'])) - nu
        assert new_cost == Fraction(case['dual']['new_column_reduced_cost']) == -4
        examples = ([2] * blocks, list(range(1, blocks + 1)),
                    [3 if j % 2 else 1 for j in range(blocks)])
    else:
        assert len(pool) == 27 and len(support) == 5
        assert base == Fraction(1223, 20)
        assert slopes == [Fraction(28, 5), 6, 6, 6, 6]
        # The conditional region is d_1>=1. Its average is strictly below
        # 61+6*sum(d), even though the unit-block average is above 61.
        assert base + slopes[0] == Fraction(1335, 20) < 67
        costs = [Fraction(p['base'] + p['gamma'][0]) +
                 sum(x * g for x, g in zip(mu, p['gamma'][1:])) - nu
                 for p in pool]
        assert min(costs) == 0
        assert nu - 6 * sum(mu) == Fraction(case['dual']['old_pool_lower_bound']) == Fraction(3291, 49) > 67
        added = case['expanded_pool']
        assert set(added) == {'set_a', 'set_b', 'set_c'}
        assert all(len(columns) == 32 for columns in added.values())
        expanded = pool + added['set_a'] + added['set_b'] + added['set_c']
        assert len(expanded) == 123
        assert all(key(p) in {key(q) for q in expanded} for p in support)
        for columns in added.values():
            for profile in columns:
                assert len(profile['gamma']) == blocks
                check_profile(state, profile)
        wide = case['expanded_dual']
        wide_mu = [Fraction(x) for x in wide['mu']]
        wide_nu = Fraction(wide['nu'])
        tight = wide['tight_slopes']
        assert tight == [1, 2, 3, 4] and all(x >= 0 for x in wide_mu)
        wide_costs = [Fraction(p['base']) +
                      sum(x * p['gamma'][j] for x, j in zip(wide_mu, tight)) - wide_nu
                      for p in expanded]
        assert min(wide_costs) == 0
        assert wide_nu - 6 * sum(wide_mu) == Fraction(wide['primal_dual_base']) == base
        examples = ([2, 1, 1, 1, 1], [2, 2, 3, 1, 4], [3, 2, 1, 2, 1])
    checks = 0
    for lengths in examples:
        d = [ell - 1 for ell in lengths]
        threshold = 31 + 6 * blocks + 6 * sum(d)
        mean = base + sum(g * x for g, x in zip(slopes, d))
        assert mean < threshold
        actual = []
        for p in support:
            length = lift(state, p['word'], lengths)
            assert length <= p['base'] + sum(g * x for g, x in zip(p['gamma'], d))
            actual.append(length)
            checks += 1
        assert min(actual) < threshold
    return {'id': case['id'], 'blocks': blocks, 'support_words': len(support),
            'control_columns': len(pool), 'weighted_base': str(base),
            'weighted_slopes': [str(x) for x in slopes],
            'control_dual_lower_bound': str(nu - 6 * sum(mu)),
            'expanded_columns': 123 if blocks == 5 else 0,
            'literal_replays': checks, 'status': 'PASS'}


def main():
    raw = (HERE / 'certificates.json').read_bytes()
    data = json.loads(raw)
    assert data['format'] == 'lrx-direct-word-certificate-v1'
    assert [c['id'] for c in data['cases']] == [
        'k6-mask221-order731', 'k5-mask302-order15713']
    output = {'data_sha256': sha256(raw).hexdigest(),
              'cases': [verify_case(c) for c in data['cases']]}
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
