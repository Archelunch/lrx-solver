# Session 06: constructive lifting rather than controller scores

The LRX conjecture remains open. This iteration derives a conditional
amortized routing bound, implements an exact fixed-word router, and resolves
all previously incomplete (8,9) test vectors with replayable positive witnesses.
One Grok review cost $0.080166 in provider-reported usage.

## Connection to a proof

Writing Q=T(m,r-1), the desired lifting statement is that every full vector
has some deletion and a smaller sorting word of length ell<=Q+1 whose full
lift costs <=Q+m-2. This requires a construction, not merely a counting
identity about an already-found full word.

[The proof note](proof-note.md) supplies:

1. A normal form for a lift of a fixed projection word: shortest invisible
   repair blocks have at most two moves. An n-position layered DP computes
   its exact optimal routing in O(n(ell+1)) operations and space.
2. An explicit L/X construction with repair overhead bounded by
   `2 floor((k+n-1-j)/(n-2))`, provided its computed final mark is admissible.
   Here k=#L. Each repair advances the mark by at least n-2 positions, so
   the bound follows by summing position changes. An infinite family attains it.
3. A free-trajectory subclass with overhead <=2, including mixed directions
   when its displacement/legality conditions hold.

These are general conditional arguments, not a proof of universal short-word
existence, not a proof-assistant formalization, and not a literature novelty
claim. The L/X condition does not cover the hard-family words found here:
all use both L and R. The conjecture still needs a universally applicable
construction and a general r=2 base theorem.

## What the new construction system establishes finitely

We froze six geodesic policies: each of the six priority orders of L,R,X,
always choosing a move that lowers the exact smaller distance by one.
For each zero deletion, route these words optimally and replay the results.
No generated program is executed; the trusted evaluator and tables are unchanged.

| Family | Result | Search time |
|---|---|---:|
| All 27 insertions into the 3 (8,4) antipodes | **A_54(v)<=58**, improving the previous <=60 | 0.171s |
| The 24 previously incomplete (8,9) vectors | All have projection <=77, full length <=81 | 0.560s |
| All 346 insertions into the 39 (8,8) antipodes | **A_77(v)<=83** | 9.331s |

Times exclude table loading. The full (8,9) graph has 980179200 visible states;
346 special vectors do not cover it. Exactly two of the 346 best portfolio
words reach length 83, saved for the next structural analysis. These are
upper bounds, not claims of optimal visible sorting distance or exact A.

The earlier breadth-first checks spent 128.52 seconds on those 24 vectors
without resolving them at their state cap. The new method finds certificates
quickly by restricting the candidate projected words. Its success is sound,
but its failure would not rule out the lifting claim. Therefore this is not
an equal-completeness runtime comparison with the exhaustive search.

Trusted-replayable artifacts:

- `m8r5-geodesics-certificates.json`
- `m8r9-all-geodesics-certificates.json`
- `m8r9-worst-portfolio-cases.json`

All 373 exported certificates were independently replayed after export
selection. The complete 346-case policy output is saved as
`m8r9-all-geodesics.json.gz`; the original JSON is preserved locally.
The summary records its SHA-256. Frozen cases and runnable scripts are included.

## What the obstructions teach us

The geodesic portfolio's best words on the known (8,3)/(9,3) old-cap
obstructions have lengths 49/61, consistent with their exact failures.
No new counterexample to a universal lifting conjecture was found.

For (9,3), the restricted repair search finds a length-59 word with projection
53 after 20 candidates (0.0115s). Its sole non-descending smaller step is a
rotation from distance 51 to 51. The repair uses six invisible moves: exactly
the allowance when ell=Q+1=53 and m=9.

For (8,3), 1653 one-defect candidates with fixed-priority descending prefixes
and suffixes miss the target. The independent forward search nevertheless
reproduces the known length-47 witness with projection 43. Its sole uphill
step is at projection index 5, from smaller distance 36 to 37. Thus a single
uphill step can suffice, but the surrounding descent choices matter. Even
plugging that known prefix into the six simple suffix policies leaves lengths
49 or 51. This exploratory prefix experiment was informed by an existing
witness; it is not independent confirmation of a general repair rule.

This is a specific next proof obligation: coordinate the smaller sorting
path with the marked-zero trajectory. Fixed global tie-breaking is insufficient
on at least this example; that does not disprove more flexible constructions.

## Model audit and validation

Grok supported the fixed-word normal form and supplied the free-trajectory
subclass. Its further claim that some pure rotation words have no lift was
false: our trusted replay supplies RXLLLL projecting to LLL in its alleged
impossible situation. Its XL projection accounting also required correction.
See [review-audit.md](review-audit.md). Model agreement is not used as a proof
certificate; the amortized L/X argument was derived locally.

- **311 tests pass** (final run: 9.579s).
- Independent marked BFS agrees with the fixed-word router for all valid
  words of length <=4 over four small parameter pairs, at every mark.
- Sweep bounds, the free subclass, input validation, and fixed-word failure
  semantics have separate tests, including cases in the conjecture domain.
- Compileall and smoke pass; trusted hashes are unchanged; diff check passes.
- Route A leads are unchanged; `python tools/orchestrator.py ratio` returns **1.5625**.
- The legacy spend guard still fails: historical `runs/` usage $56.0159
  against its default $20. It is not the current campaign account and was
  not overridden. Unifying budget accounting remains a separate follow-up.

This iteration used one request, recorded at $0.080166 against its $2 cap.
The authorized $50 campaign account now totals **$29.365861**, leaving
**$20.634139**. These are provider-reported/recorded costs, not invoice-verified,
and exclude outer Codex usage and local compute. The initial automatic approval
block was resolved by the user's explicit approval of the exact research prompt.

## Next step toward the final theorem

Use the two length-83 witnesses and the old-budget obstruction to study a
mixed-direction analogue of the amortized repair bound. The fixed-word router
can serve as a deterministic evaluator for constrained word-construction or
routing policies, including an EvoX-driven search. A useful candidate must
come with an explicit structural condition and a symbolic cost argument.
This iteration did not compare EvoX with GEPA and does not establish engine
superiority. Another general score improvement would not close the missing
existence theorem or the base case.
