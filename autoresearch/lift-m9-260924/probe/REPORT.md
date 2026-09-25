# Model probe, 2026-09-24

One live call per model with the exact GEPA first prompt (captured request-0001),
through the budget broker on separate probe ledgers ($2 cap each), then a full
development-set evaluation of the returned program (naive seed baseline 285/4588).

| Model | Latency | Prompt / completion tokens | Cost | Output | Certificates |
|---|---|---|---|---|---|
| gemini-3.8-flash (reasoning_effort low) | 6.5 s | 5329 / 1741 | $0.0116 | one full program | 317 |
| grok-4.3 (reasoning_effort low, 535 reasoning tokens) | 10.1 s | 4875 / 1149 | $0.0113 | one full program | 286 |
| grok-4.7 (campaign attempt 1) | cancelled at 480 s | ~9k reasoning chars streamed, no answer | $0.218 | none | n/a |

Decision: gemini-3.8-flash for all arms. Reasons: fastest, cheapest, only model
whose first proposal beat the seed, no reasoning overrun risk observed.
One call each is not a model ranking; it is a plumbing and viability check.
Files: run_probe.py, <model>-response.json, <model>.py, <model>-eval.json,
<model>-result.json, broker-ledger-probe-<model>.json with receipts.
The probe programs are evidence only and are NOT used as campaign seeds.
