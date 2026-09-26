"""Trusted evaluator for bound-m tree certificates (bound-eval-3, bound-contract-3).

A candidate exposes `certify(family) -> {"tree": NODE}` (schema and limits in
bound3_task.py) or the bound-contract-2 output {"words": [...]}, which is a single
root leaf with unit origins and scores exactly as bound-eval-2. The sandbox,
CPU accounting, source guard and aggregates are bound-eval-2's (bound_evaluator.py,
unchanged); only the verification differs.

Per leaf with box prod_j [l_j, h_j] (h_j = inf allowed) and origins o (o_j <= l_j):
every word must sort the refined base lrx_m.refine(unit_base, o) with no zero-zero
swap (lrx_m.Profile with the leaf's picks) and pass literal lifted execution at
z = 0, e_j, 2e_j, e_j+e_{j+1}, (1..1) above the origin, and at the leaf's box points
u = l, l+e_j, l+2e_j for the LP support words. The cost of word i is formula (6),
C_i(u) = B_i + beta_i.(u - o). The exact rational LP minimizes the left side of the
group's criterion (8),

    Cbar(l) - T(l) + sum_{j bounded} max(0, betabar_j - s)(h_j - l_j),
    subject to betabar_j <= s on every unbounded axis,

with T(l) = T_m(m + sum l) and s = m-2. A leaf passes iff the optimum is < 1; the
optimum is re-checked with lrx_m.leaf_criterion(m=m). A leaf with no bounded axis
uses lift_evaluator.mixture_lp / gap_lp on the shifted bases, as bound-eval-2 does.
Leaf gap = min_w max(0, lhs - 1) + max(0, max over unbounded j of betabar_j - s).
The family is CERTIFIED iff every leaf passes; otherwise gap = max leaf gap and
status BOUNDARY iff that gap is 0. A certificate proves d(v) <= T_m(n) for every
state of the family (the tree covers [1, inf)^k by construction, lrx_m.tree_leaves),
conditional on the group's Lemma 1 with refinement. A miss proves nothing.

    python -m integrations.bound3_evaluator --program P --families F --output OUT
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from fractions import Fraction as Fr
import importlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from integrations import bound3_task as K
from integrations import bound_evaluator as E
from integrations import lrx_m as C
from integrations.lift_evaluator import gap_lp, mixture_lp, simplex
from integrations.program_sandbox import SandboxUnavailable, sandbox_command, sandbox_profile

VERSION = 'bound-eval-3'
CONTRACT = ('bound-contract-3: certify(family) -> {"tree": NODE, "note"?}; NODE = split {"j", "t", "le", "ge"} '
            '(u_j <= t | u_j >= t+1, 1 <= t <= %d) or leaf {"words", "origins"? (default 1s), "picks"? (default 0s), '
            '"weights"?}; root box [1,inf)^k; depth <= %d, <= %d leaves, 1..%d words per leaf, <= %d letters per '
            'word, <= %d letters in all; o_j <= l_j. A plain {"words": [...]} is one root leaf with unit origins. '
            'Words are literal on the refined base (block j has o_j atoms), priced by Lemma 1 with formula (6), '
            'literal lift at z = 0, e_j, 2e_j, e_j+e_{j+1}, (1..1) above o and at box points l, l+e_j, l+2e_j for '
            'LP support words. Leaf passes iff the exact LP optimum of criterion (8) is < 1 with unbounded slopes '
            '<= m-2, T(l) = T_m(m+sum l); CERTIFIED iff every leaf passes; gap = max leaf gap; BOUNDARY iff not '
            'certified and gap 0. Sandbox, CPU limits, source guard, invalid gap 4000 and the combined score are '
            'bound-contract-2\'s.' % (K.MAX_THRESHOLD, K.MAX_DEPTH, K.MAX_LEAVES, K.MAX_LEAF_WORDS, K.MAX_LETTERS,
                                        K.MAX_TOTAL_LETTERS))
MAX_READ = 1 << 20  # worker output file cap (bound3_worker MAX_JSON is below it)
_SOURCES = ('bound3_evaluator.py', 'bound3_task.py', 'bound3_worker.py')


def evaluator_hash():
    here = Path(__file__).parent
    return E._sha(VERSION.encode() + E.evaluator_hash().encode() + b''.join((here / f).read_bytes() for f in _SOURCES))


# ------------------------------------------------------------- sandbox run (bound_evaluator.run_batch, new worker)

def _kill_group(proc):
    """Kill the worker's process group; never raise. Under Seatbelt the group can hold a member the
    caller may not signal (EPERM), and the group may already be gone (ESRCH)."""
    for fn in (lambda: os.killpg(proc.pid, signal.SIGKILL), proc.kill):
        try:
            fn()
        except (ProcessLookupError, PermissionError, OSError):
            pass

def run_batch(source, families, per_family=E.PER_FAMILY_CPU, require_os_sandbox=True,
              per_family_wall=E.PER_FAMILY_WALL):
    wall = per_family_wall * len(families) + E.IMPORT_CPU * 5 + 5.0
    cpu_cap = per_family * len(families) + E.IMPORT_CPU + E.STARTUP_CPU
    with tempfile.TemporaryDirectory(prefix='lrx-bound3-') as temp:
        scratch = Path(temp).resolve()
        (scratch / 'candidate.py').write_bytes(source)
        shutil.copyfile(Path(__file__).with_name('bound3_worker.py'), scratch / 'worker.py')
        (scratch / 'case.json').write_text(json.dumps({'families': families, 'per_family_cpu': per_family,
                                                       'per_family_wall': per_family_wall,
                                                       'import_cpu': E.IMPORT_CPU}))
        command = [sys.executable, *E._WORKER_FLAGS, str(scratch / 'worker.py'), str(scratch / 'candidate.py'),
                   str(scratch / 'case.json'), str(scratch)]
        isolation = 'process_only'
        if require_os_sandbox:
            profile = sandbox_profile(read_paths=(sys.base_prefix, '/usr', '/System', '/Library', '/private/etc'),
                                      write_paths=(scratch,)) + '(deny process-fork)\n'
            (scratch / 'sandbox.sb').write_text(profile, encoding='utf-8')
            command = sandbox_command(command, scratch / 'sandbox.sb')
            isolation = 'macos_seatbelt'
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(scratch), 'TMPDIR': str(scratch), 'PYTHONNOUSERSITE': '1',
               'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C', 'LC_ALL': 'C', **E._WORKER_ENV}
        start = time.monotonic()
        with (scratch / 'stdout').open('wb') as so, (scratch / 'stderr').open('wb') as se:
            proc = subprocess.Popen(command, cwd=scratch, env=env, stdin=subprocess.DEVNULL, stdout=so, stderr=se,
                                    start_new_session=True, preexec_fn=lambda: E._batch_preexec(cpu_cap))
            try:
                killed, cpu = E._reap(proc, wall)
            finally:
                _kill_group(proc)
        meta = {'seconds': time.monotonic() - start, 'cpu_seconds': cpu, 'isolation': isolation}
        log = (scratch / 'stderr').read_bytes()[:4096].decode('utf-8', 'replace')
        if 'sandbox_apply: Operation not permitted' in log:
            raise SandboxUnavailable('macOS Seatbelt denied by outer execution environment')
        header = {'status': 'INCOMPLETE', 'reason': 'batch wall limit' if killed else
                  'worker exit %s (a negative code or SIGXCPU is the kernel CPU cap)' % proc.returncode,
                  'stderr': log[-600:]}
        hpath = scratch / 'header.json'
        if hpath.is_file() and hpath.stat().st_size <= MAX_READ:
            try:
                obj = json.loads(hpath.read_text(encoding='utf-8', errors='replace'))
                header = obj if isinstance(obj, dict) and obj.get('status') in ('ok', 'candidate_error') \
                    else {'status': 'INCOMPLETE', 'reason': 'worker header must be a status object'}
            except ValueError:
                pass
        items = [None] * len(families)
        for i in range(len(families)):
            p = scratch / ('out-%04d.json' % i)
            if p.is_file() and p.stat().st_size <= MAX_READ:
                try:
                    obj = json.loads(p.read_text(encoding='utf-8', errors='replace'))
                except ValueError:
                    continue
                if isinstance(obj, dict) and obj.get('index') == i:
                    items[i] = obj
        if header.get('status') == 'ok' and (killed or proc.returncode):
            header = dict(header, killed='batch wall limit' if killed else
                          'batch process ended with code %s (kernel CPU cap)' % proc.returncode)
        why = E.cpu_check(cpu, items, len(families), per_family)
        if why:
            header = {'status': 'INCOMPLETE', 'timeout': True, 'reason': why}
        return dict(meta, header=header, items=items)


# ------------------------------------------------------------- leaf LP (criterion (8))
def leaf_lp(costs, box, s, T):
    """costs: [(C_i(l), beta_i)] at the leaf's lower corner l; box [(l, h|None)]; T = T(l).
    -> dict(status, weights, value = min lhs of (8) or None, gap, gap_weights, t)."""
    k, n = len(box), len(costs)
    bnd = [j for j in range(k) if box[j][1] is not None]
    if not bnd:  # bound-eval-2 path on the shifted bases (identical for the unit root leaf)
        w, B, _, t = mixture_lp(costs, k, s)
        if t == 0 and B < T + 1:
            return {'status': 'CERTIFIED', 'weights': w, 'value': B - T, 'gap': Fr(0)}
        g, gw, gB, gs = gap_lp(costs, k, s, T + 1)
        return {'status': 'BOUNDARY' if g == 0 else 'NO_CERTIFICATE', 'weights': gw, 'value': None, 'gap': g,
                'gap_value': gB - T, 't': max(Fr(0), max(gs) - s)}
    nb, width = len(bnd), [box[j][1] - box[j][0] for j in bnd]
    col = {j: i for i, j in enumerate(bnd)}

    def slope_rows(extra):  # beta_j(w) - e_j [bounded] (- t [unbounded]) + slack_j = s
        return [[bt[j] for _, bt in costs] + [-int(col.get(j) == i) for i in range(nb)]
                + [int(i == j) for i in range(k)] + ([-int(j not in col)] if extra else []) for j in range(k)]

    A = slope_rows(False) + [[1] * n + [0] * (nb + k)]
    st, x, val = simplex(A, [s] * k + [1], [b for b, _ in costs] + width + [0] * k)
    if st == 'optimal' and val < T + 1:
        return {'status': 'CERTIFIED', 'weights': x[:n], 'value': val - T, 'gap': Fr(0)}
    # gap: columns w, e, slack, t, u, base slack; min t + u
    A = [r + [0, 0] for r in slope_rows(True)]
    A.append([b for b, _ in costs] + width + [0] * k + [0, -1, 1])
    A.append([1] * n + [0] * (nb + k) + [0, 0, 0])
    st, x, g = simplex(A, [s] * k + [T + 1, 1], [0] * (n + nb + k) + [1, 1, 0])
    w = x[:n]
    lhs = sum(wi * b for wi, (b, _) in zip(w, costs)) + sum(e * h for e, h in zip(x[n:n + nb], width))
    return {'status': 'BOUNDARY' if g == 0 else 'NO_CERTIFICATE', 'weights': w, 'value': None, 'gap': g,
            'gap_value': lhs - T, 't': x[n + nb + k]}


# ------------------------------------------------------------- verification
def box_points(box, origins):
    """z (above the origin) for u = l, l+e_j, l+2e_j."""
    z0 = [l - o for (l, _), o in zip(box, origins)]
    out = [tuple(z0)]
    for j in range(len(box)):
        for d in (1, 2):
            z = list(z0)
            z[j] += d
            out.append(tuple(z))
    return out


def _text(x):
    return 'inf' if x is None else x


def score_output(fam, out):
    """Verify one parsed candidate output for one family -> row fields (no run metadata).
    Raises nothing on bad output: invalid output is a status."""
    m, k, T, s = fam['m'], fam['k'], fam['budget_unit'], fam['slope_bound']
    if T != C.budget(m, k) or s != m - 2:
        raise ValueError('budget or slope bound disagrees with T_m(m+k), m-2')
    row = {'valid': False, 'gap': str(E.INVALID_GAP)}
    try:
        tree, note = K.parse_output(out, k)
        leaves = list(C.tree_leaves(tree, [(1, None)] * k))
    except (ValueError, TypeError, C.CheckError) as exc:
        return dict(row, status='INVALID_OUTPUT', trace={'failure': str(exc)[:300]})
    if note:
        row['note'] = note
    zs, cache, info = E.z_points(k), {}, []
    for li, (leaf, box) in enumerate(leaves):
        o = leaf['origins']
        if any(o[j] > box[j][0] for j in range(k)):
            return dict(row, status='INVALID_OUTPUT', trace={'failure': 'leaf %d: origin %s exceeds lower corner %s'
                                                             % (li, o, [l for l, _ in box])})
        state = C.refine(fam['unit_base'], o)
        picks = K.pick_indices(o, leaf['picks'])
        profs = []
        for i, w in enumerate(leaf['words']):
            key = (w, tuple(o), tuple(picks))
            if key not in cache:
                try:
                    prof = C.Profile(state, w, picks)
                except C.CheckError as exc:
                    return dict(row, status='INVALID_OUTPUT', trace={'failed_word': dict(
                        E.diagnose(state, w), leaf=li, index=i, length=len(w), reason=str(exc))})
                try:
                    C.literal_lift_check(prof, zs)
                except C.CheckError as exc:  # Lemma 1 says this cannot happen
                    return dict(row, status='INVALID_OUTPUT', lemma1_literal_failure=True,
                                trace={'failed_word': {'leaf': li, 'index': i, 'reason': str(exc)}})
                cache[key] = prof
            profs.append(cache[key])
        l = [a for a, _ in box]
        Tl = C.budget(m, sum(l))
        costs = [(p.base + sum(b * (x - y) for b, x, y in zip(p.beta, l, o)), list(p.beta)) for p in profs]
        res = leaf_lp(costs, box, s, Tl)
        support = [i for i, x in enumerate(res['weights']) if x]
        for i in support:  # literal cross-check of formula (6) at the box points
            try:
                C.literal_lift_check(profs[i], box_points(box, o))
            except C.CheckError as exc:
                return dict(row, status='INVALID_OUTPUT', lemma1_literal_failure=True,
                            trace={'failed_word': {'leaf': li, 'index': i, 'reason': 'box point: ' + str(exc)}})
        if res['status'] == 'CERTIFIED':
            rows = [(res['weights'][i], profs[i].base, profs[i].beta, o) for i in support]
            ok, Cl, _, excess = C.leaf_criterion(rows, box, m=m)
            if not ok or excess != res['value']:
                raise AssertionError('leaf LP and leaf_criterion disagree')  # evaluator bug, never a score
        wts = res['weights']
        info.append({'leaf': li, 'box': [[a, _text(b)] for a, b in box], 'origins': o, 'picks': leaf['picks'],
                     'T': Tl, 'status': res['status'], 'gap': str(res['gap']),
                     'lhs': str(res['value'] if res['value'] is not None else res['gap_value']),
                     'slope_excess': str(res.get('t', 0)),
                     'support': [{'index': i, 'word': leaf['words'][i], 'weight': str(wts[i]),
                                  'base': profs[i].base, 'beta': list(profs[i].beta), 'cost_at_l': str(costs[i][0])}
                                 for i in support],
                     'given_weights_pass': None if leaf['weights'] is None else
                     _given(leaf['weights'], profs, box, o, m)})
    gap = max(Fr(x['gap']) for x in info)
    ok = all(x['status'] == 'CERTIFIED' for x in info)
    row.update(valid=True, leaves=info, n_leaves=len(info), output=out,
               status='CERTIFIED' if ok else 'BOUNDARY' if gap == 0 else 'NO_CERTIFICATE', gap=str(gap))
    if len(info) == 1 and info[0]['origins'] == [1] * k:
        row['output_words'] = leaves[0][0]['words']
    if ok:
        row['certificate'] = {'leaves': [{'box': x['box'], 'origins': x['origins'], 'picks': x['picks'],
                                          'words': [r['word'] for r in x['support']],
                                          'weights': [r['weight'] for r in x['support']]} for x in info]}
    worst = max(info, key=lambda x: Fr(x['gap']))
    row['bound'] = {'worst_leaf': worst['leaf'], 'lhs': worst['lhs'], 'slope_excess': worst['slope_excess'],
                    'statement': 'on leaf %d: d(v) <= T_m(n) + floor((%s) + %s*(sum over unbounded j of u_j - l_j))'
                    % (worst['leaf'], worst['lhs'], worst['slope_excess'])}
    return row


def _given(ws, profs, box, o, m):
    try:
        return C.leaf_criterion([(w, p.base, p.beta, o) for w, p in zip(ws, profs)], box, m=m)[0]
    except C.CheckError:
        return False


def score_family(fam, header, item, per_family=E.PER_FAMILY_CPU, per_family_wall=E.PER_FAMILY_WALL):
    row = {'id': fam['id'], 'm': fam['m'], 'k': fam['k'], 'mask': fam['mask'], 'class': fam.get('class'),
           'budget_unit': fam['budget_unit'], 'slope_bound': fam['slope_bound'], 'valid': False,
           'gap': str(E.INVALID_GAP), 'trace': {}}
    if header.get('status') != 'ok':
        row['trace']['failure'] = header.get('error') or header.get('reason')
        return dict(row, status='INCOMPLETE', **({'timeout': True} if header.get('timeout') else {}))
    if item is None:
        row['trace']['failure'] = header.get('killed') or 'no result for this family'
        return dict(row, status='INCOMPLETE')
    row['run'] = {'seconds': item.get('seconds'), 'cpu_seconds': item.get('cpu_seconds')}
    if 'error' in item:
        row['trace']['failure'] = str(item['error'])[:300]
        return dict(row, status='INCOMPLETE', timeout=str(item['error']).startswith('TimeoutError'))
    cpu, wall = item.get('cpu_seconds'), item.get('seconds')
    if not isinstance(cpu, (int, float)) or not isinstance(wall, (int, float)) or \
            cpu > per_family + E.CPU_TOLERANCE or wall > per_family_wall + E.WALL_TOLERANCE:
        row['trace']['failure'] = 'family exceeded %.1f s CPU or %.1f s wall' % (per_family, per_family_wall)
        return dict(row, status='INCOMPLETE', timeout=True)
    try:
        out = json.loads(item['output_json'])
    except (ValueError, KeyError, TypeError) as exc:
        row['trace']['failure'] = str(exc)[:300]
        return dict(row, status='INVALID_OUTPUT')
    res = score_output(fam, out)
    row['trace'].update(res.pop('trace', {}))
    row.update(res)
    return row


def _score(args):
    return score_family(*args)


# ------------------------------------------------------------- evaluate
def _result(rows, **extra):
    return dict(E.aggregate(rows), evaluator_version=VERSION, evaluator_hash=evaluator_hash(), contract=CONTRACT,
                results=rows, **extra)


def evaluate(program_path, families, *, require_os_sandbox=True, jobs=8, cache_dir=None,
             per_family=E.PER_FAMILY_CPU, per_family_wall=E.PER_FAMILY_WALL):
    src = Path(program_path)
    if src.is_symlink() or not src.is_file() or src.stat().st_size > E.MAX_SOURCE:
        raise ValueError('candidate must be a regular file of at most %d bytes' % E.MAX_SOURCE)
    source = src.read_bytes()
    set_hash = E._sha(E.canonical(families).encode())
    key = E._sha(E.canonical([E._sha(source), set_hash, evaluator_hash(), CONTRACT, require_os_sandbox,
                              per_family, per_family_wall]).encode())
    cache = Path(cache_dir) / (key + '.json') if cache_dir else None
    if cache and cache.exists():
        return dict(json.loads(cache.read_text()), cache_hit=True)
    start = time.monotonic()
    guard = E.source_guard(source.decode('utf-8', 'replace'))
    if guard:
        rows = [dict(score_family(f, {'status': 'ok'}, {'index': 0, 'output_json': 'null', 'cpu_seconds': 0,
                                                        'seconds': 0}), trace={'failure': 'source guard: ' + guard})
                for f in families]
    else:
        send = [{x: f[x] for x in ('id', 'm', 'labels', 'mask', 'gaps', 'k', 'unit_base', 'budget_unit',
                                   'slope_bound')} for f in families]
        with ThreadPoolExecutor(max(1, jobs)) as pool:  # one sandboxed process per family (BATCH = 1)
            runs = list(pool.map(lambda f: run_batch(source, [f], per_family, require_os_sandbox, per_family_wall),
                                 send))
        args = [(f, run['header'], run['items'][0], per_family, per_family_wall) for f, run in zip(families, runs)]
        if jobs > 1 and len(args) > 16:
            with ProcessPoolExecutor(jobs) as pool:
                rows = list(pool.map(_score, args, chunksize=4))
        else:
            rows = [_score(x) for x in args]
    result = _result(rows, kind='bound_program', cache_key=key, candidate_hash=E._sha(source),
                     family_set_hash=set_hash, source_guard=guard, per_family_cpu=per_family,
                     per_family_wall=per_family_wall,
                     isolation='macos_seatbelt' if require_os_sandbox else 'process_only',
                     seconds=time.monotonic() - start,
                     limitations=['A CERTIFIED family (a,S) is an exact bound d(v) <= T_m(n) for all its states at '
                                  'every block length, conditional on the group\'s Lemma 1 with refinement and '
                                  'criterion (8) with m as a parameter; it says nothing about other families. A '
                                  'miss, crash or timeout proves nothing.'])
    if cache and not result['incomplete']:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(result))
    return dict(result, cache_hit=False)


def _trusted_item(args):
    module_name, fam, index = args
    mod = importlib.import_module(module_name)
    c0, w0 = time.process_time(), time.monotonic()
    item = {'index': index}
    try:
        item['output_json'] = json.dumps(mod.certify(json.loads(json.dumps(fam))))
    except Exception as exc:  # a trusted control failure is INCOMPLETE, never a miss
        item['error'] = type(exc).__name__ + ': ' + str(exc)[:300]
    item['cpu_seconds'], item['seconds'] = time.process_time() - c0, time.monotonic() - w0
    return item


def evaluate_trusted(module_name, families, *, jobs=8):
    """Trusted repository controls (integrations.bound_control_* or bound3_control_*), in-process, no CPU limit."""
    if not module_name.startswith(('integrations.bound_control_', 'integrations.bound3_control_')):
        raise ValueError('evaluate_trusted is only for trusted integrations control modules')
    start = time.monotonic()
    send = [{x: f[x] for x in ('id', 'm', 'labels', 'mask', 'gaps', 'k', 'unit_base', 'budget_unit',
                               'slope_bound')} for f in families]
    with ProcessPoolExecutor(max(1, jobs)) as pool:
        items = list(pool.map(_trusted_item, [(module_name, f, i) for i, f in enumerate(send)], chunksize=1))
        rows = list(pool.map(_score, [(f, {'status': 'ok'}, it, 1e6, 1e6) for f, it in zip(families, items)],
                             chunksize=1))
    cpu = [it['cpu_seconds'] for it in items]
    return _result(rows, kind='bound_trusted_control', control=module_name, isolation='trusted_in_process',
                   family_set_hash=E._sha(E.canonical(families).encode()), max_family_cpu=max(cpu),
                   families_over_candidate_cpu=sum(x > E.PER_FAMILY_CPU for x in cpu),
                   seconds=time.monotonic() - start, cache_hit=False)


def rescore_stored(families, stored_rows):
    """Re-verify a bound-eval-2 result's stored output words as single unit-origin leaves (data only; nothing
    is executed). Rows without stored words keep their bound-eval-2 status (invalid or INCOMPLETE)."""
    by_id = {r['id']: r for r in stored_rows}
    rows = []
    for f in families:
        old = by_id[f['id']]
        base = {'id': f['id'], 'm': f['m'], 'k': f['k'], 'mask': f['mask'], 'class': f.get('class')}
        if old.get('output_words'):
            rows.append(dict(base, **score_output(f, {'words': old['output_words']})))
        else:
            rows.append(dict(base, status=old['status'], valid=old['valid'], gap=old['gap'],
                             timeout=old.get('timeout', False)))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--program', required=True)
    ap.add_argument('--families', required=True, help='frozen development.json (holdout needs --holdout)')
    ap.add_argument('--output', required=True)
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--cache-dir')
    ap.add_argument('--holdout', action='store_true', help='human-run one-time finalist check')
    ap.add_argument('--finalist-manifest')
    a = ap.parse_args(argv)
    if a.holdout:
        E._holdout_allowed(a.program, a.finalist_manifest, False)
    fams = E.load_set(a.families, allow_holdout=a.holdout)
    if a.limit:
        fams = fams[:a.limit]
    out = Path(a.output)
    if out.exists():
        raise SystemExit('refusing to overwrite existing %s' % out)
    res = evaluate(a.program, fams, jobs=a.jobs, cache_dir=a.cache_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({x: res[x] for x in ('families', 'certified', 'boundary', 'valid', 'invalid', 'incomplete',
                                          'timeouts', 'max_W', 'combined_score', 'isolation', 'seconds',
                                          'cache_hit')}))


if __name__ == '__main__':
    main()
