#!/usr/bin/env bash
# Sequential campaign: gepa -> sequential -> adaevolve -> evox. User approved 2026-09-24 (hash cf3f1108...).
set -uo pipefail
cd "$(dirname "$0")/../.."
for arm in gepa sequential adaevolve evox; do
  echo "=== ARM $arm start $(date -u +%FT%TZ)"
  bash "autoresearch/corr-cert-260924/run-$arm.sh"
  echo "=== ARM $arm exit $? $(date -u +%FT%TZ)"
done
echo "=== ALL ARMS DONE $(date -u +%FT%TZ)"
