# Session 07 — cheap engine-driven lifting search

The conjecture remains open. We connected the fixed-word router to the actual
search engines and ran a complete, inexpensive pilot. The result is improved
finite construction coverage and a working context/feedback loop, not a new
universal lemma or an engine-ranking result.

## Results

| Frozen policy | Development within bound | Worst excess | Fresh confirmation | API cost | Wall |
|---|---:|---:|---:|---:|---:|
| Six fixed geodesic priorities | 20/28 | 2 | 120/120 | $0 | 0.847s initial evaluation |
| Sequential finalist `556ab94746a63a8f` | 22/28 | 2 | 120/120 | $0.444744 | 757.8s |
| EvoX finalist `7e7c102248da0306` | 24/28 | 1 | 120/120 | $0.338014 | 426.3s |

Each arm made 12 valid proposals. EvoX additionally made two valid strategy
reflections. No request failed or exceeded its reservation. Total reported
provider cost: **$0.782758**, below the approved $5 ceiling. Under the user's
$50 campaign budget, cumulative session-04–07 spend is **$30.148619**, leaving
**$19.851381**. Costs come from provider usage, not an independently reconciled
invoice. The separate legacy spend guard still reports historical
`runs/` spend $56.0159 against its default $20 cap; we did not alter that ledger.

The main controller ratio remains **1.5625**. This is a route-B experiment,
not a controller promotion. Both final construction portfolios still miss the
known (8,3) obstruction. A miss is not a lower bound or lifting counterexample.

## What the engines actually did

All four inherited planners now work with constrained JSON lifting policies:
zero ordering, changing move priorities and optional single level/uphill
steps. Seven new offline tests exercise schema restrictions, projection
replay, caps, provenance, confirmation isolation, and all four planners.
Only sequential and EvoX were paid arms. GEPA and AdaEvolve are connected and
tested, not newly benchmarked here. These remain compact local adaptations.

EvoX found its best policy on proposal 3, before reflection. After a stalled
window, it switched from best-parent exploitation to Pareto-front selection,
random inspirations, longer history and more exploration. Its second rewrite
switched to random archive parents with more edits. Both strategies were
validated, applied, and influenced later proposal requests. Neither produced
a new best. The experiment demonstrates the mechanism, not a causal benefit
from strategy rewriting. A single seed, unequal actual spending and only 12
proposals per arm cannot establish an engine ranking.

Both arms had identical initial policies, evaluation budgets, static research
context and planner seed. Model outputs are stochastic; the planner seed is
not a promise of deterministic API replay. Median candidate evaluation was
**0.18 seconds in each arm**. Model inference dominated wall time. The best
policies did not hit the 96-construction-attempt cap on development cases.

## Proof-relevant finite finding

For v=(8,7,9,6,5,4,3,2,1,0,0,0,0) at (m,r)=(9,4), delete zero j=9.
The smaller exact distance is 56. Six geodesic priorities give a best full
length 68: projection 56 plus routing overhead 12.

Both finalist policies instead certify **full length 66**, with projection
length **58** and overhead **8**. The successful projected construction uses
RLX priority, with one uphill R at projected index 5 (distance 51 to 52), then
returns to strict descent. Consequently this specific vector satisfies
**A_58(v)<=66**; in particular it meets T(9,4)=66. Spending two projected
steps saved four repair steps in these two witnessed constructions. This is
not a claim that all geodesics fail or that an uphill step is necessary.

EvoX also certifies all four frozen (9,4) band-edge/neighbour vectors and
recovers the known (9,3) obstruction repair with one level step. The (9,3)
repair was already known; it is a successful rediscovery, not a new theorem.
All words and marked-zero positions are in the finalist evaluation JSON files.
The hardest (8,3) repair still requires choices outside those found here.

Development-only ablation after both arms completed:

- Removing all detours from sequential changes misses **6 -> 8**.
- Removing all detours from EvoX changes misses **4 -> 9**.
- Each of EvoX's first four components can individually be removed without
  changing its miss count or worst excess on development. This does not show
  that all four can be removed together. Ablated variants were not selected
  or promoted using confirmation results.

This supports searching non-geodesic constructions. It does not prove a
universal bound on how many detours suffice. `diagnostics.json` also verifies
the accounting identity |V|=d(u)+(#level)+2(#uphill) for each saved successful
finalist construction and attributes its word to the generating policy path.

## Context and confirmation

`context-v1.json` fixes definitions, auxiliary results, rejected claims,
finite facts and hypotheses with source hashes and explicit scopes. The same
packet was sent to both arms. Parent policies, deterministic failure feedback,
selected histories, inspirations, focus and strategy tactics evolved during
the campaigns. Model reflections never changed authoritative evidence status.

`development-observations.json` records the two finite coverage findings with
hash-verified source evaluations for the next research-context update. It
contains no confirmation observations. Future context updates must explicitly
merge reviewed development facts; context does not silently learn proofs.

Confirmation was frozen before live calls, disjoint from development, and
opened only after both arms finished. Baseline and both original finalists
passed all 120 random vectors. This does **not** demonstrate improvement on
unseen hard cases: the random set was too easy to discriminate them. No
confirmation result was sent to a proposer, and the confirmation evaluator
refuses feedback extraction. Keep these results out of future prompt context.

## Next iteration toward a proof (pre-PDF plan; superseded by paper-review.md)

1. Search the joint construction/routing decision more directly. Today's
   language chooses a smaller word using distance priorities and only then
   prices its lift. Add a bounded, handwritten routing-aware beam/frontier
   interpreter with JSON controls; let EvoX/GEPA/AdaEvolve search its policy.
   Generated source code remains forbidden. Start by recovering the known
   (8,3) witness reliably before paying for a broad campaign.
2. Feed back which path and zero choice failed, plus boundary crossings and
   repair costs. Current compact feedback lacks that detailed attribution.
   Preserve the same trusted replay and distinguish search exhaustion from
   exact infeasibility. Prefer a development archive organized by failure
   mechanism over longer undifferentiated prose.
3. Freeze a new hard confirmation family before running that search, separate
   from this completed random set. Do not tune to the present confirmation.
4. If a compact rule emerges, extract a symbolic family and a cost argument:
   projected length plus repairs must be <=T, for all parameters. Exact BFS
   distance queries are a discovery oracle, not a general construction proof.
   The universal word-existence step, mixed-direction repair bound and general
   r=2 base remain unresolved. More proposals alone do not close those gaps.

## Verification and artifacts

318 tests pass; compileall for src/tests and the new integrations passes;
CLI smoke passes; trusted hashes unchanged; git diff check passes. The legacy
spend guard limitation above remains explicit. `manifest.json` fixes the
code/data/payload contract; both run contracts retain hashes. Raw prompts,
strategies, attempts, costs and full replayed certificates are preserved.
`confirm.py` refuses a second confirmation run or changed frozen files.
`plan.md`, `authorization.md`, `payload-scope.json`, `diagnostics.json` and
`confirmation-results.json` contain the protocol and evidence.

## Incoming theorem after the pilot

The user supplied a nine-gap m=8 theorem after confirmation. An independent
exact audit reproduced all 40,320 mixture certificates and 42,030 literal
stretch checks. See `paper-review.md` for scope and the revised priority:
new rational mixtures after projection. `context-v2.json` records this new
development evidence and was never used in the paid pilot. Final verification
after adding the auditor comprises 321 tests.
