# Session 07: engine-driven lifting constructions

Goal: find a reusable short-word construction supporting the LRX induction step.
The conjecture remains open. This search uses exact smaller BFS distances and
therefore cannot itself supply an oracle-free general algorithm or proof.

## Frozen question

Can state-dependent move priorities plus one controlled non-descending step
repair the hard examples missed by six fixed geodesic priorities?
For each full vector v of (m,r), search zero deletions and smaller words of
length at most q=T(m,r-1)+1, then route the deleted zero exactly. A witness must
have full length at most T(m,r). Every emitted full word is independently
replayed by the locked certificate validator. A portfolio miss is not a
counterexample to the existential lifting statement.

## Protocol

- Engines: existing sequential and EvoX planners via LiftCampaign adapter.
  GEPA and AdaEvolve also pass offline adapter tests, but are not paid arms here.
- Each arm: 12 proposal slots, at most 18 total API requests, $2.50 ceiling,
  one proposal at a time. EvoX reflects after stalled 3-proposal windows.
- Same seed, six-priority initial candidate, train data, context and word cap.
  Equal proposal and dollar ceilings do not imply equal actual spending.
- 28 development vectors from known obstructions, neighbours, band-edge states,
  and previous antipode-insertion families. Baseline: 20/28 within bound;
  worst excess 2; one evaluation including table initialization took 0.847s.
- 120 frozen confirmation vectors, 24 per graph, excluded from campaign data.
  Evaluate baseline and frozen finalists only after all arms complete. Uniform
  random vectors may be easier than development examples; report this limitation.
- Policy schema: zero ordering, a portfolio of priority schedules, and optional
  prescribed single level/uphill steps. No explicit vector keys, graph-specific
  branches, evaluator edits, or executable model output.
- 96 candidate-construction attempts per vector, including failed constructions.
  All base variants precede detour variants. Stop at first within-bound witness.
- Score: missed cases first, then worst capped excess, sum excess, simplicity.
  This does not optimize best possible witness length once the target is reached.

## Context and orchestration

context-v1.json contains explicit statements, epistemic status, scope, and
hash-verified development evidence. It is frozen across both arms. Proposals
also receive selected parent policies and feedback; engines select histories,
focus, inspirations and tactics. Reflections remain unverified hypotheses.
The orchestrator fixes this contract, monitors caps/errors and inspects the
final certificates. It does not manually select candidate edits during arms.
After completion, new observations belong in a separate evidence packet,
retaining finite scope and keeping confirmation out of future proposal context.

## Accounting

Prior spend under the user's $50 research budget: $29.365861. This pilot's
maximum additional spend is $5. The legacy orchestrator spend command sums a
different historical runs directory and exceeds its default $20 guard; it is
not a reconciled ledger for this budget. We retain that limitation rather than
changing the locked ledger. New per-arm client ledgers enforce $2.50 each,
including reflection, reservations and token ceilings. Report actual usage.

## Status before live calls

318 tests pass (8.758s); compileall, smoke, and trusted hashes pass. Seven new
tests cover schema rejection, projection replay, detour budget, capped misses,
context provenance, confirmation isolation, and all four planners including
EvoX strategy reflection. Live execution was rejected before transmission by
automatic approval review; exact campaign-payload approval is pending.
