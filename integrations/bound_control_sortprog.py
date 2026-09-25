"""Sort-m9 finalist as a one-word family source (control c). Generated code: sandbox only.

Builds a candidate from the frozen sort-m9 GEPA finalist
(autoresearch/sort-m9-260925/finalists/sources/gepa.py, sha256 checked against
finalists/manifest.json) plus a small certify() wrapper that calls
sort_word(unit_base) once, drops any X on two zeros (a no-op on the vector that
Lemma 1 forbids) and freely reduces LR/RL/XX. The combined source is written to
a fresh path and evaluated only through bound_evaluator.evaluate with the
Seatbelt sandbox, never in-process. m = 9 is the control; m = 10 is diagnostic.

    python -m integrations.bound_control_sortprog --families F --out-dir DIR
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINALISTS = ROOT / 'autoresearch' / 'sort-m9-260925' / 'finalists'
WRAPPER = '''

def _drop_zero_swaps(v, word):
    a, n, c, out = list(v), len(v), 0, []
    for ch in word:
        if ch == 'X':
            j = (c + 1) % n
            if a[c] == 0 and a[j] == 0:
                continue
            a[c], a[j] = a[j], a[c]
        else:
            c = (c + (1 if ch == 'L' else -1)) % n
        out.append(ch)
    red = []
    for ch in out:
        if red and red[-1] + ch in ('LR', 'RL', 'XX'):
            red.pop()
        else:
            red.append(ch)
    return ''.join(red)


def certify(family):
    v = list(family['unit_base'])
    return {'words': [_drop_zero_swaps(v, sort_word(list(v)))]}
'''


def build(out_dir: Path, arm='gepa') -> Path:
    src = FINALISTS / 'sources' / (arm + '.py')
    want = {f['arm']: f['source_sha256'] for f in json.loads((FINALISTS / 'manifest.json').read_text())['finalists']}
    data = src.read_bytes()
    if hashlib.sha256(data).hexdigest() != want.get(arm):
        raise SystemExit('finalist %s does not match finalists/manifest.json' % src)
    path = Path(out_dir) / ('sortprog-%s.py' % arm)
    if path.exists():
        raise SystemExit('refusing to overwrite existing %s' % path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data + WRAPPER.encode())
    return path


def main(argv=None):
    from integrations import bound_evaluator as E

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--families', required=True)
    ap.add_argument('--out-dir', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--cache-dir')
    a = ap.parse_args(argv)
    if a.output.exists():
        raise SystemExit('refusing to overwrite existing %s' % a.output)
    program = build(a.out_dir)
    res = E.evaluate(program, E.load_set(a.families), require_os_sandbox=True, jobs=a.jobs, cache_dir=a.cache_dir)
    a.output.write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps({x: res[x] for x in ('families', 'certified', 'boundary', 'valid', 'invalid', 'incomplete',
                                          'max_W', 'combined_score', 'isolation', 'seconds')}))
    print(json.dumps({m: {x: g[x] for x in ('certified', 'families', 'pct', 'boundary', 'W', 'G')}
                      for m, g in res['per_m'].items()}))


if __name__ == '__main__':
    main()
