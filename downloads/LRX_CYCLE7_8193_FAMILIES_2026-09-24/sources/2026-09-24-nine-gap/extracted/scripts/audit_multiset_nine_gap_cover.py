#!/usr/bin/env python3
"""Standalone exact audit of all 40320 nine-gap named orders.

No optimizer, search program, domain bitset engine, or native binary is
imported. Target ranks and prefix dominance are reconstructed independently.
"""
import argparse
from collections import Counter
from fractions import Fraction
from functools import lru_cache
import hashlib
from itertools import permutations
import json
from pathlib import Path
from random import Random
import time

from multiset_zero_stretch import certificate
from audit_multiset_projected_certificates import stretch_literal


def literal(state, word):
    state = tuple(state)
    for c in word:
        if c == 'L':
            state = state[1:]+state[:1]
        elif c == 'R':
            state = state[-1:]+state[:-1]
        else:
            assert c == 'X'
            state = (state[1], state[0])+state[2:]
    return state


def geometry(n, word):
    at, forbidden = 0, set()
    for c in word:
        if c == 'X':
            forbidden.add((at+1) % n)
        else:
            assert c in 'LR'
            at = (at+(1 if c == 'L' else -1)) % n
    return at, forbidden


def ranks(state, cut, finish):
    state = tuple(state)
    n, m = len(state), max(state)
    root = tuple(range(1, m+1))+(0,)*(n-m)
    physical = root[-finish:]+root[:-finish] if finish else root
    goal = physical[cut:]+physical[:cut]
    locations = {x: j for j, x in enumerate(goal) if x}
    zeros = iter(j for j, x in enumerate(goal) if not x)
    return tuple(locations[x] if x else next(zeros) for x in state[cut:]+state[:cut])


def inversions(p):
    return sum(p[i] > p[j] for i in range(len(p)) for j in range(i+1, len(p)))


def zero_crossings(p, state, cut):
    n = len(p)
    named = [(j-cut) % n for j, x in enumerate(state) if x]
    result = []
    for j, x in enumerate(state):
        if not x:
            z = (j-cut) % n
            result.append(sum((i < z and p[i] > p[z]) or (i > z and p[i] < p[z]) for i in named))
    return result


def state_for(labels, lengths=(1,)*9):
    result = [0]*lengths[0]
    for x, length in zip(labels, lengths[1:]):
        result.append(x); result.extend([0]*length)
    return tuple(result)


def compare_word(state, word, cut):
    n = len(state)
    finish, forbidden = geometry(n, word)
    assert cut not in forbidden
    p, cursor, result = list(ranks(state, cut, finish)), (-cut) % n, []
    for c in word:
        if c == 'X':
            assert cursor < n-1
            if p[cursor] > p[cursor+1]:
                p[cursor], p[cursor+1] = p[cursor+1], p[cursor]
                result.append(c)
        else:
            cursor = (cursor+(1 if c == 'L' else -1)) % n
            result.append(c)
    assert p == list(range(n))
    result = ''.join(result)
    assert literal(state, result) == tuple(range(1, 9))+(0,)*(n-8)
    return result


def load_bundle(args):
    if args.bundle_input:
        bundle = json.loads(args.bundle_input.read_text())
        assert bundle['format'] == 'lrx_nine_gap_comparison_certificate_v1'
        return bundle, [args.bundle_input]
    primary, repairs = json.loads(args.main.read_text()), json.loads(args.repairs.read_text())
    assert primary['format'] == 'lrx_nine_gap_comparison_cover_v1'
    assert repairs['format'] == 'lrx_nine_gap_comparison_repairs_v1'
    catalog, sources = [], {}

    def remap(data):
        mapping = {}
        for i, row in enumerate(data['catalog']):
            key = tuple(row['state']), row['word']
            if key not in sources:
                sources[key] = len(catalog); catalog.append(dict(state=list(key[0]), word=key[1]))
            mapping[i] = sources[key]
        result = {}
        for record in data['records']:
            index = record['order_index']
            assert index not in result
            mixture = record['mixture']
            result[index] = dict(order_index=index, labels=record['labels'],
                mixture=None if mixture is None else [dict(row, source=mapping[row['source']]) for row in mixture])
        return result

    main_records, repaired = remap(primary), remap(repairs)
    missing = {i for i, row in main_records.items() if row['mixture'] is None}
    assert set(repaired) == missing
    assert all(row['mixture'] for row in repaired.values())
    for index, row in repaired.items():
        assert main_records[index]['labels'] == row['labels']
        main_records[index] = row
    return dict(format='lrx_nine_gap_comparison_certificate_v1', m=8, slots=list(range(9)),
        catalog=catalog, records=[main_records[i] for i in sorted(main_records)]), [args.main, args.repairs]


def universe(records):
    assert len(records) == 40320
    expected = tuple(permutations(range(1, 9)))
    seen = set()
    for record in records:
        index = record['order_index']
        assert type(index) is int and 0 <= index < 40320 and index not in seen
        assert tuple(record['labels']) == expected[index]
        assert record['mixture']
        seen.add(index)
    assert len(seen) == 40320


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--main', type=Path, default=Path('literature/multiset_nine_gap_complete_attempt_20260924.json'))
    parser.add_argument('--repairs', type=Path, default=Path('literature/multiset_nine_gap_repaired_20260924.json'))
    parser.add_argument('--bundle-input', type=Path)
    parser.add_argument('--bundle-output', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert __debug__
    for path in (args.output, args.bundle_output):
        if path and path.exists():
            raise FileExistsError(path)
    started, counts, rng = time.monotonic(), Counter(), Random(2026092410)
    bundle, input_paths = load_bundle(args)
    assert bundle['m'] == 8 and bundle['slots'] == list(range(9))
    catalog, records = bundle['catalog'], bundle['records']
    universe(records)
    infos = []
    for source in catalog:
        state, word = tuple(source['state']), source['word']
        assert len(state) == 17 and all((x == 0) == (i % 2 == 0) for i, x in enumerate(state))
        assert sorted(x for x in state if x) == list(range(1, 9))
        assert literal(state, word) == tuple(range(1, 9))+(0,)*9
        c = certificate(state, word)
        assert c['base_cost'] == len(word)
        finish, forbidden = geometry(17, word)
        infos.append(dict(state=state, word=word, c=c, finish=finish, forbidden=forbidden))
        counts['reference_words'] += 1
        for j in range(9):
            lengths = [1]*9; lengths[j] = 2
            initial, lifted = stretch_literal(state, word, lengths)
            assert literal(initial, lifted) == tuple(range(1, 9))+(0,)*10
            assert len(lifted)-len(word) == c['beta'][j]
            counts['independent_slope_checks'] += 1

    @lru_cache(None)
    def source_cut(source, cut):
        assert type(source) is int and 0 <= source < len(infos)
        info = infos[source]
        assert type(cut) is int and 0 <= cut < 17 and cut not in info['forbidden']
        q = ranks(info['state'], cut, info['finish'])
        assert inversions(q) == info['c']['x_count']
        assert zero_crossings(q, info['state'], cut) == list(info['c']['zero_swaps'])
        counts['reference_cut_checks'] += 1
        return tuple(tuple(sorted(q[:j])) for j in range(1, 18))

    def check_record(record):
        state = state_for(record['labels'])
        mixture = record['mixture']
        weights = [Fraction(row['weight']) for row in mixture]
        assert min(weights) > 0 and sum(weights) == 1
        profile_list, rank_cache = [], {}
        for row, weight in zip(mixture, weights):
            source, cut = row['source'], row['cut']
            qprefixes = source_cut(source, cut)
            info = infos[source]
            key = cut, info['finish']
            if key not in rank_cache:
                p = ranks(state, cut, info['finish'])
                rank_cache[key] = (tuple(tuple(sorted(p[:j])) for j in range(1, 18)),
                                   inversions(p), zero_crossings(p, state, cut))
            prefixes, inv_p, sigma_p = rank_cache[key]
            assert all(all(a <= b for a, b in zip(left, right)) for left, right in zip(prefixes, qprefixes))
            c = info['c']
            assert inv_p <= c['x_count']
            assert all(a >= b and (a-b) % 2 == 0 for a, b in zip(c['zero_swaps'], sigma_p))
            base = c['base_cost']-c['x_count']+inv_p
            beta = [b-s+t for b, s, t in zip(c['beta'], c['zero_swaps'], sigma_p)]
            profile_list.append((base, beta, row))
        assert sum(w*p[0] for w, p in zip(weights, profile_list)) < 85
        assert all(sum(w*p[1][j] for w, p in zip(weights, profile_list)) <= 6 for j in range(9))
        return state, profile_list

    used_sources = set()
    for record in records:
        state, profiles = check_record(record)
        used_sources.update(row['source'] for row in record['mixture'])
        cost, _, chosen = min(profiles, key=lambda p: p[0])
        answer = compare_word(state, infos[chosen['source']]['word'], chosen['cut'])
        assert len(answer) == cost <= 84
        counts['named_orders'] += 1
        counts['mixture_rows'] += len(profiles)
        counts['unit_comparison_words'] += 1; counts['unit_comparison_letters'] += len(answer)
        if record['order_index'] % 32 == 0:
            lengths = [rng.randrange(1, 8) for _ in range(9)]
            base, beta, chosen = min(profiles, key=lambda p: p[0]+sum(b*(ell-1) for b, ell in zip(p[1], lengths)))
            info = infos[chosen['source']]
            _, lifted = stretch_literal(info['state'], info['word'], lengths)
            cut = sum(1 if x else lengths[i//2] for i, x in enumerate(info['state'][:chosen['cut']]))
            answer = compare_word(state_for(record['labels'], lengths), lifted, cut)
            assert len(answer) == base+sum(b*(ell-1) for b, ell in zip(beta, lengths)) <= 30+6*sum(lengths)
            counts['expanded_comparison_words'] += 1; counts['expanded_comparison_letters'] += len(answer)
        if counts['named_orders'] % 5000 == 0:
            print(dict(checked=counts['named_orders'], seconds=time.monotonic()-started), flush=True)
    assert used_sources == set(range(len(catalog)))
    bad = dict(records[0], mixture=[dict(row) for row in records[0]['mixture']])
    bad['mixture'][0]['weight'] = str(Fraction(bad['mixture'][0]['weight'])+1)
    try:
        check_record(bad)
    except AssertionError:
        counts['negative_controls_rejected'] += 1
    else:
        raise AssertionError('Invalid mixture weight accepted')
    bad = dict(records[0], mixture=[dict(row) for row in records[0]['mixture']])
    chosen = bad['mixture'][0]
    chosen['cut'] = min(infos[chosen['source']]['forbidden'])
    try:
        check_record(bad)
    except AssertionError:
        counts['negative_controls_rejected'] += 1
    else:
        raise AssertionError('Forbidden cut accepted')
    try:
        universe(records[:-1])
    except AssertionError:
        counts['negative_controls_rejected'] += 1
    else:
        raise AssertionError('Incomplete order universe accepted')
    if args.bundle_output:
        with args.bundle_output.open('x') as stream:
            json.dump(bundle, stream, separators=(',', ':'))
        input_paths.append(args.bundle_output)
    paths = [Path(__file__), *input_paths, Path('scripts/multiset_zero_stretch.py'),
        Path('scripts/multiset_free_phase.py'), Path('scripts/audit_multiset_projected_certificates.py'),
        Path('scripts/multiset_zero_projection.py')]
    report = dict(status='PASS', counts=dict(counts), nine_gap_m8_proved=True, full_conjecture_proved=False,
        source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        seconds=time.monotonic()-started)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
    print(dict(status='PASS', counts=dict(counts), seconds=report['seconds']), flush=True)


if __name__ == '__main__':
    main()
