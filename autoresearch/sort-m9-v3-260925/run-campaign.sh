#!/usr/bin/env bash
# Loop-v3 campaign: seeds 1..3, arms interleaved by seed (an early stop leaves whole seeds). Serial.
# Each live run refuses on its own if the approval hash, keys or campaign_max_usd budget do not allow it
# (live checks spend so far + this run's per-broker max_usd_per_run against campaign_max_usd).
# Stops after the first refusal or after 2 runs end BROKER_STOPPED or INCOMPLETE, then finalizes.
set -uo pipefail
cd "$(dirname "$0")/../.."
H=autoresearch/sort-m9-v3-260925
bad=0
for seed in 1 2 3; do
  for arm in gepa sequential adaevolve evox; do
    echo "=== spend $(python -m integrations.sort_loop3 campaign-spend) $(date -u +%FT%TZ)"
    bash "$H/run-one.sh" "$arm" "$seed"; code=$?
    status=$(python -c "import glob, json; ms = sorted(glob.glob('$H/live-v3-$arm-s$seed-*/manifest.json')); print(json.load(open(ms[-1])).get('status') if ms else 'NONE')")
    echo "=== $arm s$seed exit $code status $status $(date -u +%FT%TZ)"
    case "$status" in BROKER_STOPPED|INCOMPLETE) bad=$((bad + 1));; esac
    if [ "$code" -ne 0 ] && [ "$status" = "NONE" ]; then echo "=== refused; stopping"; break 2; fi
    if [ "$bad" -ge 2 ]; then echo "=== 2 runs BROKER_STOPPED/INCOMPLETE; stopping"; break 2; fi
  done
done
python -m integrations.sort_loop3_finalize --run-dir "$H" > "$H/finalize-console.log" 2>&1
echo "=== FINALIZE exit $? $(date -u +%FT%TZ)"
