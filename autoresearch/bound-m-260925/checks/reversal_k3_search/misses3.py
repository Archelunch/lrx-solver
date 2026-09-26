"""Root misses of survey3.py: (1) unit-origin tree on the two-core front, (2) extended root pool (zero-free turns,
per-core cuts with core 1 seeded on a zero, three cores with cores 1, 2 seeded on zeros) + unit tree,
(3) refined-origin trees (origins with one coordinate 2, first/last picks), depth <= 3, thresholds <= 5.
Search side only; outputs are scored and audited here and re-checked by reversal_k3.py.
    python misses3.py JOBS.json OUT.jsonl WORKERS [stages]"""
import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_k3_search'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search')
import json, time
from multiprocessing import Pool
import gen3
from engine import TreeSearch, to_output
from integrations import lrx_m as C
from integrations.bound_task import make_family
from integrations.lift_evaluator import mixture_lp
from integrations.bound3_evaluator import score_output
from integrations.bound3_audit import audit_claim

ORIG = [(2, 1, 1), (1, 2, 1), (1, 1, 2)]


def zero_cells(st):
    return [i for i, x in enumerate(st) if x == 0]


def ext_front(st, picks, F):
    zc = zero_cells(st)
    gen3.pool(st, picks, zfree=(True,), front=F)                       # zero-free turns
    gen3.pool(st, picks, seeds1=zc, percore=True, front=F)              # per-core cuts, core 1 on a zero
    gen3.pool(st, picks, seeds1=zc, seeds2=zc, seeds3=range(len(st)), three=True, front=F)  # three cores
    return F


def tri(fr):
    return [(b, bt, w) for b, bt, w, p in fr]


def tree(fam, fronts, depth=3, tmax=5):
    return to_output(TreeSearch(fam, fronts, maxdepth=depth, tmax=tmax).run())


def verify(fam, out):
    r = score_output(fam, out)
    au = list(audit_claim(fam, r['output'], r['certificate'])) if r['status'] == 'CERTIFIED' else None
    return r, au


def job(args):
    m, mask, stages = args
    t0 = time.process_time()
    fam = make_family(list(range(m, 0, -1)), mask)
    st, T, k = fam['unit_base'], fam['budget_unit'], 3
    unit = (1, 1, 1)
    row = {'m': m, 'mask': mask, 'gaps': fam['gaps']}
    F = gen3.pool(st, [0, 1, 2])
    fr = gen3.confirm(st, F.pareto(), [0, 1, 2])
    params = {(unit, w): p for b, bt, w, p in fr}  # keyed by (origin, word): equal letters recur across origins
    out, how = None, None
    if 'tree' in stages:
        out = tree(fam, {unit: [([0, 0, 0], tri(fr))]})
        how = 'unit tree, two-core pool'
    if out is None and 'ext' in stages:
        fr = gen3.confirm(st, ext_front(st, [0, 1, 2], F).pareto(), [0, 1, 2])
        params = {(unit, w): p for b, bt, w, p in fr}
        w, B, sl, t = mixture_lp([(b, list(bt)) for b, bt, _, _ in fr], k, m - 2)
        row['ext_root_minB_minus_T'], row['ext_root_slope_excess'] = str(B - T), str(t)
        if t == 0 and B < T + 1:
            out, how = {'words': [wd for x, (b, bt, wd, p) in zip(w, fr) if x]}, 'root, extended pool'
        else:
            out, how = tree(fam, {unit: [([0, 0, 0], tri(fr))]}), 'unit tree, extended pool'
    if out is None and 'orig' in stages:
        fronts = {unit: [([0, 0, 0], tri(fr))]}
        for o in ORIG:
            rs = C.refine(st, list(o))
            lst = []
            for pk in ([0, 0, 0], [x - 1 for x in o]):
                gp = [sum(o[:j]) + pk[j] for j in range(k)]
                f2 = gen3.confirm(rs, gen3.pool(rs, gp).pareto(), gp)
                params.update({(o, w): p for b, bt, w, p in f2})
                lst.append((pk, tri(f2)))
            fronts[o] = lst
        out, how = tree(fam, fronts), 'refined-origin tree, two-core pools'
    if out is not None:
        r, au = verify(fam, out)
        row.update(status=r['status'], audit=au, how=how, output=out, n_leaves=r['n_leaves'],
                   leaves=[{'box': x['box'], 'origins': x['origins'], 'picks': x['picks'], 'lhs': x['lhs']}
                           for x in r['leaves']])
        row['params'] = [[list(o), w, params.get((tuple(o), w))] for o, w in _leafwords(out)]
    else:
        row['status'] = 'NOT_FOUND'
    row['stages'] = stages
    row['cpu'] = round(time.process_time() - t0, 1)
    return row


def _leafwords(out):
    def walk(n):
        if 'words' in n:
            yield from ((tuple(n.get('origins', [1, 1, 1])), w) for w in n['words'])
        else:
            yield from walk(n['le']); yield from walk(n['ge'])
    return list(walk(out['tree'] if 'tree' in out else out))


def _words(out):
    def walk(n):
        if 'words' in n:
            yield from n['words']
        else:
            yield from walk(n['le']); yield from walk(n['ge'])
    return list(walk(out['tree'] if 'tree' in out else out))


if __name__ == '__main__':
    jobs = json.load(open(sys.argv[1]))
    stages = sys.argv[4].split(',') if len(sys.argv) > 4 else ['tree', 'ext', 'orig']
    t0 = time.time()
    with Pool(int(sys.argv[3])) as pool, open(sys.argv[2], 'w') as fo:
        for r in pool.imap_unordered(job, [(m, mask, stages) for m, mask in jobs]):
            fo.write(json.dumps(r) + '\n'); fo.flush()
            print(r['m'], r['mask'], r['gaps'], r['status'], r.get('audit'), r.get('how'), r.get('n_leaves'),
                  r.get('ext_root_minB_minus_T'), r['cpu'], flush=True)
    print('wall', round(time.time() - t0, 1))
