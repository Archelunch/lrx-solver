#!/usr/bin/env bash
# Bound-m campaign 3: seeds 1..3 outer, arms inner, serial. After seed 1 the kill check (TASK-c3.md) runs;
# exit 3 (no arm beats the seed on validation within its first 15 proposals) stops the campaign.
# Also halts on: a HALT file in this directory, a refused start (no run manifest), FIRST_PROMPT_MISMATCH,
# or 2 runs ending INCOMPLETE/BROKER_STOPPED. Finalize (validation selection, holdout once) is separate
# and human-run; it is not built yet (REPORT-prep.md).
set -uo pipefail
cd "$(dirname "$0")/../.."
H=autoresearch/bound-m-c3-260926
bad=0
for seed in 1 2 3; do
  for arm in gepa sequential adaevolve evox; do
    if [ -e "$H/HALT" ]; then echo "=== HALT file present; stopping"; break 2; fi
    echo "=== spend $(python -m integrations.bound_c3 campaign-spend) $(date -u +%FT%TZ)"
    bash "$H/run-one-c3.sh" "$arm" "$seed"; code=$?
    status=$(python -c "import glob, json; ms = sorted(glob.glob('$H/live-$arm-s$seed-*/manifest.json')); print(json.load(open(ms[-1])).get('status') if ms else 'NONE')")
    echo "=== $arm s$seed exit $code status $status $(date -u +%FT%TZ)"
    if [ "$status" = "NONE" ]; then echo "=== refused; stopping"; break 2; fi
    if [ "$status" = "FIRST_PROMPT_MISMATCH" ]; then echo "=== first prompt mismatch; stopping"; break 2; fi
    case "$status" in BROKER_STOPPED|INCOMPLETE) bad=$((bad + 1));; esac
    if [ "$bad" -ge 2 ]; then echo "=== 2 runs BROKER_STOPPED/INCOMPLETE; stopping"; break 2; fi
  done
  if [ "$seed" = 1 ]; then
    python -m integrations.bound_c3 kill-check --seed 1 > "$H/kill-check-s1.json"; kc=$?
    echo "=== kill check exit $kc $(date -u +%FT%TZ)"
    if [ "$kc" = 3 ]; then echo "=== kill rule met; stopping"; break; fi
    if [ "$kc" != 0 ]; then echo "=== kill check failed; stopping"; break; fi
  fi
done
