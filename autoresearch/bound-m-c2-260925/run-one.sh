#!/usr/bin/env bash
# One live campaign-2 run: ENGINE SEED. Refuses unless the approval hash matches payload-approved.sha256
# (created only by a human after review). Caps come from the configs and the other c2 ledgers.
set -euo pipefail
umask 077
cd "$(dirname "$0")/../.."
python -m integrations.bound_c2 check-approval
exec python -m integrations.bound_c2 live --engine "$1" --seed "$2"
