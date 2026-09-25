# Offline post-fix smoke (2026-09-25)

Both tasks, all 4 arms each, run fresh end-to-end against a scripted offline
mock responder (no provider calls, no commits). Mocks:
`autoresearch/lift-m9-260924/mock_api_fixed.py`,
`autoresearch/corr-cert-260924/mock_api_fixed.py`. For GEPA/sequential calls
only, the mock cycles every 4th call through: plain fence, prose-wrapped
fence, two fences (scratch first, real last), truncated (`finish_reason:
length`, no closing fence). All 8 arm runs finished `status: COMPLETE`.

One more real bug found and fixed during this pass: EvoX strategy-evolution
disable was gated on the wrong SkyDiscover knob (`auto_generate_variation_operators`
has no effect; confirmed empirically — 3 strategy + 2 variation calls still
happened with it False). The actual lever is `switch_interval`; `_sky_config`
now pushes it past `iterations` when `evox_strategy_evolution_enabled()` is
False. Re-run after the fix: 0 strategy/variation calls, both tasks.

## Pass/fail

| # | Check | lift | corr | Evidence |
|---|---|---|---|---|
| 1 | Prose before a single fence accepted | PASS | PASS | `smoke-fixed-gepa.mock.texts.jsonl` kind=`solution_full_prose` (2x each); reflection_receipts valid |
| 2 | Two fences, last defining wins | PASS | PASS | same file, kind=`solution_full_multifence`; candidate source has no `scratch`/`m = 4  # scratch` text |
| 3 | Truncated response rejected + recorded | PASS | PASS | `smoke-fixed-gepa/manifest.json` mechanism_evidence.reflection_receipts call w/ `finish_reason:"length"`, `model_preflight_failures:1`; `smoke-fixed-sequential/sequential-trace.jsonl` step 4 `finish_reason:"length"`, outcome "invalid proposal: ... truncated ..." |
| 4 | violation_sum fraction string (corr) | PASS (unit) | — | `Defect1FractionParsing` in `tests/test_search_trace_audit_fixes.py` (real historical value `56934268/3465`: `float()` raises, `float(Fraction())` doesn't); `corr-cert-260924/smoke-fixed-adaevolve` ran the real trusted evaluator through `_sky_evaluator`'s generated wrapper end-to-end with no crash (this run's candidates happened to have integer-valued violation_sum, so it doesn't independently exercise the "/" case — the unit test does) |
| 5 | Rejection followed by a differing next prompt containing the rejection note | PASS | PASS | `smoke-fixed-sequential/sequential-trace.jsonl`: all 6 `request_sha256` values distinct; `smoke-fixed-sequential.mock.texts.jsonl` step-3 request text contains "Recent rejected attempts" |
| 6 | Arm with sub-cap 0 refuses to start | PASS | PASS | `smoke-fixed-live-subcap/case-a-zero-cap/` — real `_live()` call, evox sub-cap 0: `SystemExit("refusing to start arm evox: sub-cap 0 contacts, 20 contacts remaining in the shared pool of 20")` in 0.01s; no `live-evox-*` dir, no `broker-evox-*.log` created |

## Manifest checks

| Check | lift | corr |
|---|---|---|
| Per-arm ledger paths | `smoke-fixed-live-subcap/case-b-real-ledger/ledger.evox.json` (real `DurableBudget`, not through the full sandboxed broker — `research_budget.py`'s `_validate_https_url` correctly refuses a plain-http mock upstream, so this exercises `_arm_ledger_path`/`DurableBudget`/`_evox_meta_search_share` directly: 3 attempts, share 1/3=0.33) | same, `case-b-real-ledger/ledger.evox.json` |
| finish_reason present | `smoke-fixed-gepa/manifest.json` reflection_receipts (7 entries, one `"length"`); `smoke-fixed-sequential/manifest.json` steps (6 entries, step 4 `"length"`) | same shape, both present |
| truncated_steps listed | `smoke-fixed-sequential/manifest.json` mechanism_evidence.truncated_steps = `[4]` | mechanism_evidence.truncated_steps = `[4]` |
| Packet best-so-far changes after an improvement | `smoke-fixed-sequential/sequential-trace.jsonl` step 1 accepts (certs 285->286); step-2 packet's "best so far" line reads the improved score, confirmed via `LiftVerifier._current_best` (unit: `Defect7PacketBestSoFar`) plus this live run's `verified_best_full.certificates=286` vs `seed_full.certificates=285` | n/a (lift-specific staged screen/full concept; corr has no scope split) |
| research_status not NEW_CERTIFICATES when only worked examples pass | n/a | `smoke-fixed-gepa`: `GRADED_PROGRESS` (seed/best both `passed_m: []`, i.e. neither reaches even the worked examples here); `smoke-fixed-{sequential,adaevolve,evox}`: `NO_GAIN`. None is `NEW_CERTIFICATES`. Unit test `Defect8ResearchStatusExcludesWorkedExamples` directly covers the `passed_m` subset-of-worked-examples case this mock's simple MULT search never reaches live |
| EvoX meta-search disabled below 100 iterations | `smoke-fixed-evox` (iterations=6): 0 strategy/0 variation calls (`smoke-fixed-evox.mock.texts.jsonl`: `{"probe":2,"solution_diff":6}`); `stage/sky-config.yaml` `switch_interval` pushed to 7 | same: `smoke-fixed-evox.mock.texts.jsonl` `{"probe":2,"solution_diff":6}` |

All 8 arm manifests: `autoresearch/{lift-m9-260924,corr-cert-260924}/smoke-fixed-{gepa,sequential,adaevolve,evox}/manifest.json`, all `status: COMPLETE`.

## Approval hashes (recomputed, neither applied — both configs are unapproved for any live run until a human re-signs)

- corr (current `campaign-config.json`, with defect-2 per-arm caps 42/42/35/28):
  `e24e995df4fef455c52131ddd60bcc7cdf68113af4574b1c4d5ffc3fb9fa2540`
  (stored `payload-approved.sha256` is stale: `4b678b51ae91c64266df817ebfc8e3da8f78c80438192e4d76644b0c15df693a`)
- lift, `broker-config.json` as-is (max_tokens still 4096, untouched per instructions):
  `81448c9e5323cb98513b05541eaaaa66c3b90a0f0dc499d3e159682a0ead2d50`
  (stored: `93186c260cafe9374ad0ba527642476d81b21966c49fd755151c0a5cee74619a`)
- lift, hash it **would** have if `broker-config.next.json` (max_tokens 8192) were copied over `broker-config.json` — not applied, reported only as asked:
  `11a67ca18dc97005d6745ac1d98df92d6a0109cb80d35b31b867fd17a7ff3e4d`

## Verification

`python -m unittest discover -s tests -p 'test_*.py'`: OK (471 tests, 4 skipped).
`python -m compileall -q src tests`: clean. `python -m src.lrx.cli smoke`: passed=true.
`python tools/orchestrator.py trusted`: `{"ok": true, "changed": [], "missing_from_lock": []}`.
No commits made; no live-* run directory, ledger, or receipt touched or read for writing.
