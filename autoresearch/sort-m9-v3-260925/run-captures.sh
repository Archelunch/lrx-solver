#!/usr/bin/env bash
# First-prompt captures for seeds 2 and 3 (offline mock, no provider calls): each (arm, seed) runs
# twice; the second run is guarded by the first run's hashes. GEPA/sequential 1 iteration,
# AdaEvolve/EvoX 3 iterations (every solution prompt compared). Then writes the hash files.
set -uo pipefail
cd "$(dirname "$0")/../.."
H=autoresearch/sort-m9-v3-260925
for seed in 2 3; do
  for arm in gepa sequential adaevolve evox; do
    it=1; case $arm in adaevolve|evox) it=3;; esac
    python $H/run_smoke.py $arm $seed $it smoke-$arm-s$seed-capture
    python $H/run_smoke.py $arm $seed $it smoke-$arm-s$seed-capture2 smoke-$arm-s$seed-capture
    python -m integrations.sort_loop3 first-prompt --capture-dir $H/smoke-$arm-s$seed-capture/capture-flash \
      --reflection-capture-dir $H/smoke-$arm-s$seed-capture/capture-reflection --write $arm $seed
  done
done
