#!/usr/bin/env bash
# Offline campaign-2 smokes through mock_api.py (no provider, no broker, no key). Fresh paths only.
# 1) smoke-<arm>-s1: one (arm, seed=1) run per arm, 2 iterations.
# 2) first-prompt-capture/run-<arm>-s<seed>: every (arm, seed), 1 iteration; the first proposer request of each
#    is written to first-prompt-<arm>-s<seed>.{md,sha256}. The s1 smoke capture is compared with the s1 capture.
set -uo pipefail
cd "$(dirname "$0")/../.."
D=autoresearch/bound-m-c2-260925
PORT=${MOCK_PORT:-18942}
T=${SMOKE_TAG:-}  # e.g. -v2: fresh smoke-v2-* and first-prompt-capture-v2/ paths
run_arm() {  # arm seed run_dir iterations capture_dir log
  local arm=$1 seed=$2 dir=$3 it=$4 cap=$5 log=$6
  if [ -e $dir ] || [ -e $cap ] || [ -e $log ]; then echo "=== $arm s$seed $dir exists; refusing"; return; fi
  mkdir -p $(dirname $dir) $(dirname $log)
  python $D/mock_api.py $PORT $log $cap > /dev/null 2>&1 &
  local mock=$!
  sleep 1
  python -m integrations.bound_c2 run --engine $arm --seed $seed --broker-url http://127.0.0.1:$PORT/v1 \
    --run-dir $dir --iterations $it --max-evals ${MAX_EVALS:-400} > $dir.console.log 2>&1
  echo "=== $arm s$seed $dir exit $?"
  kill $mock; wait $mock 2>/dev/null
}
for arm in ${SMOKE_ARMS:-gepa sequential adaevolve evox}; do
  if [ -z "${CAPTURES_ONLY:-}" ]; then
    run_arm $arm 1 $D/smoke$T-$arm-s1 2 $D/smoke-capture$T-$arm-s1 $D/smoke-mock$T-$arm-s1.jsonl
  fi
  for seed in ${SMOKE_SEEDS:-1 2 3}; do
    run_arm $arm $seed $D/first-prompt-capture$T/run-$arm-s$seed 1 $D/first-prompt-capture$T/capture-$arm-s$seed \
      $D/first-prompt-capture$T/mock-$arm-s$seed.jsonl
    python -m integrations.bound_c2 first-prompt --write --engine $arm --seed $seed \
      --capture-dir $D/first-prompt-capture$T/capture-$arm-s$seed
  done
done
