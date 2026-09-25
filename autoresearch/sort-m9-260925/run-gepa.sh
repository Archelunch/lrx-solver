#!/usr/bin/env bash
# Live sort-m9 campaign arm: gepa. Development set only; holdout is never loaded.
# Caps come from broker-config.json and campaign-config.json, never from this script.
# Refuses to start unless the approval hash of both configs, prompts, seed, evaluator and
# frozen manifest matches payload-approved.sha256, which is created only after user approval.
set -euo pipefail
umask 077
cd "$(dirname "$0")/../.."
python -m integrations.sort_backends check-approval
exec python -m integrations.sort_backends live --engine gepa
