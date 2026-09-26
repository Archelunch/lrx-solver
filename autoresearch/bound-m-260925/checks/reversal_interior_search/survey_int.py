"""Interior masks (all k zeros in gaps 1..m-1) of the reversal m..1: root leaf LP over the two-core pool.
Search side only. Stage 1 prices the pool with cuts t0-2..t0+2 (t0 = (m-3)//4); a mask failing there is re-run over
the full two-core pool (all cuts, as reversal_k3_search/survey3.py). Root passes are scored (score_output) and audited
(audit_claim) here; reversal_interior.py re-checks and replays.
    python survey_int.py K M OUT.jsonl WORKERS"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab')
sys.path.insert(0, os.path.join(HERE, '..', 'reversal_k3_search'))
import json, time, itertools
from multiprocessing import Pool
import gen3
from integrations.bound_task import make_family
from integrations.lift_evaluator import mixture_lp
from integrations.bound3_evaluator import score_output
from integrations.bound3_audit import audit_claim


def root_row(fam, fr, tag):
    T, m, k = fam['budget_unit'], fam['m'], fam['k']
    w, B, sl, t = mixture_lp([(b, list(bt)) for b, bt, _, _ in fr], k, m - 2)
    ok = t == 0 and B < T + 1
    row = {'m': m, 'k': k, 'mask': fam['mask'], 'gaps': fam['gaps'], 'pool': tag,
           'root_minB_minus_T': str(B - T), 'root_slope_excess': str(t), 'root_slopes': [str(x) for x in sl],
           'support': [[str(x), b - T, list(bt), p] for x, (b, bt, wd, p) in zip(w, fr) if x]}
    row['status'] = 'ROOT_FAIL'
    if ok:
        out = {'words': [wd for x, (b, bt, wd, p) in zip(w, fr) if x]}
        r = score_output(fam, out)
        row['status'] = r['status']
        if r['status'] == 'CERTIFIED':
            row['audit'] = list(audit_claim(fam, r['output'], r['certificate']))
            row['output'] = out
            row['lhs'] = [x['lhs'] for x in r['leaves']]
    return row


def job(args):
    m, k, gaps = args
    t0 = time.process_time()
    fam = make_family(list(range(m, 0, -1)), sum(1 << g for g in gaps))
    st, picks, tc = fam['unit_base'], list(range(k)), (m - 3) // 4
    cuts = [t for t in range(tc - 2, tc + 3) if 0 <= t <= m]
    row = root_row(fam, gen3.confirm(st, gen3.pool(st, picks, cuts=cuts).pareto(), picks), 'two-core, cuts t0-2..t0+2')
    if row['status'] != 'CERTIFIED':
        row = root_row(fam, gen3.confirm(st, gen3.pool(st, picks).pareto(), picks), 'two-core, all cuts')
    row['cpu'] = round(time.process_time() - t0, 1)
    return row


if __name__ == '__main__':
    k, m = int(sys.argv[1]), int(sys.argv[2])
    jobs = [(m, k, g) for g in itertools.combinations(range(1, m), k)]
    t0 = time.time()
    with Pool(int(sys.argv[4])) as pool, open(sys.argv[3], 'w') as fo:
        for r in pool.imap_unordered(job, jobs):
            fo.write(json.dumps(r) + '\n'); fo.flush()
            print(r['m'], r['k'], r['gaps'], r['pool'], r['status'], r.get('audit'), r['root_minB_minus_T'],
                  r['root_slope_excess'], r['cpu'], flush=True)
    print('wall', round(time.time() - t0, 1))
