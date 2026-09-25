"""Independent audit of CERTIFIED bound-m families from the evaluator's result file.

Deliberately does not import bound_evaluator.py, bound_task.py, lrx_m.py or
lift_evaluator.py. It loads the independent m=8 checker
(autoresearch/verify-m8-260924/checker/lrxm8.py) as a fresh module with M = m
(lift_audit.checker), rebuilds each unit base from (labels, mask) with that
checker, replays every returned word, checks the Lemma 1 lift literally at
z = 0, e_j, 2e_j, every e_j + e_{j+1} and (1,...,1), and checks the claimed
mixture witness exactly: weights >= 0 summing to 1, weighted base < T_m(m+k)+1,
every weighted slope <= m-2. A witness suffices for a claim; the audit does not
search for certificates the scorer missed.

    python -m integrations.bound_audit --families F --results R [R ...]
"""
import argparse
from fractions import Fraction as Fr
import json
from pathlib import Path

from integrations.lift_audit import checker


def budget(m, k):
    return m * (m + 1) // 2 + (k - 1) * (m - 2)


def audit_claim(family, words, claim):
    """-> (agree, reason). `words` are the raw returned words; `claim` the scorer's certificate."""
    try:
        labels, mask = list(family['labels']), family['mask']
        m = len(labels)
        C = checker(m)
        base = C.base_vector(labels, mask)
        k = bin(mask).count('1')
        if base != family['unit_base'] or k != family['k'] or family['budget_unit'] != budget(m, k) \
                or family['slope_bound'] != m - 2:
            return False, 'family fields disagree with independent reconstruction'
        if not 1 <= len(words) <= 32 or any(type(w) is not str or len(w) > 4000 or set(w) - set('LRX')
                                            for w in words):
            return False, 'raw output violates word caps'
        zs = C.z_samples(k, pairs=k - 1)
        if tuple([1] * k) not in zs:
            zs.append(tuple([1] * k))
        costs = {}
        for w in words:
            prof = C.Profile(base, w)  # raises unless it sorts without a zero-zero swap
            C.literal_lift_check(prof, zs)
            costs[w] = (prof.base, prof.beta)
        ws = [Fr(x) for x in claim['weights']]
        if len(ws) != len(claim['words']) or any(x < 0 for x in ws) or sum(ws) != 1:
            return False, 'claimed weights are not a probability vector'
        if any(w not in costs for w in claim['words']):
            return False, 'claimed word not among the returned words'
        B = sum(x * costs[w][0] for x, w in zip(ws, claim['words']))
        slopes = [sum(x * costs[w][1][j] for x, w in zip(ws, claim['words'])) for j in range(k)]
        if not B < budget(m, k) + 1:
            return False, 'weighted base %s not < %d' % (B, budget(m, k) + 1)
        if any(s > m - 2 for s in slopes):
            return False, 'weighted slope above %d' % (m - 2)
        if str(B) != claim.get('base', str(B)):
            return False, 'claimed base %s differs from recomputed %s' % (claim.get('base'), B)
        return True, 'ok'
    except Exception as exc:  # checker errors are disagreements, never crashes
        return False, '%s: %s' % (type(exc).__name__, exc)


def audit_result(families, result):
    by_id = {f['id']: f for f in families}
    rows = [r for r in result['results'] if r['status'] == 'CERTIFIED']
    bad = []
    for r in rows:
        ok, why = audit_claim(by_id[r['id']], r['output_words'], r['certificate'])
        if not ok:
            bad.append({'id': r['id'], 'reason': why})
    return {'certified_claims': len(rows), 'agree': len(rows) - len(bad), 'disagreements': bad}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--families', required=True, nargs='+', help='frozen family files (development/holdout/edge)')
    ap.add_argument('--results', required=True, nargs='+')
    ap.add_argument('--output')
    a = ap.parse_args(argv)
    fams = [f for p in a.families for f in json.loads(Path(p).read_text())['families']]
    report = {p: audit_result(fams, json.loads(Path(p).read_text())) for p in a.results}
    text = json.dumps(report, indent=1)
    if a.output:
        out = Path(a.output)
        if out.exists():
            raise SystemExit('refusing to overwrite existing %s' % out)
        out.write_text(text + '\n')
    print(json.dumps({p: {x: v[x] for x in ('certified_claims', 'agree')} | {'disagreements': len(v['disagreements'])}
                      for p, v in report.items()}))


if __name__ == '__main__':
    main()
