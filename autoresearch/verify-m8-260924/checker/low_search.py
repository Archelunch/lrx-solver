"""Driver for the section 7 replication.  usage:
  python low_search.py K all|sample|listed [--sample N --seed S] [--workers W] [--budget NODES]
all     : every unit base with K zeros (K=1 only in practice)
sample  : seeded uniform sample of unit bases with K zeros
listed  : seeded sample of the package's listed exceptions (tree bases in literature/)
"""
import argparse
import itertools
import json
import multiprocessing as mp
import os
import random
import re
import sys
import time
from math import comb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lowsearch import Search, distance_table, independent_check  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LIT = os.path.join(HERE, '..', 'package', 'literature')
PERMS = list(itertools.permutations(range(1, 9)))
DIST = None
ARGS = None


def decode(idx, k):
    n = 8 + k
    combos = list(itertools.combinations(range(n), k))
    pos, pi = divmod(idx, len(PERMS))
    zs = set(combos[pos])
    it = iter(PERMS[pi])
    return tuple(0 if j in zs else next(it) for j in range(n))


def linear_blocks(b):
    return sum(1 for i, x in enumerate(b) if x == 0 and (i == 0 or b[i - 1] != 0))


def listed_exceptions(k):
    """Bases the package lists as exceptions, from literature/ only."""
    if k == 1:
        d = json.load(open(os.path.join(LIT, 'multiset_single_zero_resource_m8_20260919.json')))
        return {tuple(e['state']) for e in d['exceptions']}, 'all 338 listed'
    if k == 2:
        out = set()
        for fn in ['multiset_two_zero_full_cycle_batch_20260920.jsonl']:
            for line in open(os.path.join(LIT, fn), 'rb'):
                m = re.search(rb'"base":(\[[0-9,]*\])', line)
                if m:
                    out.add(tuple(json.loads(m.group(1))))
        fm = json.load(open(os.path.join(LIT, 'multiset_two_zero_resource_20260920.json')))['primary']['first_missing']
        out |= {tuple(b) for b in fm}
        return out, '37323 two-block tree bases + 20 first_missing; the 290 adjacent-zero exceptions are not listed'
    out = set()
    for line in open(os.path.join(LIT, 'multiset_three_zero_full_native_batch_20260920.jsonl'), 'rb'):
        m = re.search(rb'"base":(\[[0-9,]*\])', line[:300])
        if m:
            out.add(tuple(json.loads(m.group(1))))
    return out, '639357 three-block tree bases; the 65 one-block and 36888 two-block exceptions are not listed'


def work(bases):
    S = Search(ARGS.k, DIST, ARGS.budget or None)
    out = []
    for b in bases:
        t = time.time()
        st, w, r, nodes = S.run(b)
        rec = {'base': list(b), 'status': st, 'nodes': nodes, 's': round(time.time() - t, 3)}
        if st == 'found':
            ok, prof = independent_check(b, w, ARGS.k)
            rec['word'] = w
            rec['independent_ok'] = ok
            rec['resource_equals_profile_beta'] = list(r) == prof.beta
        out.append(rec)
    return out


def main():
    global DIST, ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument('k', type=int)
    ap.add_argument('mode', choices=['all', 'sample', 'listed'])
    ap.add_argument('--sample', type=int, default=5000)
    ap.add_argument('--seed', type=int, default=20260924)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--budget', type=int, default=0)
    ap.add_argument('--chunk', type=int, default=20)
    ARGS = args = ap.parse_args()
    try:
        os.nice(10)
    except OSError:
        pass
    t0 = time.time()
    k = args.k
    DIST = distance_table(k)
    listed, listed_note = listed_exceptions(k)
    total = comb(8 + k, k) * len(PERMS)
    rng = random.Random(args.seed)
    if args.mode == 'all':
        bases = [decode(i, k) for i in range(total)]
    elif args.mode == 'sample':
        bases = [decode(i, k) for i in sorted(rng.sample(range(total), args.sample))]
    else:
        pool = sorted(listed)
        bases = sorted(rng.sample(pool, min(args.sample, len(pool))))
    chunks = [bases[i:i + args.chunk] for i in range(0, len(bases), args.chunk)]
    recs = []
    with mp.get_context('fork').Pool(args.workers) as pool:
        for r in pool.imap_unordered(work, chunks):
            recs.extend(r)
    recs.sort(key=lambda r: r['base'])
    counts = {}
    mism = []
    for r in recs:
        b = tuple(r['base'])
        blocks = linear_blocks(b)
        is_listed = b in listed
        key = '%s|blocks=%d|listed=%s' % (r['status'], blocks, is_listed)
        counts[key] = counts.get(key, 0) + 1
        if r['status'] == 'found' and (not r['independent_ok'] or not r['resource_equals_profile_beta']):
            mism.append({'base': r['base'], 'issue': 'found word failed independent check or resource != beta'})
        if r['status'] == 'found' and is_listed:
            mism.append({'base': r['base'], 'issue': 'listed exception but a class word was found', 'word': r['word']})
        # only bases whose block count the listing covers can be compared
        comparable = (k == 1) or (k == 2 and blocks == 2) or (k == 3 and blocks == 3)
        if r['status'] == 'none_in_class' and comparable and not is_listed:
            mism.append({'base': r['base'], 'issue': 'no class word found but base is not listed as exception'})
    out = {
        'k': k, 'mode': args.mode, 'seed': args.seed if args.mode != 'all' else None,
        'bases_searched': len(recs), 'total_unit_bases': total, 'listed_exceptions': len(listed),
        'listed_note': listed_note, 'counts': counts,
        'found': sum(1 for r in recs if r['status'] == 'found'),
        'none_in_class': sum(1 for r in recs if r['status'] == 'none_in_class'),
        'budget_exhausted': sum(1 for r in recs if r['status'] == 'budget'),
        'node_budget': args.budget or None,
        'mismatches': mism,
        'none_in_class_bases': [r['base'] for r in recs if r['status'] == 'none_in_class'][:50000],
        'budget_bases': [r['base'] for r in recs if r['status'] == 'budget'],
        'seconds': round(time.time() - t0, 1), 'workers': args.workers,
        'note': 'none_in_class = exhaustive search found no word in the section-7 resource class; not infeasibility',
    }
    if k == 1 and args.mode == 'all':
        mine = {tuple(r['base']) for r in recs if r['status'] != 'found'}
        out['exception_set_equal_to_listed'] = mine == listed
        out['mine_minus_listed'] = sorted(map(list, mine - listed))
        out['listed_minus_mine'] = sorted(map(list, listed - mine))
    if args.mode != 'all':
        out['records'] = recs
    path = os.path.join(HERE, 'results', 'low_search_k%d_%s.json' % (k, args.mode))
    if os.path.exists(path):
        path = path.replace('.json', '_%d.json' % int(time.time()))
    json.dump(out, open(path, 'w'), indent=1)
    print(json.dumps({x: out[x] for x in ('k', 'mode', 'bases_searched', 'found', 'none_in_class', 'budget_exhausted', 'counts', 'seconds')}))
    print('mismatches', len(mism), mism[:5])
    print('wrote', path)


if __name__ == '__main__':
    main()
