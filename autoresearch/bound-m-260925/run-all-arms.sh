#!/usr/bin/env bash
# bound-m-260925 campaign: GEPA and the sequential control first; AdaEvolve and EvoX only after GEPA shows
# one productive cycle (campaign-config.json order_note). Every arm script checks payload-approved.sha256.
# Finalize (holdout once, audit, comparison with control b) is a separate human-run command:
#   python -m integrations.bound_finalize --run-dir autoresearch/bound-m-260925
set -uo pipefail
cd "$(dirname "$0")/../.."
for arm in gepa sequential; do
  echo "=== BOUND ARM $arm start $(date -u +%FT%TZ)"; bash "autoresearch/bound-m-260925/run-$arm.sh"; echo "=== BOUND ARM $arm exit $? $(date -u +%FT%TZ)"
done
