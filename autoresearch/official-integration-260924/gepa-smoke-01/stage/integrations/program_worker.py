"""Untrusted-side JSON bridge.  Its output is never accepted as a proof."""
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
        fn = getattr(module, 'propose_words')
        case = json.load(open(case_file, encoding='utf-8'))
        words = fn(case)
        result = {'status': 'ok', 'words': words}
    except BaseException as exc:
        result = {'status': 'candidate_error', 'error': type(exc).__name__ + ': ' + str(exc)[:400],
                  'traceback': traceback.format_exc(limit=3)[-1200:]}
    with open(output_file, 'w', encoding='utf-8') as stream:
        json.dump(result, stream)


if __name__ == '__main__':
    main()
