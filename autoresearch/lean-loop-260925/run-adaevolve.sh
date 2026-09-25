#!/usr/bin/env bash
# Live Track 3 (Lean) arm: adaevolve. Caps come from broker-config.json and campaign-config.json.
# Refuses to start unless the approval hash of both configs, prompts, seed, lean.lock.json and the
# evaluator matches payload-approved.sha256, which is created only after explicit user approval.
set -euo pipefail
umask 077
cd "$(dirname "$0")/../.."
python -m integrations.lean_evaluator verify-lock
python -m integrations.lean_backends check-approval
exec python -m integrations.lean_backends live --engine adaevolve
