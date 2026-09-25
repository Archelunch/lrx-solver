#!/usr/bin/env bash
# Chained runner for the three reduced live checks (a) sort-m9-v3 gepa s1, (b) bound-m sequential,
# (c) lean-loop sequential, prepared offline 2026-09-25. Runs (a) then (b) then (c), each gated on
# its own payload-approved.sha256 via the track module's own `check-approval` action (never a local
# hash comparison). Refuses to start a track whose approval is missing rather than skipping it
# silently: a missing approval stops the whole chain so later tracks are never mistaken for having
# run. No track is retried and no destructive git/data operation is performed by this script.
set -uo pipefail
cd "$(dirname "$0")/.."
LOG="autoresearch/live-checks-260925.log"
: > "$LOG"
log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG"; }

run_track() {
  local name="$1" module="$2" check_args="$3" live_args="$4" campdir="$5"
  log "=== $name: check-approval"
  # shellcheck disable=SC2086
  if ! python -m "$module" check-approval $check_args >>"$LOG" 2>&1; then
    log "=== $name: approval missing or hash mismatch (see $campdir/payload-approved.sha256); REFUSING to start $name and stopping the chain (not skipping)"
    exit 1
  fi
  log "=== $name: approved; launching live"
  # shellcheck disable=SC2086
  if ! python -m "$module" live $live_args >>"$LOG" 2>&1; then
    log "=== $name: live run exited non-zero; stopping the chain"
    exit 1
  fi
  log "=== $name: done"
}

run_track "sort-m9-v3 (a)" integrations.sort_loop3 \
  "--campaign-dir autoresearch/sort-m9-v3-260925-check" \
  "--engine gepa --seed 1 --campaign-dir autoresearch/sort-m9-v3-260925-check" \
  autoresearch/sort-m9-v3-260925-check

run_track "bound-m (b)" integrations.bound_backends \
  "--broker-config autoresearch/bound-m-260925/broker-config-check.json --campaign-config autoresearch/bound-m-260925/campaign-config-check.json" \
  "--engine sequential --broker-config autoresearch/bound-m-260925/broker-config-check.json --campaign-config autoresearch/bound-m-260925/campaign-config-check.json" \
  autoresearch/bound-m-260925

run_track "lean-loop (c)" integrations.lean_backends \
  "--broker-config autoresearch/lean-loop-260925/broker-config-check.json --campaign-config autoresearch/lean-loop-260925/campaign-config-check.json" \
  "--engine sequential --broker-config autoresearch/lean-loop-260925/broker-config-check.json --campaign-config autoresearch/lean-loop-260925/campaign-config-check.json" \
  autoresearch/lean-loop-260925

log "=== all three tracks complete"
