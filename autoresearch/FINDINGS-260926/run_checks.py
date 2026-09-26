"""Run the five re-checks of this findings package with the vendored modules only (stdlib, no numpy, no tables).

    python run_checks.py

Same steps as run_checks.sh, for systems without a POSIX shell. PYTHONPATH is replaced by <package>/vendor.
1. checks/reversal_k2.py         re-checks 390 word_G rows and 150 stored rows
2. checks/reversal_midband.py    re-checks 14 middle-band certificates and the m=9 {0,4} witness (no tables)
3. checks/wordc_proof_check.py   checks every claim of WORDC-PROOF.md against literal word_C at m=9..40 (720 pairs)
4. checks/reversal_m13.py and checks/reversal_orbit.py rebuild their JSON on a temporary copy of checks/ (both
   refuse to overwrite), then the rebuilt JSON is compared with the stored JSON, ignoring only 'seconds'.
Exit status 0 only if every step passes.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent
ENV = dict(os.environ, PYTHONPATH=str(PKG / 'vendor'), PYTHONDONTWRITEBYTECODE='1')
REBUILT = ['reversal-m13-words.json', 'reversal-orbit-words.json']


def run(script, cwd, tail, need):
    """Run one script with the vendored PYTHONPATH; pass if exit 0 and `need` is in its last output line."""
    print('$ python %s' % script, flush=True)
    p = subprocess.run([sys.executable, str(script)], cwd=cwd, env=ENV, capture_output=True, text=True)
    out = (p.stdout + p.stderr).rstrip().splitlines()
    for line in out[-tail:]:
        print('  ' + line)
    print('  exit %d' % p.returncode, flush=True)
    return p.returncode == 0 and bool(out) and need in out[-1]


def main():
    print('package', PKG)
    print('python', sys.version.split()[0])
    ok = run(PKG / 'checks' / 'reversal_k2.py', PKG, 1, 'problems: none')
    ok &= run(PKG / 'checks' / 'reversal_midband.py', PKG, 2, 'problems: none')
    ok &= run(PKG / 'checks' / 'wordc_proof_check.py', PKG, 3, 'corollary failures: 0 []')
    with tempfile.TemporaryDirectory() as w:
        work = Path(w) / 'a' / 'b' / 'checks'
        shutil.copytree(PKG / 'checks', work)
        for n in REBUILT:
            (work / n).unlink()
        ok &= run(work / 'reversal_m13.py', w, 2, 'reversal-m13-words.json')
        ok &= run(work / 'reversal_orbit.py', w, 1, 'reversal-orbit-words.json')
        for n in REBUILT:
            a = json.loads((PKG / 'checks' / n).read_text())
            b = json.loads((work / n).read_text()) if (work / n).exists() else {}
            a.pop('seconds', None)
            b.pop('seconds', None)
            same = a == b
            ok &= same
            print(n, 'identical' if same else 'DIFFERENT')
    print("""
expected last lines (timings vary):
  re-checked 390 word_G rows and 150 stored rows in 2.3 s; problems: none
  dual certificate m=9 {0,4}: witness B=54 beta=[7, 7], B+3beta0=75 (stored min 75)
  problems: none
  m = 9..40, pairs (m, a) with 1 <= a <= m-2: 720
  mismatches (Lemmas A-E, theorem): 0
  corollary failures: 0 []
  closed forms m=9..200 failures: []
  wrote a/b/checks/reversal-m13-words.json 2.2 s
  wrote a/b/checks/reversal-orbit-words.json 2.4 s
  reversal-m13-words.json identical
  reversal-orbit-words.json identical""")
    print('ALL CHECKS PASSED' if ok else 'SOME CHECK FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
