#!/usr/bin/env bash
# Offline mock smokes, seed 1: all four arms at 3 iterations, then independent re-captures
# (1 iteration for GEPA/sequential, a second 3-iteration run for AdaEvolve/EvoX) that run with the
# first run's hashes as expected hashes, so the guards are exercised. No provider calls.
set -uo pipefail
cd "$(dirname "$0")/../.."
H=autoresearch/sort-m9-v3-260925
for arm in gepa sequential adaevolve evox; do python $H/run_smoke.py $arm 1 3 smoke-$arm-s1; done
for arm in gepa sequential; do python $H/run_smoke.py $arm 1 1 smoke-$arm-s1-capture smoke-$arm-s1; done
for arm in adaevolve evox; do python $H/run_smoke.py $arm 1 3 smoke-$arm-s1-repeat smoke-$arm-s1; done
for arm in gepa sequential adaevolve evox; do
  python -m integrations.sort_loop3 first-prompt --capture-dir $H/smoke-$arm-s1/capture-flash \
    --reflection-capture-dir $H/smoke-$arm-s1/capture-reflection --write $arm 1
done
