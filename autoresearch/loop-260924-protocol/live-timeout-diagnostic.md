# Live GEPA timeout diagnostic — 2026-09-24

The approved development-only Grok-4.7 campaign produced **no model response and no generated candidate**. The frozen all-cuts seed remains 15/16 on development; this is inherited offline evidence, not a live-search result. Confirmation data was not staged or evaluated.

| Attempt | Run / ledger | Actual chat request | Broker result | Research result |
| --- | --- | --- | --- | --- |
| 1 | `gepa-live-01/`, `broker-ledger.json` | `grok-4.7`, `reasoning_effort=low`, `max_tokens=4096`; 17,833 request bytes; reviewed development context and archive row 2 | Local HTTP 502 after 601.044 s; upstream `TimeoutError`; no response body, finish reason, role, or usage; $0.200519 conservative reservation charged | Zero valid model responses/proposals. GEPA caught the ordinary HTTP error and continued locally against broker 429s. Engine exit 0 and `status=COMPLETE` mean only that the seed replayed; `research_status=NO_VALID_PROPOSAL`. There were 78 verifier requests, 108 case runs, 40 context accesses, and 20 selected reflection batches, none of which represent completed model proposals. |
| 2 | `gepa-live-recovery-01/`, `broker-ledger-recovery-01.json` | Same approved frozen seed, development inputs, model, and research context; one-iteration recovery with one broker attempt; 17,861 request bytes. Dynamic archive selected row 80 instead of row 2 after the first run appended seed-only development evaluations. | Local HTTP 502 after 180.153 s; upstream `TimeoutError`; no response body, finish reason, role, or usage; $0.2005806 conservative reservation charged | New `BrokerHalted` path escaped GEPA's ordinary-exception retry handler. Worker exited 1, manifest `INCOMPLETE`, zero proposal hashes. One context access, 20 verifier requests, and 35 case runs occurred before the sole model timeout. |

The two chat requests have different SHA-256 digests (`0823f09d4dc737a19f19bdcfc09eb5ecdd807bd432274629e0594f33a1b0d177` and `e57d3257269beacbcbf0fb9c5531804c8ab23b754cfe680458d7e82c09a6a5d0`) because the approved evolving development archive and runtime trace text changed. Neither included confirmation data. Both full sanitized request receipts are stored privately beside their ledgers. No provider response exists to diagnose proposal format or finish-reason truncation. Earlier campaign ledgers contain successful Grok-4.7 requests with 17,377–17,511 input tokens, so request size alone does not establish a failure cause; those calls are historical and not a matched latency comparison.

A separate read-only `GET https://api.x.ai/v1/models` returned HTTP 200 in 0.324 s and listed `grok-4.7`. This third HTTP contact was metadata only, outside the generation ledger, and confirms connectivity/model availability at that instant, not chat-completion health. No provider-wide incident is established.

Combined conservative generation accounting is **2 attempts, $0.4010996 charged against the $5/24 campaign cap**. The separate metadata GET makes **3 total external HTTP contacts**, so at most **21 contacts** and $4.5989004 remain under the original aggregate ceiling; the two generation ledgers alone would show 22 unused request slots and must not be treated as a larger aggregate allowance. Actual provider usage for both timed-out requests is unknown. No further model call was made; the local broker listener on port 8877 is stopped. The first halted ledger is preserved and the recovery relationship/cap is recorded in `recovery-01-link.json`.

Validation after the fail-fast change:

```text
python -m unittest tests.test_search_official_backends tests.test_search_budget_receipts -v
Ran 15 tests in 0.133s — OK
python -m compileall -q integrations/official_backends.py integrations/research_budget.py tests/test_search_official_backends.py tests/test_search_budget_receipts.py
exit 0
python - <<'PY'  # tools.orchestrator.trusted_status()
{'ok': True, 'changed': [], 'missing_from_lock': []}
PY
lsof -nP -iTCP:8877 -sTCP:LISTEN
no listener
```

The end-to-end recovery trace in `gepa-live-recovery-01/console.log` independently shows `BrokerHalted: research broker stopped: HTTP 502` escaping native GEPA's `_propose_texts_batch_safe`; this is the observed fail-fast behavior. The code-level focused test also covers local 429, 502, connection errors, and direct read timeouts. Root later reran the full guarded suite after this patch: 368 tests in 13.559 seconds, no skips, OK (`final-tests-live.log`); compileall, CLI smoke, trusted-lock status, and authored-source diff checks also passed.
