#!/bin/sh
# Run the five re-checks of this findings package with the vendored modules only (stdlib, no numpy, no tables).
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

step() {  # step <cwd> <script> <lines to show> <text required in the last line>
    echo "\$ python $2"
    OUT=$(cd "$1" && "$PY" "$2" 2>&1); RC=$?
    printf '%s\n' "$OUT" | tail -n "$3" | sed 's/^/  /'
    echo "  exit $RC"
    [ $RC -eq 0 ] && printf '%s\n' "$OUT" | tail -n 1 | grep -qF "$4" || FAIL=1
}

# 1-3. Re-check stored rows and the word_C proof (WORDC-PROOF.md) at m=9..40; nothing is written.
step "$PKG" checks/reversal_k2.py 1 'problems: none'
step "$PKG" checks/reversal_midband.py 2 'problems: none'
step "$PKG" checks/wordc_proof_check.py 3 'corollary failures: 0 []'

# 4. Rebuild the two generator JSON files on a copy (both scripts refuse to overwrite) and compare.
W=$(mktemp -d)
mkdir -p "$W/a/b"
cp -R "$PKG/checks" "$W/a/b/"
rm "$W/a/b/checks/reversal-m13-words.json" "$W/a/b/checks/reversal-orbit-words.json"
step "$W" a/b/checks/reversal_m13.py 2 'reversal-m13-words.json'
step "$W" a/b/checks/reversal_orbit.py 1 'reversal-orbit-words.json'
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
  closed forms m=9..200 failures: []
  wrote a/b/checks/reversal-m13-words.json 2.2 s
  wrote a/b/checks/reversal-orbit-words.json 2.4 s
  reversal-m13-words.json identical
  reversal-orbit-words.json identical
EOF
if [ $FAIL -eq 0 ]; then echo "ALL CHECKS PASSED"; else echo "SOME CHECK FAILED"; fi
exit $FAIL
