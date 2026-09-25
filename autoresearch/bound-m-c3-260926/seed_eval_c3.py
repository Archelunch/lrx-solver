"""Campaign-3 seed check (offline): c3 seed vs campaign-2 AdaEvolve-s2 as one unit leaf, bound-eval-3.

Runs seed/c3-seed.py in the Seatbelt sandbox (bound3_evaluator.evaluate, no cache) on the campaign-1
development set (m = 9, 10) and the campaign-2 validation set (m = 11), twice each for determinism
(raw tree outputs compared per family), audits every certificate with bound3_audit, and compares per
order class with control (a) of bound-eval3-260926 (AdaEvolve-s2 wrapped, same evaluator). The
holdout is never loaded. Writes fresh files only under seed-eval/.

    python autoresearch/bound-m-c3-260926/seed_eval_c3.py
"""
import collections
import hashlib
import json
from pathlib import Path

from integrations import bound3_audit as A, bound3_evaluator as B3
from integrations.bound_finalize import m_literals
from integrations.bound_evaluator import source_guard
from integrations.bound_task import check_family

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEED = HERE / 'seed' / 'c3-seed.py'
MAN = ROOT / 'autoresearch/bound-m-c2-260925/frozen/manifest.json'
CTRL = ROOT / 'autoresearch/bound-eval3-260926'
OUT = HERE / 'seed-eval'


def sets():
    man = json.loads(MAN.read_text())
    dev = ROOT / man['development']['path']
    val = MAN.parent / 'validation.json'
    if hashlib.sha256(dev.read_bytes()).hexdigest() != man['development']['sha256'] or \
            hashlib.sha256(val.read_bytes()).hexdigest() != man['files']['validation.json']:
        raise SystemExit('frozen set hash mismatch')
    out = {}
    for name, p in (('development', dev), ('validation', val)):
        fs = json.loads(p.read_text())['families']
        for f in fs:
            check_family(f)
        out[name] = fs
    return out


def by_class(rows):
    c = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        c[r['class']][1] += 1
        c[r['class']][0] += r['status'] == 'CERTIFIED'
    return {k: '%d/%d' % tuple(v) for k, v in sorted(c.items())}


def main():
    OUT.mkdir(exist_ok=True)
    src = SEED.read_text()
    summary = {'seed': str(SEED.relative_to(ROOT)), 'seed_sha256': hashlib.sha256(src.encode()).hexdigest(),
               'source_guard': source_guard(src), 'm_literals': m_literals(src),
               'evaluator': B3.VERSION, 'evaluator_hash': B3.evaluator_hash()}
    for name, fams in sets().items():
        runs = []
        for rep in (1, 2):
            p = OUT / ('seed-%s-run%d.json' % (name, rep))
            if p.exists():
                res = json.loads(p.read_text())
            else:
                res = B3.evaluate(SEED, fams, require_os_sandbox=True, jobs=8)
                p.write_text(json.dumps(res) + '\n')
            runs.append(res)
        a, b = ({r['id']: r.get('output') for r in x['results']} for x in runs)
        mism = sorted(i for i in a if a[i] != b.get(i))
        res = runs[0]
        ctrl = json.loads((CTRL / ('control-a-%s.json' % name)).read_text())
        cs = {r['id']: r for r in ctrl['results']}
        new = sorted(r['id'] for r in res['results'] if r['status'] == 'CERTIFIED' and cs[r['id']]['status'] != 'CERTIFIED')
        lost = sorted(r['id'] for r in res['results'] if r['status'] != 'CERTIFIED' and cs[r['id']]['status'] == 'CERTIFIED')
        audit = A.audit_result(fams, res)
        cpu = [r['run']['cpu_seconds'] for r in res['results'] if r.get('run')]
        summary[name] = {
            'families': res['families'], 'certified': res['certified'], 'boundary': res['boundary'],
            'invalid': res['invalid'], 'incomplete': res['incomplete'], 'timeouts': res['timeouts'],
            'max_W': res['max_W'], 'combined_score': res['combined_score'], 'isolation': res['isolation'],
            'per_m': {m: {x: g[x] for x in ('certified', 'families', 'W')} for m, g in res['per_m'].items()},
            'by_class': by_class(res['results']),
            'control_a': {'certified': ctrl['certified'], 'max_W': ctrl['max_W'], 'by_class': by_class(ctrl['results'])},
            'new_vs_control_a': new, 'lost_vs_control_a': lost,
            'trees': sum(1 for r in res['results'] if (r.get('n_leaves') or 0) > 1),
            'max_family_cpu': max(cpu) if cpu else None,
            'deterministic': not mism and runs[1]['certified'] == res['certified'], 'determinism_mismatches': mism,
            'audit': {k: v for k, v in audit.items() if k != 'disagreements'},
            'audit_disagreements': audit.get('disagreements')}
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
