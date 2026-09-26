#!/usr/bin/env python3
"""Python driver for the C oracle lrxfast (stdlib only; imports negcert_general.py from the parent directory
for the definitions: base vector, blocks, Profile transcription).

    run(vec, W, classes, K=None, ...) -> dict(result='FOUND'|'NONE'|'INCOMPLETE', F, word, B, beta, ...)

Encoding (same as negcert_general.encode, renumbered for 4-bit packing): label x -> x-1, the zero of block j
-> m+j.  Only unit bases with two one-zero blocks (the middle-band families) are supported.
Every word returned by the C program is re-priced here by negcert_general.price (letter-by-letter Profile
transcription) and must re-price to the F the search reported (or below, for weighted mode).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import negcert_general as NG  # noqa: E402

BIN = os.path.join(HERE, 'lrxfast')


def encode_fast(vec):
    m = sum(1 for x in vec if x)
    blocks = NG.blocks_of(vec)
    if len(vec) != m + 2 or len(blocks) != 2 or any(len(b) != 1 for b in blocks):
        raise ValueError('lrxfast supports unit bases with two one-zero blocks only')
    out, zi = [], 0
    for x in vec:
        if x == 0:
            out.append(m + zi)
            zi += 1
        else:
            out.append(x - 1)
    return m, out


def table_arg(m, classes):
    cls = [None] * m
    for i, part in enumerate(classes):
        for x in part:
            cls[x - 1] = i
    if None in cls or sorted(x for p in classes for x in p) != list(range(1, m + 1)):
        raise ValueError('classes must partition 1..m')
    return ','.join(map(str, cls))


def run(vec, W, classes_list, K=None, cap=None, mem_gb=11.0, threads=4, omega=None, log=None, no_search=False,
        wcap=None, then_exact=False, anytime=False):
    """omega: None, one 'b/a' string or a list of them (weighted passes first; with then_exact the exact pass
    follows when no weighted pass finds a word).  result 'NONE' only comes from the exact pass."""
    m, u = encode_fast(vec)
    cmd = [BIN, '--m', str(m), '--u0', ','.join(map(str, u)), '--W', '%d,%d,%d' % tuple(W),
           '--mem-gb', str(mem_gb), '--threads', str(threads)]
    for cl in classes_list:
        cmd += ['--table', table_arg(m, cl)]
    if K is not None:
        cmd += ['--K', str(K)]
    if cap:
        cmd += ['--cap', str(cap)]
    if isinstance(omega, str):
        omega = [omega]
    for om in omega or []:
        cmd += ['--omega', om]
    if wcap:
        cmd += ['--wcap', str(wcap)]
    if then_exact:
        cmd += ['--then-exact']
    if anytime:
        cmd += ['--anytime']
    if no_search:
        cmd += ['--no-search']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=None if log is None else subprocess.STDOUT,
                            text=True)
    out = {'cmd': ' '.join(cmd), 'tables': [], 'lines': []}
    for line in proc.stdout:
        line = line.rstrip('\n')
        out['lines'].append(line)
        if log:
            log(line)
        if line.startswith('TABLE'):
            out['tables'].append(dict(kv.split('=', 1) for kv in line.split()[2:] if '=' in kv))
            if 'INCONSISTENT' in line:
                out['inconsistent'] = True
        elif line.startswith('START'):
            out['start_bound'] = int(line.split('=')[1])
        elif line.startswith('STATS'):
            out['stats'] = dict(kv.split('=', 1) for kv in line.split()[1:])
        elif line.startswith('WSTATS'):
            out.setdefault('wstats', []).append(dict(kv.split('=', 1) for kv in line.split()[1:]))
        elif line.startswith('WEIGHTED'):
            out.setdefault('weighted', []).append(line)
        elif line.startswith('RESULT'):
            parts = line.split()
            out['result'] = parts[1]
            if parts[1] == 'FOUND':
                out['F'], out['word'] = int(parts[2]), parts[3]
            elif parts[1] == 'NONE':
                out['K'] = int(parts[2])
            else:
                out['reason'] = ' '.join(parts[2:])
    proc.wait()
    out['returncode'] = proc.returncode
    if out.get('result') == 'FOUND':
        Fw, B, beta = NG.price(vec, out['word'], W)
        out.update(Fw=Fw, B=B, beta=beta)
        if Fw != out['F']:
            raise AssertionError('C search reported F=%d, transcription re-prices the word to %d' % (out['F'], Fw))
        out['exact_pass'] = 'stats' in out
    if 'result' not in out and not no_search:
        out['result'] = 'ERROR'
    return out
