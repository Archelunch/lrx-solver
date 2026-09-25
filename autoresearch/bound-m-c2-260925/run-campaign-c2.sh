#!/usr/bin/env bash
# Bound-m campaign 2: seeds 1..3 outer, arms inner (an early stop leaves whole seeds), serial.
# Halts on: a HALT file in this directory, a refused start (no run manifest), FIRST_PROMPT_MISMATCH,
# or 2 runs ending INCOMPLETE/BROKER_STOPPED. Then finalize (validation selection, holdout once, audit).
set -uo pipefail
cd "$(dirname "$0")/../.."
H=autoresearch/bound-m-c2-260925
bad=0
for seed in 1 2 3; do
  for arm in gepa sequential adaevolve evox; do
    if [ -e "$H/HALT" ]; then echo "=== HALT file present; stopping"; break 2; fi
    echo "=== spend $(python -m integrations.bound_c2 campaign-spend) $(date -u +%FT%TZ)"
    bash "$H/run-one.sh" "$arm" "$seed"; code=$?
    status=$(python -c "import glob, json; ms = sorted(glob.glob('$H/live-$arm-s$seed-*/manifest.json')); print(json.load(open(ms[-1])).get('status') if ms else 'NONE')")
    echo "=== $arm s$seed exit $code status $status $(date -u +%FT%TZ)"
    if [ "$status" = "NONE" ]; then echo "=== refused; stopping"; break 2; fi
    if [ "$status" = "FIRST_PROMPT_MISMATCH" ]; then echo "=== first prompt mismatch; stopping"; break 2; fi
    case "$status" in BROKER_STOPPED|INCOMPLETE) bad=$((bad + 1));; esac
    if [ "$bad" -ge 2 ]; then echo "=== 2 runs BROKER_STOPPED/INCOMPLETE; stopping"; break 2; fi
  done
done
python -m integrations.bound_c2_finalize finalize --run-dir "$H" > "$H/finalize-c2-console.log" 2>&1
echo "=== FINALIZE exit $? $(date -u +%FT%TZ)"
