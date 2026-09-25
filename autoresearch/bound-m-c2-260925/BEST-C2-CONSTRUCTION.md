# Campaign 2 finalists: the AdaEvolve-s2 and EvoX-s3 constructions

Date 2026-09-26. Read-only note. Sources read, not executed:
- `finalists/sources/adaevolve-s2.py`, sha256 `375f6f3fbb2b9a61...` (candidate-0020 of
  `live-adaevolve-s2-260925-215719`);
- `finalists/sources/evox-s3.py`, sha256 `fbaca00246f56c19...` (candidate-0016 of
  `live-evox-s3-260925-231622`);
- the seed `seed/evox-c1-seed.py` (the c1 EvoX finalist, described in
  `../bound-m-260925/BEST-GEPA-CONSTRUCTION.md` section 6).

Evidence: `finalists/REPORT.md`, `results.json`, `selection.json`, and the stored rows in
`finalists/{development,validation,holdout}-arms/*.json`. Development CPU times come from the
runs' own `verified/evaluations/result-*.json`. No provider call, no evaluator run and no
program execution was made for this note. Tallies were recounted from stored rows.

Lemma 1 and criterion (7) are the research group's (m=8 manuscript), used with m as a
parameter. The main conjecture stays open. A certificate proves a bound only for its own
family. Section 4 contains conjectures only.

## 1. The constructions

Both finalists keep the seed's frame unchanged. That frame is a lift (target rotation t, zero
routing perm), then a sweep on the universal cover, then the exact Lemma 1 `price`. `price` is
byte-identical to the seed's in both. Both docstrings are still the seed's and do not describe
the new code.

### 1.1 AdaEvolve-s2 (m=12: 148/165; m=11 fresh: 54/60)

**Lift.** Zero routings are the same as the seed's: all k! permutations for k <= 4, and the 2k
dihedral ones for k >= 5. Two lift variants are new.
- **Second window for even n.** The seed takes each displacement in
  [-floor(n/2), n-1-floor(n/2)]. A cell exactly opposite its target gets -n/2. For even n,
  AdaEvolve-s2 also builds the window shifted by one, where that cell gets +n/2. This is the
  choice of which way round the ring an antipodal token travels. Reversal-type orders have
  many antipodal tokens.
- **Reversed tie-break in the sum-0 normalization.** When sum rho = q n with q != 0, the |q|
  most extreme cells are moved by n. The seed breaks equal-rho ties by lowest position. The
  finalist also tries highest position first. These are distinct lifts with different A_j.

A lift can therefore yield up to 4 displacement vectors, against 1 in the seed.

**Cursor.** Six sweep modes instead of four, and two start positions.
- L, R, greedy and greedy_R are unchanged.
- **bounce_L and bounce_R** (new). The cursor steps one way and swaps every must-cross pair
  it meets. After n-1 steps it reverses. This is a boustrophedon sweep. Its pass term p_j sits
  between the one-way sweeps and greedy.
- **Pre-rotated start** (new). For t != 0 the cursor is first rotated to cell t by the short
  way, and then the sweep starts there. This moves where passes over each zero happen,
  and so changes p_j, while q and A_j stay those of the lift.

Pool size at (m, k) = (10, 11) is 3960 to 4178 words. EvoX-s3 has about 1811 there.

**Selection.** This is a new geometric picker over the cost vectors
c = (B - T, beta_0 - s, ..., beta_{k-1} - s). The union of four sources is kept:
1. For each zero j, the lower convex hull of the words in the (B - T, beta_j - s) plane,
   built with Andrew's monotone chain.
2. For each j, minimizers of (B - T) + r (beta_j - s) over 7 rays, r in {0.1, 0.25, 0.5, 1,
   2, 4, 10}.
3. Four softmax Frank-Wolfe runs: temperatures 1.5 and 3, started from the min-max word and
   from the min-B word, each 39 steps. Every chosen word is kept, and the weights are
   discarded.
4. The coordinate minimizers.

The union is **sorted** by (max violation, B - T, sum) and the first 32 are kept. If fewer
than 32 remain, it fills up by max violation. The seed's multi-start loops and random
scalarizations are gone. A set of coordinate minimizers is still built at the top of
`certify` and then never used, so it is dead code.

### 1.2 EvoX-s3 (m=12: 137/165; m=11 fresh: 52/60)

**Lift.** The routings are the seed's. Two lift variants are added, both gated on k.
- **Window offset off in {-1, 0, +1}.** The midpoint becomes floor(n/2) + off. That flips the
  antipodal choice, like AdaEvolve's second window, but it applies to odd n too.
- **Reversed tie-break**, as in AdaEvolve.
- The configurations are `(-1,F), (0,F), (0,T), (1,F)` for k <= 3, and `(-1,F), (0,F), (1,F)`
  for k = 4. For **k >= 5 there is only the seed's lift.**

**Cursor.** The seed's four modes, plus **scan_L and scan_R**. The cursor steps one way. When
no must-cross pair lies within n/2 cells ahead, it reverses. This is an elevator sweep. It
turns early where bounce would run the full n-1 steps.

**Selection.** The result is an ordered list with first-come priority, cut at 32.
1. Three LogSumExp Frank-Wolfe runs, eta in {4, 10, 25}, 74 steps each. The base coordinate
   is shifted by 0.95 so it aims at B < T + 1. The support of the best-valued iterate is kept.
2. The coordinate minimizers.
3. Ten explicit complementary pairs. Candidates are the top 6 per coordinate plus the 10
   lowest by max violation. Pairs are ranked by the max violation of their midpoint.
4. Forty seeded scalarizations (random.Random(42)).
5. Fill-ups by max violation, then by B.

### 1.3 Diff against the seed, and what raised m=12 from 129 to 148

| component | seed (c1 EvoX) | EvoX-s3 | AdaEvolve-s2 |
|---|---|---|---|
| zero routing | k! (k<=4), dihedral (k>=5) | same | same |
| antipodal window | one | off in {-1,0,1}, k<=4 only | second window, even n, all k |
| q-normalization tie | lowest position | both, k<=3 only | both, all k |
| cursor start | 0 | 0 | 0 and t |
| sweep modes | L, R, greedy, greedy_R | + scan_L, scan_R | + bounce_L, bounce_R |
| selection | FW loops, scalarizations, `list(set)[:32]` | LSE-FW support, pairs, ordered list | hulls, rays, softmax FW, sorted cut |

**AdaEvolve-s2 against the seed at m=12: 19 gained and 0 lost.**

| class | gained |
|---|---|
| rev_rot | 8 |
| refl | 5 |
| near_rev | 5 |
| high_inv | 1 |

The gains fall at k = 3 to 10, and the largest are at k = 7 (+5) and k = 8 (+4). For
k >= 5, EvoX-s3 lifts only as the seed does. AdaEvolve-s2 keeps its lift variants, cursor
starts and bounce modes at every k. That fits EvoX-s3 winning only 5 of these 19.

The gains include odd n, where AdaEvolve's second window never fires, for example k = 7 at
m = 12. So the tie-break lifts, the pre-rotated cursor and bounce must carry part of the gain.
The split between pool and selection was not measured. Separating them would need an ablation
run, which was not authorized here.

## 2. Holdout coverage per order class

Certified out of N, from the stored rows. Control (b) is `sweeplp-b`, the sweep pool with the
exact LP.

| class | N m=12 | Ada-s2 | EvoX-s3 | seed | (b) | N m=11 | Ada-s2 | EvoX-s3 | seed | (b) |
|---|---|---|---|---|---|---|---|---|---|---|
| rev_rot | 44 | 36 | 31 | 28 | 11 | 16 | 14 | 14 | 14 | 10 |
| refl | 22 | 20 | 16 | 15 | 12 | 8 | 5 | 5 | 5 | 2 |
| near_rev | 33 | 27 | 25 | 22 | 9 | 12 | 12 | 10 | 9 | 5 |
| high_inv | 33 | 33 | 32 | 32 | 31 | 12 | 11 | 11 | 11 | 10 |
| uniform | 22 | 21 | 22 | 21 | 21 | 8 | 8 | 8 | 8 | 8 |
| easy | 11 | 11 | 11 | 11 | 11 | 4 | 4 | 4 | 4 | 4 |
| **total** | 165 | **148** | **137** | **129** | **95** | 60 | **54** | **52** | **51** | **39** |

| worst gap W | Ada-s2 | EvoX-s3 | seed | (b) |
|---|---|---|---|---|
| m=12 | 5 | 5 | 5 | 28/5 |
| m=11 | 3 | 18/5 | 4 | 11/2 |

BOUNDARY counts at m=12 are 0, 1, 0 and 2. At m=11 they are 2, 1, 0 and 0.

**Missed by all four at m=12: 14 families.** Eight are rev_rot, four near_rev and two refl.
Each is the reversal orbit or a one-transposition perturbation of it. The worst gaps, shown as
Ada-s2 / EvoX-s3 / seed / (b):

| family | k | gaps |
|---|---|---|
| 12..1, mask 4097 (gaps 0 and 12) | 2 | 5 / 5 / 5 / 5 |
| 2.1.12..3, mask 1060 | 3 | 4 / 5 / 5 / 5 |
| 12..1, mask 4098 | 2 | 3 / 3 / 3 / 3 |
| near_rev 1.12.10.11.9..2, mask 130 | 2 | 25/11 / 25/11 / 7/3 / 7/3 |
| near_rev 12..4.2.3.1, mask 165 | 4 | 5/3 / 1 / 17/7 / 59/16 |

The worst family is the m=12 analogue of c1's m=11 worst: the plain reversal with k=2 and the
two zeros cyclically adjacent. It stays at a gap of exactly 5 in every arm.

Three more m=12 misses of AdaEvolve-s2 are certified by EvoX-s3:
- 7.5.4.3.2.1.12.11.10.9.8.6, mask 1090;
- 7.6.5.4.3.1.2.12.11.10.9.8, mask 2254;
- the uniform family 5.4.8.1.2.9.6.7.10.11.3.12, mask 7471.

**Certified by AdaEvolve-s2 and missed by the seed, m=12 (19).** The seed's gap is in
brackets.
- **rev_rot.** Masks 522 (2/17), 5377 (2), 2513 (149/409), 6981 (27/106), 5970 (1/2),
  4319 (2295/6589), 5342 (173/848) and 831 (20/431).
- **refl.** Masks 5834 (9/446), 7338 (15/23), 2997 (23/66), 1279 (1057/1718) and
  8147 (51/373).
- **near_rev.** Masks 7488 (1/4), 715 (9/62), 5466 (45/278), 5847 (2/25) and 2031 (128/407).
- **high_inv.** 12.9.7.8.10.6.4.5.11.3.1.2, mask 69 (12/67).

The largest recovered seed gap is 2, on 12..1 with mask 5377 and k=4.

At fresh m=11, AdaEvolve-s2 gains 3 over the seed, all near_rev: masks 130, 1386 and 1899. It
loses none. Six m=11 families are missed by all four: three refl, two rev_rot and one high_inv.
Two of them are BOUNDARY, with gap 0, for AdaEvolve-s2.

## 3. Uniformity, largest k, CPU

- **No m-specific tuning.** The finalize m-literal screen found nothing for either finalist.
  On reading, m, k, T and s are all derived from v. The constants are search knobs: 32 kept
  words, the 7 ray ratios, temperatures, step counts, top-N cut-offs and the 0.95 offset.
- **Mild k-gating.** Both use all k! routings for k <= 4. EvoX-s3 also gates its lift variants
  to k <= 4, which is k-specific, not m-specific. AdaEvolve-s2 has no k-gate beyond the
  seed's.
- **Largest k.** Both run up to k = 12: n = 24 at m = 12, and all gaps open at m = 11.
  AdaEvolve-s2 certifies 15 of 15 at m=12 for each of k = 7, 10, 11 and 12. At k = 2 it
  certifies 11 of 15. k = 13 at m = 12 was not drawn.
- **CPU.** The holdout rows do not store per-family CPU; finalize strips the `run` field. The
  evaluator enforced 3 s CPU plus 0.1 s tolerance and 5 s wall per family. The result was 0
  timeouts and 0 INCOMPLETE across all 225 holdout families for both finalists. So every m=12
  family finished under the limit, but the margin at m=12 is not recorded.

| finalist | worst development CPU | at (m, k) | total over 303 |
|---|---|---|---|
| AdaEvolve-s2 | 1.49 s | (10, 11) | 137 s |
| EvoX-s3 | 1.05 s | (10, 11) | 105 s |

AdaEvolve-s2 is the one closer to the limit, because its pool is about twice as large.

## 4. Conjectures (evidence counts only; not theorems)

**CONJECTURE A' (identity rotations, all k).** For m >= 9, a a cyclic rotation of 1..m and
any mask S, the lift-and-sweep pool contains words whose exact mixture meets criterion (7).
- **Evidence in these records.** 23 of 23 identity-rotation families are certified, in every
  arm including control (b):

  | m | 9 | 10 | 11 | 12 |
  |---|---|---|---|---|
  | certified / N | 4/4 | 6/6 | 8/8 | 5/5 |

  The m=11 count covers validation plus fresh holdout.
- **Earlier evidence.** The c1 holdout adds 11 more at m = 9 and 10, which gives 34 of 34 in
  total.
- **Scale.** The sample is small next to 12 x (2^13 - 1) families at m = 12.

**CONJECTURE E (easy class).** The same holds for the "easy" low-inversion class, which
contains the identity rotations.
- AdaEvolve-s2 certifies 45 of 45 across m = 9..12, and so does EvoX-s3: 9/9, 10/10, 15/15
  and 11/11.
- The seed and (b) each miss one family at m = 9.
- This is engine-dependent, so it is weaker than A'.

**Not fully certified.**
- uniform: AdaEvolve-s2 misses one at m = 9 and one at m = 12.
- high_inv: it misses one each at m = 9, 10 and 11.
- The reversal orbit and near_rev are far from full coverage.

**What a human proof of A' would need.** A' is the easiest class, since plain control (b)
already closes it. In every (b) certificate the base has large slack below T+1. At m=12 k=4
the base is 22 against T = 108. The slopes are pinned at exactly m-2 by 1 to 4 support words.
So the difficulty is purely the per-zero slope. A proof would need four things:
1. **Arcs.** Write the mask as k arcs of lengths l_0..l_{k-1} between consecutive zeros, with
   the arcs summing to m.
2. **Explicit words.** Give lifts with explicit routing, for example greedy, and closed forms
   for A_j and p_j in terms of the arcs and t.
3. **Explicit weights.** Give weights, as functions of the arcs, with every mixed
   2 Abar_j + pbar_j <= m-2. The base only needs the crude bound B <= q + (q+1) floor(n/2)
   against T+1.
4. **Every composition.** Cover every composition of m, for every k from 1 to m+1.

The hard sub-case is k = 2 with two long arcs. There one word loads about 2 min(l, m-l) on one
zero, and a mirrored pair must average it down. The proof also rests on the group's Lemma 1,
and on (7) with m as a parameter, which is not confirmed by the group for m != 8.

## 5. Determinism and the 32-word cap

- **Both finalists passed the check.** `determinism_check` passed for both: `deterministic:
  true` with no mismatches in `results.json`. The check evaluated the first 20 development
  screen families (m = 9 and 10) twice, each time in two fresh sandboxed processes, and
  compared the raw output words. It was not repeated on m = 11 or 12.
- **The evaluator now fixes the hash seed.** The worker launch fixes PYTHONHASHSEED=0, in
  `integrations/bound_evaluator.py`.
- **The finalists no longer depend on set iteration order.**
  - AdaEvolve-s2 collects integer indices and sorts them by a total key before cutting at 32.
    Integer hashing is not randomized.
  - EvoX-s3 builds an insertion-ordered list and cuts it at 32. The seed's `list(set)[:32]`
    over strings is gone.
  - The seed's docstring text still describes the old truncation.
- **The cap is always active.** Both finalists return exactly 32 words in all 225 holdout
  families.
- **Validity does not depend on selection.** A certificate's validity never depends on which
  words were kept. The evaluator re-derives the mixture from the words, and the independent
  audit reports 0 disagreements for both finalists.
