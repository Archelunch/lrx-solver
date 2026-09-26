# research/claims.md, Sessions 10-23 (verbatim excerpt)

Source: `research/claims.md` lines 372-830 at commit 6e56ddf (2026-09-26), copied without edits below the rule.
Paths inside the text are relative to the repository root, not to this folder.

---

## Session 10: independent replication of the external full m=8 package

On 2026-09-24 the research group supplied `lrx_m8_complete_verification`
(834 MB, 147 manifest entries, all SHA-256 verified), claiming
E_(n-8)(n) <= 6n-18 for every n >= 9 with all 20,603,520 (a,S) families
covered. This is the group's theorem, not ours. Two replications ran here,
recorded under `autoresearch/verify-m8-260924/`:

1. **Their pipeline, our machine.** `scripts/replay_multiset_m8_package.py`
   unchanged: 30 stages PASS in 1009.6 s, completion audit reports 0 remaining
   families and rejects 5 negative controls (`replay-full.json`).
2. **Our checker, written from the theorem text.** Stdlib and exact Fractions,
   no package script imported (`checker/`). Every k=4..9 certificate file
   verified in full by Lemma 3 transfer, formula (11), and criteria (7)/(8),
   with literal stretched execution at z = 0, e_j, 2e_j and adjacent pairs:
   four 262,513 / five 337,965 / six 228,966 / seven 74,614 / eight 10,278 /
   nine 40,320 families, 0 failures, 0 stored-claim mismatches. The k>=4
   union was rebuilt over all 8! x 382 masks without any package coverage
   table: 0 uncovered, per-k counts equal to the package table. All 338
   one-block exception mixtures, 37,323 two-block trees and 639,357
   three-block trees pass. Five corrupted records were rejected.

The repo's hardest development family `k5-mask302-order15713` (unit block
a=1, our pool optimum 1223/20) is certified in the package by Lemma 4
projection from seven-gap record 37688 (mask 446): weights 3/44, 5/11, 9/44,
3/11, weighted base 121/2 < 61, slopes (6, 63/11, 6, 6, 6). Reproduced by a
stdlib replay and by `integrations/projected_mixtures.py`
(`autoresearch/verify-m8-260924/k5-mask302/REPORT.md`).

Low-block single-word certificates were partly replicated by an independent
bounded search from the section 7 resource table: k=1 in full (362,542 words,
the 338 exceptions match exactly); k=2 and k=3 by seeded samples of 5,000
bases plus listed exceptions, 0 mismatches. Not independently replicated: the
full k=2 and k=3 enumerations (1.81M and 6.65M bases), the unlisted
fewer-block exception counts (290, 65+36,888), the Lean files, the
C++ programs, and the n>=130 theorem (unneeded, since the unbounded criteria
were checked). Lemmas 1-4 were read and re-derived, not formalised. The
general conjecture for arbitrary m remains open. No optimizer was involved
and no provider call was made; optimizer contribution this session is zero.

## Session 11: live three-engine campaign on the m=8 -> m=9 lift task

After the m=8 replication, the search target moved to a label-insertion
gadget: a program lifting certified m=8 family certificates to m=9 children
(budget T_9(n) = 7n-25; unit-base criterion weighted base < 39+7k, slopes
<= 7). Frozen sets: 210 development parents / 4588 instances, 105 holdout
parents / 2295 instances. Model gemini-3.8-flash through the budget broker,
after a grok-4.7 attempt hit the 480 s wall with no answer.

Exact finite results, all independently audited with 0 disagreements
(`autoresearch/lift-m9-260924/finalists/`): the naive fixed gadget certifies
285 development and 158 holdout m=9 families; GEPA 336 / 190, sequential
refinement control 334 (337 intermediate) / 190, AdaEvolve 337 / 190, EvoX
337 / 190. The union adds **84 audited m=9 family certificates** (52
development, 32 holdout) beyond the control, each an exact bound for all
positive block lengths of that family. Cost $4.41 of the $150 cap over 264
calls.

Operational success: all three native engines ran live end to end with
mechanism traces. Mathematical: finite certificates only; no label-insertion
lemma and no progress on the general conjecture. Comparative: not
established; one seed per arm, all arms tie the sequential control on
holdout. Proposals mostly re-ranked the same constructed words; the
constructor itself rarely changed. Misses prove nothing.

## Session 12: correlation certificate C <= 4K + 2H, reproduction and ansatz search

The group's note (2026-09-24) proves C <= 4K + 2H for 4 <= m <= 16 via a
general certificate criterion (their Theorem 3) plus numeric LP certificates,
and states that a universal coefficient formula is missing. Their coefficient
files were not available. Here (`autoresearch/corr-cert-260924/`):

- Definitions and Lemma 2 identities re-derived and validated by full
  enumeration for m = 4..8 and seeded samples for m = 9, 10; no failures.
  Max E = C - 4K - 2H is 0, attained only at the reversal orders p_i = -i.
- Certificates regenerated independently by LP (system scipy, search side
  only) and re-checked by a stdlib exact checker for every m = 4..16; all
  epsilon < 1, corruptions rejected. New facts: the LP optimum is exactly 0
  at every m tested (positive epsilons are rounding), and exact epsilon = 0
  certificates exist for m = 4..7 with Q = 1, 1, 2, 596. This reproduces
  their Theorem 1 for m <= 16 with independent code and is not a priority claim.
- Negative result: coefficient formulas polynomial of degree <= 3 in
  (a, b, c, m) with step terms at the kappa thresholds (and q times steps)
  fit m = 4..8 but fail exactly at m = 9; no such family reaches m = 12.
  The obstruction concentrates on triples with a unit gap and on wrap rows
  q + t > m (dual certificates stored). So a universal formula, if it
  exists, is not of that polynomial-plus-threshold form.
The general conjecture is untouched. Misses prove nothing beyond the stated
ansatz classes.

Addendum (2026-09-25): the structure hunt (`STRUCTURE.md`) shows certificates
supported on adjacent-label triples exist only for m <= 10, and the needed
gap width grows with m (2 for m = 11..14, then 3, 4, 5, 6 at m = 15..18), so
no label-local universal formula exists. Exact epsilon = 0 certificates are
now verified for m = 4..9. Conjecture (not proved): the triple LP relaxation
is exact, optimum 0, for every m; proved m <= 9, float evidence to m = 18.
A live campaign of GEPA / AdaEvolve / EvoX / sequential on the program
`coefficients(m)` produced no certificate beyond the two worked examples
(m = 4, 5) on development and none on holdout m = 13..20; $3.58 spent
(`autoresearch/corr-cert-260924/REPORT-CAMPAIGN.md`). Engines do not solve
exact dual feasibility; the deterministic LP did.
Correction (2026-09-25): a trace audit (`autoresearch/TRACE-AUDIT-260925.md`)
found plumbing defects that invalidate the engine comparison in the
correlation campaign (fraction-to-float scoring bug, exhausted shared cap,
over-strict output parsing, repeated prompts, stale packet line). The
deterministic mathematical results stand; the "engines failed" statement is
withdrawn pending a rerun with fixed plumbing.

## Session 13: exact m=9 tables and the outer-layer class (2026-09-25)

New exact radii by complete ranked BFS (`src/lrx/table_bfs.py`, tables under
`datasets/generated/outer-layer-260925/`, sha256 recorded):
(9,4) radius 66 on 259,459,200 states; (9,5) radius 73 on 726,485,760 states;
(8,5) 60; (8,6) 66. All equal T_m(n). Together with the locked tables, the
conjecture is verified at m=9 for r<=5 and at m=8 for r<=6.

Against the group's note of 2026-09-25 (deletion criterion, Theorems 1-2,
condition (6)): the class of m=9 states whose every single-label deletion lies
in the outer layer P-c_p < d_q <= P contains 93.7 / 95.2 / 95.7 / 94.5 / 94.5 %
of all states for r=1..5 (full enumeration, no sampling), because each (8,r)
radius equals P. Theorem 2 alone proves the remaining 5-6 %, whose distances
stay 20-29 below T. Every class member is within budget (class maximum equals
the radius). Exact pointwise lifting constants: d(v) <= min_q d_q(v) + K with
K = 14, 15, 17, 18, 20 for r=1..5, exceeding n-1 by 5..7. Distance-T states
number 1, 2, 5, 1, 6; ten of fifteen have the label cycle exactly reversed.
The note's example is confirmed: d(u)=34 (their upper bound is tight), d(v)=43.
Cross-checks (independent BFS, rank checks, literal replay of extremal words):
0 failures. Finite results for m=9, r<=5; patterns are observations.

Addendum (2026-09-25, tables for the sort task): two further complete ranked
BFS tables, built with the unmodified `table_bfs.build_table` and verified by
an independent checker (sha256, layer sums, triangle consistency, literal
replay of shortest words; `autoresearch/outer-layer-260925/INDEPENDENT-CHECK.md`):
(10,3): 1,037,836,800 states, radius 71 = T_10(13), 4 states at the radius,
sha256 6deed7ea4ad9ea199a12877fe8c50485207f39d35814b9ff591d2a4fa505285f.
(9,6): 1,816,214,400 states, radius **79 < T_9(15) = 80**, 26 states at 79,
no state at 80, sha256 4f8cc2c236511a5f0fe3f7462c8a32180050132edca41ec567d4c892ddcee6dd.
This is the first computed case with m >= 8 where the visible sorting radius
is strictly below T_m(n); the earlier statement "all m>=8 values equal
T_m(n)" in the table above holds for the graphs listed there, not universally.
The reversal (0^6,9,...,1) and the reflection image (2,1,0^6,9,...,3) have
distance 73 at (9,6), not extremal. Tables live in `datasets/generated/`
(gitignored); hashes above identify them.

## Session 14: uniform sorting program for m=9, live campaign (2026-09-25)

Task: evolve `sort_word(v)` for m=9 with exact scoring against complete BFS
tables, 0.2 s CPU per state so state-space search cannot pass. Development
1500 states (r=1..5), holdout 2100 states including (9,6) and (10,3),
evaluated once; independent audit 0 disagreements
(`autoresearch/sort-m9-260925/REPORT.md`). Holdout within-budget counts:
naive 157, cyclic-sweep control 1846, sequential control 1918 (collapsed to
136/300 on the unseen r=6), EvoX 2053, AdaEvolve 2059, GEPA 2080 of 2100;
GEPA 290/300 on (9,6) and 295/300 on (10,3). Each within-budget word is an
exact certificate for its one state. No program meets T on all sampled
states; GEPA's best is a heuristic portfolio on the seed's construction with
no length bound. One seed per arm: descriptive, not an engine ranking. The
general conjecture is untouched.
Correlation rerun with fixed plumbing (2026-09-25, v3): still no certificate
beyond the worked examples m=4,5 in any arm; three campaigns now agree. The
negative is specific to LLM proposers on exact dual feasibility; the
mathematics from the deterministic LP work stands
(`autoresearch/corr-cert-260924/REPORT-CAMPAIGN.md`).

## Session 15: bounded-construction campaign, evolved certifiers transfer to m=11 (2026-09-25)

Task (`autoresearch/bound-m-260925/TASK.md`): a program certify(family) emits
words for the unit base of an m-label family (a,S); the evaluator recomputes
exact Lemma 1 lift costs, solves an exact LP, and certifies the family for all
positive block lengths iff weighted base < T_m(unit)+1 and all slopes <= m-2
(the group's criterion (7) with m as a parameter). Development: 303 families
at m=9,10; holdout evaluated once: 468 families including all 165 at m=11
(never seen by any engine). Model gemini-3.8-flash, 168 calls, $3.45.

Holdout certified (m=9/10/11 of 153/150/165) and worst gap at m=11:
EvoX 108/119/**129**, gap 4; GEPA 91/105/**125**, gap 4; sweep+LP control
76/84/98, gap 7; AdaEvolve 127/111/100 and sequential 124/114/109 with
invalid outputs at m=10,11 (bound broken off-distribution). Independent
audit (`integrations/bound_audit.py`, lrxm8 checker with M=m): 0
disagreements. Each certified family is a machine-checked theorem
d(v) <= T_m(n) for every block-length vector of that family, conditional on
the group's Lemma 1 and criterion (7).

New: two evolved, m-parametric constructions (no m-specific data) certify
125-129 of 165 unseen m=11 families with sound worst-case gap 4, against 98
for the best hand-written control. The constructions are bubble sorts on the
universal cover with new cursor routings and per-zero complementary word
selection (`BEST-GEPA-CONSTRUCTION.md`). Conjecture only: identity-rotation
families are certified at every m. No family class is proved for all m; the
general conjecture remains open. One seed per arm; no engine ranking.
Determinism caveat: the GEPA and EvoX finalists truncate a word union in
set order; audited certificates are unaffected, reproducibility is not yet.

## Session 16: bound-m campaign 2, three seeds, transfer to unseen m=12 (2026-09-25/26)

Campaign `autoresearch/bound-m-c2-260925/`: development m=9,10 (303 families),
validation = campaign-1 m=11 holdout (165, used only to pick each arm's
finalist), holdout evaluated once = 165 fresh m=12 families plus 60 fresh
m=11 families, all never seen by any engine. Seed program = campaign-1 EvoX
finalist. Four arms x three seeds, 30 iterations each, gemini-3.8-flash,
360 calls, about $7. Per-family word pool (development only) reported as a
secondary metric; selection standalone.

Holdout certified share, mean over seeds (SD): AdaEvolve 84.7 % (4.4),
EvoX 83.1 % (0.8), GEPA 80.3 % (0.5), sequential 76.4 % (6.9); seed 80.0 %;
sweep+LP control 59.6 %. Best single finalist: AdaEvolve seed 2 certifies
148 of 165 m=12 families and 54 of 60 fresh m=11 families; the control
certifies 95 and 39. Independent audit 0 disagreements; every finalist
deterministic under PYTHONHASHSEED=0; no m-specific literals. Each
certified family is a machine-checked bound d(v) <= T_12(n) for all block
lengths of that family, conditional on the group's Lemma 1 and criterion
(7) at general m. GEPA returned the seed unchanged in two of three seeds.
This is the first multi-seed result where evolved constructions beat both
the seed and the hand control on an m none of them saw. No family class is
proved for all m; the general conjecture remains open.

## Session 17: tree certificates (bound-eval-3), construction note, broker retry (2026-09-26)

Evaluator `integrations/bound3_*.py` (new files; `bound_evaluator.py` and
TRUSTED untouched) accepts a tree of box splits with leaves of words and
decides the group's criterion (8) per leaf by exact LP, re-checked by
`lrx_m.leaf_criterion`, plus a literal lift at sampled block lengths. Limits:
depth <= 6, <= 32 leaves, <= 32 words per leaf. A plain word list scores
byte-identically to bound-eval-2 (20 development families, every status,
gap and score equal). Audit `bound3_audit.py` reuses `lrxm8` through an exact
affine change of the m=8 criterion; it agrees with the evaluator on 411/411
stored campaign-2 rows and 24/24 new tree certificates.

Tree control (`bound3_control_revtree.py`, words taken from exact tables, so
not m-uniform): the m=9 reversal (9..1){0,4} is CERTIFIED with three leaves
(u0 in [1,2], [3,4], >= 5), where every campaign-2 arm had gap 15/7 or 9/5;
the m=8 analogue reproduces the group's 3-leaf tree; the m=10 tight family
{0,10} is CERTIFIED; the m=10 reversal {0,4} is not (gap 47/20: certified up
to u0 = 4, but u0 >= 5 needs origins above 2 and no (10, r>=4) table exists). Of the 43 development families AdaEvolve-s2 misses, the
tree control certifies 19 (16 at m=9, 3 at m=10; 8 rev_rot, 7 tight, 2 refl,
1 high_inv, 1 uniform). Nothing at m=11: no (11,r) table yet, so the limit is
word supply, not the certificate shape. Conditional on Lemma 1 with
refinement.

Construction note `bound-m-c2-260925/BEST-C2-CONSTRUCTION.md` (read-only):
AdaEvolve-s2 keeps the seed's routings and Lemma 1 price and adds lift
variants at every k (second window for even n, reversed tie-break in the
sum-0 normalization), rotated cursor start, two sweep modes, and a
hull/Frank-Wolfe word selection. It certifies 19 m=12 families the seed
misses and loses none; EvoX-s3 (variants only for k <= 4) gets 5 of those.
All arms miss the same 14 m=12 families, worst the plain reversal with two
zeros at gap 5. Observations only: identity rotations 23/23 and the easy
class 45/45 across m=9..12 in every arm.

Broker: bounded in-slot retry for 502/503/504 and 429 with Retry-After (3
tries, backoff 2/4/8 s, never after a partial stream), receipts record each
try; 4 mock tests. Suite 604 tests OK. No provider calls this session.
The (11,2) exact table (low-memory builder) is at layer 52 of about 75.

## Session 18: exact (11,2) table, reversal with two outer zeros has distance 74 (2026-09-26)

Complete ranked BFS of (m,r)=(11,2), n=13, 3,113,510,400 states, by the
low-memory builder (`tools/table_bfs_lowmem.py`, 4 workers, 3.2 h, table
sha256 `1c3f4915f4bea4e856d2eaed66f1c58caa4c7f43d896ae25e63475bc83192325`,
`datasets/generated/m11-260925/`, gitignored). Checks: layer sizes equal the
byte histogram, no unreached state, triangle inequality on 20,000 random
states under L, R, X, and literal replay of the extracted words.

Radius 75 = T_11(13). Exactly two states at 75: (0,0,11,10,...,1) and its
rotation (2,1,0,0,11,...,3); eight states at 74. The reversal with two outer
zeros, (0,11,10,...,1,0) (family 11..1 {0,11}, mask 2049), has exact
distance 74 = T-1; a shortest word is stored in
`autoresearch/bound-m-260925/checks/m11-r2-reversal-words.json`. So the
base-bound gap 4 recorded for that family in REVERSAL-OBSTACLE.md was a
limit of the word generators, not an obstruction: a unit-corner word of
length T-1 exists. The rotations of that state have distances
74,73,72,71,71,71,72,73,74,74,75,74,75. Family 5.4.3.2.1.11..6 {5,10} has
unit distance 64. The conjecture E_2(13) <= T_11(13) holds with equality.

## Session 19: reversal with two outer zeros, shortest words at m=8..11 and certificates to m=12 (2026-09-26)

Note `autoresearch/bound-m-260925/REVERSAL-WORDS.md`, script and words in
`checks/`. Exact (10,2) table built (409 s, low-memory builder, sha256
equal to an in-memory rebuild). Tables (8,2), (9,2), (10,2), (11,2) all
checked (histogram, no unreached, 20,000-sample triangle and predecessor).

Computed: the unit state (0,m,...,1,0) has distance exactly T_m(m+2) - 1 for
m = 4..11 (41, 51, 62, 74 at m = 8..11); numbers of shortest words 108,
132, 1104, 1296; every shortest word has floor((m+1)^2/4) - 1 swaps. The
radius of (m,2) equals T_m for m = 8..11 and is attained by exactly two
states, (0,0,m,...,1) and (2,1,0,0,m,...,3). Three stdlib generators of
words as pure functions of m: word_E(m) reproduces a shortest word at
m = 8..11 and sorts the state with T-1 letters for every m = 8..200 by
literal replay (upper bound only); word_A(m) (length T-1+floor((m-10)^2/2),
slopes (9,8) for all m) and word_B(m) (length T-1+floor((m-8)^2/2), slopes
(7,6); the W_m word of REVERSAL-OBSTACLE.md).

Certified, conditional on the group's Lemma 1 and criterion (7) at general
m, evaluator bound-eval-3 and the independent lrxm8-based audit agreeing
(orchestrator re-ran both): family (m..1){0,m} for all block lengths at
m = 9 (word_B), m = 10 (word_A and word_B with weights 1/2, 1/2), m = 11
(word_A alone, 74 letters, slopes (9,8)), m = 12 (word_A and word_E with
weights 6/7, 1/7). Not certified at m = 13..16 (gap 6/5 at m = 13, growing):
word_A's base overshoots T by about (m-10)^2/2 while every shortest word
has slope about 3m/2 > m-2, so no shortest word or mixture of shortest
words certifies at m >= 10. At m = 11 the stored lexicographically least
shortest word has slopes (15,14) and does not certify; word_A does.

Conjectures only: d((0,m,...,1,0)) = T_m(m+2) - 1 for all m; the (m,2)
radius equals T_m with exactly two extremal states for all m >= 8. What a
proof for this family needs from m = 13 on: an m-uniform word (or mixture)
with base <= T and slopes <= m-2 at once, which none of the three
generators provides.

## Session 20: m-uniform certificate for the reversal with two outer zeros, m = 9..40 (2026-09-26)

Note `autoresearch/bound-m-260925/REVERSAL-M13.md`, generator and words in
`checks/reversal_m13.py`, `checks/reversal-m13-words.json`. The "two-core"
word word_C(m, a), a pure stdlib function of (m, a): core 1 grows a zigzag
around the zero block carrying a labels across it (a label carried through
the zeros inside a sweep costs exactly 2 per zero, so the Lemma 1 slopes
are (2a+1, 2a)); core 2 is an in-place zigzag on the other m-a labels; a
final R walk ends the word. Closed forms verified by replay for m = 9..200
(worker) and m = 9..120 (orchestrator): length - T = 2(a-(m-2)/2)^2 - 1 -
(m mod 2)/2 for every a except a = 2 floor(m/2).

Certificate of the family (m..1){0,m} for all block lengths, root leaf,
unit origins, no tree: odd m, one word with a = (m-3)/2, length T-1, slopes
(m-2, m-3); even m, weights 1/2, 1/2 on a = (m-2)/2 (length T-1, slopes
(m-1, m-2)) and a = (m-4)/2 (length T+1, slopes (m-3, m-4)), averaging to
base T and slopes (m-2, m-3). CERTIFIED by bound-eval-3 and the independent
lrxm8-based audit at every m = 9..40 (worker 32 rows; orchestrator re-ran
all 32 with replay to the root), and by lrx_m.mixture_criterion. The LP
over the whole family a = 0..m at m = 9..20 selects exactly this support.
At m = 9..11 the T-1 words are members of the enumerated shortest sets.
Why the earlier generators failed: word_E carries zeros through labels at
cost 3 per crossing (slope about 3m/2); word_A lets only 4 labels cross
(base overshoot (m-10)^2/2).

This is the first m-uniform, closed-form certificate family in this
repository. Scope and conditionality: one family only; conditional on the
group's Lemma 1 and criterion (7) at general m; evaluator and audit ran to
m = 40, replay only beyond. Conjecture: the certificate holds for all
m >= 9 (a hand proof needs only the two closed forms above).

## Session 21: reversal orbit, 111 certified families and a second closed form (2026-09-26)

Note `autoresearch/bound-m-260925/REVERSAL-ORBIT.md`; words, trees and
search scripts in `checks/reversal_orbit.py`, `checks/reversal-orbit-words.json`,
`checks/reversal_orbit_search/`. Generic insertion-core generator
core_word(state, t, cores, fin) (two cores grown by partial carries, zeros
tied), full enumeration, Pareto front on (base, slopes), then the exact
leaf LP at the root or in a memoized tree search (depth <= 3, thresholds
<= 5, refined origins). The orchestrator re-ran every stored row through
bound-eval-3, the independent audit and literal replay: 111/111 agree.

- Second closed form: word_R1(m) = core_word(state, (m-3)//4, [(0, m//2,
  'l'), (m//2+1, None, 'r' if m%4==1 else 'l')], 'R') certifies the
  reversal with zeros in gaps {1,m} (the mask-4098 type, gap 3 in every
  campaign-2 arm) with one word of length T-2 (T when m = 2 mod 4) and
  slopes <= m-2; CERTIFIED and audited at m = 9..40 (orchestrator re-ran
  all 32), replay and criterion (7) to m = 200 (worker).
- Reversal with zeros in gaps {0,4}: CERTIFIED at m = 10..16 (two-leaf
  trees at m = 10, 11; root leaf at m = 12..16); not at m = 9.
- All two-zero masks of the reversal: m = 9 42/45, m = 10 53/55 certified.
  Misses: m = 9 {0,4}, {0,5}, {5,9}; m = 10 {0,5}, {0,6}. The m = 11..16
  survey was not run.
- Of the 14 m = 12 families every campaign-2 arm missed: 10 CERTIFIED
  (masks 4097, 4098, 2064, 4113, 1060 by a two-leaf tree, 1089, 4370,
  5252, 165, 4592); 130 (near_rev) and 7300 not certified; 6309 and 3534
  not completed (CPU). Of the m = 11 misses: 145 CERTIFIED; 1056 and 2456
  not; 3685 not completed.
- Every miss binds on the base, not the slopes: slopes <= m-2 are feasible
  at the root and the minimum base excess over T is 7/3, 4, 1 (m = 9),
  17/4, 4 (m = 10), 74/15 (mask 130), about 5.41 (7300), 2 (1056), 9/2
  (2456). The trees tried did not close them.
- Hand-proof sketch (REVERSAL-ORBIT.md section 4, labelled a sketch) of
  the word_C closed forms: len = (a^2+3a-1) + ((r-1)^2+r-2) + W0 +
  floor(a/2) with r = m-a and W0 = r/2+1 (r even), (r+3)/2 (a, r odd),
  (r+1)/2 (a even, r odd), giving len - T = 2(a-(m-2)/2)^2 - 1 - (m mod 2)/2
  for 1 <= a <= m-2; slopes (2a+1, 2a) from 2 per zero per carried label
  with cursor-crossing terms cancelling inside sweeps (exception a = 1, m
  even: (4,3)). Numerically checked m = 5..60.

Per-m rows other than word_C and word_R1 are search outputs, not formulas.
Conditional on the group's Lemma 1 and criteria (7)/(8) at general m.

## Session 22: k=2 reversal masks, closed form word_G for the outer band (2026-09-26)

Note `autoresearch/bound-m-260925/REVERSAL-K2.md`; words in
`checks/reversal-k2-words.json`, re-check script `checks/reversal_k2.py`
(evaluator, audit and replay on every row; orchestrator re-ran it: 390
word_G rows and 150 stored rows, no problems), searches in
`checks/reversal_k2_search/`.

- Closed form word_G(m, g), one two-core word with cut, seeds, sweep count
  and sides fixed by m mod 4 and by min(g, m-g), certifies the reversal
  (m..1) with zeros in gaps {0, g} whenever g <= floor(m/4) or m-g <=
  floor(m/4): 390 certificates at m = 9..40 (evaluator + audit + replay),
  1210 more at m = 41..80 by replay and criterion (7). Length between T-11
  and T, slopes <= m-2. The rules were read off the data, not derived.
- Middle band floor(m/4) < g < m - floor(m/4): no closed form; at
  m = 9..13 a root LP over the whole two-core pool fails where min(g, m-g)
  >= about m/2 - 2, always with slopes feasible and the base binding (the
  cheap words put nearly all slope on the gap-0 zero).
- Survey at the root, all k=2 masks: m = 11 59/66, m = 12 72/78, m = 13
  18/25 (only masks with a zero in gap 0 or 13 run). Every miss has one
  zero in gap 0 or gap m and the other near m/2; every mask with both
  zeros in gaps 1..m-1 certified at m = 11, 12.
- Misses: m = 9 {5,9} newly CERTIFIED by a 5-leaf tree. Still not found
  (trees to depth 4, thresholds 6, up to 11 origins): m = 9 {0,4} (base
  excess 9/4), {0,5} (4); m = 10 {0,5} (17/4), {0,6} (4); m = 12 mask 130
  (74/15); m = 11 mask 1056 (2). Not run: three-core words, rotated-cut
  sweeps, higher-k masks 7300, 2456, 6309, 3534, 3685, trees on the survey
  misses, m = 14.

Since the table-fed tree control (Session 17) certifies m = 9 {0,4} from
BFS words with origins (3,1) and (5,1), that miss is a word-generation
limit; the next step is to mine the (9,2), (10,2), (11,2) tables for the
structure of shortest refined-origin words in the middle band.

## Session 23: middle band mined from exact tables; first exact negative for a root leaf (2026-09-26)

Note `autoresearch/bound-m-260925/REVERSAL-MIDBAND.md`; data
`checks/reversal-midband-words.json`; re-check `checks/reversal_midband.py`
(orchestrator re-ran with `--tables`: 14 certificates CERTIFIED, audit ok,
replay ok, word_S re-derived letter by letter, exact negative reproduced,
no problems); searches in `checks/reversal_midband_search/`.

- Exact negative (computed; the first for a root leaf): for m = 9, zeros
  in gaps {0,4}, every sorting word of the unit base has B + 3 beta_0 >= 75
  (exact A* over all reduced words with Lemma 1 bookkeeping, heuristic from
  the stretched-zero tables (9,3)..(9,6), matched against brute force on 25
  small cases at m = 5, 6; 8760 nodes), while a certifying root mixture
  needs < 74. The exact optimum of the criterion (8) left side over all
  words is 2; witness word B = 54, slopes (7,7). No root-leaf certificate
  exists for that family; the tree with leaves u0 = 1 and u0 >= 2 (origin
  (2,1), exact optimum 4/5) certifies it. Table distances alone never
  refute a leaf (every distance is <= T(u)); the refutation needs the
  base-slope trade-off. Caveat: exactness rests on the oracle's
  completeness over reduced words.
- New m = 9 certificates: {0,5} at the root (length T-1, slopes (7,4)),
  {0,4} by the two-leaf tree, {0,3} and {0,6} at the root; so every k=2
  mask of the m = 9 reversal is now certified (with Sessions 21, 22).
- Exact data: unit distances of all band masks at m = 9, 10, 11 lie 7..11
  below T; every shortest word loads beta_0 = 9..16 on the gap-0 zero and
  nearly nothing on the other; along u1 the distance does not grow, along
  u0 it grows by 10 per zero at m = 9 {0,4} against 7 allowed; the state
  (0^4, 9..6, 0, 5..1) is at distance exactly T.
- Structure: certifying middle-band words split the crossings between
  the two zeros, i.e. two independent one-zero reversals on disjoint
  blocks; the two-core pool always loaded the gap-0 zero. Generator
  word_S(m, g, b, ds, schedule, fin) (schedules rr(lr)*, chosen per
  (m, g), so not a closed form) certifies at the root: m = 9 {0,5},{0,6};
  10 {0,6},{0,7}; 11 {0,7},{0,8}; 12 {0,7},{0,8}; 13 {0,8},{0,9}; nothing
  at m = 14..16 (gaps 1/10, 1, 2) because it walks the zero at 3 per
  crossing (beta_0 = 3b-2); the carry-across variant at 2 per crossing, as
  in word_C, was not written.
- Not certified: m = 10 {0,5} (leaves u0 in [1,2] and u0 >= 5 pass, u0 =
  3, 4 fail with every word tried; no (10,4) table); m = 11 {0,4},{0,5},
  {0,6}; m = 12 {0,5},{0,6}; m = 13 {0,5},{0,6},{0,7}; the whole band at
  m = 14..16. Base binds in every miss. Exact root and (2,1) optima at
  m = 10 unknown (1.5M-node cap); m = 9 origins (1,2), (2,2) hit the cap;
  picks first-atom only.
