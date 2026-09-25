"""Untrusted-side JSON bridge for bound-m tree programs (bound-contract-3; calls `certify`).

bound_worker.py (bound-contract-2) with a larger output cap for tree certificates.

Same contract as sort_worker.py: runs inside the sandboxed child, imports the
candidate once under an import CPU alarm, then calls certify(family) for each
family of the (small) batch under a per-family CPU alarm (ITIMER_PROF) and wall
alarm (ITIMER_REAL). Each family's result goes to its own file out-NNNN.json
(RLIMIT_FSIZE is per file), serialized inside the alarm window. The candidate
shares this process and could rewrite these files or disarm the alarms, so the
recorded times are only reports: the parent measures the process CPU with
os.wait4 and rejects a batch that disagrees, the kernel RLIMIT_CPU bounds the
whole batch, fork is denied, and nothing here is accepted as proof: the trusted
parent (bound_evaluator.py) replays and prices every word.

The launch command (bound_evaluator.run_batch) fixes PYTHONHASHSEED so a
candidate's `set(...)` iterates in the same order on every run; random.seed(0)
below covers a candidate that draws from `random` without seeding it. Neither
changes what a word means, only whether the same candidate returns the same
words twice.
"""
import importlib.util
import json
import os
import random
import signal
import sys
import time
import traceback

MAX_JSON = 600000  # bound-contract-3 trees: up to 256000 letters plus JSON overhead


def _cpu_limit(*_args):
    raise TimeoutError('per-family CPU limit')


def _wall_limit(*_args):
    raise TimeoutError('per-family wall limit')


def _arm(cpu, wall):
    signal.setitimer(signal.ITIMER_PROF, cpu)
    signal.setitimer(signal.ITIMER_REAL, wall)


def _disarm():
    signal.setitimer(signal.ITIMER_PROF, 0)
    signal.setitimer(signal.ITIMER_REAL, 0)


def _write(path, obj):
    with open(path, 'w', encoding='utf-8') as out:
        out.write(json.dumps(obj))


def main():
    program, case_file, out_dir = sys.argv[1:4]
    case = json.load(open(case_file, encoding='utf-8'))
    cpu, wall, import_cpu = case['per_family_cpu'], case['per_family_wall'], case['import_cpu']
    process_time, monotonic = time.process_time, time.monotonic
    signal.signal(signal.SIGPROF, _cpu_limit)
    signal.signal(signal.SIGALRM, _wall_limit)
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    random.seed(0)  # a candidate that calls random.* without seeding must still be reproducible
    try:
        _arm(import_cpu, import_cpu * 5)
        spec = importlib.util.spec_from_file_location('generated_candidate', program)
        if spec is None or spec.loader is None:
            raise ValueError('candidate is not an importable Python file')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _disarm()
        if not callable(getattr(module, 'certify', None)):
            raise ValueError('candidate does not define certify(family)')
    except BaseException as exc:
        _disarm()
        _write(os.path.join(out_dir, 'header.json'),
               {'status': 'candidate_error', 'error': type(exc).__name__ + ': ' + str(exc)[:400],
                'traceback': traceback.format_exc(limit=3)[-1200:]})
        return
    _write(os.path.join(out_dir, 'header.json'), {'status': 'ok'})
    for index, fam in enumerate(case['families']):
        c0, w0 = process_time(), monotonic()
        item = {'index': index}
        try:
            _arm(cpu, wall)
            text = json.dumps(module.certify(json.loads(json.dumps(fam))))
            _disarm()
            if len(text) > MAX_JSON:
                item['error'] = 'OutputTooLarge: certify output is %d bytes of JSON (limit %d)' % (len(text), MAX_JSON)
            else:
                item['output_json'] = text
        except BaseException as exc:
            _disarm()
            item['error'] = type(exc).__name__ + ': ' + str(exc)[:300]
        item['cpu_seconds'] = process_time() - c0
        item['seconds'] = monotonic() - w0
        _write(os.path.join(out_dir, 'out-%04d.json' % index), item)


if __name__ == '__main__':
    main()
