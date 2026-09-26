"""Interior masks of the reversal m..1 (every zero in gaps 1..m-1): root certificates over the two-core pool.
Re-check only: this script never searches.

Offline (no provider calls, no tables, no LLM-generated code). Sources, all unchanged search outputs:
  k = 2, m = 9, 10   reversal_orbit_search/k2-m9-10-results.json   (REVERSAL-ORBIT.md)
  k = 2, m = 11, 12  reversal_k2_search/survey-m{11,12}.jsonl      (REVERSAL-K2.md)
  k = 3, m = 9..11   reversal_k3_search/survey-m{9,10,11}.jsonl    (REVERSAL-K3.md)
  k = 2 m = 13, k = 3 m = 12, k = 4 m = 9, 10   reversal_interior_search/survey-k{K}-m{M}.jsonl (this note)

    PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_interior.py --build   # writes
        reversal-interior-words.json from the sources; refuses to overwrite
    PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_interior.py           # re-checks the JSON,
        writes nothing

Both modes, for every stored certificate: bound3_evaluator.score_output must return CERTIFIED,
bound3_audit.audit_claim must return (True, 'ok'), and every word must sort the unit base under lrx_m.run_naive
and lrx_m.run. The script also checks that each (m, k) cell lists every interior mask exactly once.
"""
import ast
import itertools
import json
import sys
import time
from pathlib import Path

from integrations import lrx_m as C
from integrations.bound3_audit import audit_claim
from integrations.bound3_evaluator import score_output
from integrations.bound_task import make_family

HERE = Path(__file__).resolve().parent
OUT = HERE / 'reversal-interior-words.json'
CELLS = [(2, 9), (2, 10), (2, 11), (2, 12), (2, 13), (3, 9), (3, 10), (3, 11), (3, 12), (4, 9), (4, 10)]


def interior(m, gaps):
    return all(1 <= g <= m - 1 for g in gaps)


def load():
    """-> {(k, m): [(gaps, output | None, miss_info | None, source)]}"""
    cells = {c: [] for c in CELLS}
    for x in json.loads((HERE / 'reversal_orbit_search/k2-m9-10-results.json').read_text()):
        m, mask = int(x['m']), int(x['mask'])
        if m not in (9, 10):
            continue
        gaps = [g for g in range(m + 1) if mask >> g & 1]
        if len(gaps) == 2 and interior(m, gaps) and x.get('tag', 'rev_k2') == 'rev_k2':
            ok = x['status'] == 'CERTIFIED'
            cells[(2, m)].append((gaps, (ast.literal_eval(x['output']) if isinstance(x['output'], str) else x['output']) if ok else None,
                                  None if ok else {'root_minB_minus_T': x.get('root_minB_minus_T'),
                                                   'root_slope_excess': x.get('root_slope_excess')},
                                  'reversal_orbit_search/k2-m9-10-results.json'))
    srcs = [((2, m), 'reversal_k2_search/survey-m%d.jsonl' % m) for m in (11, 12)]
    srcs += [((3, m), 'reversal_k3_search/survey-m%d.jsonl' % m) for m in (9, 10, 11)]
    srcs += [((k, m), 'reversal_interior_search/survey-k%d-m%d.jsonl' % (k, m)) for k, m in ((2, 13), (3, 12), (4, 9), (4, 10))]
    for key, f in srcs:
        for line in (HERE / f).read_text().splitlines():
            r = json.loads(line)
            if not interior(r['m'], r['gaps']):
                continue
            ok = r['status'] in ('CERTIFIED', 'ROOT_OK') and 'output' in r
            cells[key].append((r['gaps'], r['output'] if ok else None,
                               None if ok else {'root_minB_minus_T': r['root_minB_minus_T'],
                                                'root_slope_excess': r['root_slope_excess'],
                                                'root_slopes': r.get('root_slopes'),
                                                'support_beta': [s[2] for s in r['support']],
                                                'support_weight': [s[0] for s in r['support']]}, f))
    return cells


def check_output(m, gaps, out):
    fam = make_family(list(range(m, 0, -1)), sum(1 << g for g in gaps))
    r = score_output(fam, out)
    au = tuple(audit_claim(fam, r['output'], r['certificate'])) if r['status'] == 'CERTIFIED' else None
    rep = all(C.is_root(C.run_naive(fam['unit_base'], w)) and C.is_root(C.run(fam['unit_base'], w))
              for w in out['words'])
    return r, au, rep


def completeness(rows_by_cell):
    bad = []
    for (k, m), gl in rows_by_cell.items():
        want = sorted(list(g) for g in itertools.combinations(range(1, m), k))
        if sorted(gl) != want:
            bad.append(('incomplete cell', k, m, len(gl), len(want)))
    return bad


def summarize(data):
    print(' k  m  certified/interior  misses (gaps: B-T, slope excess)')
    for c in data['cells']:
        print('%2d %2d  %4d / %-4d' % (c['k'], c['m'], c['certified'], c['interior']),
              '; '.join('%s: %s, %s' % (x['gaps'], x['root_minB_minus_T'], x['root_slope_excess'])
                        for x in data['misses'] if (x['k'], x['m']) == (c['k'], c['m'])))


def build():
    if OUT.exists():
        sys.exit('refusing to overwrite %s' % OUT)
    t0 = time.time()
    cells, certified, misses, bad, seen = load(), [], [], [], {}
    for (k, m), rows in cells.items():
        seen[(k, m)] = [g for g, *_ in rows]
        for gaps, out, miss, src in rows:
            if out is None:
                miss.update(k=k, m=m, gaps=gaps, source=src,
                            binding='slope' if miss['root_slope_excess'] not in ('0', None) else 'base')
                misses.append(miss)
                continue
            r, au, rep = check_output(m, gaps, out)
            if not (r['status'] == 'CERTIFIED' and au == (True, 'ok') and rep):
                bad.append((k, m, gaps, r['status'], au, rep))
            certified.append({'k': k, 'm': m, 'gaps': gaps, 'source': src, 'output': out,
                              'lhs': [x['lhs'] for x in r['leaves']], 'audit': list(au) if au else None,
                              'replay': rep})
    bad += completeness(seen)
    data = {'date': '2026-09-26', 'notes': 'REVERSAL-INTERIOR.md; conditional on Lemma 1 and criteria (7)/(8) '
                                         '(group, m=8 manuscript) with m as a parameter; root leaf only, unit origins',
            'cells': [{'k': k, 'm': m, 'interior': len(cells[(k, m)]),
                       'certified': sum(1 for r in certified if (r['k'], r['m']) == (k, m))} for k, m in CELLS],
            'certified': certified, 'misses': misses, 'problems': [list(map(str, x)) for x in bad]}
    OUT.write_text(json.dumps(data, indent=1))
    summarize(data)
    print('problems:', bad or 'none', 'wall', round(time.time() - t0, 1))
    sys.exit(1 if bad else 0)


def check():
    t0 = time.time()
    data = json.loads(OUT.read_text())
    bad, seen = [], {c: [] for c in CELLS}
    for row in data['certified']:
        seen[(row['k'], row['m'])].append(row['gaps'])
        r, au, rep = check_output(row['m'], row['gaps'], row['output'])
        if not (r['status'] == 'CERTIFIED' and au == (True, 'ok') and rep):
            bad.append((row['k'], row['m'], row['gaps'], r['status'], au, rep))
    for x in data['misses']:
        seen[(x['k'], x['m'])].append(x['gaps'])
    bad += completeness(seen)
    summarize(data)
    print('stored certified rows re-checked: %d; misses stored: %d' % (len(data['certified']), len(data['misses'])))
    print('problems:', bad or 'none', 'wall', round(time.time() - t0, 1))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    build() if '--build' in sys.argv else check()
