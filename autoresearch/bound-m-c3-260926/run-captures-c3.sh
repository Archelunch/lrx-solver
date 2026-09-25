#!/usr/bin/env bash
# Offline campaign-3 first-prompt captures through mock_api.py on a loopback port (no provider, no broker,
# no key). Every (arm, seed): one 1-iteration run under first-prompt-capture/run-<arm>-s<seed>, the mock's
# request log and captures beside it, then first-prompts/first-prompt-<arm>-s<seed>.{md,sha256}. Fresh paths only.
set -uo pipefail
cd "$(dirname "$0")/../.."
D=autoresearch/bound-m-c3-260926
C=$D/first-prompt-capture
PORT=${MOCK_PORT:-18953}
mkdir -p $C
for arm in ${ARMS:-gepa sequential adaevolve evox}; do
  for seed in ${SEEDS:-1 2 3}; do
    dir=$C/run-$arm-s$seed cap=$C/capture-$arm-s$seed log=$C/mock-$arm-s$seed.jsonl
    if [ -e $dir ] || [ -e $cap ] || [ -e $log ]; then echo "=== $arm s$seed exists; refusing"; continue; fi
    python $D/mock_api.py $PORT $log $cap > /dev/null 2>&1 &
    mock=$!
    sleep 1
    python -m integrations.bound_c3 run --engine $arm --seed $seed --broker-url http://127.0.0.1:$PORT/v1 \
      --run-dir $dir --iterations 1 --max-evals 400 --max-tokens 16384 --reasoning-effort low \
      --llm-timeout 510 > $dir.console.log 2>&1
    echo "=== $arm s$seed exit $?"
    kill $mock; wait $mock 2>/dev/null
    python -m integrations.bound_c3 first-prompt --write --engine $arm --seed $seed --capture-dir $cap
  done
done
