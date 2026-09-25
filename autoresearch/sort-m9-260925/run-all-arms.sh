#!/usr/bin/env bash
# Sort campaign then correlation rerun. User approved both hashes 2026-09-25.
set -uo pipefail
cd "$(dirname "$0")/../.."
for arm in gepa sequential adaevolve evox; do
  echo "=== SORT ARM $arm start $(date -u +%FT%TZ)"; bash "autoresearch/sort-m9-260925/run-$arm.sh"; echo "=== SORT ARM $arm exit $? $(date -u +%FT%TZ)"
done
echo "=== SORT FINALIZE start $(date -u +%FT%TZ)"
python -m integrations.sort_finalize --run-dir autoresearch/sort-m9-260925 > autoresearch/sort-m9-260925/finalize-console.log 2>&1; echo "=== SORT FINALIZE exit $? $(date -u +%FT%TZ)"
for arm in gepa sequential adaevolve evox; do
  echo "=== CORR ARM $arm start $(date -u +%FT%TZ)"; bash "autoresearch/corr-cert-260924/run-$arm.sh"; echo "=== CORR ARM $arm exit $? $(date -u +%FT%TZ)"
done
echo "=== ALL DONE $(date -u +%FT%TZ)"
