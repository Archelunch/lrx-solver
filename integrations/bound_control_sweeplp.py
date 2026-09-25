"""Sweep-pool exact-LP certifier (control b). Trusted repository code, run in-process.

Same pool as control b16 (integrations/bound_control_sweep.py: every target
rotation x zero assignment x sweep mode), deduplicated by Lemma 1 cost and
pruned to the cost vectors not dominated by another (a dominated word can be
replaced by its dominator in any mixture). The exact LP of the evaluator
(lift_evaluator.mixture_lp / gap_lp) then picks the mixture; the support of the
min-base optimum, plus the gap-LP optimum when the family is not certified, is
returned. This is the strongest deterministic reference; an engine claims
progress only if it beats it on the holdout.

    python -m integrations.bound_control_sweeplp --families F --output OUT [--holdout]
"""
import argparse
import json
from pathlib import Path

from integrations.bound_control_sweep import pool
from integrations.lift_evaluator import gap_lp, mixture_lp


def frontier(words):
    """One word per cost vector, keeping only vectors not dominated componentwise."""
    by_cost = {}
    for w in sorted(words, key=lambda w: (len(w), w)):
        B, beta = words[w]
        by_cost.setdefault((B,) + tuple(beta), w)
    keys = sorted(by_cost)
    keep = [a for a in keys if not any(b != a and all(x <= y for x, y in zip(b, a)) for b in keys)]
    return [(by_cost[c], c[0], list(c[1:])) for c in keep]


def certify(family):
    k, s, T = family['k'], family['slope_bound'], family['budget_unit']
    cols = frontier(pool(family['unit_base']))
    costs = [(B, beta) for _, B, beta in cols]
    w, B, _, t = mixture_lp(costs, k, s)
    pick = {i for i, x in enumerate(w) if x}
    if t or B >= T + 1:
        _, gw, _, _ = gap_lp(costs, k, s, T + 1)
        pick |= {i for i, x in enumerate(gw) if x}
    return {'words': [cols[i][0] for i in sorted(pick)][:32],
            'note': 'pool frontier %d cost vectors; LP base %s' % (len(cols), B)}


def main(argv=None):
    from integrations import bound_evaluator as E

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--families', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--holdout', action='store_true', help='trusted control: does not consume the holdout')
    a = ap.parse_args(argv)
    out = Path(a.output)
    if out.exists():
        raise SystemExit('refusing to overwrite existing %s' % out)
    res = E.evaluate_trusted('integrations.bound_control_sweeplp', E.load_set(a.families, allow_holdout=a.holdout),
                             jobs=a.jobs)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps({x: res[x] for x in ('families', 'certified', 'boundary', 'valid', 'max_W', 'combined_score',
                                          'max_family_cpu', 'families_over_candidate_cpu', 'seconds')}))
    print(json.dumps({m: {x: g[x] for x in ('certified', 'families', 'pct', 'boundary', 'W', 'G')}
                      for m, g in res['per_m'].items()}))


if __name__ == '__main__':
    main()
