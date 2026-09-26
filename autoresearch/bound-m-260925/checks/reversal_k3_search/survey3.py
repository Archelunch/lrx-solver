"""All three-zero masks of m..1 at one m: root leaf LP over the full two-core pool (gen3.pool = fast.gen_pool front).
Search side only. Root passes are scored (score_output) and audited (audit_claim) here; reversal_k3.py re-checks.
    python survey3.py M OUT.jsonl WORKERS [masks.json]"""
import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_k3_search')
import json, time, itertools
from multiprocessing import Pool
import gen3
from integrations.bound_task import make_family
from integrations.lift_evaluator import mixture_lp
from integrations.bound3_evaluator import score_output
from integrations.bound3_audit import audit_claim


def root_row(fam, fr, tag):
    T, m = fam['budget_unit'], fam['m']
    w, B, sl, t = mixture_lp([(b, list(bt)) for b, bt, _, _ in fr], 3, m - 2)
    ok = t == 0 and B < T + 1
    row = {'m': m, 'mask': fam['mask'], 'gaps': fam['gaps'], 'pool': tag,
           'root_minB_minus_T': str(B - T), 'root_slope_excess': str(t), 'root_slopes': [str(x) for x in sl],
           'support': [[str(x), b - T, list(bt), p] for x, (b, bt, wd, p) in zip(w, fr) if x]}
    if ok:
        out = {'words': [wd for x, (b, bt, wd, p) in zip(w, fr) if x]}
        r = score_output(fam, out)
        row['status'] = r['status']
        if r['status'] == 'CERTIFIED':
            row['audit'] = list(audit_claim(fam, r['output'], r['certificate']))
            row['output'] = out
            row['lhs'] = [x['lhs'] for x in r['leaves']]
    else:
        row['status'] = 'ROOT_FAIL'
    return row


def job(args):
    m, mask = args
    t0 = time.process_time()
    fam = make_family(list(range(m, 0, -1)), mask)
    st = fam['unit_base']
    fr = gen3.confirm(st, gen3.pool(st, [0, 1, 2]).pareto(), [0, 1, 2])
    row = root_row(fam, fr, 'two-core')
    row['cpu'] = round(time.process_time() - t0, 1)
    return row


if __name__ == '__main__':
    m = int(sys.argv[1])
    jobs = [(m, (1 << a) | (1 << b) | (1 << c)) for a, b, c in itertools.combinations(range(m + 1), 3)]
    if len(sys.argv) > 4:
        jobs = [(m, x) for x in json.load(open(sys.argv[4]))]
    t0 = time.time()
    with Pool(int(sys.argv[3])) as pool, open(sys.argv[2], 'w') as fo:
        for r in pool.imap_unordered(job, jobs):
            fo.write(json.dumps(r) + '\n'); fo.flush()
            print(r['m'], r['mask'], r['gaps'], r['status'], r.get('audit'), r['root_minB_minus_T'], r['root_slope_excess'],
                  r['cpu'], flush=True)
    print('wall', round(time.time() - t0, 1))
