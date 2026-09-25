# Reduced live checks — three tracks (2026-09-25)

Prepared OFFLINE. No provider calls, no commits, no `payload-approved.sha256` written anywhere in
this pass. `python tools/orchestrator.py trusted` unaffected (no TRUSTED file touched). Repo
verification this session: `python -m unittest discover -s tests -p 'test_*.py'` -> 567 tests,
OK (skipped=4); `python -m compileall -q src tests integrations` -> clean; `python -m src.lrx.cli
smoke` -> `passed: true`.

**Code change (search-side, `integrations/` — allowed by AGENTS.md for the autoresearch
orchestrator):** `integrations/sort_loop3.py`'s `live`/`approval-hash`/`check-approval`/
`campaign-spend` actions hardcoded `camp = CAMP` (the production `sort-m9-v3-260925` directory)
with no CLI override, so a reduced check config placed anywhere else was invisible to the approval
hash. Added `--campaign-dir` (default `CAMP`, so existing production behavior and hashes are
unchanged when omitted) to those four subparsers, threaded into `approval_hash_v3`/
`check_approval_v3`/`campaign_spend`/`v3_ledgers` (already accepted a `camp` parameter) and into
`_live_v3` (previously hardcoded). Verified: `tests/test_search_loop_v3.py` +
`tests/test_search_loop_v3_regressions.py`, 25 tests, still pass; production
`approval-hash` (no `--campaign-dir`) now differs from the prior report's
`8ec9bbe8e7d91b2a66d063a183c22222478e507ad6490703023890711e8cb5c7` only because editing the file
itself changes its own `code_sha256` entry — this is expected and means the production payload
needs re-approval too (not evaluated further here; out of scope).
`integrations/bound_backends.py` and `integrations/lean_backends.py` already accept
`--broker-config`/`--campaign-config`, so no code change was needed for tracks (b)/(c).

**Model check (a):** could not confirm `gemini-3.8-pro` is a valid model id. No live model-listing
evidence exists anywhere in the repo for it — `autoresearch/lift-m9-260924/transport-notes.md`
lists only x.ai's grok-4.7; no probe file lists Gemini models. The broker configs themselves
already say this is an unverified placeholder (O2). Unresolved; a live listing call would be
needed and is not authorized here.

## (a) sort-m9-v3 — gepa, seed 1, 20 iterations

Files: `autoresearch/sort-m9-v3-260925-check/{campaign-config.json, broker-config.json,
broker-config-reflection.json, approval-material.json, first-prompt-gepa-s1{.md,.sha256},
first-prompt-gepa-s1-diagnosis.sha256}` (first-prompt hashes copied from the already-captured,
already-fix3-verified production files — the reduced iteration/cap fields don't affect the seed's
first request). gepa: iterations 20, `max_metric_calls` 786 (`gepa_metric_calls(30, 3, 20)`),
`max_state_evals` 41200 (scaled), flash sub-cap 36 (`floor(6/0.1666368)`), reflection sub-cap 8
(`floor(3/0.374048)`, below the ~20-25 diagnosis calls a full run would make — expected to halt
`BROKER_STOPPED` once hit). `campaign_max_usd` 9.0 (= 6+3, one run only).

Approval hash (covers the check config, via `--campaign-dir`):
```
python -m integrations.sort_loop3 approval-hash --campaign-dir autoresearch/sort-m9-v3-260925-check
-> 5029d36eb0bf01260e143bef94bd8f5a512fbcd097a520b812e9146d34e9263b
```
check-approval / live:
```
python -m integrations.sort_loop3 check-approval --campaign-dir autoresearch/sort-m9-v3-260925-check
python -m integrations.sort_loop3 live --engine gepa --seed 1 --campaign-dir autoresearch/sort-m9-v3-260925-check
```
Verified offline: check-approval refuses (`payload-approved.sha256` missing). Est. wall time
15-40 min (20 iterations, sub-caps likely bind before completion). Est. cost: up to $6 flash +
$3 reflection = $9 cap; real spend likely lower since reflection halts early.

## (b) bound-m — sequential, 20 iterations

Files: `autoresearch/bound-m-260925/{campaign-config-check.json, broker-config-check.json,
approval-material-check.json}`. sequential: iterations 20, max_evals 25, sub-cap 25. Broker
max_usd 4 -> formula ceiling is `floor(4/0.1666368)` = 24, one below the requested sub-cap of 25;
set `max_requests` to 25 explicitly (documented in both files) rather than silently lowering the
sub-cap — flagged, not resolved. **Collision:** `payload-approved.sha256` lives at
`broker-config.json`'s parent, i.e. the same `autoresearch/bound-m-260925/` directory as the
production config, so approving this check hash there also gates (and is indistinguishable from)
approving the production payload unless the human manages that one file deliberately.

Approval hash:
```
python -m integrations.bound_backends approval-hash --broker-config autoresearch/bound-m-260925/broker-config-check.json --campaign-config autoresearch/bound-m-260925/campaign-config-check.json
-> 3dc8ccb0e756eb17a093e54f4a837f24274e150ced757f52553d511203cf6494
```
check-approval / live:
```
python -m integrations.bound_backends check-approval --broker-config autoresearch/bound-m-260925/broker-config-check.json --campaign-config autoresearch/bound-m-260925/campaign-config-check.json
python -m integrations.bound_backends live --engine sequential --broker-config autoresearch/bound-m-260925/broker-config-check.json --campaign-config autoresearch/bound-m-260925/campaign-config-check.json
```
Verified offline: check-approval refuses. Est. wall time 10-25 min. Est. cost up to $4.

## (c) lean-loop — sequential, 10 iterations, target L1

No milestone/target CLI flag exists in `lean_task.py`/`lean_backends.py`: GEPA's dataset is the
fixed 11 instances (L1-L3, M1-M7, M9) every run. "Target L1" means the reduced run is aimed at L1
as the simplest target via the existing `combined_score`/`closed_targets`, not scope restriction.
Toolchain: `lean_task.toolchain_dir()` already resolves to
`~/.elan/toolchains/leanprover--lean4---v4.34.0` by default (env override
`LRX_LEAN_TOOLCHAIN_DIR` not needed) and calls the binary by absolute path, not through `PATH`, so
`lean`/`lake` missing from `PATH` does not block it — no env file was needed. Confirmed by running
the evaluator directly, offline, this session:
`python -m integrations.lean_evaluator eval autoresearch/lean-loop-260925/reference/control-L1.lean
--full` -> `status VALID`, `closed_targets: ["L1"]`, `combined_score 0.373` (not 1.0 — this
reference only proves L1, not L2/L3/M1-M9, so the weighted T/3+M/8 formula caps it there);
`python -m integrations.lean_evaluator eval autoresearch/lean-loop-260925/seed.lean --full` (the
sorry stub) -> `status VALID`, `combined_score 0.0`. Both as expected.

Files: `autoresearch/lean-loop-260925/{campaign-config-check.json, broker-config-check.json,
approval-material-check.json}`. sequential: iterations 10, max_evals 14, sub-cap 14. Broker
max_usd 3 -> ceiling `floor(3/0.1666368)` = 18, sub-cap 14 fits within it, no override needed.

Approval hash:
```
python -m integrations.lean_backends approval-hash --broker-config autoresearch/lean-loop-260925/broker-config-check.json --campaign-config autoresearch/lean-loop-260925/campaign-config-check.json
-> e77362616b1581dfa798682a31f413693955ac0a8f197f06fa09963fd8de1271
```
check-approval / live:
```
python -m integrations.lean_backends check-approval --broker-config autoresearch/lean-loop-260925/broker-config-check.json --campaign-config autoresearch/lean-loop-260925/campaign-config-check.json
python -m integrations.lean_backends live --engine sequential --broker-config autoresearch/lean-loop-260925/broker-config-check.json --campaign-config autoresearch/lean-loop-260925/campaign-config-check.json
```
Verified offline: check-approval refuses. Est. wall time 10-20 min (Lean compiles are CPU-bound,
not token-bound). Est. cost up to $3.

## Runner

`autoresearch/run-live-checks-260925.sh` — chains (a) then (b) then (c), each gated on its own
`check-approval` (not a local hash compare); a missing/mismatched approval stops the whole chain
(exit 1) rather than skipping that track, logs to `autoresearch/live-checks-260925.log`. Its own
dry-run execution was blocked by this session's permission classifier ("Production Deploy") even
though it can only reach `live` after `check-approval` succeeds and no approval file exists yet;
its gating logic was instead verified by directly exercising each track's `check-approval` above
(all three refuse correctly with `payload-approved.sha256` missing).
