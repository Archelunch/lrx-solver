# Focused native GEPA stream outcome — 2026-09-24

One further approved native GEPA reflection used the same frozen all-cuts seed, 16 development cases, incumbent, exact dual, research context, and development archive. A fixed 369-character system instruction asked for one small k5 constructor mutation and left replay/LP proof to the trusted evaluator. Grok-4.7 remained at low reasoning effort. The provider leg streamed with `max_completion_tokens: 4096`, final usage requested, and a 600-second total deadline. The broker allowed one upstream attempt, with a fresh ledger linked to all previous campaign ledgers.

The provider **completed**, but the budget broker did not pass the response to GEPA:

| Event | Seconds after request |
| --- | ---: |
| Headers / first reasoning delta | 1.058 |
| First visible content | 518.011 |
| Complete stream `[DONE]` | 533.975 |

There were 1,774 SSE events, 2,516 reasoning characters, 5,516 visible content characters, and 437,083 streamed bytes. The final assistant message was a complete fenced Python `propose_words` source with `finish_reason=stop`. Provider usage was 6,232 prompt tokens, 1,723 visible completion tokens, and **43,919 reasoning tokens**. The provider's cost field was $0.284588; the broker conservatively charged $0.3149476, versus its $0.201663 reservation (20,000 reasoning-token allowance). The broker therefore marked `reservation_overrun`, halted, and returned local HTTP 502. Native GEPA exited 1 with `INCOMPLETE` and zero accepted proposals. This is a broker accounting boundary, not a provider error or a model-format failure.

The complete source was frozen separately as `broker-rejected-complete-proposal.py` (SHA-256 `d061094815415ad528e1f195423df107ac47aab4a33679bc936ab07cee1f6619`) with provenance in `broker-rejected-complete-proposal.json`. This is **diagnostic output, not an official GEPA-accepted proposal**. It passed fenced-source/AST preflight. Strict development-only sandbox replay produced 15/16 inherited certificates, no new k5 certificate, and all 16 candidate runs `ok`. For k5, the exact feasible base improved from `24149/392` to `4297/70`, still `27/70` above the strict target 61; the best old-pool dual reduced cost is `-19/14`. The bounded secondary score is `14887/630696` (about 0.023604). An independent saved-output audit confirmed the source hash, exact LP/dual/score, 512 accepted words, and 147 nonunit literal support replays. No confirmation data was used.

Campaign conservative generation accounting is now **5 attempts / $0.9204712**, leaving $4.0795288 of the original $5 ceiling. Counting the read-only model-catalog GET as an HTTP contact leaves 18 of 24 contacts. No further model request was made. The broker listener is stopped.

The complete provider response required nearly nine minutes even with low effort and a small steering instruction; visible output appeared only after 518 seconds. `max_completion_tokens` did not constrain internal reasoning, as [xAI documents](https://docs.x.ai/developers/rest-api-reference/inference/chat-completions). The current fixed 20,000-token reasoning reservation is therefore insufficient for this request shape. Any later official run would need a reviewed budget accounting decision; this diagnostic candidate can be independently studied without a new model call.
