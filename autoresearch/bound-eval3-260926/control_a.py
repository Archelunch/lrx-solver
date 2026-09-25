"""Control (a): campaign-2 AdaEvolve-s2 finalist under bound-eval-3 as a single unit-origin leaf.

1. Data only: re-verify the stored bound-eval-2 output words of development, validation and
   holdout through bound3_evaluator.rescore_stored and compare every family's status and gap.
2. End to end: wrap the frozen finalist source so certify returns {"tree": leaf} and run it in the
   Seatbelt sandbox on development and validation (never the holdout). Writes fresh files only.
"""
import json, sys
from pathlib import Path
from integrations import bound3_evaluator as B3, bound3_audit as A, bound_evaluator as E
from integrations.bound_task import check_family

HERE = Path(__file__).parent
C2 = Path('autoresearch/bound-m-c2-260925')
SETS = {'development': Path('autoresearch/bound-m-260925/frozen/development.json'),
        'validation': C2 / 'frozen/validation.json', 'holdout': C2 / 'frozen/holdout.json'}
WRAP = '''

_certify_c2 = certify


def certify(family):
    out = _certify_c2(family)
    leaf = {"words": out["words"], "origins": [1] * family["k"]}
    if "weights" in out:
        leaf["weights"] = out["weights"]
    return {"tree": leaf}
'''


def fams(p):
    fs = json.loads(p.read_text())['families']
    for f in fs:
        check_family(f)
    return fs


def main():
    summary = {}
    for name, p in SETS.items():
        stored = json.loads((C2 / 'finalists' / (name + '-arms') / 'adaevolve-s2.json').read_text())['result']
        rows = B3.rescore_stored(fams(p), stored['rows'])
        by = {r['id']: r for r in stored['rows']}
        mism = [r['id'] for r in rows if (r['status'], r['gap']) != (by[r['id']]['status'], by[r['id']]['gap'])]
        agg = E.aggregate(rows)
        summary['rescore/' + name] = {'certified': agg['certified'], 'stored_certified': stored['certified'],
                                      'families': agg['families'], 'boundary': agg['boundary'],
                                      'stored_boundary': stored['boundary'], 'max_W': agg['max_W'],
                                      'stored_max_W': stored['max_W'], 'status_or_gap_mismatches': mism}
    src = (C2 / 'finalists/sources/adaevolve-s2.py').read_text() + WRAP
    prog = HERE / 'adaevolve-s2-wrapped.py'
    if not prog.exists():
        prog.write_text(src)
    for name in ('development', 'validation'):
        out = HERE / ('control-a-%s.json' % name)
        if out.exists():
            res = json.loads(out.read_text())
        else:
            fs = fams(SETS[name])
            res = B3.evaluate(prog, fs, require_os_sandbox=True, jobs=8)
            out.write_text(json.dumps(res) + '\n')
        stored = json.loads((C2 / 'finalists' / (name + '-arms') / 'adaevolve-s2.json').read_text())['result']
        by = {r['id']: r for r in stored['rows']}
        mism = [r['id'] for r in res['results'] if (r['status'], r['gap']) != (by[r['id']]['status'], by[r['id']]['gap'])]
        summary['sandbox/' + name] = {'certified': res['certified'], 'stored_certified': stored['certified'],
                                      'combined': res['combined_score'], 'stored_combined': stored['combined_score'],
                                      'incomplete': res['incomplete'], 'isolation': res['isolation'],
                                      'status_or_gap_mismatches': mism,
                                      'audit': {k: v for k, v in A.audit_result(fams(SETS[name]), res).items()
                                                if k != 'disagreements'}}
    (HERE / 'control-a-summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
