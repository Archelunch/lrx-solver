"""Run the thirteen re-checks of this findings package with the vendored modules only (stdlib, no numpy, no tables).

    python run_checks.py

Same steps as run_checks.sh, for systems without a POSIX shell. PYTHONPATH is replaced by <package>/vendor.
1. checks/reversal_k2.py         re-checks 390 word_G rows and 150 stored rows
2. checks/reversal_midband.py    re-checks 14 middle-band certificates and the m=9 {0,4} witness (no tables)
3. checks/wordc_proof_check.py   checks every claim of WORDC-PROOF.md against literal word_C at m=9..40 (720 pairs)
4. checks/wordr1_proof_check.py  checks every claim of WORDR1-PROOF.md against literal word_R1 at m=9..60
5. checks/wordg_formula_check.py tests the 28 word_G rule-row hypotheses and C1-C7 at m=9..80 (C1, C3, C5 fail by design)
6. checks/reversal_carry.py      re-checks the 59 stored carry-across certificates and the word_M closed form to m=60
7. negcert/negcert_check.py      portable negative certificate for m=9 {0,4}; run with -I (stdlib only, about 16 s)
8. checks/reversal_k3.py         re-checks the 455 stored k=3 class-survey certificates and the word_W closed form
9. checks/reversal_interior.py   re-checks the interior-mask root certificates and cell completeness
10. checks/midband_trees.py      re-checks the middle-band tree certificates (without --refutations)
11. negcert/midband_positive_check.py  re-checks the positive root certificates from column generation
12-13. checks/reversal_m13.py and checks/reversal_orbit.py rebuild their JSON on a temporary copy of checks/ (both
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


def run(script, cwd, tail, need, *args, flags=()):
    """Run one script with the vendored PYTHONPATH; pass if exit 0 and `need` is in its last output line."""
    print('$ python %s' % ' '.join([*flags, str(script), *args]), flush=True)
    p = subprocess.run([sys.executable, *flags, str(script), *args], cwd=cwd, env=ENV, capture_output=True,
                       text=True)
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
    ok &= run(PKG / 'checks' / 'wordr1_proof_check.py', PKG, 2, 'mismatches (Lemmas P, A-E, theorem, corollary): 0')
    ok &= run(PKG / 'checks' / 'wordg_formula_check.py', PKG, 3, 'n=1600 exceptions=0')
    ok &= run(PKG / 'checks' / 'reversal_carry.py', PKG, 2, 'problems: none')
    ok &= run(Path('negcert') / 'negcert_check.py', PKG, 3, 'VERIFIED', str(Path('negcert') / 'negcert-m9-04.json'),
              flags=('-I',))
    ok &= run(PKG / 'checks' / 'reversal_k3.py', PKG, 3, 'problems: none')
    ok &= run(PKG / 'checks' / 'reversal_interior.py', PKG, 3, 'problems: none')
    ok &= run(PKG / 'checks' / 'midband_trees.py', PKG, 1, 'ALL OK')
    ok &= run(PKG / 'negcert' / 'midband_positive_check.py', PKG, 1, 'problems: none')
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
  m = 9..60: 52 values of m
  mismatches (Lemmas P, A-E, theorem, corollary): 0
  C5 beta_0 = m-2 on every row  n=1600 exceptions=107 [...]   (coarse on purpose; C1, C3, C5 are expected to fail)
  C6 B = length (Lemma 1 base equals the word length)  n=1600 exceptions=0
  C7 B <= T and beta_0, beta_1 <= m-2 (criterion (7) numbers, weight 1)  n=1600 exceptions=0
  closed form: 160 rows scored by evaluator + audit (m <= 40), 207 rows by replay + criterion (7)
  problems: none
  root mixture needs Bbar < T+1 = 53 and betabar_0 <= s = 7, ...: NO ROOT-LEAF CERTIFICATE
  total 16.5 s
  VERIFIED
  word_W rows: 122 by evaluator+audit+replay (m <= 24), 728 by replay+criterion (7) (m = 25..40)
  stored certified rows re-checked: 455; misses stored: 50
  problems: none wall 1.9
  stored certified rows re-checked: 837; misses stored: 14
  problems: none wall 2.1
  ALL OK
  problems: none
  closed forms m=9..200 failures: []
  wrote a/b/checks/reversal-m13-words.json 2.2 s
  wrote a/b/checks/reversal-orbit-words.json 2.4 s
  reversal-m13-words.json identical
  reversal-orbit-words.json identical""")
    print('ALL CHECKS PASSED' if ok else 'SOME CHECK FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
