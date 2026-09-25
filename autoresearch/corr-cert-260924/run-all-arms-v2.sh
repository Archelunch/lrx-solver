#!/usr/bin/env bash
# Correlation rerun with fixed plumbing. User approved hash fa1d6070... on 2026-09-25.
set -uo pipefail
cd "$(dirname "$0")/../.."
for arm in gepa sequential adaevolve evox; do
  echo "=== CORR ARM $arm start $(date -u +%FT%TZ)"; bash "autoresearch/corr-cert-260924/run-$arm.sh"; echo "=== CORR ARM $arm exit $? $(date -u +%FT%TZ)"
done
echo "=== CORR FINALIZE start $(date -u +%FT%TZ)"
mv autoresearch/corr-cert-260924/finalists autoresearch/corr-cert-260924/finalists-attempt2 2>/dev/null
python -m integrations.corr_finalize --run-dir autoresearch/corr-cert-260924 > autoresearch/corr-cert-260924/finalize-v2-console.log 2>&1; echo "=== CORR FINALIZE exit $? $(date -u +%FT%TZ)"
echo "=== ALL DONE $(date -u +%FT%TZ)"
