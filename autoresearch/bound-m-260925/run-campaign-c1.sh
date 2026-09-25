#!/usr/bin/env bash
# bound-m campaign 1: all four arms, then finalize (holdout once, audit). User approved 2026-09-25.
set -uo pipefail
cd "$(dirname "$0")/../.."
for arm in gepa sequential adaevolve evox; do
  echo "=== BOUND ARM $arm start $(date -u +%FT%TZ)"; bash "autoresearch/bound-m-260925/run-$arm.sh"; echo "=== BOUND ARM $arm exit $? $(date -u +%FT%TZ)"
done
echo "=== BOUND FINALIZE start $(date -u +%FT%TZ)"
python -m integrations.bound_finalize --run-dir autoresearch/bound-m-260925 > autoresearch/bound-m-260925/finalize-c1-console.log 2>&1; echo "=== BOUND FINALIZE exit $? $(date -u +%FT%TZ)"
echo "=== BOUND CAMPAIGN DONE $(date -u +%FT%TZ)"
