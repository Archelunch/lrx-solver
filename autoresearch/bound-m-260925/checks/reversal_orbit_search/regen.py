import sys, json, time
from multiprocessing import Pool
from survey import fronts_for
from engine import TreeSearch, to_output, check, make_family, mixture_lp

LAZY = [(2, 1), (1, 2), (3, 1), (1, 3)]


def solve(args):
    labels, mask, tag = args
    t0 = time.process_time()
    fam = make_family(labels, mask)
    k, m = fam['k'], fam['m']
    fr = fronts_for(fam, [tuple([1] * k)])
    out = to_output(TreeSearch(fam, fr, maxdepth=1, tmax=1).run())
    origins = LAZY if k == 2 else [tuple(2 if i == j else 1 for i in range(k)) for j in range(k)]
    for o in origins:
        if out is not None:
            break
        fr.update(fronts_for(fam, [o]))
        out = to_output(TreeSearch(fam, fr, maxdepth=3, tmax=5).run())
    info = {'tag': tag, 'id': fam['id'], 'labels': labels, 'mask': mask, 'm': m, 'k': k}
    if out is not None:
        row, r = check(fam, out)
        info.update(status=row['status'], gap=row['gap'], audit=row.get('audit'), n_leaves=row['n_leaves'],
                    output=out, leaves=[{'box': x['box'], 'origins': x['origins'], 'picks': x['picks'],
                                         'lhs': x['lhs'], 'support': [[s['weight'], s['base'], s['beta']] for s in x['support']]}
                                        for x in r['leaves']])
    else:
        info['status'] = 'NOT_FOUND'
    info['cpu'] = round(time.process_time() - t0, 1)
    return info


if __name__ == '__main__':
    jobs = json.load(open(sys.argv[1]))
    with Pool(10) as pool, open(sys.argv[2], 'a') as f:
        for info in pool.imap_unordered(solve, [tuple(j) for j in jobs]):
            f.write(json.dumps(info) + '\n'); f.flush()
            print(info['m'], info['mask'], info['tag'], info['status'], info.get('audit'), info.get('n_leaves'), 'cpu', info['cpu'], flush=True)
