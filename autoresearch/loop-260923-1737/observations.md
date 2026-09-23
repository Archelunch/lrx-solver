# Mechanism observations (completed comparison)

- First-round proposal prompts are identical across the three engines for
  each seed (initial-prompt-audit.json). Initial differences are generation
  variability, not a search-selection effect.
- Ratio plateau detection works: EvoX reflects despite mean-score-only gains.
- EvoX 204, proposals 5-8: three new controllers sort every checked state but
  have worst ratios 3.8846, 2.5417 and 2.5385; one has 125 sanity failures.
  New algorithmic families exist, but are worse than the heavily refined seed.
- EvoX 205 reflection after proposal 12 requests kind potential/bound although
  campaign kinds=[rules]. reflection_summary does not explicitly supply allowed
  kinds, and LLMProposer.reflect includes the DSL for all kinds. Candidate
  validation remains intact, but the contradictory tactic can waste calls.
  Repair after the frozen comparison: include allowed_kinds in reflection
  summary and system constraints, restrict its DSL reference to those kinds;
  test propagation. Do not silently change prompts in current arms.
- Synchronous rounds give clean policy attribution but amplify long-tail
  request latency. One GEPA 204 call hit 1200s; unknown usage is conservatively
  charged by the existing ledger, not recorded as zero session spend.
- Retained sequential 204 changes include skipping already attached successors
  and a dimension-specific m8r2 start branch. Neither lowered worst train ratio
  at the observed checkpoint.
- GEPA 204 proposal 10 lowers train worst ratio to 73/48 = 1.5208333.
  It adds an odd-n, r>=3, m>=8 startup branch for pos1=2 and adjacent
  tokens 2,3 on the long arc. This is a narrow structural special case;
  fresh-state confirmation is required before treating it as general progress.
- Candidate traces show reasoning tokens dominate output tokens, while model
  generation time greatly exceeds evaluator time. Cache/simplification gains
  should not be presented as equivalent reductions in paid model cost.
- The edit-mode guard treats every condition mentioning csorted as a finishing
  rule. It also freezes ordinary insertion rules guarded by csorted == 0.
  On the original baseline this freezes 10 of 12 rules, sharply restricting
  the advertised local-edit operator. This predates the comparison; fix and
  test separately, preserving actual finishing behavior.

Final outcome: GEPA 204 train ratio 1.5000; sequential 205 1.520833;
other main arms 1.5625. All seven confirmation controllers have identical
per-graph maxima, with 49000 successful word replays and zero failures.
No lead promoted. Post-comparison contract fixes pass 301 tests; three paid
edits recovered locally, none better than the finalists. Total recorded API
spend $29.233227; no further calls scheduled. See report.md for scope.
