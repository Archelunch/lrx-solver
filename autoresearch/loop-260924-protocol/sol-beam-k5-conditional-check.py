"""Check the saved conditional k5 direct-word mixture without candidate execution.

Run once with --freeze to write the exact support JSON from the immutable
development evaluation. Later runs check the saved support, old finite-pool
dual, symbolic inequality, and several literal nonunit block expansions.
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
HERE = Path(__file__).resolve().parent
FROZEN = HERE / 'frozen'
SOURCE = HERE / 'sol-beam-k5.py'
EVALUATION = HERE / 'sol-beam-k5-eval-01/5eebd52cd158f497-evaluation.json'
SUPPORT = HERE / 'sol-beam-k5-conditional-support.json'
SOURCE_SHA = '5eebd52cd158f497ba0b609c23d9396b14c192d843f5df8fc5f707ec5418908b'
EVALUATION_SHA = 'd3468f9dc8f60be46a8773e106028f0c9383fe4ef3873d39910c1eafcb2e7069'
CASE_ID = 'k5-mask302-order15713'
sys.path.insert(0, str(ROOT))

from integrations.mixture_lp import solve
from integrations.program_evaluator import ProgramEvaluator
from integrations.projected_mixtures import resources, state_for
from src.lrx.certificates import replay_visible

spec = importlib.util.spec_from_file_location('literal_audit', ROOT / 'autoresearch/loop-260924-live/finalist-audit.py')
literal_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(literal_module)
literal = literal_module._literal


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def verify(*, freeze=False):
    assert digest(SOURCE) == SOURCE_SHA
    assert digest(EVALUATION) == EVALUATION_SHA
    cases = json.loads((FROZEN / 'development.json').read_text())
    baseline = json.loads((FROZEN / 'development-baseline.json').read_text())
    incumbent = json.loads((FROZEN / 'development-incumbent.json').read_text())
    dual = json.loads((FROZEN / 'development-dual.json').read_text())
    evaluator = ProgramEvaluator(cases, baseline, incumbent=incumbent, dual=dual)
    result = json.loads(EVALUATION.read_text())
    row = next(row for row in result['families'] if row['case']['id'] == CASE_ID)
    state = state_for(row['case']['labels'], row['case']['mask'])
    fixed = evaluator.baseline[CASE_ID] + evaluator.incumbent[CASE_ID]
    pool = fixed + [entry['profile'] for entry in row['accepted_words']]
    weights = [Fraction(s) for s in row['candidate_lp']['weights']]
    assert len(weights) == len(pool) and all(w >= 0 for w in weights) and sum(weights) == 1
    support = []
    for index, (weight, profile) in enumerate(zip(weights, pool)):
        if not weight:
            continue
        assert profile['kind'] == 'direct'
        assert tuple(profile['state']) == state
        assert replay_visible(state, profile['word'], max_steps=len(profile['word']) + 1) == tuple(range(1, 9)) + (0,) * 5
        exact = resources(state, profile['word'])
        assert profile['base'] == exact['base'] == len(profile['word'])
        assert profile['gamma'] == exact['beta']
        support.append({'pool_index': index, 'origin': 'beam' if index >= len(fixed) else 'fixed',
                        'weight': str(weight), 'base': profile['base'],
                        'gamma': profile['gamma'], 'word': profile['word']})
    B = sum(Fraction(item['weight']) * item['base'] for item in support)
    gamma = [sum(Fraction(item['weight']) * item['gamma'][j] for item in support)
             for j in range(5)]
    assert B == Fraction(2147, 35) == Fraction(row['candidate_lp']['base'])
    assert gamma == [Fraction(28, 5), Fraction(6), Fraction(6), Fraction(6), Fraction(6)]
    frozen_support = {'case_id': CASE_ID, 'source_sha256': SOURCE_SHA,
                      'evaluation_sha256': EVALUATION_SHA, 'base': str(B),
                      'gamma': [str(x) for x in gamma], 'support': support}
    if freeze:
        SUPPORT.write_text(json.dumps(frozen_support, indent=2) + '\n')
    assert json.loads(SUPPORT.read_text()) == frozen_support

    # For all integer d_1 >= 1 and d_2..5 >= 0, the averaged upper bound is
    # B + sum gamma_j d_j <= B + gamma_1 + 6(sum d_j - 1) < 61 + 6 sum d_j.
    # A strict average below an integer threshold selects a word of length
    # at most 6n-18 after the direct-word triangle expansion.
    assert B + gamma[0] < 67
    assert gamma[1:] == [6] * 4
    assert (61 - B) == Fraction(-12, 35)
    assert (6 - gamma[0]) == Fraction(2, 5)

    # Compare a *single uniform* old-pool mixture, not pointwise old coverage.
    old_result = row['incumbent_lp']
    old_weights = [Fraction(s) for s in old_result['weights']]
    old_B = sum(w * p['base'] for w, p in zip(old_weights, fixed))
    old_gamma = [sum(w * p['gamma'][j] for w, p in zip(old_weights, fixed)) for j in range(5)]
    assert old_B == Fraction(24149, 392)
    assert old_gamma == [Fraction(2179, 392), 6, 6, 6, 6]
    # Exact dual for minimum B+gamma_1 subject to gamma_2..5 <= 6.
    old_indices = [i for i, w in enumerate(old_weights) if w]
    assert old_indices == [0, 1, 2, 3, 6]
    matrix = [[fixed[i]['gamma'][j] for j in range(1, 5)] + [-1] for i in old_indices]
    rhs = [-fixed[i]['base'] - fixed[i]['gamma'][0] for i in old_indices]
    solution = solve(matrix, rhs, exact=True)
    mu, nu = solution[:4], solution[4]
    assert mu == [Fraction(5, 7), Fraction(47, 49), Fraction(2, 3), Fraction(50, 147)]
    assert all(x >= 0 for x in mu)
    reduced = [Fraction(p['base']) + p['gamma'][0] +
               sum(x * p['gamma'][j] for j, x in enumerate(mu, 1)) - nu
               for p in fixed]
    assert min(reduced) == 0 and all(reduced[i] == 0 for i in old_indices)
    assert nu - 6 * sum(mu) == Fraction(3291, 49) > 67

    literal_checks = []
    for lengths in ([2, 1, 1, 1, 1], [2, 2, 3, 1, 4], [3, 2, 1, 2, 1]):
        ds = [ell - 1 for ell in lengths]
        threshold = 61 + 6 * sum(ds)
        costs = []
        for item in support:
            actual = literal(state, item['word'], lengths)
            bound = item['base'] + sum(g * d for g, d in zip(item['gamma'], ds))
            assert actual <= bound
            costs.append(actual)
        average_bound = B + sum(g * d for g, d in zip(gamma, ds))
        assert average_bound < threshold
        assert min(costs) < threshold
        literal_checks.append({'lengths': lengths, 'averaged_upper': str(average_bound),
                               'strict_integer_threshold': threshold,
                               'minimum_literal_support_length': min(costs)})
    return {'source_sha256': SOURCE_SHA, 'evaluation_sha256': EVALUATION_SHA,
            'support_sha256': digest(SUPPORT), 'support_count': len(support),
            'base': str(B), 'gamma': [str(x) for x in gamma],
            'uniform_region': 'first block length >= 2; other four lengths >= 1',
            'old_pool_uniform_mixture_lower_bound': str(nu - 6 * sum(mu)),
            'old_pool_column_checks': len(reduced), 'literal_replay_checks': len(support) * len(literal_checks),
            'literal_examples': literal_checks,
            'scope': 'Saved development evidence and general direct-word triangle expansion; not pointwise novelty against all old words or a unit-family certificate.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(freeze=args.freeze), indent=2))
