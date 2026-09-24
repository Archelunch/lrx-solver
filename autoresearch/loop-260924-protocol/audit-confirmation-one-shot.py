"""Read-only exact audit of the consumed, frozen 16-case confirmation.

Never executes candidate sources, reads provider secrets, or sends model calls.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FROZEN = HERE / 'frozen'
RUN = HERE / 'confirmation-one-shot'
sys.path.insert(0, str(ROOT))

from integrations.mixture_lp import optimize
from integrations.program_evaluator import ProgramEvaluator
from integrations.projected_mixtures import resources, state_for
from src.lrx.certificates import replay_visible

spec = importlib.util.spec_from_file_location('literal_audit', ROOT / 'autoresearch/loop-260924-live/finalist-audit.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
literal = module._literal


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def check_profile(profile, state, blocks):
    assert profile['kind'] == 'direct'
    assert tuple(profile['state']) == tuple(profile['target']) == state
    word = profile['word']
    assert replay_visible(state, word, max_steps=len(word) + 1) == tuple(range(1, 9)) + (0,) * blocks
    cost = resources(state, word)
    assert cost['base'] == profile['base'] == len(word)
    assert cost['beta'] == profile['gamma']


def check_primal(lp, profiles, blocks):
    if 'weights' not in lp or 'base' not in lp:
        return None
    weights = [Fraction(s) for s in lp['weights']]
    assert len(weights) == len(profiles) and all(w >= 0 for w in weights) and sum(weights) == 1
    base = sum(w * p['base'] for w, p in zip(weights, profiles))
    slopes = [sum(w * p['gamma'][j] for w, p in zip(weights, profiles)) for j in range(blocks)]
    assert base == Fraction(lp['base']) and all(g <= 6 for g in slopes)
    return base, slopes


def check_certificate(cert, profiles, state, blocks):
    if cert is None:
        return 0, 0
    available = {(p['word'], p['base'], tuple(p['gamma'])) for p in profiles}
    support = cert['support']
    weights = [Fraction(item['weight']) for item in support]
    assert weights and all(w > 0 for w in weights) and sum(weights) == 1
    base = Fraction(0)
    slopes = [Fraction(0)] * blocks
    literal_checks = 0
    for item, weight in zip(support, weights):
        p = item['profile']
        assert (p['word'], p['base'], tuple(p['gamma'])) in available
        check_profile(p, state, blocks)
        base += weight * p['base']
        for j in range(blocks):
            slopes[j] += weight * p['gamma'][j]
        for lengths in ([2] * blocks, list(range(1, blocks + 1)),
                        [3 if j % 2 else 1 for j in range(blocks)]):
            actual = literal(state, p['word'], lengths)
            upper = p['base'] + sum(g * (ell - 1) for g, ell in zip(p['gamma'], lengths))
            assert actual <= upper
            literal_checks += 1
    assert base < 31 + 6 * blocks and all(g <= 6 for g in slopes)
    assert str(base) == cert['bounds']['base']
    assert [str(g) for g in slopes] == cert['bounds']['gamma']
    return len(support), literal_checks


def audit():
    selection = json.loads((RUN / 'selection-frozen.json').read_text())
    receipts = json.loads((RUN / 'run-receipts.json').read_text())
    manifest = json.loads((FROZEN / 'manifest.json').read_text())
    assert selection['status'] == 'FROZEN_BEFORE_CONFIRMATION'
    assert receipts['status'] == 'CONSUMED_ONE_SHOT'
    assert receipts['selection_sha256'] == digest(RUN / 'selection-frozen.json')
    assert selection['frozen_manifest_sha256'] == digest(FROZEN / 'manifest.json')
    assert receipts['provider_calls'] == 0 and receipts['model_prompt_access'] is False
    for name, field in [('confirmation.json', 'confirmation_cases_sha256'),
                        ('confirmation-baseline.json', 'confirmation_baseline_sha256')]:
        assert digest(FROZEN / name) == selection[field] == manifest['files'][name]
    assert receipts['cases_sha256'] == selection['confirmation_cases_sha256']
    assert receipts['baseline_sha256'] == selection['confirmation_baseline_sha256']
    cases = json.loads((FROZEN / 'confirmation.json').read_text())
    catalog = json.loads((FROZEN / 'confirmation-baseline.json').read_text())
    evaluator = ProgramEvaluator(cases, catalog, require_os_sandbox=True)
    by_id = {c['id']: c for c in cases}
    assert len(by_id) == 16
    evaluations = {}
    summary = {}
    all_support = all_literal = accepted_count = fixed_count = 0
    for selected, receipt in zip(selection['sources'], receipts['results']):
        label = selected['label']
        assert label == receipt['label']
        source = ROOT / selected['source_snapshot']
        evaluation = ROOT / receipt['evaluation_artifact']
        assert digest(source) == selected['sha256'] == receipt['source_sha256']
        assert digest(evaluation) == receipt['evaluation_sha256']
        result = json.loads(evaluation.read_text())
        assert result['candidate_hash'] == selected['sha256']
        assert result['score_reference'] == 'fixed_catalog'
        assert result['isolation'] == receipt['isolation'] == 'macos_seatbelt'
        rows = {r['case']['id']: r for r in result['families']}
        assert set(rows) == set(by_id) and result['total_families'] == 16
        certified = new = supports = literal_checks = accepted = 0
        for case_id, case in by_id.items():
            row = rows[case_id]
            assert row['case'] == case
            assert row['candidate_run']['status'] == 'ok'
            assert row['candidate_run']['isolation'] == 'macos_seatbelt'
            assert row['status'] == receipt['case_statuses'][case_id]
            assert not row['rejected_words']
            state = state_for(case['labels'], case['mask'])
            fixed = evaluator.baseline[case_id]
            for p in fixed:
                check_profile(p, state, case['blocks'])
                fixed_count += 1
            candidate = [item['profile'] for item in row['accepted_words']]
            for item, p in zip(row['accepted_words'], candidate):
                assert item['normalized_word'] == p['word']
                check_profile(p, state, case['blocks'])
                accepted += 1
            baseline_lp = check_primal(row['baseline_lp'], fixed, case['blocks'])
            candidate_lp = check_primal(row['candidate_lp'], fixed + candidate, case['blocks'])
            assert row['baseline_certified'] == (baseline_lp is not None and baseline_lp[0] < 31 + 6 * case['blocks'])
            has_cert = row['certificate'] is not None
            assert has_cert == (row['status'] == 'CERTIFICATE')
            if has_cert:
                certified += 1
                new += not row['baseline_certified']
                assert candidate_lp is not None and candidate_lp[0] < 31 + 6 * case['blocks']
            s, lit = check_certificate(row['certificate'], fixed + candidate, state, case['blocks'])
            supports += s
            literal_checks += lit
        assert result['certified'] == receipt['certified'] == certified
        assert result['new_vs_catalog'] == receipt['new_vs_catalog'] == new
        assert result['combined_score'] == receipt['combined_score'] == 1000 * new + certified
        assert result['new_vs_incumbent'] == receipt['new_vs_incumbent'] == new
        summary[label] = {'source_sha256': selected['sha256'],
                          'evaluation_sha256': receipt['evaluation_sha256'],
                          'certified': certified, 'new_vs_catalog': new,
                          'accepted_word_checks': accepted, 'certificate_support_checks': supports,
                          'nonunit_literal_replays': literal_checks,
                          'certified_ids': sorted(case_id for case_id, row in rows.items() if row['certificate'])}
        all_support += supports
        all_literal += literal_checks
        accepted_count += accepted
        evaluations[label] = rows
    catalog_ids = set(summary['fixed_catalog_only']['certified_ids'])
    allcuts_ids = set(summary['deterministic_all_cuts']['certified_ids'])
    grok_ids = set(summary['broker_rejected_complete_grok']['certified_ids'])
    union_ids = set()
    mixed_additions = []
    for case_id, case in by_id.items():
        fixed = evaluator.baseline[case_id]
        allcuts = [item['profile'] for item in evaluations['deterministic_all_cuts'][case_id]['accepted_words']]
        grok = [item['profile'] for item in evaluations['broker_rejected_complete_grok'][case_id]['accepted_words']]
        combined = fixed + allcuts + grok
        lp = optimize(combined)
        exact = check_primal(lp, combined, case['blocks'])
        if exact is None or exact[0] >= 31 + 6 * case['blocks']:
            continue
        union_ids.add(case_id)
        if case_id not in allcuts_ids:
            weights = [Fraction(s) for s in lp['weights']]
            support = [{'origin': 'catalog' if i < len(fixed) else 'allcuts' if i < len(fixed) + len(allcuts) else 'broker_rejected_grok',
                        'weight': str(w), 'base': p['base'], 'gamma': p['gamma'], 'word': p['word']}
                       for i, (w, p) in enumerate(zip(weights, combined)) if w]
            mixed_additions.append({'case_id': case_id, 'base': str(exact[0]),
                                    'slopes': [str(x) for x in exact[1]], 'support': support})
    assert catalog_ids <= allcuts_ids <= union_ids
    assert grok_ids <= union_ids
    # Exact finite-pool exclusion for the newly confirmed k6 arrangement.
    k6_id = 'k6-mask221-order731'
    old_pool = evaluator.baseline[k6_id] + [
        item['profile'] for item in evaluations['deterministic_all_cuts'][k6_id]['accepted_words']]
    old_lp = evaluations['deterministic_all_cuts'][k6_id]['candidate_lp']
    old_primal = check_primal(old_lp, old_pool, 6)
    mu = [Fraction(0), Fraction(0), Fraction(1), Fraction(59, 12), Fraction(1, 12), Fraction(0)]
    nu = Fraction(207, 2)
    old_reduced = [Fraction(p['base']) + sum(x * g for x, g in zip(mu, p['gamma'])) - nu
                   for p in old_pool]
    assert len(old_pool) == 29 and min(old_reduced) == 0
    assert old_primal == (Fraction(135, 2), [Fraction(11, 2), Fraction(11, 2), 6, 6, 6, Fraction(11, 2)])
    assert nu - 6 * sum(mu) == old_primal[0] > 67
    k6_addition = next(item for item in mixed_additions if item['case_id'] == k6_id)
    assert Fraction(k6_addition['base']) == Fraction(1255, 19)
    assert k6_addition['slopes'] == ['110/19', '110/19', '6', '6', '108/19', '102/19']
    assert [item['weight'] for item in k6_addition['support']] == ['3/19', '9/19', '7/19']
    assert [item['origin'] for item in k6_addition['support']] == [
        'catalog', 'catalog', 'broker_rejected_grok']
    new_p = k6_addition['support'][-1]
    new_reduced = Fraction(new_p['base']) + sum(x * g for x, g in zip(mu, new_p['gamma'])) - nu
    assert new_reduced == -4
    return {'selection_sha256': digest(RUN / 'selection-frozen.json'),
            'receipt_sha256': digest(RUN / 'run-receipts.json'),
            'confirmation_cases': len(cases), 'arms': summary,
            'fixed_profile_checks': fixed_count,
            'accepted_word_checks': accepted_count,
            'certificate_support_checks': all_support,
            'nonunit_literal_replays': all_literal,
            'allcuts_additions_vs_catalog': sorted(allcuts_ids - catalog_ids),
            'grok_additions_vs_allcuts': sorted(grok_ids - allcuts_ids),
            'union_certified': len(union_ids), 'union_certified_ids': sorted(union_ids),
            'union_new_vs_catalog_plus_allcuts': mixed_additions,
            'k6_old_pool_dual': {'columns_checked': len(old_pool), 'mu': [str(x) for x in mu],
                                 'nu': str(nu), 'minimum_old_reduced_cost': str(min(old_reduced)),
                                 'old_pool_primal_equals_dual': str(old_primal[0]),
                                 'new_grok_word_reduced_cost': str(new_reduced)},
            'scope': 'Consumed one-shot confirmation, saved outputs only. Missing certificates do not prove infeasibility; recovered Grok source was broker-rejected, not an accepted native GEPA proposal.'}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
