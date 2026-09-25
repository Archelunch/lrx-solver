# Grok transport notes for `lift-m9-260924`

Docs-only research (WebFetch of docs.x.ai; no API calls). Findings, exact
parameter names, and their documented semantics, as fetched 2026-09-24:

## No hard numeric reasoning-token cap exists

[Reasoning](https://docs.x.ai/developers/model-capabilities/text/reasoning)
documents `reasoning_effort` for the grok-4 family (`grok-4.7`, `grok-4.6`,
`grok-4.5`) as one of `"low"`, `"medium"`, `"high"` (default), `"xhigh"`
(4.6+). It "controls how much effort the model spends thinking before
responding" and is explicitly a *level*, not a token count. The same page
states reasoning **cannot be disabled**. There is no documented
`max_reasoning_tokens` or equivalent numeric cap parameter for any grok-4
model. This matches the prior finding already recorded in
`autoresearch/loop-260924-protocol/stream-diagnostic-01.md`: reasoning_effort
"low" was in effect during the focused run that still produced 43,919
reasoning tokens, so the level is a hint, not an enforced ceiling.

## `max_completion_tokens` / `max_tokens`

[Streaming](https://docs.x.ai/developers/model-capabilities/text/streaming)
and the base [text capabilities](https://docs.x.ai/developers/models) pages
were checked directly; neither documents whether `max_completion_tokens`
bounds reasoning tokens, visible content tokens, or their sum. The prior
session's finding (stream-diagnostic-01.md, citing the same docs) is that it
"bounds visible output rather than internal reasoning." No page found in this
task contradicts that. Per AGENTS.md, this is stated as the existing citation,
not re-verified word-for-word in this task; do not treat it as a reasoning
bound.

## Cost / usage reporting

[Cost tracking](https://docs.x.ai/developers/cost-tracking) documents
`cost_in_usd_ticks` in the `usage` object as "the exact cost you were charged
for that request." It does **not** document billing behavior for timed-out,
cancelled, or client-aborted requests — this remains an open/unknown item
(see "Unknowns" below). `stream_options.include_usage: true` is required to
get final usage on a streamed response (already implemented in
`integrations/research_budget.py`).

## Pricing

[Models](https://docs.x.ai/developers/models), fetched 2026-09-24: grok-4.7,
prompts under 200k tokens, is $2.00 input / $6.00 output per million tokens
(prompts at or above 200k tokens bill the whole request at $4.00 / $12.00).
`broker-config.json` for this run keeps the repository's existing $2.2 / $6.6
rates (a 10% conservative markup already used across
`autoresearch/loop-260924-protocol/*.json` ledgers) rather than tightening
below what was already reconciled — see `budget-ledger-notes.md`.

## Conclusion: what is actually enforced

Since no provider-side hard reasoning cap is documented, `~8k reasoning
tokens` is implemented as a **local, broker-side enforcement**, not a claim
that xAI enforces it:

1. `reasoning_effort` is forced (ENFORCED) to `"low"` on every forwarded
   request by the broker, overriding whatever the client sent
   (`integrations/research_budget.py`, `Broker.reasoning_effort`,
   `BrokerHandler.do_POST`). This is the best available provider-side lever,
   known to reduce but not guarantee reasoning token count.
2. `max_completion_tokens` bounds the requested visible-output tokens
   (existing broker behavior, unchanged).
3. New: when the broker runs in `--upstream-stream` mode, it counts
   cumulative reasoning characters from each SSE delta in real time (no
   per-chunk token count is available from the API, only characters) and
   aborts the connection the moment that count exceeds
   `reasoning_cap_tokens * 3` characters (a deliberately conservative,
   undocumented, locally-chosen chars-per-token estimate — see
   `_CONSERVATIVE_CHARS_PER_REASONING_TOKEN` in `research_budget.py`). An
   aborted request never receives final `usage`, so it settles at exactly
   the reservation (`DurableBudget.settle` with `usage=None`), never above
   it. This is the mechanism that makes a single request's actual charge
   provably bounded by its reservation, independent of anything xAI does.
4. The existing hard wall timeout (`--timeout`, default 180s) remains a
   second, independent backstop.

## Unknowns (explicitly not claimed as known)

- Whether xAI bills anything for a request whose connection the client (the
  broker) closes before `[DONE]`/final usage arrives. Cost tracking docs are
  silent on this. If xAI does bill partial reasoning on an aborted request,
  the broker's ledger still only ever *charges the run's own accounting* at
  the reservation, since no usage is returned to compute a higher figure —
  but the true upstream invoice could still be nonzero and is unverifiable
  offline. This mirrors the caveat already recorded for the earlier timeouts
  in `stream-diagnostic-01.md` and `CONTINUATION.md`.
- Whether `reasoning_effort: "low"` behaves identically across all grok-4.7
  prompt shapes; the one observed counterexample (43,919 reasoning tokens
  under "low") is in `CONTINUATION.md`.
