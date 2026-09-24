"""Read-only exact audit of one saved development evaluation.

Never executes candidate source, reads confirmation files, or calls a model.
Use --allow-partial only for GEPA's per-case evaluation artifacts.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
FROZEN = Path(__file__).resolve().parent / 'frozen'
sys.path.insert(0, str(ROOT))

from integrations.program_evaluator import ProgramEvaluator
from integrations.projected_mixtures import resources, state_for
from src.lrx.certificates import replay_visible

spec = importlib.util.spec_from_file_location('literal_audit', ROOT / 'autoresearch/loop-260924-live/finalist-audit.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
literal = module._literal


def _sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _check_profile(profile, state, blocks):
    assert profile['kind'] == 'direct'
    assert tuple(profile['state']) == tuple(profile['target']) == state
    word = profile['word']
    assert replay_visible(state, word, max_steps=len(word) + 1) == tuple(range(1, 9)) + (0,) * blocks
    cost = resources(state, word)
    assert cost['base'] == profile['base'] == len(word)
    assert cost['beta'] == profile['gamma']


def _check_primal(result, profiles, blocks):
    if 'weights' not in result or 'base' not in result:
        return None
    weights = [Fraction(x) for x in result['weights']]
    assert len(weights) == len(profiles) and all(w >= 0 for w in weights) and sum(weights) == 1
    slopes = [sum(w * p['gamma'][j] for w, p in zip(weights, profiles)) for j in range(blocks)]
    base = sum(w * p['base'] for w, p in zip(weights, profiles))
    assert all(g <= 6 for g in slopes) and base == Fraction(result['base'])
    return base


def audit(program, evaluation, *, allow_partial=False):
    manifest = json.loads((FROZEN / 'manifest.json').read_text())
    for name in ('development.json', 'development-baseline.json',
                 'development-incumbent.json', 'development-dual.json'):
        assert _sha(FROZEN / name) == manifest['files'][name]
    cases = json.loads((FROZEN / 'development.json').read_text())
    catalog = json.loads((FROZEN / 'development-baseline.json').read_text())
    incumbent = json.loads((FROZEN / 'development-incumbent.json').read_text())
    duals = json.loads((FROZEN / 'development-dual.json').read_text())
    evaluator = ProgramEvaluator(cases, catalog, incumbent=incumbent, dual=duals,
                                 require_os_sandbox=True)
    by_id = {case['id']: case for case in cases}
    result = json.loads(Path(evaluation).read_text())
    source_hash = _sha(program)
    assert result['candidate_hash'] == source_hash
    assert result['score_reference'] == 'frozen_incumbent'
    assert result['isolation'] == 'macos_seatbelt'
    rows = result['families']
    ids = [row['case']['id'] for row in rows]
    assert len(ids) == len(set(ids)) and set(ids) <= set(by_id)
    if not allow_partial:
        assert set(ids) == set(by_id)
    assert result['total_families'] == len(rows)

    certified = 0
    new_catalog = 0
    new_incumbent = 0
    invalid = 0
    secondary = Fraction(0)
    supports = literal_checks = accepted_count = baseline_checks = 0
    hard_case = None
    for row in rows:
        case = row['case']
        case_id = case['id']
        assert case == by_id[case_id]
        state = state_for(case['labels'], case['mask'])
        blocks = case['blocks']
        fixed = evaluator.baseline[case_id] + evaluator.incumbent[case_id]
        for p in fixed:
            _check_profile(p, state, blocks)
            baseline_checks += 1
        accepted = [entry['profile'] for entry in row['accepted_words']]
        for entry, p in zip(row['accepted_words'], accepted):
            assert entry['normalized_word'] == p['word']
            _check_profile(p, state, blocks)
            accepted_count += 1
        full = fixed + accepted
        _check_primal(row['baseline_lp'], evaluator.baseline[case_id], blocks)
        incumbent_base = _check_primal(row['incumbent_lp'], fixed, blocks)
        candidate_base = _check_primal(row['candidate_lp'], full, blocks)
        selected_pool = fixed if row['lp'] == row['incumbent_lp'] else full
        selected_base = _check_primal(row['lp'], selected_pool, blocks)
        if selected_base is None and row['lp'] != row['candidate_lp']:
            raise AssertionError('selected LP has no feasible witness')
        if incumbent_base is not None and selected_base is not None:
            assert selected_base <= incumbent_base
        if candidate_base is not None and incumbent_base is not None and candidate_base > incumbent_base:
            assert row['lp'] == row['incumbent_lp']

        cert = row['certificate']
        valid = row['candidate_run']['status'] == 'ok'
        if cert is not None:
            certified += 1
            assert cert['scope'].startswith('all positive lengths via direct word resources')
            available = {(p['word'], p['base'], tuple(p['gamma'])) for p in full}
            weights = [Fraction(item['weight']) for item in cert['support']]
            assert weights and all(w > 0 for w in weights) and sum(weights) == 1
            base = Fraction(0)
            slopes = [Fraction(0)] * blocks
            for item, weight in zip(cert['support'], weights):
                p = item['profile']
                assert (p['word'], p['base'], tuple(p['gamma'])) in available
                _check_profile(p, state, blocks)
                base += weight * p['base']
                for j in range(blocks):
                    slopes[j] += weight * p['gamma'][j]
                for lengths in ([2] * blocks, list(range(1, blocks + 1)),
                                [3 if j % 2 else 1 for j in range(blocks)]):
                    actual = literal(state, p['word'], lengths)
                    upper = p['base'] + sum(g * (ell - 1) for g, ell in zip(p['gamma'], lengths))
                    assert actual <= upper
                    literal_checks += 1
                supports += 1
            assert base < 31 + 6 * blocks and all(g <= 6 for g in slopes)
            assert str(base) == cert['bounds']['base']
            assert [str(g) for g in slopes] == cert['bounds']['gamma']
            new_catalog += not row['baseline_certified']
            new_incumbent += valid and not row['incumbent_certified']
        else:
            assert row['status'] != 'CERTIFICATE'
        if row['status'] in ('INVALID_OUTPUT', 'candidate_error', 'INCOMPLETE'):
            invalid += 1
        progress = row['progress']
        assert progress is not None
        before = incumbent_base
        after = selected_base if valid else None
        assert progress['feasible_base_before'] == (str(before) if before is not None else None)
        assert progress['feasible_base_after'] == (str(after) if after is not None else None)
        improvement = max(Fraction(0), before-after) if before is not None and after is not None else Fraction(0)
        assert progress['base_improvement'] == str(improvement)
        dual = evaluator.dual.get(case_id)
        costs = sorted({dual['reduced_cost'](p) for p in accepted}) if dual else []
        best = costs[0] if costs else None
        assert progress['best_reduced_cost'] == (str(best) if valid and best is not None else None)
        negative = max(Fraction(0), -best) if valid and best is not None else Fraction(0)
        assert progress['negative_reduced_cost'] == str(negative)
        rewardable = valid and not row['incumbent_certified']
        grade = ((improvement/(1+improvement) + negative/(1+negative))/2
                 if rewardable else Fraction(0))
        assert progress['secondary_grade'] == str(grade)
        secondary += grade
        if case_id in duals:
            hard_case = {'id': case_id, 'incumbent_base': str(before) if before is not None else None,
                         'candidate_feasible_base': str(after) if after is not None else None,
                         'base_improvement': str(improvement),
                         'minimum_new_reduced_cost': str(best) if best is not None else None,
                         'certificate': cert is not None,
                         'valid_execution': valid}

    secondary /= len(rows)
    assert result['certified'] == certified
    assert result['new_vs_catalog'] == result['new_certified'] == new_catalog
    assert result['new_vs_incumbent'] == new_incumbent
    assert result['secondary_score'] == str(secondary)
    weight = result.get('certificate_weight', max(1001, len(rows) + 2))
    assert weight == max(1001, len(rows) + 2)
    expected_score = float(weight * new_incumbent - invalid + secondary)
    assert result['combined_score'] == expected_score
    return {'source_sha256': source_hash, 'evaluation_sha256': _sha(evaluation),
            'evaluated_development_cases': len(rows), 'certified': certified,
            'new_vs_catalog': new_catalog, 'new_vs_incumbent': new_incumbent,
            'invalid_executions': invalid, 'secondary_score': str(secondary),
            'combined_score': expected_score,
            'fixed_profile_checks': baseline_checks, 'accepted_word_checks': accepted_count,
            'certificate_support_checks': supports, 'nonunit_literal_replays': literal_checks,
            'hard_case': hard_case,
            'scope': 'Frozen development only; saved evidence, no candidate execution or confirmation access. A missing certificate is not infeasibility.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--program', type=Path, required=True)
    parser.add_argument('--evaluation', type=Path, required=True)
    parser.add_argument('--allow-partial', action='store_true')
    args = parser.parse_args()
    print(json.dumps(audit(args.program, args.evaluation, allow_partial=args.allow_partial), indent=2))
