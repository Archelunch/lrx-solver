"""Read-only exact audit of the single frozen confirmation evaluation set.

This checks saved evidence. It never runs candidate programs or calls models.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PREP = Path(__file__).resolve().parent
FROZEN = ROOT / 'autoresearch/official-integration-260924/frozen'
sys.path.insert(0, str(ROOT))

from integrations.program_evaluator import ProgramEvaluator
from integrations.projected_mixtures import resources, state_for
from src.lrx.certificates import replay_visible

spec = importlib.util.spec_from_file_location('development_literal_audit', ROOT / 'autoresearch/loop-260924-live/finalist-audit.py')
literal_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(literal_module)
literal = literal_module._literal


def check_profile(profile, state, blocks):
    assert profile['kind'] == 'direct'
    assert tuple(profile['state']) == tuple(profile['target']) == state
    word = profile['word']
    assert replay_visible(state, word, max_steps=len(word) + 1) == tuple(range(1, 9)) + (0,) * blocks
    actual = resources(state, word)
    assert actual['base'] == profile['base'] == len(word)
    assert actual['beta'] == profile['gamma']


def audit():
    selection = json.loads((PREP / 'selection-frozen.json').read_text())
    cases = json.loads((FROZEN / 'confirmation.json').read_text())
    baselines = json.loads((FROZEN / 'confirmation-baseline.json').read_text())
    evaluator = ProgramEvaluator(cases, baselines, require_os_sandbox=True)
    case_by_id = {case['id']: case for case in cases}
    assert len(case_by_id) == len(cases) == 8
    baseline_profiles = evaluator.baseline
    baseline_checks = 0
    for case in cases:
        state = state_for(case['labels'], case['mask'])
        for profile in baseline_profiles[case['id']]:
            check_profile(profile, state, case['blocks'])
            baseline_checks += 1

    results = {}
    for selected in selection['sources']:
        label = selected['label']
        source_path = ROOT / selected['source_snapshot']
        digest = sha256(source_path.read_bytes()).hexdigest()
        assert digest == selected['sha256']
        result_path = PREP / 'results' / label / (digest[:16] + '-evaluation.json')
        result = json.loads(result_path.read_text())
        assert result['candidate_hash'] == digest
        assert result['isolation'] == 'macos_seatbelt'
        assert result['total_families'] == 8
        assert {row['case']['id'] for row in result['families']} == set(case_by_id)

        certified, accepted_count, support_count, literal_checks = set(), 0, 0, 0
        per_case = {}
        for row in result['families']:
            case = row['case']
            case_id = case['id']
            assert case == case_by_id[case_id]
            assert row['candidate_run']['status'] == 'ok'
            assert row['candidate_run']['isolation'] == 'macos_seatbelt'
            state = state_for(case['labels'], case['mask'])
            blocks = case['blocks']
            pool = baseline_profiles[case_id] + [a['profile'] for a in row['accepted_words']]
            available = {(p['word'], p['base'], tuple(p['gamma'])) for p in pool}
            for accepted in row['accepted_words']:
                p = accepted['profile']
                assert accepted['normalized_word'] == p['word']
                check_profile(p, state, blocks)
                accepted_count += 1

            certificate = row['certificate']
            if certificate is None:
                assert row['status'] in ('NO_CERTIFICATE', 'INCOMPLETE')
                per_case[case_id] = {'outcome': row['status'],
                                     'returned_feasible_base': row['lp'].get('base'),
                                     'strict_target': 31 + 6 * blocks,
                                     'baseline_certified': row['baseline_certified']}
                continue

            assert row['status'] == 'CERTIFICATE'
            certified.add(case_id)
            assert certificate['scope'].startswith('all positive lengths via direct word resources')
            assert certificate['support']
            weights = [Fraction(item['weight']) for item in certificate['support']]
            assert all(weight > 0 for weight in weights) and sum(weights) == 1
            base = Fraction(0)
            slopes = [Fraction(0)] * blocks
            for item, weight in zip(certificate['support'], weights):
                profile = item['profile']
                check_profile(profile, state, blocks)
                assert (profile['word'], profile['base'], tuple(profile['gamma'])) in available
                base += weight * profile['base']
                for j in range(blocks):
                    slopes[j] += weight * profile['gamma'][j]
                for lengths in ([2] * blocks, list(range(1, blocks + 1)),
                                [3 if j % 2 else 1 for j in range(blocks)]):
                    actual_length = literal(state, profile['word'], lengths)
                    upper = profile['base'] + sum(g * (length - 1) for g, length in zip(profile['gamma'], lengths))
                    assert actual_length <= upper
                    literal_checks += 1
                support_count += 1
            assert base < 31 + 6 * blocks and all(slope <= 6 for slope in slopes)
            assert str(base) == certificate['bounds']['base']
            assert [str(slope) for slope in slopes] == certificate['bounds']['gamma']
            per_case[case_id] = {'outcome': 'CERTIFICATE', 'base': str(base),
                                 'base_margin': str(Fraction(31 + 6 * blocks) - base),
                                 'slopes': [str(slope) for slope in slopes],
                                 'baseline_certified': row['baseline_certified']}

        assert len(certified) == result['certified']
        assert result['new_certified'] == sum(not row['baseline_certified'] and row['certificate'] is not None
                                              for row in result['families'])
        results[label] = {'role': selected['role'], 'source_sha256': digest,
                          'evaluation': str(result_path.relative_to(ROOT)),
                          'evaluation_sha256': sha256(result_path.read_bytes()).hexdigest(),
                          'certified': len(certified), 'certified_ids': sorted(certified),
                          'new_vs_catalog': result['new_certified'],
                          'accepted_words_rechecked': accepted_count,
                          'support_profiles_rechecked': support_count,
                          'nonunit_literal_replays': literal_checks,
                          'execution_statuses': {r['case']['id']: r['candidate_run']['status'] for r in result['families']},
                          'cases': per_case}

    catalog_ids = set(results['fixed_catalog_only']['certified_ids'])
    union_ids = set().union(*(set(result['certified_ids']) for result in results.values()))
    assert all(set(result['certified_ids']) == catalog_ids for result in results.values())
    return {'selection_sha256': sha256((PREP / 'selection-frozen.json').read_bytes()).hexdigest(),
            'case_file_sha256': sha256((FROZEN / 'confirmation.json').read_bytes()).hexdigest(),
            'baseline_file_sha256': sha256((FROZEN / 'confirmation-baseline.json').read_bytes()).hexdigest(),
            'cases': len(cases), 'catalog_baseline_profiles_rechecked': baseline_checks,
            'arms': results, 'union_certified_ids': sorted(union_ids),
            'union_new_vs_catalog': sorted(union_ids - catalog_ids),
            'unresolved_ids': sorted(set(case_by_id) - union_ids),
            'scope': 'Saved one-shot confirmation artifacts; exact direct resource and rational mixture checks plus finite literal expansion checks. A missing certificate is not infeasibility; no global LRX solution claimed.'}


if __name__ == '__main__':
    output = PREP / 'confirmation-audit.json'
    output.write_text(json.dumps(audit(), indent=2) + '\n')
    print(output)
