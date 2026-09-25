"""Control (b): staircase tree constructor (integrations/bound3_control_revtree.py) under bound-eval-3.

Named reversal families m..1 with masks {0,4} and {0,m} at m = 8..11, plus every campaign-1
development family that the campaign-2 AdaEvolve-s2 finalist does not certify. Trusted code,
in-process, exact tables used only to find words; every word is replayed by the evaluator and
every certificate re-checked by bound3_audit. Writes control-b.jsonl (fresh file) line by line.
"""
import json, sys, time
from pathlib import Path
from integrations import bound3_control_revtree as R, bound3_evaluator as B3, bound3_audit as A
from integrations.bound_task import make_family, check_family

HERE = Path(__file__).parent
DEV = Path('autoresearch/bound-m-260925/frozen/development.json')
ADA = Path('autoresearch/bound-m-c2-260925/finalists/development-arms/adaevolve-s2.json')


def main():
    out_path = HERE / 'control-b.jsonl'
    done = set()
    if out_path.exists():
        done = {json.loads(x)['id'] for x in out_path.read_text().splitlines() if x.strip()}
    named = [make_family(list(range(m, 0, -1)), 1 | (1 << g), tag='named') for m in (8, 9, 10, 11) for g in (4, m)]
    stored = {r['id']: r for r in json.loads(ADA.read_text())['result']['rows']}
    dev = [dict(f, tag='ada-s2-miss', ada_status=stored[f['id']]['status'], ada_gap=stored[f['id']]['gap'])
           for f in json.loads(DEV.read_text())['families'] if stored[f['id']]['status'] != 'CERTIFIED']
    with out_path.open('a') as fh:
        for f in named + dev:
            if f['id'] in done and f['tag'] != 'named':
                continue
            if f['id'] in done:
                continue
            check_family(f)
            t = time.time()
            out = json.loads(json.dumps(R.certify(f)))
            row = B3.score_output(f, out)
            audit = A.audit_claim(f, row['output'], row['certificate']) if row['status'] == 'CERTIFIED' else None
            rec = {'id': f['id'], 'tag': f['tag'], 'class': f.get('class'), 'k': f['k'], 'status': row['status'],
                   'gap': row['gap'], 'ada_status': f.get('ada_status'), 'ada_gap': f.get('ada_gap'),
                   'note': out.get('note'), 'audit': audit, 'seconds': round(time.time() - t, 1),
                   'leaves': [{'box': x['box'], 'origins': x['origins'], 'status': x['status'], 'gap': x['gap'],
                               'lhs': x['lhs'], 'support': [[s['base'], s['beta'], s['weight'], s['word']]
                                                            for s in x['support']]} for x in row.get('leaves', [])]}
            fh.write(json.dumps(rec) + '\n')
            fh.flush()
            print(rec['id'], rec['status'], rec['gap'], rec['ada_status'], rec['ada_gap'], rec['seconds'], flush=True)


if __name__ == '__main__':
    main()
