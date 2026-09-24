# Native GEPA streamed diagnosis — 2026-09-24

One approved native GEPA reflection was sent to `https://api.x.ai/v1/chat/completions` through the durable broker. The broker retained the ordinary JSON interface for GEPA and converted only the provider leg to SSE with `stream: true`, `stream_options: {"include_usage": true}`, and `max_completion_tokens: 4096`. Model `grok-4.7`, `reasoning_effort: low`, frozen all-cuts seed/development inputs/dual/context, and the selected development archive excerpt were the same approved categories as the earlier attempts. No confirmation input was staged. This run had a one-attempt broker cap and a 180-second total stream deadline.

The one request timed out **after inference had begun**:

| Observation | Seconds after request |
| --- | ---: |
| HTTP response headers | 0.821 |
| First SSE event and reasoning delta | 1.071 |
| First visible content | Never within 180 s |
| Complete response / `[DONE]` / final usage | Never within 180 s |

The private receipt contains 68 SSE events, 6,518 reasoning characters and 23,780 streamed bytes, but zero visible content characters. The broker recorded `TimeoutError`, local HTTP 502, and the full $0.2007192 reservation as a conservative charge because final provider usage is unknown. It halted; GEPA's fail-fast path exited 1. `gepa-live-stream-01/manifest.json` is `INCOMPLETE`, with zero proposal hashes and no new certificate. The broker is stopped. This isolates the long wait to model reasoning/output after prompt acceptance; it does not establish why the reasoning took so long or whether xAI ultimately billed the interrupted request.

A bounded read-only review of the partial reasoning shows it stayed on the k5 constructor and recognized the positive reduced-cost obstacle. It asserted an improved profile and certificate without replay or exact LP evidence, then began drafting a replacement Python source in the reasoning channel. The captured source stops mid-function. Those assertions and partial code are **not a candidate or a certificate**; the receipt records no visible assistant content or completed response. The next proposed prompt steering asks for one small executable constructor mutation and leaves proof to the trusted verifier.

Request provenance: client request SHA-256 `a1362deec2670162da681dcca1fe3fd35dbc358897296d7802f6c05042887204`; forwarded SSE request SHA-256 `ac01fcf7f7a4449ef83373fe796d604fcbcee30fbd5a8c84b251f6e1bb3ec188`; dynamic development context SHA-256 `0f43935ef9ce77a81de5d804aea967fd3fdded41e031d2f6d2e8f7654c5eceb6`, archive row 2. The full sanitized SSE events and request are preserved in the mode-0600 receipt `broker-ledger-stream-01.json.receipts/attempt-0001.json`; raw reasoning is not copied into this report.

Before this research attempt, a one-slot `LRX_READY` chat probe returned HTTP 200 with final usage in 2.325 seconds, costing $0.0037048. Its model reply declined the exact-token wording, so it establishes small-request transport responsiveness, not instruction fidelity. A separate read-only model-catalog GET returned HTTP 200 in 0.324 seconds and listed `grok-4.7`.

Aggregate conservative generation accounting across the two earlier research timeouts, the tiny probe, and this streamed research timeout is **4 attempts / $0.6055236**, leaving $4.3944764 under the originally approved $5 ceiling. Including the catalog GET as an HTTP contact leaves 19 of 24 contacts. No further request was made.

Official xAI documentation says Grok 4.7 supports SSE and low reasoning effort, `max_completion_tokens` bounds visible output rather than internal reasoning, and REST streaming requires `stream_options.include_usage` for final cost data: [Streaming](https://docs.x.ai/developers/model-capabilities/text/streaming), [Reasoning](https://docs.x.ai/developers/model-capabilities/text/reasoning), [Cost tracking](https://docs.x.ai/developers/cost-tracking). The broker's 20,000-token reasoning reservation is an accounting allowance, not a provider-enforced reasoning cap or invoice guarantee.

Offline validation for the default-off upstream-stream mode: `python -m unittest tests.test_search_budget_stream tests.test_search_budget_receipts -v` passed 8 tests; `python -m compileall -q integrations/research_budget.py tests/test_search_budget_stream.py` and `bash -n autoresearch/loop-260924-protocol/launch-live-gepa-stream-01.sh` passed. The live receipt and native manifest provide the end-to-end timeout/fail-fast evidence.
