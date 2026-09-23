# Bounded experiment protocol

1. Freeze dataset and evaluator hashes before a campaign.
2. Run the unchanged baseline, independent proposals, sequential refinement,
   and small parallel proposal batches with the same caps.
3. Use at least three seeds. Record every proposal, including failures.
4. Optimize verified budget coverage first, worst finite length excess second,
   then search cost. UNSOLVED is not a lower bound.
5. Expose training examples and compact failure feedback only. Reserve entire
   parameter pairs, parity cases, and family ranges for later evaluation.
6. A finite failure of the lifting statement is not a refutation of the main
   conjecture. Independently reproduce a purported exact counterexample.
7. Stop when the request, CPU-work, or spend reservation limit is reached.
8. Cache trusted BFS/DP outputs by source hash, parameters, and completeness.
   Never let a candidate cache partial results as exact ground truth.

First scientific target: determine whether `A_P<=P+m-2` holds on the original
four audited graphs, then compare it with the weaker cap `Q=T_m(n-1)`.
This requires the unavailable original tools or a new optimized exact engine;
the tiny Python demo does not answer that question.

## v2 campaign plan (configs in `campaigns/`)

- **E0 smoke** (paid, one request): `llm-smoke campaigns/grok-smoke.json`.
  Record parse success, tokens, latency, cost.
- **E1 rules** (paid): `grok-rules-adaevolve` vs `grok-rules-gepa` vs a
  `sequential` copy, same `max_proposals`, `max_spend_usd`, seeds 1..3.
  Question: how far below the bubble baseline (124 vs T=42 at (8,2)) does
  each get? Report best train score, feasible flag, heldout rows, USD.
- **E2 potentials** (paid): `grok-potential-adaevolve`. Question: can any
  closed-form phi reach zero local-descent failures on sanity + train
  probes, then `certify` on (8,2)?
- **Control**: the matching `offline-*` configs at equal proposal count.

Held-out rows are read by the human/orchestrator only. Do not copy them into
`prompts/insights.md`.
