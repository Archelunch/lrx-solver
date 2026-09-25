#!/usr/bin/env bash
# Live lift campaign arm: sequential. Development set only; holdout is never loaded.
# Caps come from broker-config.json and campaign-config.json, never from this script.
# Refuses to start unless the approval hash of both configs, prompts, seed and frozen
# manifest matches payload-approved.sha256, which is created only after user approval.
set -euo pipefail
umask 077
cd "$(dirname "$0")/../.."
python -m integrations.lift_backends check-approval
exec python -m integrations.lift_backends live --engine sequential
