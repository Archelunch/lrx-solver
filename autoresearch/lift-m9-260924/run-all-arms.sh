#!/usr/bin/env bash
# Sequential campaign: gepa -> sequential -> adaevolve -> evox. Approved by the user 2026-09-24
# (payload hash 3ead0205...). Each arm shares broker-config.json, campaign-config.json and the ledger.
set -uo pipefail
cd "$(dirname "$0")/../.."
for arm in gepa sequential adaevolve evox; do
  echo "=== ARM $arm start $(date -u +%FT%TZ)"
  bash "autoresearch/lift-m9-260924/run-$arm.sh"
  echo "=== ARM $arm exit $? $(date -u +%FT%TZ)"
done
echo "=== ALL ARMS DONE $(date -u +%FT%TZ)"
