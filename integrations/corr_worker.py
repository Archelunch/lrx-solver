"""Untrusted-side JSON bridge for corr-cert candidates (calls `coefficients`).

Same contract as lift_worker.py / program_worker.py: runs inside the sandboxed
child process, imports the candidate module, calls coefficients(m) and writes
a status object. Its output is never accepted as a proof -- the trusted
parent (corr_evaluator.py) decodes the JSON-safe dict and replays it through
corrcert.check_certificate.
"""
import importlib.util
import json
import sys
import traceback


def main():
    program, case_file, output_file = sys.argv[1:4]
    try:
        spec = importlib.util.spec_from_file_location('generated_candidate', program)
        if spec is None or spec.loader is None:
            raise ValueError('candidate is not an importable Python file')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, 'coefficients'):
            raise ValueError('candidate does not define coefficients(m)')
        case = json.load(open(case_file, encoding='utf-8'))
        m = case['m']
        result = {'status': 'ok', 'output': module.coefficients(m)}
    except BaseException as exc:
        result = {'status': 'candidate_error', 'error': type(exc).__name__ + ': ' + str(exc)[:400],
                  'traceback': traceback.format_exc(limit=3)[-1200:]}
    with open(output_file, 'w', encoding='utf-8') as stream:
        json.dump(result, stream)


if __name__ == '__main__':
    main()
