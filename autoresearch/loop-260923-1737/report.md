# Session 04: budgeted search and program optimization

Paid comparison and fresh-state confirmation complete. No confirmed improvement in the fresh-state worst ratio.

Six matched local-engine campaigns plus a two-proposal pilot used **$29.233227**
of the authorized $50 Grok budget, leaving **$20.766773** unused. This is recorded
API usage accounting, not an independently reconciled provider invoice. It
excludes outer Codex work and local compute. There are no more paid runs planned.

## What the comparison establishes

The best training ratio fell from 1.5625 to **1.5000** in one GEPA seed. One
sequential seed reached 1.520833; neither EvoX seed improved this primary metric.
This is finite probe evidence, not a proof or a decisive ranking of engines.
The conjecture remains open.

| Engine | Campaign seed | Request-started proposal slots | Valid JSON | Solved all checked states | Best train word/T | Recorded USD | Minutes |
|---|---:|---:|---:|---:|---:|---:|---:|
| evox | 204 | 22/24 | 17 | 12 | 1.562500 | $4.9632 | 77.2 |
| evox | 205 | 23/24 | 17 | 10 | 1.562500 | $4.9180 | 71.1 |
| gepa | 204 | 24/24 | 17 | 17 | 1.500000 | $4.4797 | 78.0 |
| gepa | 205 | 24/24 | 19 | 15 | 1.562500 | $4.2821 | 63.9 |
| sequential | 204 | 24/24 | 18 | 17 | 1.562500 | $4.5235 | 68.9 |
| sequential | 205 | 22/24 | 19 | 17 | 1.520833 | $5.5289 | 99.2 |

“Request-started” excludes slots rejected by the budget ledger before a request.
It includes aborted requests; “valid JSON” does not imply a correct controller.
Five of the 144 main proposal slots were budget-denied before any request.
The pilot adds two proposals and $0.537862. All runs together made 207 model
requests, including repairs and reflection. Five requests failed at the
infrastructure/accounting layer: two timeouts and three missing-usage responses.
The ledger conservatively charges unknown usage; it also records two reservation
overruns. All final ledgers match the campaign summaries.

The design matched starting candidate, model, initial prompt, four-proposal
synchronous rounds, proposal caps and $6 run caps. Actual spend and launched
proposals differ, so these are not strictly equal-cost completed searches.
The first-round user prompt hashes match across engines for each seed
([audit](initial-prompt-audit.json)). Seeds control campaign sampling and prompt
identifiers; model outputs still vary. Two seeds are exploratory.

At completed-round cost checkpoints, GEPA 204 first reaches 1.520833 within $3;
sequential 205 reaches it within $4. GEPA's 1.5000 appears above $4. The other
four arms stay at 1.5625. See [analysis.json](analysis.json) for every checkpoint.
No statistical superiority claim is warranted.

The winning GEPA candidate, `657bee0717db3498`, merges two startup shortcuts:
an odd-n branch for adjacent tokens 2 and 3 on the long arc, and an r=2 branch
that swaps a particular front inversion before insertion. These are narrow
structural conditions. Their train improvement alone cannot establish that
the controller has a better universal worst case.

## Fresh-state confirmation

The seven frozen controllers (baseline plus six train-selected finalists) each
sorted 7,000 fresh states: 1,000 per graph, **49,000 successful word replays** in
total, with zero failures. Their observed maximum word lengths are identical
on **every** confirmation graph:

| (m, r) | T | Maximum word, all seven controllers | Ratio |
|---|---:|---:|---:|
| (8, 2) | 42 | 65 | 1.547619 |
| (8, 3) | 48 | 78 | 1.625000 |
| (9, 2) | 52 | 84 | 1.615385 |
| (8, 4) | 54 | 91 | 1.685185 |
| (10, 4) | 79 | 129 | 1.632911 |
| (8, 9) | 84 | 141 | 1.678571 |
| (16, 4) | 178 | 280 | 1.573034 |

Thus the overall maximum is 91/54 = **1.685185** for every finalist, including
the baseline. The training reduction to 1.5000 does **not** transfer to a lower
fresh-state maximum in this sample. Means change slightly in both directions;
that does not rescue the missing worst-case improvement. No new controller is
promoted to the lead directory from this session. Train-selected artifacts are
retained for inspection, not presented as a stronger general sorting bound.

The corpus and its checksum were frozen before the campaigns, and all finalists
were recorded before confirmation. These are random-state checks, partly on
known dimensions, not exhaustive graph certificates or a universal result.
Confirmation results were not fed to any proposer. Treat this section as
reporting-only evidence, not future optimization feedback. See
[confirmation-results.json](confirmation-results.json) and
[frozen-finalists.json](frozen-finalists.json).

## What we learned about EvoX

Each main EvoX run deployed five strategy revisions. Exploration produced
several different controllers, including sound finite controllers that were
worse than the mature insertion baseline. No new family beat its worst ratio.
The experiments also exposed limitations in our adaptation:

- A reflector recommended potential/bound candidates inside a rules-only
  campaign. A bound proposal was correctly rejected. The reflection prompt now
  receives explicit allowed kinds and only their candidate shapes.
- The edit guard froze every rule mentioning `csorted`, including ordinary
  insertion rules gated by `csorted == 0`: 10 of the baseline's 12 rules.
  It now exempts conditions syntactically proved false when `csorted` is true,
  while preserving the actual finishing rules and the two-edit limit.
- Ratio focus could send a fourth sibling to an already-passed sanity graph
  after using the three target graphs. It now revisits a target graph; actual
  failures or incomplete checks remain eligible regardless of dimension.

These fixes were applied **after all six campaigns completed**. They do not
retroactively change the results. A separate, zero-new-API-cost salvage pass
recovered three rejected EvoX edits. All three sort every training state checked;
their worst ratios are 1.8125, 1.5625 and 1.645833. None beats the existing
finalists. See [salvage-results.json](salvage-results.json).

Our EvoX is a constrained JSON-policy adaptation. It does not implement the
full strategy-program evolution of SkyDiscover. The [published EvoX experiment](https://arxiv.org/html/2602.23413v1)
uses a 100-iteration budget, so this smaller experiment cannot settle its
long-horizon claim. The local contract problems are reasons to improve this
implementation, not evidence against the general approach.

## Computational improvements kept

1. **Training evaluation cache.** Namespaced by candidate semantics, evaluator
   hash and data paths, with checksums and atomic writes. Held-out and incomplete
   evaluations bypass reuse. The main campaigns reused six baseline evaluations,
   about 55.5 source seconds. Unique candidates still require evaluation.
2. **Position lookup simplification.** A guarded direct lookup replaces a scan
   over every token, preserving absent-label behavior. The baseline JSON shrank
   about 7%. An ABBA train benchmark measured 9.56 to 7.59 seconds on average
   (about 21% less time), with identical graph metrics. Exact controller words
   also agree on all 360 m4r2 states. Only two timings per variant were taken,
   under concurrent campaign activity; this is not an end-to-end cost claim.
3. **Decision-specific lifting checks.** Stop after a replayed witness proves
   A_Q(v) <= B. A negative answer still requires complete bounded searches for
   every deletion; resource exhaustion remains INCOMPLETE. On 100 small states,
   decisions agree with full search and take 0.092 versus 0.255 seconds (2.76x).
   Known m8r3 and m9r3 positive cases are about 2.4x and 2.3x faster; negative
   cases have little saving. These reproduce known obstructions and repairs,
   and do not establish a new lifting lemma.
4. **Selection and reporting correctness.** Worst train ratio drives ranking
   and EvoX plateau detection; mean-only gains no longer mask a ratio plateau.
   `final_heldout_top=0` genuinely skips held-out evaluation. The optional official
   GEPA adapter now reports actual held-out scores rather than a training score;
   that adapter was not part of the live comparison.

## Recommended architecture

Keep the verifier boundary and a small deterministic campaign runner. Use the
outer coding agent at experiment boundaries, and bounded model reflection within
the loop. Prioritize proposal validity, a cheap representation for local edits,
retention/refinement of new controller families, and cost-aware scheduling.
Temporary in-flight reservations should defer work rather than consume proposal
slots. Do not reduce ledger safety to obtain more calls.

This is the concrete route toward cheaper autoresearch. A richer JSON strategy
space or a separately reviewed sandbox for official EvoX is a next experiment,
not an outcome already demonstrated here. See [architecture.md](architecture.md)
for the diagram, alternatives and claim boundaries.

## Verification and reproducibility

After the post-comparison fixes: **301 tests passed in 8.292 seconds**;
compileall and session-script compilation exited 0; smoke returned `passed=true`;
trusted check returned `ok=true`, no changed or missing locked files;
`git diff --check` passed. The promoted-lead verification metric remains
**1.5625** ([verify-ratio.txt](verify-ratio.txt)). See
[verification-final.log](verification-final.log).
No generated Python was executed, no dependency was installed, no data or locked
verifier was edited, and no remote write was made.

The frozen campaigns all recorded evaluator hash `5b1487a48a68a159`. The hash
includes search-side Python, so later search fixes change it even though the
locked core remains unchanged. Configs, prompt audit, confirmation corpus,
compact summaries and local raw traces are retained in this directory.
