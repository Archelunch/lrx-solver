#!/bin/sh
# Run the nine re-checks of this findings package with the vendored modules only (stdlib, no numpy, no tables).
#   sh run_checks.sh            (python3 is used; set PYTHON=... to override)
# Same steps as run_checks.py. PYTHONPATH is replaced by <package>/vendor. Exit status 0 only if every step passes.
set -u
PKG=$(cd "$(dirname "$0")" && pwd)
PY=${PYTHON:-python3}
PYTHONPATH="$PKG/vendor"
PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH PYTHONDONTWRITEBYTECODE
FAIL=0
echo "package $PKG"
echo "python $("$PY" -c 'import sys; print(sys.version.split()[0])')"

step() {  # step <cwd> <lines to show> <text required in the last line> <python arguments...>
    D=$1; N=$2; NEED=$3; shift 3
    echo "\$ python $*"
    OUT=$(cd "$D" && "$PY" "$@" 2>&1); RC=$?
    printf '%s\n' "$OUT" | tail -n "$N" | sed 's/^/  /'
    echo "  exit $RC"
    [ $RC -eq 0 ] && printf '%s\n' "$OUT" | tail -n 1 | grep -qF "$NEED" || FAIL=1
}

# 1-3. Re-check stored rows and the word_C proof (WORDC-PROOF.md) at m=9..40; nothing is written.
step "$PKG" 1 'problems: none' checks/reversal_k2.py
step "$PKG" 2 'problems: none' checks/reversal_midband.py
step "$PKG" 3 'corollary failures: 0 []' checks/wordc_proof_check.py

# 4-7. word_R1 proof (WORDR1-PROOF.md) at m=9..60, word_G closed-form hypotheses at m=9..80, the carry-across
# words of REVERSAL-CARRY.md, and the portable negative certificate for m=9 {0,4} (stdlib only, -I ignores
# PYTHONPATH, about 16 s). Nothing is written.
step "$PKG" 2 'mismatches (Lemmas P, A-E, theorem, corollary): 0' checks/wordr1_proof_check.py
step "$PKG" 3 'n=1600 exceptions=0' checks/wordg_formula_check.py
step "$PKG" 2 'problems: none' checks/reversal_carry.py
step "$PKG" 3 'VERIFIED' -I negcert/negcert_check.py negcert/negcert-m9-04.json

# 8-9. Rebuild the two generator JSON files on a copy (both scripts refuse to overwrite) and compare.
W=$(mktemp -d)
mkdir -p "$W/a/b"
cp -R "$PKG/checks" "$W/a/b/"
rm "$W/a/b/checks/reversal-m13-words.json" "$W/a/b/checks/reversal-orbit-words.json"
step "$W" 2 'reversal-m13-words.json' a/b/checks/reversal_m13.py
step "$W" 1 'reversal-orbit-words.json' a/b/checks/reversal_orbit.py
"$PY" - "$PKG/checks" "$W/a/b/checks" <<'EOF' || FAIL=1
import json, os, sys
bad = 0
for n in ['reversal-m13-words.json', 'reversal-orbit-words.json']:
    a = json.load(open(os.path.join(sys.argv[1], n)))
    p = os.path.join(sys.argv[2], n)
    b = json.load(open(p)) if os.path.exists(p) else {}
    a.pop('seconds', None); b.pop('seconds', None)
    print(n, 'identical' if a == b else 'DIFFERENT')
    bad |= a != b
sys.exit(bad)
EOF
rm -rf "$W"

cat <<'EOF'

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
  closed forms m=9..200 failures: []
  wrote a/b/checks/reversal-m13-words.json 2.2 s
  wrote a/b/checks/reversal-orbit-words.json 2.4 s
  reversal-m13-words.json identical
  reversal-orbit-words.json identical
EOF
if [ $FAIL -eq 0 ]; then echo "ALL CHECKS PASSED"; else echo "SOME CHECK FAILED"; fi
exit $FAIL
