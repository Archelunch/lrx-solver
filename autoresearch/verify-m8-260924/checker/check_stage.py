"""Verify one stage of the LRX m=8 package from its certificate files.

usage: python check_stage.py STAGE [--sample N --seed S] [--workers W] [--out PATH]
STAGE in four five six seven eight nine reverse low1 low2 low3 low3ref
"""
import argparse
import json
import multiprocessing as mp
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lrxm8 import (CheckError, Fr, Profile, Reference, base_vector, leaf_criterion,  # noqa: E402
                   literal_lift_check, mixture_criterion, parse_state, refine, tree_leaves,
                   z_samples)

HERE = os.path.dirname(os.path.abspath(__file__))
LIT = os.path.join(HERE, '..', 'package', 'literature')
RESULTS = os.path.join(HERE, 'results')

STAGES = {
    'four': ('search', 'multiset_four_gap_bounded_search_20260924.json',
             'multiset_four_gap_bounded_repairs_final_20260924.json', 4),
    'five': ('search', 'multiset_five_gap_bounded_search_20260924.json',
             'multiset_five_gap_bounded_repairs_final_20260924.json', 5),
    'six': ('search', 'multiset_six_gap_bounded_search_20260924.json',
            'multiset_six_gap_bounded_repairs_final_20260924.json', 6),
    'seven': ('complement', 'multiset_seven_gap_complement_certificates_20260924.json', None, 7),
    'eight': ('complement', 'multiset_eight_gap_complement_certificates_20260924.json', None, 8),
    'nine': ('complement', 'multiset_nine_gap_complete_certificates_20260924.json', None, 9),
    'reverse': ('reverse', 'multiset_reverse_m8_complete_certificates_20260923.json', None, None),
    'low1': ('low1', 'multiset_single_zero_mixture_certificates_20260919.json', None, 1),
    'low2': ('jsonl', ['multiset_two_zero_full_cycle_batch_20260920.jsonl'] +
             ['multiset_two_zero_refinement_round%d_20260920.jsonl' % i for i in range(1, 9)], None, 2),
    'low3': ('jsonl', ['multiset_three_zero_full_native_batch_20260920.jsonl',
                       'multiset_three_zero_refinement_follow1_20260920.jsonl',
                       'multiset_three_zero_refinement_follow2_20260920.jsonl',
                       'multiset_three_zero_last_family_20260920.jsonl'], None, 3),
    'low3ref': ('jsonl', ['multiset_three_zero_refinement_follow1_20260920.jsonl',
                          'multiset_three_zero_refinement_follow2_20260920.jsonl',
                          'multiset_three_zero_last_family_20260920.jsonl'], None, 3),
}

REVERSE_FILE = 'multiset_reverse_m8_complete_certificates_20260923.json'

CATALOG = []   # list of (state, word) for comparison stages
ITEMS = []     # family items
REVERSE_BY_BASE = {}


def popcount(x):
    return bin(x).count('1')


def load_reverse():
    d = json.load(open(os.path.join(LIT, REVERSE_FILE)))
    return {tuple(f['base']): f['tree'] for f in d['families']}


def load_stage(stage, sample_idx_fn=None):
    """Fill CATALOG / ITEMS.  Returns metadata dict."""
    kind, f1, f2, k = STAGES[stage]
    meta = {'files': []}
    if kind in ('search', 'complement'):
        d = json.load(open(os.path.join(LIT, f1)))
        meta['files'].append(f1)
        CATALOG.extend((tuple(c['state']), c['word']) for c in d['catalog'])
        repairs = {}
        if f2:
            r = json.load(open(os.path.join(LIT, f2)))
            meta['files'].append(f2)
            for res in r['results']:
                repairs[(res['mask'], tuple(res['labels']))] = res['result']
        fallback = None
        for rec in d['records']:
            mask = rec.get('mask', 511)
            labels = tuple(rec['labels'])
            mix = rec.get('mixture')
            if rec.get('method') == 'unresolved' or mix is None:
                if (mask, labels) in repairs:
                    res = repairs.pop((mask, labels))
                    ITEMS.append(('tree', mask, labels, rec['order_index'], tuple(res['base']), res['tree'], 'repair'))
                else:
                    if fallback is None:
                        fallback = load_reverse()
                    base = tuple(base_vector(labels, mask))
                    ITEMS.append(('tree', mask, labels, rec['order_index'], base, fallback.get(base), 'reverse_fallback'))
                continue
            claimed = None
            if 'check' in rec:
                claimed = (rec['check']['base'], rec['check']['beta'])
            rows = tuple((m['source'], m['cut'], m['weight']) for m in mix)
            ITEMS.append(('mix', mask, labels, rec['order_index'], rows, claimed))
        meta['unused_repairs'] = [list(key) for key in repairs]
        meta['declared_counts'] = d.get('counts')
        meta['target_total'] = d.get('target_total')
    elif kind == 'reverse':
        d = json.load(open(os.path.join(LIT, f1)))
        meta['files'].append(f1)
        for fam in d['families']:
            labels, mask, _ = parse_state(fam['base'])
            ITEMS.append(('tree', mask, tuple(labels), None, tuple(fam['base']), fam['tree'], 'reverse'))
    elif kind == 'low1':
        d = json.load(open(os.path.join(LIT, f1)))
        meta['files'].append(f1)
        for fam in d['families']:
            labels, mask, _ = parse_state(fam['state'])
            ITEMS.append(('lowmix', mask, tuple(labels), None, tuple(fam['state']), fam['rows'],
                          (fam['checked']['mean_base'], fam['checked']['mean_beta'])))
    elif kind == 'jsonl':
        # index case lines first, then parse only the selected ones
        index = []
        status = {}
        for fn in f1:
            path = os.path.join(LIT, fn)
            meta['files'].append(fn)
            with open(path, 'rb') as fh:
                off = 0
                for line in fh:
                    if line.startswith(b'{"kind":"case"'):
                        st = b'"status":"certified"' in line[:400]
                        index.append((fn, off, st))
                    off += len(line)
        meta['case_lines'] = len(index)
        meta['certified_case_lines'] = sum(1 for x in index if x[2])
        pool = [i for i, x in enumerate(index) if x[2]]
        chosen = sample_idx_fn(len(pool)) if sample_idx_fn else range(len(pool))
        handles = {}
        for c in chosen:
            fn, off, _ = index[pool[c]]
            if fn not in handles:
                handles[fn] = open(os.path.join(LIT, fn), 'rb')
            fh = handles[fn]
            fh.seek(off)
            case = json.loads(fh.readline())
            labels, mask, _ = parse_state(case['base'])
            ITEMS.append(('tree', mask, tuple(labels), case.get('rank'), tuple(case['base']), case['tree'],
                          '%s@%d' % (fn, off)))
        meta['sampled_from_certified_lines'] = True
    return meta


# ------------------------------------------------------------------ worker
_REFS = {}
_STATS = None


def get_ref(src, zs, stats):
    ref = _REFS.get(src)
    if ref is None:
        if len(_REFS) > 60000:
            _REFS.clear()
        state, word = CATALOG[src]
        ref = Reference(state, word)
        stats['reference_words'] += 1
        stats['reference_letters_literal'] += literal_lift_check(ref.prof, zs)
        if not ref.prof.same_sign:
            stats['same_sign_violations'] += 1
        _REFS[src] = ref
    return ref


def verify_item(item, stats):
    kind, mask = item[0], item[1]
    k = popcount(mask)
    zs = z_samples(k)
    if kind == 'mix':
        _, mask, labels, oi, rows, claimed = item
        P = base_vector(labels, mask)
        costs = []
        for src, cut, w in rows:
            ref = get_ref(src, zs, stats)
            b, bt, _ = ref.transfer(P, cut)
            stats['literal_transfer_letters'] += ref.literal_transfer(P, cut, zs, b, bt)
            stats['mixture_rows'] += 1
            costs.append((b, bt))
        ok, B, beta = mixture_criterion(costs, [r[2] for r in rows], k)
        if claimed is not None and (Fr(claimed[0]) != B or [Fr(x) for x in claimed[1]] != beta):
            stats['claim_mismatches'].append({'mask': mask, 'labels': list(labels),
                                              'claimed': claimed, 'recomputed': [str(B), [str(x) for x in beta]]})
        if not ok:
            raise CheckError('criterion (7) fails: Bbar=%s beta=%s budget<%d' % (B, [str(x) for x in beta], 31 + 6 * k))
        return
    if kind == 'lowmix':
        _, mask, labels, oi, state, rows, claimed = item
        costs = []
        for row in rows:
            prof = Profile(list(state), row['word'])
            stats['reference_letters_literal'] += literal_lift_check(prof, zs)
            stats['mixture_rows'] += 1
            if (prof.base, prof.beta) != (row['base_cost'], row['beta']):
                stats['claim_mismatches'].append({'labels': list(labels), 'mask': mask, 'word': row['word'],
                                                  'claimed': [row['base_cost'], row['beta']],
                                                  'recomputed': [prof.base, prof.beta]})
            costs.append((prof.base, prof.beta))
        ok, B, beta = mixture_criterion(costs, [r['weight'] for r in rows], k)
        if not ok:
            raise CheckError('criterion (7) fails: Bbar=%s beta=%s' % (B, [str(x) for x in beta]))
        return
    if kind == 'tree':
        _, mask, labels, oi, base, tree, origin_tag = item
        if tree is None:
            raise CheckError('no tree certificate found (%s)' % origin_tag)
        if list(base) != base_vector(labels, mask):
            raise CheckError('tree base does not match family')
        box = [(1, None)] * k
        for leaf, lbox in tree_leaves(tree, box):
            stats['tree_leaves'] += 1
            rows = []
            for row in leaf['rows']:
                state = refine(list(base), row['origin'])
                prof = Profile(state, row['word'], row['picks'])
                stats['tree_rows'] += 1
                stats['reference_letters_literal'] += literal_lift_check(prof, zs)
                if not prof.same_sign:
                    stats['same_sign_violations'] += 1
                if (prof.base, prof.beta) != (row['base_cost'], row['beta']):
                    stats['claim_mismatches'].append({'labels': list(labels), 'mask': mask, 'word': row['word'],
                                                      'claimed': [row['base_cost'], row['beta']],
                                                      'recomputed': [prof.base, prof.beta]})
                rows.append((row['weight'], prof.base, prof.beta, row['origin']))
            ok, C, g, ex = leaf_criterion(rows, lbox)
            if not ok:
                raise CheckError('leaf criterion (8) fails on box %s: excess=%s gbar=%s' % (lbox, ex, [str(x) for x in g]))
        return
    raise CheckError('unknown item kind')


def new_stats():
    return {'families': 0, 'passed': 0, 'failed': [], 'mixture_rows': 0, 'tree_rows': 0, 'tree_leaves': 0,
            'reference_words': 0, 'reference_letters_literal': 0, 'literal_transfer_letters': 0,
            'same_sign_violations': 0, 'claim_mismatches': [], 'by_kind': {}}


def work(idx_chunk):
    stats = new_stats()
    for i in idx_chunk:
        item = ITEMS[i]
        stats['families'] += 1
        tag = item[0] if item[0] != 'tree' else 'tree:' + item[6].split('@')[0]
        stats['by_kind'][tag] = stats['by_kind'].get(tag, 0) + 1
        try:
            verify_item(item, stats)
            stats['passed'] += 1
        except CheckError as e:
            stats['failed'].append({'index': i, 'mask': item[1], 'labels': list(item[2]),
                                    'order_index': item[3], 'reason': str(e)})
    return stats


def merge(a, b):
    for key, v in b.items():
        if isinstance(v, list):
            a[key].extend(v)
        elif isinstance(v, dict):
            for kk, vv in v.items():
                a[key][kk] = a[key].get(kk, 0) + vv
        else:
            a[key] += v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=sorted(STAGES))
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--chunk', type=int, default=400)
    ap.add_argument('--out', default=None)
    ap.add_argument('--slice', default=None, help='jsonl stages only: i/n takes certified cases with index %% n == i')
    args = ap.parse_args()
    try:
        os.nice(10)
    except OSError:
        pass
    t0 = time.time()
    rng = random.Random(args.seed)
    kind = STAGES[args.stage][0]
    sample_fn = (lambda n: sorted(rng.sample(range(n), min(args.sample, n)))) if args.sample else None
    if args.slice:
        si, sn = map(int, args.slice.split('/'))
        sample_fn = lambda n: range(si, n, sn)  # noqa: E731
    meta = load_stage(args.stage, sample_fn if kind == 'jsonl' else None)
    t_load = time.time() - t0
    fams = [(it[1], it[2]) for it in ITEMS]
    structure = {'items': len(ITEMS), 'distinct_families': len(set(fams)),
                 'masks': len(set(m for m, _ in fams))}
    k = STAGES[args.stage][3]
    if k is not None and kind != 'jsonl':
        structure['wrong_popcount'] = sum(1 for m, _ in fams if popcount(m) != k)
    if args.sample and kind != 'jsonl':
        chosen = sorted(rng.sample(range(len(ITEMS)), min(args.sample, len(ITEMS))))
    else:
        chosen = list(range(len(ITEMS)))
    chunks = [chosen[i:i + args.chunk] for i in range(0, len(chosen), args.chunk)]
    stats = new_stats()
    if args.workers > 1:
        ctx = mp.get_context('fork')
        with ctx.Pool(args.workers) as pool:
            for s in pool.imap_unordered(work, chunks):
                merge(stats, s)
    else:
        for c in chunks:
            merge(stats, work(c))
    stats['failed'].sort(key=lambda x: x['index'])
    out = {
        'stage': args.stage,
        'mode': 'sample' if args.sample else ('slice ' + args.slice if args.slice else 'full'),
        'seed': args.seed if args.sample else None,
        'sample_size': len(chosen) if args.sample else None,
        'chosen_indices': chosen if args.sample and kind != 'jsonl' else None,
        'z_samples_per_k': 'z=0, e_j, 2e_j (all j), e_i+e_{i+1} (i<3)',
        'meta': meta,
        'structure': structure,
        'counts': {k2: (len(v) if isinstance(v, list) else v) for k2, v in stats.items()},
        'failures': stats['failed'][:2000],
        'claim_mismatches': stats['claim_mismatches'][:2000],
        'seconds_load': round(t_load, 1),
        'seconds_total': round(time.time() - t0, 1),
        'workers': args.workers,
    }
    if kind == 'jsonl' and args.sample:
        out['chosen_note'] = 'items sampled uniformly from certified case lines; item tag holds file@offset'
        out['chosen_items'] = [[it[3], it[6]] for it in ITEMS]
    suffix = '_sample' if args.sample else ('_slice%s' % args.slice.replace('/', 'of') if args.slice else '')
    path = args.out or os.path.join(RESULTS, '%s%s.json' % (args.stage, suffix))
    if os.path.exists(path):
        base, ext = os.path.splitext(path)
        path = '%s_%d%s' % (base, int(time.time()), ext)
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k2: out[k2] for k2 in ('stage', 'mode', 'structure', 'counts', 'seconds_total')}))
    print('wrote', path)


if __name__ == '__main__':
    main()
