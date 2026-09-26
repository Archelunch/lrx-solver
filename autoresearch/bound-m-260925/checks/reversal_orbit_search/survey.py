import sys, json, time, pickle, itertools
from multiprocessing import Pool
from fast import gen_pool, front_fast, C
from engine import TreeSearch, to_output, check, make_family, mixture_lp
from fractions import Fraction as Fr

ORIGINS = [(2, 1), (1, 2), (3, 1), (1, 3), (2, 2)]


def fronts_for(fam, origins, picks_modes=('first', 'last')):
    k = fam['k']
    res = {}
    for o in origins:
        st = C.refine(fam['unit_base'], list(o))
        p = gen_pool(st)
        lst = []
        seen = set()
        for pm in picks_modes:
            pk = tuple(0 if pm == 'first' else oj - 1 for oj in o)
            if pk in seen:
                continue
            seen.add(pk)
            gp = [sum(o[:j]) + pk[j] for j in range(k)]
            lst.append((list(pk), front_fast(st, p, gp)))
        res[tuple(o)] = lst
    return res


def origins_for(k, maxo=3):
    if k >= 4:
        return [tuple(2 if i == j else 1 for i in range(k)) for j in range(k)]
    out = []
    for o in itertools.product(range(1, maxo + 1), repeat=k):
        if sum(x - 1 for x in o) <= 2 and any(x > 1 for x in o):
            out.append(o)
    return out


def solve(args):
    labels, mask, tag = args
    t0 = time.process_time()
    fam = make_family(labels, mask)
    k, m = fam['k'], fam['m']
    fr = fronts_for(fam, [tuple([1] * k)])
    f1 = fr[tuple([1] * k)][0][1]
    w, B, sl, t = mixture_lp([(b, list(bt)) for b, bt, _ in f1], k, m - 2)
    info = {'tag': tag, 'id': fam['id'], 'm': m, 'k': k, 'mask': mask, 'T': fam['budget_unit'],
            'root_minB_minus_T': str(B - fam['budget_unit']), 'root_slope_excess': str(t),
            'root_slopes': [str(x) for x in sl]}
    ts = TreeSearch(fam, fr, maxdepth=1, tmax=1)
    out = to_output(ts.run())
    if out is None:
        fr.update(fronts_for(fam, origins_for(k)))
        ts = TreeSearch(fam, fr, maxdepth=3, tmax=5)
        out = to_output(ts.run())
    if out is not None:
        row, r = check(fam, out)
        info.update(status=row['status'], gap=row['gap'], audit=row.get('audit'), n_leaves=row['n_leaves'],
                    output=out, leaves=[{'box': x['box'], 'origins': x['origins'], 'picks': x['picks'],
                                         'lhs': x['lhs']} for x in r['leaves']])
    else:
        info.update(status='NOT_FOUND')
    info['cpu'] = round(time.process_time() - t0, 1)
    return info


if __name__ == '__main__':
    jobs = json.loads(open(sys.argv[1]).read())
    outp = sys.argv[2]
    t0 = time.time()
    with Pool(int(sys.argv[3]) if len(sys.argv) > 3 else 10) as pool:
        res = []
        for info in pool.imap_unordered(solve, [tuple(j) for j in jobs]):
            res.append(info)
            print(info['m'], info['mask'], info['tag'], info['status'], info.get('gap'), info.get('audit'),
                  info.get('n_leaves'), 'root', info['root_minB_minus_T'], info['root_slope_excess'], 'cpu', info['cpu'],
                  flush=True)
    json.dump(res, open(outp, 'w'), indent=1)
    print('total cpu', sum(x['cpu'] for x in res), 'wall', time.time() - t0)
