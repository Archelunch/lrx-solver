"""Development-only, read-only audit of one frozen executable finalist.

This never loads the sealed confirmation files or calls a model. With
--execute it re-runs candidate code through the strict OS sandbox, so that
mode must be launched on a host permitting macOS Seatbelt.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from integrations.program_evaluator import ProgramEvaluator
from integrations.projected_mixtures import resources, state_for
from src.lrx.certificates import replay_visible


FROZEN = ROOT / 'autoresearch/official-integration-260924/frozen'
SEED_EVAL = (ROOT / 'autoresearch/official-integration-260924/gepa-smoke-02/verified'
             / 'c27df808a5d2265c-evaluation.json')


def _literal(state, word, lengths):
    """Second literal implementation: expand atomic operations, then replay."""
    atoms = []
    z = 0
    start = []
    for value in state:
        if value:
            atoms.append((value, 1))
            start.append(value)
        else:
            width = lengths[z]
            atoms.append((0, width))
            start.extend([0] * width)
            z += 1
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
                raise AssertionError('zero-zero X in normalized support')
            if left[0] == 0:
                q = left[1]-1
                parts.extend(('L'*q, 'X', 'RX'*q))
            elif right[0] == 0:
                q = right[1]-1
                parts.extend(('X', 'LX'*q, 'R'*q))
            else:
                parts.append('X')
            atoms[0], atoms[1] = right, left
        else:
            raise AssertionError('non-LRX letter')
    reduced = []
    for letter in ''.join(parts):
        if reduced and (reduced[-1], letter) in (('L','R'), ('R','L')):
            reduced.pop()
        else:
            reduced.append(letter)
    expanded = ''.join(reduced)
    assert replay_visible(tuple(start), expanded, max_steps=len(expanded)+1) == tuple(range(1,9))+(0,)*sum(lengths)
    return len(expanded)


def audit(program, evaluation, *, execute=False):
    source = Path(program).read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    reported = json.loads(Path(evaluation).read_text())
    assert reported['candidate_hash'] == digest
    cases = json.loads((FROZEN / 'development.json').read_text())
    baseline = json.loads((FROZEN / 'development-baseline.json').read_text())
    by_id = {c['id']: c for c in cases}
    assert set(by_id) == {r['case']['id'] for r in reported['families']}
    cycle_path = (ROOT / 'downloads/LRX_CYCLE7_8193_FAMILIES_2026-09-24'
                  / 'runs/cycle7/certificates.json')
    cycle_pairs = {(r['mask'], r['order_index']) for r in json.loads(cycle_path.read_text())['cases']}
    for case in cases:
        match = re.fullmatch(r'k[4-7]-mask(\d+)-order(\d+)', case['id'])
        assert match and int(match[1]) == case['mask']
        assert (case['mask'], int(match[2])) not in cycle_pairs
    evaluator = ProgramEvaluator(cases, baseline, require_os_sandbox=True)
    if execute:
        fresh = evaluator.evaluate(program)
        assert fresh['candidate_hash'] == digest
        assert {r['case']['id'] for r in fresh['families'] if r['certificate']} == {
            r['case']['id'] for r in reported['families'] if r['certificate']}
        assert fresh['combined_score'] == reported['combined_score']
        reported = fresh
    seed = json.loads(SEED_EVAL.read_text())
    seed_ids = {r['case']['id'] for r in seed['families'] if r['certificate']}
    catalog_ids = {r['case']['id'] for r in reported['families'] if r['baseline_certified']}
    certified = set()
    components = 0
    literal_checks = 0
    for row in reported['families']:
        case = by_id[row['case']['id']]
        assert row['case'] == case
        state = state_for(case['labels'], case['mask'])
        k = case['blocks']
        pool = evaluator.baseline[case['id']] + [entry['profile'] for entry in row['accepted_words']]
        for item in row['accepted_words']:
            p = item['profile']
            assert p['kind'] == 'direct' and tuple(p['state']) == state
            assert replay_visible(state, p['word'], max_steps=len(p['word'])+1) == tuple(range(1,9))+(0,)*k
            cost = resources(state, p['word'])
            assert cost['base'] == p['base'] == len(p['word']) and cost['beta'] == p['gamma']
        cert = row['certificate']
        if cert is None:
            continue
        certified.add(case['id'])
        weights = [Fraction(item['weight']) for item in cert['support']]
        assert weights and all(w > 0 for w in weights) and sum(weights) == 1
        base = Fraction(0)
        slopes = [Fraction(0)] * k
        available = {(p['word'], p['base'], tuple(p['gamma'])) for p in pool}
        for item, weight in zip(cert['support'], weights):
            p = item['profile']
            assert p['kind'] == 'direct' and tuple(p['state']) == tuple(p['target']) == state
            assert (p['word'], p['base'], tuple(p['gamma'])) in available
            assert replay_visible(state, p['word'], max_steps=len(p['word'])+1) == tuple(range(1,9))+(0,)*k
            cost = resources(state, p['word'])
            assert p['base'] == len(p['word']) == cost['base'] and p['gamma'] == cost['beta']
            base += weight * p['base']
            for j in range(k):
                slopes[j] += weight * p['gamma'][j]
            for lengths in ([2]*k, list(range(1,k+1)), [3 if j%2 else 1 for j in range(k)]):
                actual = _literal(state, p['word'], lengths)
                upper = p['base'] + sum(g*(length-1) for g, length in zip(p['gamma'], lengths))
                assert actual <= upper
                literal_checks += 1
            components += 1
        assert base < 31+6*k and max(slopes) <= 6
        assert str(base) == cert['bounds']['base']
        assert [str(x) for x in slopes] == cert['bounds']['gamma']
    assert reported['certified'] == len(certified)
    assert reported['new_certified'] == len(certified-catalog_ids)
    return {
        'candidate_hash': digest,
        'reported_score': reported['combined_score'],
        'development_certified': len(certified),
        'catalog_certified': len(catalog_ids),
        'seed_certified': len(seed_ids),
        'additional_to_catalog': sorted(certified-catalog_ids),
        'additional_to_seed': sorted(certified-seed_ids),
        'seed_only': sorted(seed_ids-certified),
        'support_components_rechecked': components,
        'nonunit_literal_replays': literal_checks,
        'cycle7_certificate_overlap': False,
        'confirmation_inspected': False,
        'scope': 'frozen development families only; disjoint from named cycle7 certificates; no full historical novelty claim',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--program', type=Path, required=True)
    parser.add_argument('--evaluation', type=Path, required=True)
    parser.add_argument('--execute', action='store_true', help='re-run under strict OS sandbox')
    args = parser.parse_args()
    print(json.dumps(audit(args.program, args.evaluation, execute=args.execute), indent=2))
