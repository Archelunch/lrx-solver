"""Exact finite-pool dual check for the two frozen development misses.

No model calls, confirmation reads, or claims about words outside this pool.
Run from the repository root.  The baseline is reconstructed by the trusted
program evaluator; the seed profiles come from its frozen smoke artifact.
"""
import json
from fractions import Fraction
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from integrations.program_evaluator import ProgramEvaluator


FROZEN = ROOT / 'autoresearch/official-integration-260924/frozen'
SEED_EVAL = (ROOT / 'autoresearch/official-integration-260924/gepa-smoke-02/verified'
             / 'c27df808a5d2265c-evaluation.json')
TARGETS = {
    'k5-mask302-order15713': {
        'tight': (1, 2, 3, 4),
        'mu': ('11/14', '197/196', '1/8', '261/392'),
        'nu': '30221/392',
    },
    'k6-mask315-order31970': {
        'tight': (1, 4, 5),
        'mu': ('1/3', '91/27', '8/9'),
        'nu': '2561/27',
    },
}


def main():
    cases = json.loads((FROZEN / 'development.json').read_text())
    baseline = json.loads((FROZEN / 'development-baseline.json').read_text())
    evaluator = ProgramEvaluator(cases, baseline, require_os_sandbox=False)
    rows = {r['case']['id']: r for r in json.loads(SEED_EVAL.read_text())['families']}
    result = {}
    for case_id, dual in TARGETS.items():
        row = rows[case_id]
        assert row['certificate'] is None and row['candidate_run']['status'] == 'ok'
        profiles = evaluator.baseline[case_id] + [x['profile'] for x in row['accepted_words']]
        weights = list(map(Fraction, row['lp']['weights']))
        tight = dual['tight']
        mu = tuple(map(Fraction, dual['mu']))
        nu = Fraction(dual['nu'])
        assert len(weights) == len(profiles) and all(x >= 0 for x in mu + tuple(weights))
        assert sum(weights) == 1
        slopes = [sum(w*p['gamma'][j] for w, p in zip(weights, profiles))
                  for j in range(row['case']['blocks'])]
        assert all(g <= 6 for g in slopes)
        assert all(slopes[j] == 6 for j in tight)
        base = sum(w*p['base'] for w, p in zip(weights, profiles))
        assert base == Fraction(row['lp']['base']) == nu - 6*sum(mu)
        reduced = [Fraction(p['base']) + sum(x*p['gamma'][j] for x, j in zip(mu, tight)) - nu
                   for p in profiles]
        assert all(x >= 0 for x in reduced)
        assert all(reduced[i] == 0 for i, w in enumerate(weights) if w)
        threshold = 31 + 6*row['case']['blocks']
        assert base >= threshold
        result[case_id] = {
            'pool_profiles': len(profiles),
            'threshold_strictly_below': threshold,
            'exact_pool_minimum_base': str(base),
            'deficit': str(base-threshold),
            'weighted_slopes': [str(x) for x in slopes],
            'tight_slope_positions_1_based': [j+1 for j in tight],
            'dual_multipliers': [str(x) for x in mu],
            'dual_intercept': str(nu),
            'minimum_new_seed_reduced_cost': str(min(reduced[len(evaluator.baseline[case_id]):])),
            'interpretation': 'finite baseline-plus-seed pool only; new word must have negative reduced cost to lower this pool optimum',
        }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
