#!/usr/bin/env bash
# Live bound-m-260925 campaign arm: gepa. Development set only; the holdout (m = 9, 10, 11) is never loaded.
# Caps come from broker-config.json and campaign-config.json, never from this script.
# Refuses to start unless the approval hash of both configs, prompts, seed, evaluator, SkyDiscover settings
# and frozen manifest matches payload-approved.sha256, which is created only after explicit user approval.
set -euo pipefail
umask 077
cd "$(dirname "$0")/../.."
python -m integrations.bound_backends check-approval
exec python -m integrations.bound_backends live --engine gepa
