# Next autoresearch iteration: new mixtures after projection

Status: local phase completed in session 08; paid phase was unnecessary and
was not launched. See [the report](loop-260923-2154/report.md): 76 named family
certificates, $0 API cost. The protocol below is preserved as the pre-run plan.
Next: a wider existing-catalog search with fresh structural confirmation.
Repository documentation is maintained in
English. The objective is progress toward the general LRX sorting-radius
conjecture, starting with additional infinite families at m=8.

## Hypothesis

Some families missed by the original nine-gap mixture after deleting blocks
can be certified by reweighting already available projected words. Failing
with inherited weights does not establish infeasibility for new weights.

A candidate is a finite list of catalog word/cut references and nonnegative
rational weights. For k retained blocks, verify exactly:

- weights sum to one;
- weighted base cost is strictly less than 31+6k;
- each retained block coefficient is at most 6;
- every referenced word, projection, cut, dominance condition, and coefficient
  calculation satisfies the supporting lemmas.

These conditions certify the entire family for arbitrary positive lengths.
Floating-point feasibility alone is never accepted. No generated code runs.
The existing trusted core stays unchanged; the new search-side verifier must
have independent replay checks, negative controls and recorded hashes.

## Phase 1 — deterministic baseline, no API cost

1. Read the supplied data archive as data. Independently reconstruct projection
   prices and an auditable coverage baseline for retained gap sets with 4–8
   blocks. Check overlap with the supplied reverse-order results before calling
   a family newly covered. Report dependencies that remain unchecked; do not
   assume the manuscript's 4,495,529 count is already our verified complement.
2. Freeze a small structural batch: provisionally 100 development families
   and 50 confirmation families, stratified across 4–8 retained blocks. Select
   deterministically before running new optimizers; preserve IDs and hashes.
   If sampling cannot yet use a fully audited complement, label gains relative
   to the checked baseline instead of claiming a global coverage increment.
3. Recompute projected profiles, retaining nondominated word/cut profiles.
   A cheap deterministic optimizer proposes new mixtures; exact rational
   reconstruction and validation decide acceptance. First test the inherited
   support, then a larger compatible catalog pool. Distinguish these scopes.
4. Stop after the frozen batch or 30 minutes of local evaluation, whichever
   comes first. Keep certificates and useful failures. A timeout, restricted
   support failure, or heuristic miss is not an infeasibility proof.

No new solver dependency is assumed. Prefer the existing standard-library
runtime for a bounded prototype. If a new numerical solver is materially
needed, present the concrete dependency and integration choice before adding
it. A solver would be a proposer; exact checking remains separate.

## Phase 2 — engine pilot, only after the verifier and baseline work

Connect a mixture-domain adapter to the existing campaign planners. Avoid
rewriting the orchestration layer or paying an LLM to perform routine weight
arithmetic. Engines should choose useful supports, catalog neighborhoods,
word/cut generation policies and unresolved structural families.

Initial comparison: EvoX versus sequential, 12 proposal slots per arm, same
starting archive, development data and evaluation ceiling. Proposed API cap:
$2 per arm, $4 total, including reflection. This is a proposal, not approval
to transmit the new paper or launch calls. The completed campaign's approval
covered its previous payload only. Current recorded budget remaining is
$19.851381; reconcile new spending against that ledger before launching.

GEPA is a natural next arm for complementary coefficient profiles; AdaEvolve
can allocate islands to block counts and structural gap patterns. All four
are supported by the existing lifting adapter, but the new mixture adapter
and these mixture experiments still need implementation and validation.

## Context and feedback

Start from the reviewed development facts in
`loop-260923-2107/context-v2.json`, with a fresh immutable campaign snapshot.
Add catalog provenance, the projection certificate contract, and current
training failures. Preserve the distinction between mathematically justified
claims, exact finite checks, attributed coverage, and hypotheses.

Feedback should expose violated inequalities, base/slopes, support size,
catalog-search scope and work spent. Add separating or dual certificates only
when the optimizer actually provides checked ones. Reflections remain
hypotheses. Do not send raw archives, unrelated files or confirmation cases.

## Metric, stopping and deliverables

Primary: number of additional infinite families with exact accepted
certificates, relative to a named verified baseline. Secondary: inequality
margins for search guidance, support size, evaluation work, wall time and API
cost. A method comparison uses held-out structural families once, after all
arms finish; the ultimate proof requires exhaustive coverage, not good
held-out performance.

Stop for checker disagreement, changed trusted hashes, spending limits, or
repeated infrastructure failures. A failed mixture does not refute LRX.
A feasible mixture closes a family, not the full m=8 case. No extra campaign
is launched merely to consume remaining budget.

Deliver: frozen family manifest, tested mixture interpreter/verifier,
deterministic baseline, exact new certificates or clearly scoped failures,
engine traces if phase 2 runs, reconciled cost, updated English report and
claim register. A zero-cost discovery of new families is already a successful
iteration; if none are found, identify whether the restriction is inherited
support, available catalog columns, the search method, or a verified
infeasibility result for a precisely defined finite LP.
