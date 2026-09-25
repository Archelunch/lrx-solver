#!/usr/bin/env bash
# Waits for the sort v2 campaign to finish, then runs the approved corr rerun (hash bca29cd3...).
set -uo pipefail
cd "$(dirname "$0")/../.."
until grep -q "=== SORT DONE" autoresearch/sort-m9-260925/live-v2-console.log 2>/dev/null; do sleep 60; done
bash autoresearch/corr-cert-260924/run-all-arms-v2.sh
