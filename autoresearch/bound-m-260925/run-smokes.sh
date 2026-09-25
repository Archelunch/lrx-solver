#!/usr/bin/env bash
# Offline smokes of the four bound-m arms through mock_api.py (no provider, no broker, no key).
# Each arm: 2 iterations in smoke-<arm>/; first-prompt captures twice (capture-<arm>-a/b, 1 iteration)
# to check the first proposer prompt is reproducible before approval. Fresh paths only.
# SMOKE_TAG=-v2 writes smoke-v2-<arm>/ and first-prompt-capture-v2/ instead; existing paths are refused.
set -uo pipefail
cd "$(dirname "$0")/../.."
D=autoresearch/bound-m-260925
PORT=18932
T=${SMOKE_TAG:-}
run_arm() {  # arm run_dir iterations capture_dir log
  local arm=$1 dir=$2 it=$3 cap=$4 log=$5
  if [ -e $dir ] || [ -e $cap ] || [ -e $log ]; then echo "=== $arm $dir exists; refusing (set a fresh SMOKE_TAG)"; return; fi
  mkdir -p $(dirname $dir) $(dirname $log)
  python $D/mock_api.py $PORT $log $cap > /dev/null 2>&1 &
  local mock=$!
  sleep 1
  if [ "$arm" = sequential ]; then
    python -m integrations.bound_backends sequential --broker-url http://127.0.0.1:$PORT/v1 --run-dir $dir \
      --iterations $it --max-evals 20 > $dir.console.log 2>&1
  else
    python -m integrations.bound_backends run --engine $arm --broker-url http://127.0.0.1:$PORT/v1 --run-dir $dir \
      --iterations $it --max-evals 400 > $dir.console.log 2>&1
  fi
  echo "=== $arm $dir exit $?"
  kill $mock; wait $mock 2>/dev/null
}
for arm in ${SMOKE_ARMS:-gepa sequential adaevolve evox}; do
  run_arm $arm $D/smoke$T-$arm 2 $D/smoke-capture$T-$arm $D/smoke-mock$T-$arm.jsonl
  for c in a b; do
    run_arm $arm $D/first-prompt-capture$T/run-$arm-$c 1 $D/first-prompt-capture$T/capture-$arm-$c \
      $D/first-prompt-capture$T/mock-$arm-$c.jsonl
  done
done
