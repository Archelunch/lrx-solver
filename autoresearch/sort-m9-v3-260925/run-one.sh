#!/usr/bin/env bash
# One live loop-v3 run: ENGINE SEED. Refuses unless the approval hash matches payload-approved.sha256
# (created only by a human after review) and campaign_max_usd is set. Caps come from the configs.
set -euo pipefail
umask 077
cd "$(dirname "$0")/../.."
python -m integrations.sort_loop3 check-approval
exec python -m integrations.sort_loop3 live --engine "$1" --seed "$2"
