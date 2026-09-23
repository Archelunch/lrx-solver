# Session 07: engine-driven lifting constructions

See `autoresearch/loop-260923-2107/report.md` for the full protocol and evidence.

- Added a JSON lifting-policy adapter for all four existing planners, with
  versioned evidence context, deterministic train feedback and isolated confirmation.
- Ran 12 sequential and 12 EvoX proposals with grok-4.7; total $0.782758.
- Development: baseline 20/28, sequential 22/28, EvoX 24/28 within T.
  All three passed 120/120 fresh random confirmation vectors; this set did not
  distinguish them. One seed and unequal actual spend do not rank engines.
- EvoX applied two strategy rewrites; neither improved its proposal-3 best.
- Both finalists give a (9,4) band-edge certificate A_58(v)<=66, trading two
  extra projected steps for four fewer repairs compared with the six-geodesic
  baseline. Detour ablation worsens coverage. The hardest (8,3) case remains.
- No new universal lemma; conjecture open. Controller ratio stays 1.5625.
- 318 tests pass, smoke/compile/trusted pass. Legacy historical spend guard
  still fails its unrelated default cap. Remaining current research budget:
  $19.851381 (provider-reported costs, not invoice reconciliation).
- Next: bounded routing-aware construction policies, structural failure
  feedback, fresh hard confirmation, then a symbolic construction/cost proof.

After the pilot, an incoming PDF supplied a stronger nine-gap m=8 theorem.
Our independent data-only audit checked all 40,320 rational certificates and
42,030 literal stretch cases. See `loop-260923-2107/paper-review.md`: next
priority is reweighting projected mixtures, superseding the pre-PDF plan.
Final verification including the auditor: 321 tests pass.
