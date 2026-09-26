# Session report, 2026-09-26

One-page summary of the day for the maintainer. Details: claims Sessions
17-36, HANDOFF.md, the notes under autoresearch/bound-m-260925/.

## Achieved
- Two infinite families closed at every m >= 9 and every block length,
  with complete written proof chains (word_C, word_R1 plus general-m
  Lemma 1 / criterion (7)). Model-written, mechanically checked (720 and
  192 cases, 0 mismatches), awaiting human review.
- The group's m=8 lemma stack audited at general m: no m=8 dependence;
  proofs written; 21,896 exact table points, 0 violations.
- Exact impossibility theorems: no single-leaf certificate for m = 9
  {0,4}, 11 {0,5}, 12 {0,5}, 12 {0,6}; portable checkers, verified from
  clean builds in isolation. Trees then certify all four.
- Exact oracle as column-generation pricing: every instance ends in a
  certificate or a refutation; closed the cases every generator missed.
- New exact tables (10,2), (11,2); radius = T, two extremal states.
- Surveys: k=2 masks near-complete to m = 13; k=3 first survey (455
  certificates); interior masks all root-certifiable for k = 2, 3.
- Three closed-form word families read off data (word_G, word_M, word_W),
  with exact hypotheses stated for proof.
- External review by the group confirmed the stored certificates with
  their own checker; all their corrections applied (package v4).

## Engines (GEPA / AdaEvolve / EvoX)
- Campaign 3 seed 1: AdaEvolve beats the strong seed on development (287
  vs 283) and validation (159 vs 157); the others tie or fail. Cost
  $4.04. Seeds 2-3 need re-approval after two robustness fixes.
- Honest reading across all campaigns: engines amplify coverage on a
  strong seed at low cost; every closed form, proof and refutation came
  from exact tools and structured analysis by Opus workers.

## Corrections made today
- "Base excess" figures from generator pools are not lower bounds.
- m = 11 {0,4} was certified by an earlier tree; a later note had listed
  it as a miss.
- Two Session 33 conjectures refuted at m = 12.

## Cost
About $4 in provider calls today (campaign 3 seed 1); the rest offline.

## Files to look at first
autoresearch/FINDINGS-260926/FINDINGS.md (section i: proof status),
WORDC-PROOF.md, LEMMA1-GENERAL-M-260926.md, negcert/NEGCERT.md,
MIDBAND-TREES-M12-V2.md, bound-m-c3-260926/KILL-CHECK-S1-NOTE.md.
