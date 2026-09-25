"""Trusted evaluator for lift gadgets (autoresearch/lift-m9-260924/TASK.md).

A candidate program exposes `lift(instance) -> {"words": [...], "weights"?, "note"?}`.
It runs only in a separate process under the official-integration Seatbelt
profile (program_sandbox.py, program_evaluator._preexec, unchanged).  Only
words cross back.  The parent here replays every word on the child unit base,
prices it by the Lemma 1 affine cost, cross-checks literal stretched executions,
solves the exact rational LP over the words, and applies the mixture
criterion.  A miss, crash or time limit is never evidence of infeasibility.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from fractions import Fraction as Fr
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from integrations import lrx_m as C
from integrations.lift_task import check_instance
from integrations.program_evaluator import MAX_OUTPUT_BYTES, _preexec
from integrations.program_sandbox import SandboxUnavailable, sandbox_command, sandbox_profile

VERSION = 'lift-eval-2'
CONTRACT = ('lift-contract-2: certificate iff every returned word sorts the child unit base '
            '(no zero-zero swap), <=16 words, <=4000 letters, and the exact LP optimum over the '
            'words (weights>=0, sum 1, weighted Lemma-1 slopes <= slope_bound) has weighted base '
            '< budget_unit+1. gap = min over mixtures of max(0, B - (budget_unit+1)) + max(0, max_j '
            'slope_j - slope_bound) (exact LP; never grows when words are added) for valid misses, '
            '4000 for invalid/crash/timeout. combined_score = certificates + 0.5*valid/N + '
            '0.5/(1+gap_sum/N).')
MAX_WORDS, MAX_LETTERS, INVALID_GAP, MAX_SOURCE = 16, 4000, 4000, 65536
_SOURCES = ('lift_evaluator.py', 'lift_task.py', 'lrx_m.py', 'lift_worker.py', 'program_sandbox.py')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def evaluator_hash():
    here = Path(__file__).parent
    return _sha(VERSION.encode() + b''.join((here / f).read_bytes() for f in _SOURCES))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


# ------------------------------------------------------------- exact LP
def simplex(A, b, c):
    """min c.x, A x = b, x >= 0 in exact Fractions; Bland's rule, two phases.
    -> ('optimal', x, value) | ('infeasible', None, None) | ('unbounded', None, None)."""
    m, n = len(A), len(c)
    T = []
    for i in range(m):
        s = -1 if b[i] < 0 else 1
        T.append([Fr(s * a) for a in A[i]] + [Fr(int(r == i)) for r in range(m)] + [Fr(s * b[i])])
    basis = list(range(n, n + m))

    def pivot(r, j):
        p = T[r][j]
        T[r] = [v / p for v in T[r]]
        for i in range(m):
            if i != r and T[i][j]:
                f = T[i][j]
                T[i] = [v - f * w for v, w in zip(T[i], T[r])]
        basis[r] = j

    def run(cost, cols):
        while True:
            enter = None
            for j in cols:
                if j not in basis and cost[j] - sum(cost[basis[i]] * T[i][j] for i in range(m)) < 0:
                    enter = j
                    break
            if enter is None:
                return True
            rows = [i for i in range(m) if T[i][enter] > 0]
            if not rows:
                return False
            r = min(rows, key=lambda i: (T[i][-1] / T[i][enter], basis[i]))
            pivot(r, enter)

    run([Fr(0)] * n + [Fr(1)] * m, range(n + m))
    if sum(T[i][-1] for i in range(m) if basis[i] >= n) > 0:
        return 'infeasible', None, None
    for r in range(m):  # drive zero artificials out where possible
        if basis[r] >= n:
            j = next((j for j in range(n) if T[r][j] and j not in basis), None)
            if j is not None:
                pivot(r, j)
    cost = [Fr(v) for v in c] + [Fr(0)] * m
    if not run(cost, range(n)):
        return 'unbounded', None, None
    x = [Fr(0)] * n
    for i, j in enumerate(basis):
        if j < n:
            x[j] = T[i][-1]
    return 'optimal', x, sum(Fr(v) * t for v, t in zip(c, x))


def mixture_lp(costs, k, bound):
    """costs: [(base, slopes)].  Minimum weighted base with weighted slopes <= bound.
    If infeasible, first minimize the uniform slope excess t, then the base at bound+t."""
    n = len(costs)

    def min_base(cap):
        A = [[bt[j] for _, bt in costs] + [int(i == j) for i in range(k)] for j in range(k)]
        A.append([1] * n + [0] * k)
        st, x, val = simplex(A, [cap] * k + [1], [b for b, _ in costs] + [0] * k)
        return (x[:n], val) if st == 'optimal' else (None, None)

    w, B = min_base(Fr(bound))
    t = Fr(0)
    if w is None:
        A = [[bt[j] for _, bt in costs] + [int(i == j) for i in range(k)] + [-1] for j in range(k)]
        A.append([1] * n + [0] * k + [0])
        st, x, t = simplex(A, [bound] * k + [1], [0] * (n + k) + [1])
        w, B = min_base(bound + t)
    slopes = [sum(wi * bt[j] for wi, (_, bt) in zip(w, costs)) for j in range(k)]
    return w, B, slopes, t


def gap_lp(costs, k, bound, strict):
    """min u + t over mixtures w: B(w) - u <= strict, slopes_j(w) - t <= bound, u, t >= 0."""
    n = len(costs)
    # columns: w (n), slope slacks (k), t, u, base slack
    A = [[bt[j] for _, bt in costs] + [int(i == j) for i in range(k)] + [-1, 0, 0] for j in range(k)]
    A.append([b for b, _ in costs] + [0] * k + [0, -1, 1])
    A.append([1] * n + [0] * k + [0, 0, 0])
    st, x, val = simplex(A, [bound] * k + [strict, 1], [0] * (n + k) + [1, 1, 0])
    w = x[:n]
    B = sum(wi * b for wi, (b, _) in zip(w, costs))
    slopes = [sum(wi * bt[j] for wi, (_, bt) in zip(w, costs)) for j in range(k)]
    return val, w, B, slopes


# ------------------------------------------------------------- sandbox run
def run_program(source, instance, timeout, require_os_sandbox=True):
    """Same mechanism as ProgramEvaluator._run_case, with lift_worker.py."""
    with tempfile.TemporaryDirectory(prefix='lrx-lift-') as temp:
        scratch = Path(temp).resolve()
        (scratch / 'candidate.py').write_bytes(source)
        shutil.copyfile(Path(__file__).with_name('lift_worker.py'), scratch / 'worker.py')
        (scratch / 'case.json').write_text(json.dumps(instance), encoding='utf-8')
        out = scratch / 'output.json'
        command = [sys.executable, '-I', '-S', str(scratch / 'worker.py'), str(scratch / 'candidate.py'),
                   str(scratch / 'case.json'), str(out)]
        isolation = 'process_only'
        if require_os_sandbox:
            profile = sandbox_profile(read_paths=(sys.base_prefix, '/usr', '/System', '/Library', '/private/etc'),
                                      write_paths=(scratch,))
            (scratch / 'sandbox.sb').write_text(profile, encoding='utf-8')
            command = sandbox_command(command, scratch / 'sandbox.sb')
            isolation = 'macos_seatbelt'
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(scratch), 'TMPDIR': str(scratch),
               'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C', 'LC_ALL': 'C'}
        start = time.monotonic()
        with (scratch / 'stdout').open('wb') as so, (scratch / 'stderr').open('wb') as se:
            proc = subprocess.Popen(command, cwd=scratch, env=env, stdin=subprocess.DEVNULL, stdout=so,
                                    stderr=se, start_new_session=True, preexec_fn=lambda: _preexec(timeout))
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                return {'status': 'INCOMPLETE', 'reason': 'time limit', 'seconds': time.monotonic() - start,
                        'isolation': isolation}
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        meta = {'seconds': time.monotonic() - start, 'isolation': isolation}
        log = (scratch / 'stderr').read_bytes()[:4096].decode('utf-8', 'replace')
        if proc.returncode:
            if 'sandbox_apply: Operation not permitted' in log:
                raise SandboxUnavailable('macOS Seatbelt denied by outer execution environment')
            return dict(meta, status='INCOMPLETE', reason='worker exit %d' % proc.returncode, stderr=log)
        if not out.exists() or out.stat().st_size > MAX_OUTPUT_BYTES:
            return dict(meta, status='INCOMPLETE', reason='missing or oversized worker output')
        try:
            payload = json.loads(out.read_text(encoding='utf-8'))
        except (ValueError, UnicodeError):
            return dict(meta, status='INCOMPLETE', reason='invalid worker JSON')
        if not isinstance(payload, dict) or payload.get('status') not in ('ok', 'candidate_error'):
            return dict(meta, status='INVALID_OUTPUT', reason='worker JSON must be a status object')
        return dict(payload, **meta)


# ------------------------------------------------------------- verification
def _reduce(word):
    out = []
    for ch in word:
        if out and out[-1] + ch in ('LR', 'RL'):
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


def delete_label(state, word, label):
    """Delete one label atom from a child run (diagnostic analog of Lemma 4)."""
    a, n, c, out = list(state), len(state), 0, []
    for ch in word:
        if ch == 'L':
            if a[c] != label:
                out.append('L')
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            if a[c] != label:
                out.append('R')
        else:
            c2 = (c + 1) % n
            if label not in (a[c], a[c2]):
                out.append('X')
            a[c], a[c2] = a[c2], a[c]
    return _reduce(''.join(out))


def _parse_output(out):
    if not isinstance(out, dict) or not isinstance(out.get('words'), list):
        raise ValueError('output must be an object with a list "words"')
    words = out['words']
    if not 1 <= len(words) <= MAX_WORDS:
        raise ValueError('%d words; need 1..%d' % (len(words), MAX_WORDS))
    for i, w in enumerate(words):
        if type(w) is not str or len(w) > MAX_LETTERS or set(w) - set('LRX'):
            raise ValueError('word %d is not a string over LRX of length <= %d' % (i, MAX_LETTERS))
    weights = out.get('weights')
    if weights is not None:
        if not isinstance(weights, list) or len(weights) != len(words) or \
                any(type(x) not in (str, int) for x in weights):
            raise ValueError('weights must be a list of rational strings, one per word')
        weights = [Fr(x) for x in weights]
        if any(x < 0 for x in weights) or sum(weights) != 1:
            raise ValueError('weights are not a probability vector')
    return words, weights


def score_instance(inst, rows, attempt):
    ch = inst['child']
    k, bound, strict = ch['k'], ch['slope_bound'], ch['budget_unit'] + 1
    res = {'id': inst['id'], 'child_id': ch['id'], 'k': k, 'budget_unit': ch['budget_unit'],
           'run': {x: attempt.get(x) for x in ('seconds', 'isolation', 'reason', 'error') if x in attempt},
           'valid': False, 'certificate': None, 'gap': str(INVALID_GAP), 'trace': {}}
    if attempt['status'] != 'ok':
        res['status'] = attempt['status']
        res['trace']['failure'] = attempt.get('reason') or attempt.get('error')
        return res
    out = attempt.get('output')
    if isinstance(out, dict) and isinstance(out.get('note'), str):
        res['note'] = out['note'][:500]
    try:
        words, given = _parse_output(out)
    except (ValueError, ZeroDivisionError) as exc:
        res['status'] = 'INVALID_OUTPUT'
        res['trace']['failure'] = str(exc)[:300]
        return res
    state, zs = ch['unit_base'], C.z_samples(k)
    parent_words = {_reduce(r['word']): i for i, r in enumerate(rows)}
    costs, info = [], []
    for i, w in enumerate(words):
        try:
            prof = C.Profile(state, w)
            C.literal_lift_check(prof, zs)
        except C.CheckError as exc:
            res['status'] = 'INVALID_OUTPUT'
            res['trace']['failed_word'] = {'index': i, 'length': len(w), 'reason': str(exc)}
            return res
        costs.append((prof.base, list(prof.beta)))
        info.append({'index': i, 'length': len(w), 'base': prof.base, 'slopes': list(prof.beta),
                     'parent_row': parent_words.get(delete_label(state, w, inst['insert']['label']))})
    res['valid'] = True
    weights, B, slopes, t = mixture_lp(costs, k, bound)
    ok, B2, s2 = C.mixture_criterion(costs, weights, k, m=len(ch['labels']))
    if B2 != B or s2 != slopes:
        raise AssertionError('LP and criterion disagree')  # evaluator bug, never a score
    res['words'] = info
    res['lp'] = {'weights': [str(x) for x in weights], 'base': str(B),
                 'slopes': [str(x) for x in slopes], 'slope_excess': str(t)}
    if given is not None:
        res['given_weights_pass'] = C.mixture_criterion(costs, given, k, m=len(ch['labels']))[0]
    res['trace']['parent_rows_used'] = sorted({x['parent_row'] for x in info if x['parent_row'] is not None})
    if ok:
        res['status'], res['gap'] = 'CERTIFICATE', '0'
        res['certificate'] = {'words': [w for w, x in zip(words, weights) if x],
                              'weights': [str(x) for x in weights if x], 'base': str(B)}
        return res
    res['status'] = 'NO_CERTIFICATE'
    gap, gw, gB, gs = gap_lp(costs, k, bound, strict)
    res['gap'] = str(gap)
    res['gap_lp'] = {'weights': [str(x) for x in gw], 'base': str(gB), 'slopes': [str(x) for x in gs]}
    res['trace'].update({
        'base_overshoot': str(gB - strict) if gB >= strict else None,
        'slopes_over': [[j, str(s)] for j, s in enumerate(gs) if s > bound],
        'word_slopes_over': [[x['index'], j, x['slopes'][j]] for x in info
                             for j in range(k) if x['slopes'][j] > bound]})
    top = max(range(len(words)), key=lambda i: (gw[i], -costs[i][0]))
    res['trace']['construction'] = {'index': top, 'weight': str(gw[top]), 'word': words[top][:600],
                                    'truncated': len(words[top]) > 600, 'base': costs[top][0],
                                    'slopes': costs[top][1]}
    return res


def _score(args):
    return score_instance(*args)


def load_instances(path):
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    items = raw['instances'] if isinstance(raw, dict) else raw
    out = []
    for inst in items:
        want, rows = check_instance(inst)
        send = json.loads(json.dumps(want))
        send['parent']['certificate'] = dict(inst['parent']['certificate'], rows=[
            dict(r, base=x['base'], slopes=x['slopes']) for r, x in zip(inst['parent']['certificate']['rows'], rows)])
        out.append((send, rows))
    if not out or len({i['id'] for i, _ in out}) != len(out):
        raise ValueError('empty instance set or duplicate instance ids')
    return out


def evaluate(program_path, instances, *, timeout=10.0, require_os_sandbox=True, jobs=4, cache_dir=None):
    src = Path(program_path)
    if src.is_symlink() or not src.is_file() or src.stat().st_size > MAX_SOURCE:
        raise ValueError('candidate must be a regular file of at most %d bytes' % MAX_SOURCE)
    source = src.read_bytes()
    set_hash = _sha(canonical([i for i, _ in instances]).encode())
    key = _sha(canonical([_sha(source), set_hash, evaluator_hash(), CONTRACT, require_os_sandbox]).encode())
    cache = Path(cache_dir) / (key + '.json') if cache_dir else None
    if cache and cache.exists():
        return dict(json.loads(cache.read_text()), cache_hit=True)
    start = time.monotonic()
    with ThreadPoolExecutor(max(1, jobs)) as pool:
        attempts = list(pool.map(lambda x: run_program(source, x[0], timeout, require_os_sandbox), instances))
    args = [(inst, prows, a) for (inst, prows), a in zip(instances, attempts)]
    if jobs > 1 and len(args) > 64:  # exact scoring is CPU-bound pure Python
        with ProcessPoolExecutor(jobs) as pool:
            rows = list(pool.map(_score, args, chunksize=16))
    else:
        rows = [_score(x) for x in args]
    N = len(rows)
    certs = sum(r['status'] == 'CERTIFICATE' for r in rows)
    valid = sum(r['valid'] for r in rows)
    gap = sum(Fr(r['gap']) for r in rows)
    result = {'kind': 'lift_program', 'evaluator_version': VERSION, 'evaluator_hash': evaluator_hash(),
              'contract': CONTRACT, 'cache_key': key, 'candidate_hash': _sha(source),
              'instance_set_hash': set_hash, 'instances': N, 'certificates': certs, 'valid': valid,
              'gap_sum': str(gap), 'invalid': N - valid,
              'timeouts': sum(r['run'].get('reason') == 'time limit' for r in rows),
              'combined_score': certs + 0.5 * valid / N + 0.5 / (1 + float(gap) / N),
              'isolation': 'macos_seatbelt' if require_os_sandbox else 'process_only',
              'seconds': time.monotonic() - start, 'results': rows,
              'limitations': ['Finite frozen instances only. A certificate is an exact m+1 family bound '
                              'via direct Lemma 1 profiles; a miss or timeout proves nothing.']}
    if cache and not any(r['status'] == 'INCOMPLETE' for r in rows):
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(result))
    return dict(result, cache_hit=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--program', required=True)
    ap.add_argument('--instances', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--timeout', type=float, default=10.0)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--limit', type=int, default=0, help='evaluate only the first N instances')
    ap.add_argument('--cache-dir')
    ap.add_argument('--no-os-sandbox', action='store_true', help='trusted controls only; never generated code')
    a = ap.parse_args(argv)
    inst = load_instances(a.instances)
    if a.limit:
        inst = inst[:a.limit]
    res = evaluate(a.program, inst, timeout=a.timeout, require_os_sandbox=not a.no_os_sandbox,
                   jobs=a.jobs, cache_dir=a.cache_dir)
    out = Path(a.output)
    if out.exists():
        raise SystemExit('refusing to overwrite existing %s' % out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({x: res[x] for x in ('instances', 'certificates', 'valid', 'gap_sum', 'timeouts',
                                          'combined_score', 'isolation', 'seconds', 'cache_hit')}))


if __name__ == '__main__':
    main()
