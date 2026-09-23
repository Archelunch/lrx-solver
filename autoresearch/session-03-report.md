# Session 03 report

> Loop logs, campaign configs of the session and `runs/` directories are local
> and not published. Published evidence lives in `evidence/`.

Autoresearch loop `autoresearch/loop-260923-0838/`, 2026-09-23 08:38 to about
15:00. Owner request: search v3 (GEPA, AdaEvolve, EvoX, grok-4.7 as proposer
and reflector), spend limit $60, the queued Route B checks, and an evaluation of
an external handoff plus arXiv:2601.08715. Four iterations (campaign rounds).
Nothing pushed.

## Outcome

| | before | after |
|---|---|---|
| Verify, `python tools/orchestrator.py ratio` (rules lead, max value/T on m >= 8 train graphs) | 1.8333 (4189a604963f7a9e) | **1.5625** (49ab346cb44b2f1b) |
| Best sound potential, max value/T on m >= 8 train graphs | none | **3.875** (6ff08052bb698f26) |
| Logged spend, `python tools/orchestrator.py spend` | $4.82 | $56.02 (session $51.20; limit $60) |
| Guard: `trusted`, `spend`, unit suite | pass | pass (285 tests) |

The conjecture is open. No lead or potential reached ratio <= 1.

## Iterations

| iter | round | arms | USD logged | rules Verify | potential ratio | decision | commit |
|---|---|---|---|---|---|---|---|
| 1 | 1 | seq, gepa, ada, evox, med, pot | 17.31 | 1.6346 | none | promoted 26b3e8cd4c1d2934 (GEPA P x N with focus) | d1383df |
| 2 | 2 | seq, gepa, gepamed, evox, ada, pot | 14.60 | **1.5625** | 33.06 | promoted c01093d94ab5aaab (seq); first sound potential a5bd55171a2e922c | 4deba3f |
| 3 | 3 | seq, gepa, potg, pots | 11.54 | 1.5625 | 5.29 | lead 49ab346cb44b2f1b (train score better, no train graph worse); potential ba656bf2c7e03787 | a361ea5 |
| 4 | 4 | seq, pots | 7.75 | 1.5625 | **3.875** | rules unchanged; potential 5d536a0608217df6, generalised to 6ff08052bb698f26 | this commit |

Per-run rows with hypotheses and findings: `autoresearch/results.tsv` rows 9-26.
Loop log: `autoresearch/loop-260923-0838/loop-results.tsv`; checkpoints
`evals-checkpoint-1.md`, `evals-checkpoint-2.md`, final `evals-final.md`.
Search-side commits, each tested offline before live use: 51d81ff (search v3:
async steady state, tactics, GEPA P x N, AdaEvolve formulas, EvoX strategies),
8b39583 (campaigns, archive fallback), b6a13ec (select potentials by failing
states), 4deba3f (held-out uses the selection ranking).

## Route C: sound potentials (main new result)

A potential phi certifies d(v) <= phi(v) when every non-root state has a
neighbour with phi at most phi - 1. Details, arguments and evidence paths: the
Route C section of `research/claims.md`.

1. **First sound potentials.** None existed before round 2. a5bd55171a2e922c
   (33x T) holds on every state of 11 complete tables up to m8r4.
2. **ba656bf2c7e03787 (round 3, 5.3x T)**: phi = (floor(n/2)+1) e + k, with e =
   inversions read from token 1 + positional excess. Its descent argument is
   valid for all m, r (checked by the orchestrator, written out in claims.md);
   it implies E_r(n) <= (floor(n/2)+1)(C(m-1,2)+(m-1)r) + floor(n/2), which is
   cubic and weaker than the manuscript's C(n,2).
3. **6ff08052bb698f26 (round 4, 3.875x T)**: phi = a e + k + c u, u = number of
   improving cells + 1, c = floor(n/4), a = c + 2. grok-4.7 proposed the n <= 11
   case (4e + k + 2u, 5d536a0608217df6); the orchestrator derived the conditions
   a >= c + 2 and a + c >= floor(n/2) + 1 and the general constants. Exhaustive
   certify: 6ff08 holds on all 11 tables up to m8r4 (272 vs 54 at n = 12); the
   constant version fails on m8r4 (227 states without a descending neighbour).
   ba656 holds on all 11 tables (346 vs 54 at m8r4).
4. Both gains implemented ideas written into `prompts/insights-potential.md`
   (a quantity X lowers by exactly 1; k in the shorter direction; an amortised
   2e + k + c u shape). This is the clearest effect of orchestrator guidance
   this session.

## Rules track

- 1.8333 -> 1.6346 (round 1, GEPA with a focus graph per child) -> 1.5625
  (round 2, sequential; a general cut that removes an L the next rule undoes).
- Plateau since round 2: m8r3 stays at 75 vs T 48 in about 50 proposals. The
  round 2 GEPA, EvoX and AdaEvolve arms each reached 1.5625 through start
  special cases keyed to one probe state. Round 4's two-sided attempts (from the
  external two-arc structure) tied the parent or were much worse.

## Route B (finite)

- (13,10,3) k = 3: no over-budget vector among 1998 covered (df2180a).
- (13,9,4) k = 3: no over-budget vector among 11258 covered; four new vectors
  tight at 66 sit at the edge of the covered band, so k >= 4 may still find one.
  Recorded in `research/claims.md` and `autoresearch/lift-thresholds.md`.

## External input: handoff from cayleypy_experiments and arXiv:2601.08715

- The paper claims the pure LRX (r = 1) lower bound D_n >= C(n,2). The handoff
  reports its values correct but its optimality step unproven (their T8). This
  is a lower bound for r = 1 and does not bear on our upper bound for r >= 2.
  `research/claims.md` now marks statements that use it as conditional; none of
  our claims depend on it.
- Used as search guidance (attributed, unproven): word length = #X +
  #rotations, one X plus one shift per inverted pair inside a carried block,
  two complementary arcs. It helped the potential track (round 4) and not the
  rules track.
- Their requests (our certificate upper bound, Lean files) refer to material
  that is not in this repository.

## Method lessons

- Sequential refinement won both tracks in rounds 2-4. GEPA with focus won
  round 1 only. AdaEvolve's exploration never paid at 12 proposals. Medium
  reasoning effort cost 1.4x for the same result.
- Waste: 3 potential requests in round 3 hit the 1500 s wall cap (one valid
  answer in the same round ended in long repeated text), 2 responses had no
  usage field, 3 proposals exceeded the 80-node limit, and round 4 lost 4
  requests to network timeouts during a connection drop. The ledger logged
  $1.66 more than candidates were charged in round 3.
- Held-out results were reported but never used for promotion or feedback.

## Limitations

- Every potential result above T is a weak bound. Exhaustive checks cover
  complete tables only (n <= 12). The descent arguments are short and checked
  by the orchestrator, not reviewed by a mathematician.
- Rules ratios are probe-based upper bounds on the probed states, not on E_r(n).
- One seed per arm; arm comparisons are noisy.

## Next

1. Potential: a third amortisation level (a count of blocks or runs) or a
   smaller e; the 80-node limit is binding, so a human could consider raising it
   in the trusted DSL.
2. Rules: build a two-sided controller on small graphs first, then refine it.
3. Route B: (13,9,4) at k = 4 around the four band-edge tight vectors.
4. A human review of the potential arguments in `research/claims.md`.
