"""Trusted evaluator for uniform LRX sorting programs (autoresearch/sort-m9-260925/TASK.md).

A candidate program exposes `sort_word(v: list[int]) -> str`. It runs only in a
separate process under the official-integration Seatbelt profile
(program_sandbox.py, program_evaluator._preexec, unchanged, exactly as
lift_evaluator.py uses them), one process per batch of states with a per-state
alarm. Only words cross back. The parent replays every word literally with
src/lrx/certificates.replay_visible and compares with the canonical root.
Exact distances d(v) come from the frozen set (read from sha256-verified BFS
tables at freeze time). A long word, crash or time limit is never evidence
about d(v); a valid word is only an upper bound. Version 2 limits each state to
0.2 s of CPU (constructive programs only; state-space search times out) and
adds a uniformity term, the worst per-r within-budget rate, to the score.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import mmap
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from integrations.program_evaluator import MAX_OUTPUT_BYTES, _preexec
from integrations.program_sandbox import SandboxUnavailable, sandbox_command, sandbox_profile
from src.lrx.certificates import replay_visible
from src.lrx.table_bfs import Ranker

VERSION = 'sort-eval-2'
CONTRACT = ('sort-contract-2: candidate defines sort_word(v) -> str over L,R,X (L rotates left, R '
            'rotates right, X swaps the first two entries). A state is valid iff the word has at most '
            '1000 letters, the call used at most 0.2 s of CPU time and 1 s of wall time, and '
            'certificates.replay_visible(v, word) equals (1..m, 0^r). Module import may use 0.5 s of CPU. '
            'Batches hold 10 states; the kernel caps each batch process at 10*0.2 + 1.5 CPU seconds. '
            'Any state-space search (BFS, IDA*, beam search over LRX states) times out, and a timeout counts '
            'as invalid. within_budget iff valid and len(word) <= T_m(n) = m(m+1)/2 + (r-1)(m-2). '
            'excess = len(word) - d(v) with d(v) the exact BFS distance to the canonical root. Crash, '
            'non-str, bad letters, >1000 letters, a time limit or a killed batch count as invalid. '
            'combined_score = within/N + 0.5 * min over r of the per-r within rate + 0.25/(1 + mean excess '
            'over valid states) - invalid/N (third term 0 if no valid state).')
MAX_LETTERS, MAX_SOURCE, BATCH = 1000, 65536, 10
PER_STATE_CPU, PER_STATE_WALL, IMPORT_CPU, STARTUP_CPU = 0.2, 1.0, 0.5, 1.0
CPU_TOLERANCE, WALL_TOLERANCE = 0.05, 0.25
SCHEMA = 'lrx-sort-set-v1'
_SOURCES = ('sort_evaluator.py', 'sort_worker.py', 'program_sandbox.py')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def evaluator_hash():
    here = Path(__file__).parent
    certs = here.parent / 'src' / 'lrx' / 'certificates.py'
    return _sha(VERSION.encode() + b''.join((here / f).read_bytes() for f in _SOURCES) + certs.read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def budget(m, r):
    return m * (m + 1) // 2 + (r - 1) * (m - 2)


def root(m, r):
    return tuple(range(1, m + 1)) + (0,) * r


# ------------------------------------------------------------- frozen sets
def guard_not_holdout(path):
    raw = json.loads(Path(path).read_text())
    if 'holdout' in Path(path).name or raw.get('set') != 'development':
        raise ValueError('engines may load only the frozen development set, never holdout')


def load_set(path, allow_holdout=False):
    """Frozen state list; the holdout file loads only with allow_holdout=True (human finalist check)."""
    raw = json.loads(Path(path).read_text())
    if raw.get('schema') != SCHEMA or raw.get('set') not in ('development', 'holdout'):
        raise ValueError('not a frozen sort state set')
    if raw['set'] == 'holdout' and not allow_holdout:
        raise ValueError('holdout is evaluated only once, after finalist freeze')
    states = raw['states']
    for s in states:
        m, r, v = s['m'], s['r'], tuple(s['v'])
        if sorted(v) != sorted(root(m, r)) or s['budget'] != budget(m, r) or not 0 <= s['d'] <= s['budget']:
            raise ValueError('malformed frozen state %r' % s.get('id'))
    if not states or len({s['id'] for s in states}) != len(states):
        raise ValueError('empty state set or duplicate ids')
    return states


# ------------------------------------------------------------- sandbox run
def run_batch(source, vectors, per_state=PER_STATE_CPU, require_os_sandbox=True, per_state_wall=PER_STATE_WALL):
    """Same mechanism as lift_evaluator.run_program; one sandboxed process per small batch.

    The kernel RLIMIT_CPU (program_evaluator._preexec) caps the whole batch at
    per_state * len + IMPORT_CPU + STARTUP_CPU CPU seconds, whatever the candidate does
    to the worker's own alarms; the wall kill bounds sleeping candidates."""
    wall = per_state_wall * len(vectors) + IMPORT_CPU * 5 + 5.0
    cpu_cap = per_state * len(vectors) + IMPORT_CPU + STARTUP_CPU
    with tempfile.TemporaryDirectory(prefix='lrx-sort-') as temp:
        scratch = Path(temp).resolve()
        (scratch / 'candidate.py').write_bytes(source)
        shutil.copyfile(Path(__file__).with_name('sort_worker.py'), scratch / 'worker.py')
        (scratch / 'case.json').write_text(json.dumps({'states': vectors, 'per_state_cpu': per_state,
                                                       'per_state_wall': per_state_wall, 'import_cpu': IMPORT_CPU}))
        out = scratch / 'output.jsonl'
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
        killed = False
        with (scratch / 'stdout').open('wb') as so, (scratch / 'stderr').open('wb') as se:
            proc = subprocess.Popen(command, cwd=scratch, env=env, stdin=subprocess.DEVNULL, stdout=so,
                                    stderr=se, start_new_session=True, preexec_fn=lambda: _preexec(cpu_cap))
            try:
                proc.wait(timeout=wall)
            except subprocess.TimeoutExpired:
                killed = True
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        meta = {'seconds': time.monotonic() - start, 'isolation': isolation}
        log = (scratch / 'stderr').read_bytes()[:4096].decode('utf-8', 'replace')
        if 'sandbox_apply: Operation not permitted' in log:
            raise SandboxUnavailable('macOS Seatbelt denied by outer execution environment')
        items = [None] * len(vectors)
        header = {'status': 'INCOMPLETE', 'reason': 'batch wall limit' if killed else
                  'worker exit %s (a negative code or SIGXCPU is the kernel CPU cap)' % proc.returncode,
                  'stderr': log[-600:]}
        if out.exists() and out.stat().st_size <= MAX_OUTPUT_BYTES:
            lines = out.read_bytes().decode('utf-8', 'replace').splitlines()
            for i, line in enumerate(lines):
                try:
                    obj = json.loads(line)
                except ValueError:
                    break  # a torn last line from a killed batch
                if i == 0:
                    header = obj if isinstance(obj, dict) and obj.get('status') in ('ok', 'candidate_error') \
                        else {'status': 'INVALID_OUTPUT', 'reason': 'worker header must be a status object'}
                elif isinstance(obj, dict) and type(obj.get('index')) is int and 0 <= obj['index'] < len(items):
                    items[obj['index']] = obj
        if header.get('status') == 'ok' and (killed or proc.returncode):
            header = dict(header, killed='batch wall limit' if killed else
                          'batch process ended with code %s (kernel CPU cap)' % proc.returncode)
        return dict(meta, header=header, items=items)


# ------------------------------------------------------------- scoring
def score_state(state, header, item, per_state=PER_STATE_CPU, per_state_wall=PER_STATE_WALL):
    m, r, T, d = state['m'], state['r'], state['budget'], state['d']
    row = {'id': state['id'], 'm': m, 'r': r, 'd': d, 'budget': T, 'valid': False, 'within': False,
           'length': None, 'excess': None, 'slack': None}
    if header.get('status') != 'ok':
        row['status'] = 'CANDIDATE_ERROR' if header.get('status') == 'candidate_error' else 'INCOMPLETE'
        row['failure'] = header.get('error') or header.get('reason')
        return row
    if item is None:
        row['status'], row['failure'] = 'INCOMPLETE', header.get('killed') or 'no result for this state'
        return row
    row['seconds'], row['cpu_seconds'] = item.get('seconds'), item.get('cpu_seconds')
    if 'error' in item:
        timeout = item['error'].startswith('TimeoutError')
        row['status'], row['failure'] = ('TIMEOUT' if timeout else 'CANDIDATE_ERROR'), item['error']
        return row
    word = item.get('word')
    if not isinstance(word, str) or item.get('length', len(word)) > MAX_LETTERS or set(word) - set('LRX'):
        row['status'] = 'INVALID_OUTPUT'
        row['failure'] = 'word must be a string over L,R,X of at most %d letters' % MAX_LETTERS
        return row
    cpu, wall = item.get('cpu_seconds'), item.get('seconds')
    if not isinstance(cpu, (int, float)) or not isinstance(wall, (int, float)) or \
            cpu > per_state + CPU_TOLERANCE or wall > per_state_wall + WALL_TOLERANCE:
        row['status'], row['failure'] = 'TIMEOUT', 'state exceeded %.2f s CPU or %.1f s wall' % (per_state, per_state_wall)
        return row
    row['length'] = len(word)
    final = replay_visible(tuple(state['v']), word)
    if final != root(m, r):
        row['status'], row['final'], row['word'] = 'NOT_SORTED', list(final), word
        return row
    row.update(valid=True, within=len(word) <= T, excess=len(word) - d, slack=T - len(word), word=word)
    if len(word) < d:
        raise AssertionError('word shorter than the exact distance: table or replay bug, never a score')
    row['status'] = 'WITHIN_BUDGET' if row['within'] else 'OVER_BUDGET'
    return row


def aggregate(rows):
    N = len(rows)
    valid = [r for r in rows if r['valid']]
    within = sum(r['within'] for r in rows)
    mean_excess = sum(r['excess'] for r in valid) / len(valid) if valid else None
    invalid = N - len(valid)
    per_r = {}
    for r in rows:
        key = 'm%dr%d' % (r['m'], r['r'])
        g = per_r.setdefault(key, {'states': 0, 'within': 0, 'valid': 0, 'excess_sum': 0, 'timeouts': 0})
        g['states'] += 1
        g['timeouts'] += r['status'] == 'TIMEOUT'
        g['within'] += r['within']
        g['valid'] += r['valid']
        g['excess_sum'] += r['excess'] or 0
    for g in per_r.values():
        g['within_rate'] = g['within'] / g['states']
        g['mean_excess'] = g['excess_sum'] / g['valid'] if g['valid'] else None
    min_rate = min(g['within_rate'] for g in per_r.values())
    score = within / N + 0.5 * min_rate + (0.25 / (1 + mean_excess) if valid else 0.0) - invalid / N
    return {'states': N, 'within_budget': within, 'within_fraction': within / N, 'min_r_within_rate': min_rate,
            'worst_r': min(per_r, key=lambda k: (per_r[k]['within_rate'], k)), 'valid': len(valid),
            'invalid': invalid, 'invalid_fraction': invalid / N, 'mean_excess': mean_excess,
            'max_excess': max((r['excess'] for r in valid), default=None),
            'min_slack': min((r['slack'] for r in valid), default=None),
            'timeouts': sum(r['status'] == 'TIMEOUT' for r in rows),
            'incomplete': sum(r['status'] == 'INCOMPLETE' for r in rows),
            'per_r': dict(sorted(per_r.items())), 'combined_score': score}


def evaluate(program_path, states, *, require_os_sandbox=True, jobs=8, cache_dir=None,
             per_state=PER_STATE_CPU, batch=BATCH, per_state_wall=PER_STATE_WALL):
    src = Path(program_path)
    if src.is_symlink() or not src.is_file() or src.stat().st_size > MAX_SOURCE:
        raise ValueError('candidate must be a regular file of at most %d bytes' % MAX_SOURCE)
    source = src.read_bytes()
    set_hash = _sha(canonical(states).encode())
    key = _sha(canonical([_sha(source), set_hash, evaluator_hash(), CONTRACT, require_os_sandbox,
                          per_state, per_state_wall, batch]).encode())
    cache = Path(cache_dir) / (key + '.json') if cache_dir else None
    if cache and cache.exists():
        return dict(json.loads(cache.read_text()), cache_hit=True)
    start = time.monotonic()
    chunks = [states[i:i + batch] for i in range(0, len(states), batch)]
    with ThreadPoolExecutor(max(1, jobs)) as pool:
        runs = list(pool.map(lambda c: run_batch(source, [s['v'] for s in c], per_state, require_os_sandbox,
                                                 per_state_wall), chunks))
    rows = []
    for chunk, run in zip(chunks, runs):
        rows += [score_state(s, run['header'], it, per_state, per_state_wall) for s, it in zip(chunk, run['items'])]
    result = dict(aggregate(rows), kind='sort_program', evaluator_version=VERSION, evaluator_hash=evaluator_hash(),
                  contract=CONTRACT, cache_key=key, candidate_hash=_sha(source), state_set_hash=set_hash,
                  isolation='macos_seatbelt' if require_os_sandbox else 'process_only',
                  seconds=time.monotonic() - start, results=rows,
                  limitations=['Finite frozen states only. A valid word is an upper bound on d(v) for that '
                               'state; a miss, crash or timeout proves nothing, and development scores do '
                               'not extend to unseen states or r.'])
    if cache and not result['incomplete']:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(result))
    return dict(result, cache_hit=False)


# ------------------------------------------------------------- exact-table diagnostics
class Tables:
    """Read-only mmap of sha256-verified distance tables, for packet prefix diagnostics only."""

    def __init__(self, entries, verify=True):
        self.maps, self.rankers = {}, {}
        for (m, r), (path, digest) in entries.items():
            with open(path, 'rb') as fh:
                mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
            if verify:
                h = hashlib.sha256()
                for i in range(0, len(mm), 1 << 26):
                    h.update(mm[i:i + (1 << 26)])
                if h.hexdigest() != digest:
                    raise ValueError('table hash mismatch for m=%d r=%d' % (m, r))
            self.maps[(m, r)], self.rankers[(m, r)] = mm, Ranker(m, r)

    def distance(self, v):
        m = max(v)
        r = len(v) - m
        ranker = self.rankers[(m, r)]
        return self.maps[(m, r)][ranker.rank(ranker.positions(tuple(v)))]

    def prefix_trace(self, state, word):
        """First step leaving every shortest path, and first step after which T is unreachable."""
        v, T, d0 = tuple(state['v']), state['budget'], state['d']
        off_path = lost = None
        cur = v
        for t, ch in enumerate(word, 1):
            cur = replay_visible(cur, ch)
            dt = self.distance(cur)
            if off_path is None and t + dt > d0:
                off_path = {'step': t, 'prefix': word[:t], 'd_after': dt}
            if lost is None and t + dt > T:
                lost = {'step': t, 'd_after': dt}
                break
        return {'first_off_shortest_path': off_path, 'first_budget_lost': lost}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--program', required=True)
    ap.add_argument('--states', required=True, help='frozen development.json (holdout needs --holdout)')
    ap.add_argument('--output', required=True)
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--cache-dir')
    ap.add_argument('--holdout', action='store_true', help='human-run one-time finalist check only')
    ap.add_argument('--no-os-sandbox', action='store_true', help='trusted controls only; never generated code')
    a = ap.parse_args(argv)
    states = load_set(a.states, allow_holdout=a.holdout)
    out = Path(a.output)
    if out.exists():
        raise SystemExit('refusing to overwrite existing %s' % out)
    res = evaluate(a.program, states, require_os_sandbox=not a.no_os_sandbox, jobs=a.jobs, cache_dir=a.cache_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({x: res[x] for x in ('states', 'within_budget', 'within_fraction', 'min_r_within_rate',
                                          'worst_r', 'valid', 'invalid',
                                          'mean_excess', 'max_excess', 'timeouts', 'incomplete',
                                          'combined_score', 'per_r', 'isolation', 'seconds', 'cache_hit')}))


if __name__ == '__main__':
    main()
