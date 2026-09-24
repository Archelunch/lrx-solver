"""Exact read-only check of the finite-pool k5 LP dual; no candidate execution."""
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FROZEN = HERE / 'frozen'
sys.path.insert(0, str(ROOT))

from integrations.program_evaluator import ProgramEvaluator
from integrations.mixture_lp import solve


def check():
    frozen = json.loads((HERE / 'sol-beam-k5-allcuts64-dual.json').read_text())
    source = HERE / 'sol-beam-k5-allcuts64.py'
    evaluation = HERE / 'sol-beam-k5-allcuts64-eval-01/29df962327cba31c-evaluation.json'
    assert sha256(source.read_bytes()).hexdigest() == frozen['source_sha256']
    assert sha256(evaluation.read_bytes()).hexdigest() == frozen['evaluation_sha256']
    cases = json.loads((FROZEN / 'development.json').read_text())
    baseline = json.loads((FROZEN / 'development-baseline.json').read_text())
    incumbent = json.loads((FROZEN / 'development-incumbent.json').read_text())
    old_dual = json.loads((FROZEN / 'development-dual.json').read_text())
    evaluator = ProgramEvaluator(cases, baseline, incumbent=incumbent, dual=old_dual)
    result = json.loads(evaluation.read_text())
    row = next(item for item in result['families'] if item['case']['id'] == frozen['case_id'])
    pool = (evaluator.baseline[frozen['case_id']] + evaluator.incumbent[frozen['case_id']] +
            [item['profile'] for item in row['accepted_words']])
    weights = [Fraction(s) for s in row['candidate_lp']['weights']]
    assert len(pool) == 59 and len(weights) == len(pool)
    assert all(w >= 0 for w in weights) and sum(weights) == 1
    active = [i for i, w in enumerate(weights) if w]
    assert active == frozen['support_indices']
    gamma = [sum(w * p['gamma'][j] for w, p in zip(weights, pool)) for j in range(5)]
    assert gamma == [Fraction(28, 5), 6, 6, 6, 6]
    primal = sum(w * p['base'] for w, p in zip(weights, pool))
    assert primal == Fraction(frozen['primal_and_dual_base'])
    tight = frozen['tight_slope_indices_zero_based']
    matrix = [[pool[i]['gamma'][j] for j in tight] + [-1] for i in active]
    rhs = [-pool[i]['base'] for i in active]
    solved = solve(matrix, rhs, exact=True)
    mu = [Fraction(s) for s in frozen['mu']]
    nu = Fraction(frozen['nu'])
    assert solved == mu + [nu] and all(x >= 0 for x in mu)
    costs = [Fraction(p['base']) + sum(x * p['gamma'][j] for x, j in zip(mu, tight)) - nu
             for p in pool]
    assert all(x >= 0 for x in costs) and all(costs[i] == 0 for i in active)
    dual_bound = nu - 6 * sum(mu)
    assert dual_bound == primal
    added = {}
    for name, source_name, evaluation_name, source_key, evaluation_key in (
        ('broker_rejected', 'broker-rejected-complete-proposal.py',
         'broker-rejected-proposal-evaluation/d061094815415ad5-evaluation.json',
         'broker_rejected_source_sha256', 'broker_rejected_evaluation_sha256'),
        ('reweighted', 'sol-beam-k5-reweighted.py',
         'sol-beam-k5-reweighted-eval-01/2e72f7de60d18c1c-evaluation.json',
         'reweighted_source_sha256', 'reweighted_evaluation_sha256'),
    ):
        other_source = HERE / source_name
        other_evaluation = HERE / evaluation_name
        assert sha256(other_source.read_bytes()).hexdigest() == frozen[source_key]
        assert sha256(other_evaluation.read_bytes()).hexdigest() == frozen[evaluation_key]
        other = json.loads(other_evaluation.read_text())
        other_row = next(item for item in other['families'] if item['case']['id'] == frozen['case_id'])
        columns = [item['profile'] for item in other_row['accepted_words']]
        column_costs = [Fraction(p['base']) + sum(x * p['gamma'][j] for x, j in zip(mu, tight)) - nu
                        for p in columns]
        assert len(columns) == 32 and all(x >= 0 for x in column_costs)
        added[name] = {'columns_checked': len(columns), 'minimum_reduced_cost': str(min(column_costs))}
    return {'source_sha256': frozen['source_sha256'], 'evaluation_sha256': frozen['evaluation_sha256'],
            'columns_checked': len(pool), 'support_indices': active,
            'mu': [str(x) for x in mu], 'nu': str(nu),
            'minimum_reduced_cost': str(min(costs)),
            'primal_equals_dual': str(primal),
            'additional_verified_pools': added,
            'combined_columns_checked': len(pool) + sum(item['columns_checked'] for item in added.values()),
            'scope': 'Only these saved finite pools; generated columns outside them can have negative reduced cost.'}


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
