"""Deeper refined-origin tree search for k=2 misses (depth <= 4, thresholds <= 6). Search side only."""
import sys, json, time
from multiprocessing import Pool
from survey import fronts_for
from engine import TreeSearch, to_output, check, make_family

ORIG = [(2, 1), (1, 2), (3, 1), (1, 3), (2, 2), (4, 1), (1, 4)]
# trees-a.jsonl (m=9 masks 17, 33, 544; m=10 masks 33, 65) ran with the longer list
# ORIG = [(2, 1), (1, 2), (3, 1), (1, 3), (2, 2), (4, 1), (1, 4), (3, 2), (2, 3), (5, 1), (1, 5)];
# trees-b.jsonl (m=12 mask 130, m=11 mask 1056) ran with the list above. Nothing else changed.


def solve(args):
    labels, mask, maxdepth, tmax = args
    t0 = time.process_time()
    fam = make_family(labels, mask)
    fr = fronts_for(fam, [(1, 1)])
    out = None
    used = [(1, 1)]
    for o in ORIG:
        fr.update(fronts_for(fam, [o]))
        used.append(o)
        out = to_output(TreeSearch(fam, fr, maxdepth=maxdepth, tmax=tmax).run())
        if out is not None:
            break
    info = {'id': fam['id'], 'labels': labels, 'mask': mask, 'm': fam['m'], 'k': fam['k'], 'origins_tried': used,
            'maxdepth': maxdepth, 'tmax': tmax}
    if out is not None:
        row, r = check(fam, out)
        info.update(status=row['status'], audit=row.get('audit'), n_leaves=row['n_leaves'], output=out)
    else:
        info['status'] = 'NOT_FOUND'
    info['cpu'] = round(time.process_time() - t0, 1)
    return info


if __name__ == '__main__':
    jobs = json.loads(sys.argv[1])
    with Pool(int(sys.argv[3])) as pool, open(sys.argv[2], 'a') as f:
        for info in pool.imap_unordered(solve, [tuple(j) for j in jobs]):
            f.write(json.dumps(info) + '\n'); f.flush()
            print(info['m'], info['mask'], info['status'], info.get('audit'), info.get('n_leaves'), 'cpu', info['cpu'], flush=True)
import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search')  # added when copied from the scratch run directory, which held identical copies of fast.py, gen.py, engine.py, survey.py
