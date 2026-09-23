# Session 05: proof ingredients and cheaper exact lifting checks

The main LRX conjecture remains open. This local iteration adds two elementary
auxiliary arguments, a faster bounded checker, and a precisely scoped finite
lifting result. One approved Grok review cost $0.052468 in recorded API usage.

## Mathematical output

[Proof note](proof-note.md) gives the exact identity
`projection_z(W) = |W| - S(W) - I_z(W)` for every labelled zero and every word
when m>=2, r>=1. It also proves that smaller-state distance is a lower bound
on remaining full sorting length. These are general move-case arguments,
not conclusions extrapolated from finite tests. Neither supplies the missing
universal construction of short sorting words or the general induction base.
They have not been checked in a proof assistant or reviewed by an external
human mathematician. Grok agreed with the identity but made three follow-on
errors, independently corrected in [review-audit.md](review-audit.md). No literature novelty is claimed.

`integrations/zero_erasure.py` counts all marked projections in linear time.
It agrees with trusted replay on 14762 state/word pairs, comprising 28314
marked replays, plus explicit edge cases. Actual positive campaign witnesses
are still validated by the unchanged trusted checker.

## Finite evidence

- **(8,5): 27/27 positive.** This is the entire family of distinct zero
  insertions into the three smaller (8,4) antipodes, not the entire graph
  of 51891840 visible states. Search at q=55,B=60 took 27.01 seconds.
  Replaying every deletion establishes the stronger **A_54(v)<=60** for
  every member. Word lengths are 54–60. No exact A value is claimed.
- **(8,9): 24/24 incomplete.** Cases were frozen before evaluation from
  zero insertions into smaller antipodes. q=79,B=84, 100000 states per
  deletion, 128.52 seconds total. Every case exhausted resources; none
  is evidence for or against the universal lifting claim. State caps are
  checked between layers and may be exceeded within the last layer.
- Known negative controls at (8,3),q=42 and (9,3),q=52 remain negative;
  the corresponding q=P+1 controls remain positive. No new lifting
  counterexample was found.

## Kept optimization

Bounded `forward_h` now prunes a successor at depth t if `t+d(w)>B`.
Exhausting a pruned search returns COMPLETE_BOUND, never infinity.
Unbounded search and the trusted core are unchanged.

Four controlled ABBA benchmarks (two timings per implementation):

| Graph | Projection cap | B | Answer | Before/after time ratio | Stored states before → after |
|---|---:|---:|---|---:|---:|
| (8,3) | 42 | 48 | negative | 1.98× | 27866 → 14332 |
| (8,3) | 43 | 48 | positive | 3.56× | 93108 → 26632 |
| (9,3) | 52 | 59 | negative | 2.40× | 22942 → 9532 |
| (9,3) | 53 | 59 | positive | 5.21× | 66088 → 12352 |

These are small local benchmarks, not a universal speedup guarantee.
`pruning-benchmark.json` preserves results and timings. The independent DP
comparison covers all 120 visible states of (3,3), three q caps, and bounds
on both sides of each exact answer. A new regression exercises early
pruned exhaustion when an unbounded finite lift exists.

## Validation, accounting, and limitations

- Full unittest discovery: **305 tests pass**, 11.453 seconds.
- `python -m compileall -q src tests`: exit 0.
- `python -m src.lrx.cli smoke`: passed, 12 visible states.
- `python tools/orchestrator.py trusted`: ok, no changed/missing files.
- `python tools/orchestrator.py ratio`: **1.5625**, unchanged.
- The default legacy `spend` guard reports $56.0159 against its default $20
  and exits 1. It aggregates historical `runs/*/summary.json`, not this
  session's separately located campaign ledger. It is not a passing guard
  and is not the current campaign account; it was not overridden. The single
  approved review used its own $1.50 cap, within the $20.766773 remaining
  campaign allowance. A unified ledger remains an architecture follow-up.
- This iteration makes one successful request: recorded cost $0.052468. The
  authorized $50 campaign account is now at $29.285695 recorded usage,
  leaving $20.714305. Provider-reported cost is not invoice-verified. These
  figures exclude outer Codex usage/local compute.
- Automatic approval review initially blocked the research-prompt transmission.
  The user then explicitly approved the exact payload, and the request ran
  successfully. No approval block remains. See `usage.json` and `review-audit.md`.

## Next proof-focused experiment

The missing theorem is still an existence statement. Use the identity to
study whether a constructive family of words can guarantee enough erasures
on some marked zero. For the conjecture-facing Q+1 step, a word of maximum
allowed length Q+m-2 needs m-3 such erasures. A count identity alone cannot
supply that word. Inspect the replayed tight length-60 witness for a reusable
construction before spending on another optimizer campaign.

The (8,9) failures are computational limits. A separately verified
bidirectional or memory-bounded lifting search is a plausible next systems
experiment; increasing caps or labeling these cases negative is not a proof.

A concrete design lesson: the sole recorded length-60 witness has zero-erasure
profile `(4,4,4,2,6)`. Its best projection is 54; the average-only bound gives
56 and misses even q=55. Future proof search should preserve per-zero erasure
profiles in feedback. EvoX could steer the choice of marked zero and word
construction family, but this iteration does not compare search engines or
show that EvoX beats GEPA.
