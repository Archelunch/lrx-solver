"""Untrusted-side JSON bridge for uniform sorting programs (calls `sort_word`).

Same contract as lift_worker.py / corr_worker.py: runs inside the sandboxed
child, imports the candidate once under an import CPU alarm, then calls
sort_word(v) for each state of the (small) batch under a per-state CPU alarm
(ITIMER_PROF, process CPU time) and a per-state wall alarm (ITIMER_REAL, so a
sleeping candidate cannot escape the CPU alarm). It appends one JSON line per
state, with CPU and wall seconds, so a batch killed by the parent's limits still
reports the states it finished. The parent re-checks the recorded times, and the
kernel RLIMIT_CPU set by the parent bounds the whole batch process even if a
candidate disables these alarms. Its output is never accepted as a proof: the
trusted parent (sort_evaluator.py) replays every word literally.
"""
import importlib.util
import json
import signal
import sys
import time
import traceback

MAX_LETTERS = 1000


def _cpu_limit(*_args):
    raise TimeoutError('per-state CPU limit')


def _wall_limit(*_args):
    raise TimeoutError('per-state wall limit')


def _arm(cpu, wall):
    signal.setitimer(signal.ITIMER_PROF, cpu)
    signal.setitimer(signal.ITIMER_REAL, wall)


def _disarm():
    signal.setitimer(signal.ITIMER_PROF, 0)
    signal.setitimer(signal.ITIMER_REAL, 0)


def main():
    program, case_file, output_file = sys.argv[1:4]
    case = json.load(open(case_file, encoding='utf-8'))
    cpu, wall, import_cpu = case['per_state_cpu'], case['per_state_wall'], case['import_cpu']
    process_time, monotonic = time.process_time, time.monotonic
    signal.signal(signal.SIGPROF, _cpu_limit)
    signal.signal(signal.SIGALRM, _wall_limit)
    with open(output_file, 'w', encoding='utf-8') as out:
        try:
            _arm(import_cpu, import_cpu * 5)
            spec = importlib.util.spec_from_file_location('generated_candidate', program)
            if spec is None or spec.loader is None:
                raise ValueError('candidate is not an importable Python file')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _disarm()
            if not callable(getattr(module, 'sort_word', None)):
                raise ValueError('candidate does not define sort_word(v)')
        except BaseException as exc:
            _disarm()
            out.write(json.dumps({'status': 'candidate_error', 'error': type(exc).__name__ + ': ' + str(exc)[:400],
                                  'traceback': traceback.format_exc(limit=3)[-1200:]}) + '\n')
            return
        out.write(json.dumps({'status': 'ok'}) + '\n')
        out.flush()
        for index, v in enumerate(case['states']):
            c0, w0 = process_time(), monotonic()
            item = {'index': index}
            try:
                _arm(cpu, wall)
                word = module.sort_word(list(v))
                _disarm()
                if isinstance(word, str):
                    item['word'] = word[:MAX_LETTERS + 1]
                    item['length'] = len(word)
                else:
                    item['error'] = 'sort_word returned %s, not str' % type(word).__name__
            except BaseException as exc:
                _disarm()
                item['error'] = type(exc).__name__ + ': ' + str(exc)[:300]
            item['cpu_seconds'] = process_time() - c0
            item['seconds'] = monotonic() - w0
            out.write(json.dumps(item) + '\n')
            out.flush()


if __name__ == '__main__':
    main()
