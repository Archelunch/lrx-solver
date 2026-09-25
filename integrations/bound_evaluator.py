"""Trusted evaluator for bound-m programs (autoresearch/bound-m-260925/TASK.md).

A candidate program exposes `certify(family) -> {"words": [...], "weights"?, "note"?}`.
It runs only in a separate process under the official-integration Seatbelt
profile (program_sandbox.py, program_evaluator._preexec), one process per small
batch (BATCH = 1 family) with per-family CPU/wall alarms (bound_worker.py). Only
words cross back. The candidate may not fork (Seatbelt deny process-fork, RLIMIT_NPROC 1). The parent
reaps the batch with os.wait4 and compares the kernel's CPU time for the process
with the worker-reported per-family times (which the candidate could rewrite): a
batch whose measured CPU exceeds the reported total by more than the import and
startup allowance, or the batch cap, is INCOMPLETE for every family in it.
The parent replays every word on the unit base with the group's Lemma 1 profile
(lrx_m.Profile, m-independent rules), cross-checks literal stretched executions
at z = 0, e_j, 2e_j, e_j+e_{j+1} and (1,...,1), solves the exact rational LP
(lift_evaluator.mixture_lp), cross-checks it with lrx_m.mixture_criterion(m=m),
and solves the gap LP for families that are not certified.

Status per family: CERTIFIED (LP optimum has weighted base < T+1 and every
weighted slope <= m-2), BOUNDARY (gap 0 but min weighted base exactly T+1),
NO_CERTIFICATE, INVALID_OUTPUT, INCOMPLETE (timeout, crash, worker failure).
A certificate proves d(v) <= T_m(n) for every state of that family only,
conditional on the group's Lemma 1. A miss, crash or timeout proves nothing.
"""
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from fractions import Fraction as Fr
import hashlib
import math
import importlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from integrations import lrx_m as C
from integrations.bound_task import SCHEMA, check_family
from integrations.lift_evaluator import gap_lp, mixture_lp
from integrations.program_evaluator import MAX_OUTPUT_BYTES, _preexec
from integrations.program_sandbox import SandboxUnavailable, sandbox_command, sandbox_profile

VERSION = 'bound-eval-2'
CONTRACT = ('bound-contract-2: candidate defines certify(family) -> {"words": [...], "weights"?: [...], '
            '"note"?: str}; 1..32 words over L,R,X of at most 4000 letters; weights optional strings p or '
            'p/q (at most 40 digits each) or ints below 10**40 forming a probability vector (checked and '
            'reported, never trusted). INVALID_OUTPUT '
            'unless every word sorts the unit base with no zero-zero swap (lrx_m.Profile) and passes '
            'literal lifted execution at z=0, e_j, 2e_j, e_j+e_{j+1}, (1..1) with length F(z) <= B+beta.z. '
            'CERTIFIED iff the exact LP optimum (lift_evaluator.mixture_lp) has weighted base < T+1 and '
            'weighted slopes <= m-2, T = T_m(m+k). gap = lift_evaluator.gap_lp with strict T+1; BOUNDARY '
            'iff not certified and gap 0. Invalid and INCOMPLETE (timeout 3 s CPU / 5 s wall per family, '
            'crash, worker failure; one process per family, no fork; a family whose parent-measured process '
            'CPU exceeds 5 s or its reported time by more than 2 s import/startup is INCOMPLETE) get gap 4000. Per m: pct = 100 C/N, '
            'W = max gap, G = mean gap over valid. combined = mean_m pct + min_m pct + 0.06 V/N + '
            '0.06/(1+max_m W) + 0.03/(1+mean_m G). Source guard (a screen, not a guarantee): no str '
            'constant or constant concatenation (a + b, sep.join([...])) >= 24 chars that is >= 90% '
            'L/R/X/l/r/x, at most 512 such characters in all str constants, at most 4096 characters of non-docstring str constants, no literal container > 64 '
            'elements, at most 256 constant elements in all literal containers, no int constant >= 10**40, '
            'no bytes constant > 256 bytes.')
MAX_WORDS, MAX_LETTERS, MAX_NOTE, INVALID_GAP, MAX_SOURCE = 32, 4000, 500, 4000, 65536
# BATCH = 1: one process per family, so CPU cannot be pooled across families of a batch.
PER_FAMILY_CPU, PER_FAMILY_WALL, IMPORT_CPU, STARTUP_CPU, BATCH = 3.0, 5.0, 1.0, 1.0, 1
CPU_TOLERANCE, WALL_TOLERANCE = 0.1, 0.5
WEIGHT = re.compile(r'-?[0-9]{1,40}(/[0-9]{1,40})?')
MAX_WEIGHT_INT = 10 ** 40
GUARD_LRX_RUN, GUARD_LRX_SHARE, GUARD_LRX_TOTAL = 24, 0.9, 512
GUARD_STR_TOTAL, GUARD_LITERAL_TOTAL, GUARD_INT = 4096, 256, 10 ** 40
STATUSES = ('CERTIFIED', 'BOUNDARY', 'NO_CERTIFICATE', 'INVALID_OUTPUT', 'INCOMPLETE')
_SOURCES = ('bound_evaluator.py', 'bound_task.py', 'bound_worker.py', 'lrx_m.py', 'lift_evaluator.py',
            'lift_task.py', 'program_sandbox.py', 'program_evaluator.py')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def evaluator_hash():
    here = Path(__file__).parent
    return _sha(VERSION.encode() + b''.join((here / f).read_bytes() for f in _SOURCES))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


# ------------------------------------------------------------- sets
def guard_not_holdout(path):
    raw = json.loads(Path(path).read_text())
    if 'holdout' in Path(path).name or raw.get('set') != 'development':
        raise ValueError('engines may load only the frozen development set, never holdout')


def load_set(path, allow_holdout=False, allow_edge=True):
    raw = json.loads(Path(path).read_text())
    if raw.get('schema') != SCHEMA or raw.get('set') not in ('development', 'holdout', 'edge'):
        raise ValueError('not a frozen bound family set')
    if raw['set'] == 'holdout' and not allow_holdout:
        raise ValueError('holdout is evaluated only once, after finalist freeze')
    if raw['set'] == 'edge' and not allow_edge:
        raise ValueError('edge set not allowed here')
    fams = raw['families']
    for f in fams:
        check_family(f)
    if not fams or len({f['id'] for f in fams}) != len(fams):
        raise ValueError('empty family set or duplicate ids')
    return fams


# ------------------------------------------------------------- source guard
def _docstrings(tree):
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                    and isinstance(first.value.value, str):
                ids.add(id(first.value))
    return ids


def _lrx_heavy(v):
    return bool(v) and sum(c in 'LRXlrx' for c in v) >= GUARD_LRX_SHARE * len(v)


def _concat(node):
    """Value of a str concatenation of constants (a + b + ..., 'sep'.join([...])), else None."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'join' \
            and isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str) \
            and len(node.args) == 1 and not node.keywords and isinstance(node.args[0], (ast.List, ast.Tuple)) \
            and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.args[0].elts):
        return node.func.value.value.join(e.value for e in node.args[0].elts)
    parts, stack = [], [node]
    while stack:
        n = stack.pop()
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            stack += [n.right, n.left]
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            parts.append(n.value)
        else:
            return None
    return ''.join(parts)


def source_guard(source):
    """None if the source passes the table screen, else the reason (TASK.md, Candidate).

    A screen against embedded word or answer tables, not a guarantee: per-node limits plus
    whole-file budgets, so chunked literals (concatenated strings, merged dicts) are counted
    together. Soundness never depends on it; every word is replayed."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
        return 'source does not parse: %s' % exc
    docs = _docstrings(tree)
    inner = {id(c) for n in ast.walk(tree) if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add)
             for c in (n.left, n.right)}
    lrx_total = str_total = literal_total = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.BinOp, ast.Call)) and id(node) not in inner:
            v = _concat(node) if isinstance(node, ast.Call) or isinstance(node.op, ast.Add) else None
            if v is not None and len(v) >= GUARD_LRX_RUN and _lrx_heavy(v):
                return 'L/R/X-heavy string concatenation of %d characters (limit %d)' % (len(v), GUARD_LRX_RUN - 1)
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, str) and v:
                lrx = _lrx_heavy(v)
                if lrx and len(v) >= GUARD_LRX_RUN:
                    return 'L/R/X-heavy string constant of %d characters (limit %d)' % (len(v), GUARD_LRX_RUN - 1)
                if id(node) not in docs:
                    str_total += len(v)
                    lrx_total += len(v) if lrx else 0
            elif isinstance(v, bytes) and len(v) > 256:
                return 'bytes constant of %d bytes (limit 256)' % len(v)
            elif isinstance(v, int) and abs(v) >= GUARD_INT:
                return 'integer constant of %d digits (limit 40)' % len(str(abs(v)))
        elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            if len(node.elts) > 64:
                return 'literal container with %d elements (limit 64)' % len(node.elts)
            literal_total += sum(isinstance(e, ast.Constant) for e in node.elts)
        elif isinstance(node, ast.Dict):
            if len(node.keys) > 64:
                return 'literal dict with %d entries (limit 64)' % len(node.keys)
            literal_total += sum(isinstance(e, ast.Constant) for e in node.keys + node.values)
    if lrx_total > GUARD_LRX_TOTAL:
        return 'L/R/X-heavy string constants total %d characters (limit %d)' % (lrx_total, GUARD_LRX_TOTAL)
    if str_total > GUARD_STR_TOTAL:
        return 'string constants outside docstrings total %d characters (limit %d)' % (str_total, GUARD_STR_TOTAL)
    if literal_total > GUARD_LITERAL_TOTAL:
        return 'literal containers hold %d constant elements in total (limit %d)' % (literal_total,
                                                                                    GUARD_LITERAL_TOTAL)
    return None


# ------------------------------------------------------------- sandbox run
def _batch_preexec(cpu_cap):
    # Runs in the child before exec: CPU/file caps, and no further processes (RLIMIT_CPU is per process).
    _preexec(cpu_cap)
    resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))


def _reap(proc, wall):
    """Wait for the child with os.wait4 (its own kernel rusage); SIGKILL the group at the wall limit.
    -> (killed, CPU seconds of the child as measured by the kernel)."""
    deadline, delay, killed = time.monotonic() + wall, 0.005, False
    while True:
        pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
        if pid:
            break
        if time.monotonic() >= deadline:
            killed = True
            os.killpg(proc.pid, signal.SIGKILL)
            _, status, usage = os.wait4(proc.pid, 0)
            break
        time.sleep(delay)
        delay = min(0.05, delay * 2)
    proc.returncode = os.waitstatus_to_exitcode(status)
    return killed, usage.ru_utime + usage.ru_stime


def cpu_check(parent_cpu, items, n_families, per_family=PER_FAMILY_CPU):
    """None if the parent-measured CPU is consistent with the worker's per-family reports, else why.
    The reports live in files the candidate can write, so only the kernel figure is trusted."""
    top = per_family + CPU_TOLERANCE  # a larger report already makes that family INCOMPLETE
    reported = sum(min(it['cpu_seconds'], top) for it in items
                   if isinstance(it, dict) and type(it.get('cpu_seconds')) in (int, float)
                   and math.isfinite(it['cpu_seconds']) and it['cpu_seconds'] >= 0)
    cap = per_family * n_families + IMPORT_CPU + STARTUP_CPU
    if parent_cpu > cap + CPU_TOLERANCE:
        return 'parent-measured batch CPU %.2f s exceeds the batch cap %.1f s' % (parent_cpu, cap)
    if parent_cpu - reported > IMPORT_CPU + STARTUP_CPU + CPU_TOLERANCE:
        return ('parent-measured batch CPU %.2f s exceeds the reported per-family total %.2f s by more than '
                'the %.1f s import/startup allowance' % (parent_cpu, reported, IMPORT_CPU + STARTUP_CPU))
    return None


def run_batch(source, families, per_family=PER_FAMILY_CPU, require_os_sandbox=True,
              per_family_wall=PER_FAMILY_WALL):
    """One sandboxed process per small batch; kernel RLIMIT_CPU caps the whole batch, the parent
    measures its CPU with os.wait4, and the candidate cannot fork."""
    wall = per_family_wall * len(families) + IMPORT_CPU * 5 + 5.0
    cpu_cap = per_family * len(families) + IMPORT_CPU + STARTUP_CPU
    with tempfile.TemporaryDirectory(prefix='lrx-bound-') as temp:
        scratch = Path(temp).resolve()
        (scratch / 'candidate.py').write_bytes(source)
        shutil.copyfile(Path(__file__).with_name('bound_worker.py'), scratch / 'worker.py')
        (scratch / 'case.json').write_text(json.dumps({'families': families, 'per_family_cpu': per_family,
                                                       'per_family_wall': per_family_wall,
                                                       'import_cpu': IMPORT_CPU}))
        command = [sys.executable, '-I', '-S', str(scratch / 'worker.py'), str(scratch / 'candidate.py'),
                   str(scratch / 'case.json'), str(scratch)]
        isolation = 'process_only'
        if require_os_sandbox:
            profile = sandbox_profile(read_paths=(sys.base_prefix, '/usr', '/System', '/Library', '/private/etc'),
                                      write_paths=(scratch,)) + '(deny process-fork)\n'
            (scratch / 'sandbox.sb').write_text(profile, encoding='utf-8')
            command = sandbox_command(command, scratch / 'sandbox.sb')
            isolation = 'macos_seatbelt'
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(scratch), 'TMPDIR': str(scratch),
               'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C', 'LC_ALL': 'C'}
        start = time.monotonic()
        with (scratch / 'stdout').open('wb') as so, (scratch / 'stderr').open('wb') as se:
            proc = subprocess.Popen(command, cwd=scratch, env=env, stdin=subprocess.DEVNULL, stdout=so,
                                    stderr=se, start_new_session=True, preexec_fn=lambda: _batch_preexec(cpu_cap))
            try:
                killed, cpu = _reap(proc, wall)
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        meta = {'seconds': time.monotonic() - start, 'cpu_seconds': cpu, 'isolation': isolation}
        log = (scratch / 'stderr').read_bytes()[:4096].decode('utf-8', 'replace')
        if 'sandbox_apply: Operation not permitted' in log:
            raise SandboxUnavailable('macOS Seatbelt denied by outer execution environment')
        header = {'status': 'INCOMPLETE', 'reason': 'batch wall limit' if killed else
                  'worker exit %s (a negative code or SIGXCPU is the kernel CPU cap)' % proc.returncode,
                  'stderr': log[-600:]}
        hpath = scratch / 'header.json'
        if hpath.is_file() and hpath.stat().st_size <= MAX_OUTPUT_BYTES:
            try:
                obj = json.loads(hpath.read_text(encoding='utf-8', errors='replace'))
                header = obj if isinstance(obj, dict) and obj.get('status') in ('ok', 'candidate_error') \
                    else {'status': 'INCOMPLETE', 'reason': 'worker header must be a status object'}
            except ValueError:
                pass
        items = [None] * len(families)
        for i in range(len(families)):
            p = scratch / ('out-%04d.json' % i)
            if p.is_file() and p.stat().st_size <= MAX_OUTPUT_BYTES:
                try:
                    obj = json.loads(p.read_text(encoding='utf-8', errors='replace'))
                except ValueError:
                    continue  # torn file from a killed batch
                if isinstance(obj, dict) and obj.get('index') == i:
                    items[i] = obj
        if header.get('status') == 'ok' and (killed or proc.returncode):
            header = dict(header, killed='batch wall limit' if killed else
                          'batch process ended with code %s (kernel CPU cap)' % proc.returncode)
        why = cpu_check(cpu, items, len(families), per_family)
        if why:
            header = {'status': 'INCOMPLETE', 'timeout': True, 'reason': why}
        return dict(meta, header=header, items=items)


# ------------------------------------------------------------- verification
def parse_output(out):
    """-> (words, given weights or None, note). Raises ValueError; output is never repaired."""
    if not isinstance(out, dict) or not isinstance(out.get('words'), list):
        raise ValueError('output must be an object with a list "words"')
    words = out['words']
    if not 1 <= len(words) <= MAX_WORDS:
        raise ValueError('%d words; need 1..%d' % (len(words), MAX_WORDS))
    for i, w in enumerate(words):
        if type(w) is not str or len(w) > MAX_LETTERS or set(w) - set('LRX'):
            raise ValueError('word %d is not a string over L,R,X of length <= %d' % (i, MAX_LETTERS))
    weights = out.get('weights')
    if weights is not None:
        if not isinstance(weights, list) or len(weights) != len(words) or \
                any(type(x) not in (str, int) for x in weights):
            raise ValueError('weights must be a list of rational strings, one per word')
        for i, x in enumerate(weights):  # bounded before Fraction: '1e10000000' would stall the parent
            if (abs(x) >= MAX_WEIGHT_INT) if type(x) is int else not WEIGHT.fullmatch(x):
                raise ValueError('weight %d is not p or p/q with at most 40 digits each' % i)
        try:
            weights = [Fr(x) for x in weights]
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError('weights are not rationals: %s' % exc) from None
        if any(x < 0 for x in weights) or sum(weights) != 1:
            raise ValueError('weights are not a probability vector')
    note = out.get('note')
    return words, weights, (note[:MAX_NOTE] if isinstance(note, str) else None)


def diagnose(state, word):
    """First zero-zero swap (letter index) or the final vector of a word that does not sort."""
    a, n, c = list(state), len(state), 0
    for i, ch in enumerate(word):
        if ch == 'X':
            j = (c + 1) % n
            if a[c] == 0 and a[j] == 0:
                return {'first_bad_letter': i, 'why': 'X swaps two zeros (a zero-zero swap)',
                        'prefix': word[max(0, i - 11):i + 1]}
            a[c], a[j] = a[j], a[c]
        else:
            c = (c + (1 if ch == 'L' else -1)) % n
    fin = a[c:] + a[:c]
    return {'why': 'word does not sort the unit base', 'final_prefix': fin[:24]}


def z_points(k):
    zs = C.z_samples(k, pairs=k - 1)
    ones = tuple([1] * k)
    return zs if ones in zs else zs + [ones]


def bound_text(B, T, t):
    return 'd(v) <= T_m(n) + floor((%s) + %s*(r-k))' % (B - T, t)


def score_family(fam, header, item, per_family=PER_FAMILY_CPU, per_family_wall=PER_FAMILY_WALL):
    m, k, T, s = fam['m'], fam['k'], fam['budget_unit'], fam['slope_bound']
    row = {'id': fam['id'], 'm': m, 'k': k, 'mask': fam['mask'], 'class': fam.get('class'),
           'budget_unit': T, 'slope_bound': s, 'valid': False, 'gap': str(INVALID_GAP), 'trace': {}}
    if header.get('status') != 'ok':
        row['status'] = 'INCOMPLETE'
        row['trace']['failure'] = header.get('error') or header.get('reason')
        if header.get('timeout'):
            row['timeout'] = True
        return row
    if item is None:
        row['status'] = 'INCOMPLETE'
        row['trace']['failure'] = header.get('killed') or 'no result for this family'
        return row
    row['run'] = {'seconds': item.get('seconds'), 'cpu_seconds': item.get('cpu_seconds')}
    if 'error' in item:
        row['status'] = 'INCOMPLETE'
        row['timeout'] = str(item['error']).startswith('TimeoutError')
        row['trace']['failure'] = str(item['error'])[:300]
        return row
    cpu, wall = item.get('cpu_seconds'), item.get('seconds')
    if not isinstance(cpu, (int, float)) or not isinstance(wall, (int, float)) or \
            cpu > per_family + CPU_TOLERANCE or wall > per_family_wall + WALL_TOLERANCE:
        row['status'], row['timeout'] = 'INCOMPLETE', True
        row['trace']['failure'] = 'family exceeded %.1f s CPU or %.1f s wall' % (per_family, per_family_wall)
        return row
    try:
        out = json.loads(item['output_json'])
        words, given, note = parse_output(out)
    except (ValueError, KeyError, TypeError) as exc:
        row['status'] = 'INVALID_OUTPUT'
        row['trace']['failure'] = str(exc)[:300]
        return row
    if note:
        row['note'] = note
    state, zs = fam['unit_base'], z_points(k)
    costs, info = [], []
    for i, w in enumerate(words):
        try:
            prof = C.Profile(state, w)
        except C.CheckError as exc:
            row['status'] = 'INVALID_OUTPUT'
            row['trace']['failed_word'] = dict(diagnose(state, w), index=i, length=len(w), reason=str(exc))
            return row
        try:
            C.literal_lift_check(prof, zs)
        except C.CheckError as exc:  # Lemma 1 says this cannot happen: evaluator or lemma alarm
            row['status'] = 'INVALID_OUTPUT'
            row['lemma1_literal_failure'] = True
            row['trace']['failed_word'] = {'index': i, 'length': len(w), 'reason': str(exc)}
            return row
        costs.append((prof.base, list(prof.beta)))
        info.append({'index': i, 'length': len(w), 'base': prof.base, 'beta': list(prof.beta),
                     'swaps': prof.q, 'A': list(prof.A),
                     'rotation_passes': [sum(abs(cz[j]) for _, cz in prof.segs) for j in range(k)],
                     'same_sign': prof.same_sign})
    row['valid'] = True
    row['words'] = info
    row['output_words'] = words
    row.update(classify(costs, k, s, T, m, fam['gaps']))
    if row['status'] == 'CERTIFIED':
        row['certificate']['words'] = [words[i] for i in row['certificate'].pop('indices')]
    if given is not None:
        try:
            row['given_weights_pass'] = C.mixture_criterion(costs, given, k, m=m)[0]
        except C.CheckError:
            row['given_weights_pass'] = False
    return row


def classify(costs, k, s, T, m, gaps=None):
    """Exact status of a priced word set: CERTIFIED / BOUNDARY / NO_CERTIFICATE, LP data and bound."""
    if T != C.budget(m, k) or s != m - 2:
        raise ValueError('budget or slope bound disagrees with T_m(m+k), m-2')
    weights, B, slopes, t = mixture_lp(costs, k, s)
    ok, B2, s2 = C.mixture_criterion(costs, weights, k, m=m)
    if B2 != B or s2 != slopes:
        raise AssertionError('LP and criterion disagree')  # evaluator bug, never a score
    out = {'lp': {'weights': [str(x) for x in weights], 'base': str(B), 'slopes': [str(x) for x in slopes],
                  'slope_excess': str(t)}}
    if ok:
        out.update(status='CERTIFIED', gap='0',
                   certificate={'indices': [i for i, x in enumerate(weights) if x],
                                'weights': [str(x) for x in weights if x], 'base': str(B),
                                'slopes': [str(x) for x in slopes]},
                   bound={'const_excess': str(B - T), 'slope_excess': '0', 'statement': bound_text(B, T, 0)})
        return out
    g, gw, gB, gs = gap_lp(costs, k, s, T + 1)
    tg = max(Fr(0), max(gs) - s)
    out.update(status='BOUNDARY' if g == 0 else 'NO_CERTIFICATE', gap=str(g),
               gap_lp={'weights': [str(x) for x in gw], 'base': str(gB), 'slopes': [str(x) for x in gs],
                       'slope_excess': str(tg)},
               bound={'const_excess': str(gB - T), 'slope_excess': str(tg), 'statement': bound_text(gB, T, tg)})
    out['trace'] = {'slopes': [{'j': j, 'gap_index': (gaps or list(range(k)))[j], 'slope': str(x),
                                'excess': str(x - s), 'tight': x >= s + tg} for j, x in enumerate(gs)]}
    return out


def _score(args):
    return score_family(*args)


# ------------------------------------------------------------- aggregates
def per_example_metric(row):
    """GEPA per-family score: 1 certified, 0.5/(1+g) valid not certified, 0 otherwise."""
    if row['status'] == 'CERTIFIED':
        return 1.0
    return 0.5 / (1 + float(Fr(row['gap']))) if row['valid'] else 0.0


def aggregate(rows):
    per_m = {}
    for r in rows:
        g = per_m.setdefault(r['m'], {'N': 0, 'C': 0, 'boundary': 0, 'no_certificate': 0, 'invalid': 0,
                                      'incomplete': 0, 'timeouts': 0, 'valid': 0, 'W': Fr(0), 'gsum': Fr(0),
                                      'per_k': {}})
        g['N'] += 1
        g['C'] += r['status'] == 'CERTIFIED'
        g['boundary'] += r['status'] == 'BOUNDARY'
        g['no_certificate'] += r['status'] == 'NO_CERTIFICATE'
        g['invalid'] += r['status'] == 'INVALID_OUTPUT'
        g['incomplete'] += r['status'] == 'INCOMPLETE'
        g['timeouts'] += bool(r.get('timeout'))
        g['valid'] += r['valid']
        g['W'] = max(g['W'], Fr(r['gap']))
        if r['valid']:
            g['gsum'] += Fr(r['gap'])
        pk = g['per_k'].setdefault(str(r['k']), [0, 0])
        pk[0] += r['status'] == 'CERTIFIED'
        pk[1] += 1
    out = {}
    for m, g in sorted(per_m.items()):
        G = g['gsum'] / g['valid'] if g['valid'] else None
        out[str(m)] = {'certified': g['C'], 'families': g['N'], 'pct': 100.0 * g['C'] / g['N'],
                       'boundary': g['boundary'], 'no_certificate': g['no_certificate'], 'invalid': g['invalid'],
                       'incomplete': g['incomplete'], 'timeouts': g['timeouts'], 'valid': g['valid'],
                       'W': str(g['W']), 'W_complete': g['valid'] == g['N'],
                       'G': None if G is None else str(G),
                       'per_k': dict(sorted(g['per_k'].items(), key=lambda x: int(x[0])))}
    N = len(rows)
    V = sum(r['valid'] for r in rows)
    pcts = [x['pct'] for x in out.values()]
    Ws = [float(Fr(x['W'])) for x in out.values()]
    Gs = [float(Fr(x['G'])) for x in out.values() if x['G'] is not None]
    combined = (sum(pcts) / len(pcts) + min(pcts) + 0.06 * V / N + 0.06 / (1 + max(Ws))
                + (0.03 / (1 + sum(Gs) / len(Gs)) if Gs else 0.0))
    return {'families': N, 'certified': sum(r['status'] == 'CERTIFIED' for r in rows),
            'boundary': sum(r['status'] == 'BOUNDARY' for r in rows), 'valid': V, 'invalid': N - V,
            'incomplete': sum(r['status'] == 'INCOMPLETE' for r in rows),
            'timeouts': sum(bool(r.get('timeout')) for r in rows),
            'per_m': out, 'worst_m': min(out, key=lambda x: (out[x]['pct'], x)),
            'max_W': str(max(Fr(x['W']) for x in out.values())), 'combined_score': combined,
            'example_scores': {r['id']: per_example_metric(r) for r in rows}}


def holdout_tuple(result):
    pm = result['per_m']
    return {'C': {m: x['certified'] for m, x in pm.items()}, 'N': {m: x['families'] for m, x in pm.items()},
            'W': {m: x['W'] for m, x in pm.items()}, 'G': {m: x['G'] for m, x in pm.items()},
            'invalid': result['invalid'] - result['incomplete'], 'incomplete': result['incomplete'],
            'timeouts': result['timeouts']}


# ------------------------------------------------------------- evaluate
def evaluate(program_path, families, *, require_os_sandbox=True, jobs=8, cache_dir=None,
             per_family=PER_FAMILY_CPU, per_family_wall=PER_FAMILY_WALL, batch=BATCH):
    src = Path(program_path)
    if src.is_symlink() or not src.is_file() or src.stat().st_size > MAX_SOURCE:
        raise ValueError('candidate must be a regular file of at most %d bytes' % MAX_SOURCE)
    source = src.read_bytes()
    set_hash = _sha(canonical(families).encode())
    key = _sha(canonical([_sha(source), set_hash, evaluator_hash(), CONTRACT, require_os_sandbox,
                          per_family, per_family_wall, batch]).encode())
    cache = Path(cache_dir) / (key + '.json') if cache_dir else None
    if cache and cache.exists():
        return dict(json.loads(cache.read_text()), cache_hit=True)
    start = time.monotonic()
    guard = source_guard(source.decode('utf-8', 'replace'))
    if guard:
        rows = [dict(score_family(f, {'status': 'ok'}, {'index': 0, 'output_json': 'null', 'cpu_seconds': 0,
                                                        'seconds': 0}),
                     trace={'failure': 'source guard: ' + guard}) for f in families]
    else:
        send = [{x: f[x] for x in ('id', 'm', 'labels', 'mask', 'gaps', 'k', 'unit_base', 'budget_unit',
                                   'slope_bound')} for f in families]
        chunks = [list(range(i, min(i + batch, len(send)))) for i in range(0, len(send), batch)]
        with ThreadPoolExecutor(max(1, jobs)) as pool:
            runs = list(pool.map(lambda c: run_batch(source, [send[i] for i in c], per_family, require_os_sandbox,
                                                     per_family_wall), chunks))
        args = []
        for c, run in zip(chunks, runs):
            args += [(families[i], run['header'], it, per_family, per_family_wall) for i, it in zip(c, run['items'])]
        if jobs > 1 and len(args) > 16:  # exact scoring is CPU-bound pure Python
            with ProcessPoolExecutor(jobs) as pool:
                rows = list(pool.map(_score, args, chunksize=4))
        else:
            rows = [_score(x) for x in args]
    result = dict(aggregate(rows), kind='bound_program', evaluator_version=VERSION, evaluator_hash=evaluator_hash(),
                  contract=CONTRACT, cache_key=key, candidate_hash=_sha(source), family_set_hash=set_hash,
                  source_guard=guard, per_family_cpu=per_family, per_family_wall=per_family_wall,
                  isolation='macos_seatbelt' if require_os_sandbox else 'process_only',
                  seconds=time.monotonic() - start, results=rows,
                  limitations=['A CERTIFIED family (a,S) is an exact bound d(v) <= T_m(n) for all its states at '
                               'every block length, conditional on the group\'s Lemma 1 and criterion (7) with '
                               'm as a parameter; it says nothing about other families. A miss, crash or '
                               'timeout proves nothing.'])
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
    """Trusted repository controls (integrations.bound_control_*) run in-process, never generated
    code. No CPU limit is enforced; the result reports how many families exceeded the 3 s
    candidate limit so the comparison with sandboxed candidates stays honest."""
    if not module_name.startswith('integrations.bound_control_'):
        raise ValueError('evaluate_trusted is only for integrations.bound_control_* modules')
    start = time.monotonic()
    send = [{x: f[x] for x in ('id', 'm', 'labels', 'mask', 'gaps', 'k', 'unit_base', 'budget_unit',
                               'slope_bound')} for f in families]
    with ProcessPoolExecutor(max(1, jobs)) as pool:
        items = list(pool.map(_trusted_item, [(module_name, f, i) for i, f in enumerate(send)], chunksize=2))
    limit = 1e6
    with ProcessPoolExecutor(max(1, jobs)) as pool:
        rows = list(pool.map(_score, [(f, {'status': 'ok'}, it, limit, limit) for f, it in zip(families, items)],
                             chunksize=4))
    cpu = [it['cpu_seconds'] for it in items]
    return dict(aggregate(rows), kind='bound_trusted_control', control=module_name, evaluator_version=VERSION,
                evaluator_hash=evaluator_hash(), contract=CONTRACT, family_set_hash=_sha(canonical(families).encode()),
                isolation='trusted_in_process', max_family_cpu=max(cpu),
                families_over_candidate_cpu=sum(x > PER_FAMILY_CPU for x in cpu),
                seconds=time.monotonic() - start, results=rows, cache_hit=False)


def _require_control(program):
    p = Path(program).resolve()
    if p.parent != Path(__file__).resolve().parent or not p.name.startswith('bound_control_') or p.suffix != '.py':
        raise SystemExit('--no-os-sandbox is only for trusted integrations/bound_control_*.py')


def _holdout_allowed(program, finalist_manifest, no_os_sandbox):
    p = Path(program).resolve()
    if no_os_sandbox:
        _require_control(program)
        return
    if not finalist_manifest:
        raise SystemExit('--holdout needs --finalist-manifest listing the frozen finalist source sha256')
    frozen = json.loads(Path(finalist_manifest).read_text()).get('frozen_sources', {})
    if _sha(p.read_bytes()) not in set(frozen.values()):
        raise SystemExit('program is not a frozen finalist in %s' % finalist_manifest)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--program', required=True)
    ap.add_argument('--families', required=True, help='frozen development.json (holdout needs --holdout)')
    ap.add_argument('--output', required=True)
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--cache-dir')
    ap.add_argument('--holdout', action='store_true', help='human-run one-time finalist check (or trusted controls)')
    ap.add_argument('--finalist-manifest')
    ap.add_argument('--no-os-sandbox', action='store_true', help='trusted controls only; never generated code')
    ap.add_argument('--per-family-cpu', type=float, default=PER_FAMILY_CPU,
                    help='trusted controls only (with --no-os-sandbox); candidates always get 3 s')
    a = ap.parse_args(argv)
    if a.per_family_cpu != PER_FAMILY_CPU and not a.no_os_sandbox:
        raise SystemExit('--per-family-cpu is for trusted controls only')
    if a.no_os_sandbox:
        _require_control(a.program)
    if a.holdout:
        _holdout_allowed(a.program, a.finalist_manifest, a.no_os_sandbox)
    fams = load_set(a.families, allow_holdout=a.holdout)
    if a.limit:
        fams = fams[:a.limit]
    out = Path(a.output)
    if out.exists():
        raise SystemExit('refusing to overwrite existing %s' % out)
    wall = max(PER_FAMILY_WALL, a.per_family_cpu + 2)
    res = evaluate(a.program, fams, require_os_sandbox=not a.no_os_sandbox, jobs=a.jobs, cache_dir=a.cache_dir,
                   per_family=a.per_family_cpu, per_family_wall=wall)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({x: res[x] for x in ('families', 'certified', 'boundary', 'valid', 'invalid', 'incomplete',
                                          'timeouts', 'max_W', 'combined_score', 'isolation', 'seconds',
                                          'cache_hit')}))
    print(json.dumps({m: {x: g[x] for x in ('certified', 'families', 'pct', 'boundary', 'W', 'W_complete', 'G')}
                      for m, g in res['per_m'].items()}))


if __name__ == '__main__':
    main()
