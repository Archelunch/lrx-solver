# GEPA arm best program: the construction in mathematical terms

Date 2026-09-25. Subject: `live-gepa-260925-182207/verified/best.py`, sha256
`7d55f269bbf1c5ff73582ff30e9dfb394c06618bbba2758d498ed5da2e27be87` (identical to `output/best.py`).
Evidence: the two full development records `verified/evaluations/result-0662.json` (fresh) and
`result-0663.json` (cache hit, same content), the development controls in `controls/`, and a
read of the source. The generated program was **not executed** for this note. The only code run
was trusted repository code (`integrations/bound_control_sweep.pool`, `lrx_m.base_vector`) over
development families, to test pool membership. No holdout data was read.

Lemma 1, formulas (4)-(5) and criterion (7) are the research group's (m=8 manuscript). They are
used here with m as a parameter, as in TASK.md. The main conjecture stays open. Everything in
section 4 labeled CONJECTURE is a conjecture.

## 0. Headline numbers (development, 303 families; from the records)

| program | certified | boundary | worst gap W (m=9 / m=10) |
|---|---|---|---|
| seed (b16), `bound_control_sweep` | 111 | 1 | 8 / 17/4 |
| control (b), sweep pool + exact LP | 151 | 2 | 4 / 3 |
| GEPA best | 204 | 2 | 11/4 / 8/5 |

Correction to the brief: "151 and worst gap 4" is control (b), not the seed. The seed (b16) is
111 and 8. The GEPA program beats both. It gains 94 families over the seed and loses 1. It gains
57 over (b) and loses 4 (listed in section 5).

## 1. The construction

Input: a family (a,S) with unit base v, n = m+k, T = m(m+1)/2 + (k-1)(m-2), s = m-2. All of
m, k, T, s are read off v.

### 1.1 Lifts (which permutation is realized)

A lift is a pair lambda = (t, sigma):
- t in Z_n is the target rotation. Label v goes to cell t+v-1. The zero slots are t+m, ..., t+n-1.
- sigma is a cyclic shift in Z_k. It assigns the i-th zero of v (in cell order) to slot
  t+m+(i+sigma mod k). Zeros are interchangeable, so this is a choice of zero routing.

Each cell p gets a displacement rho_p on the universal cover (the ring Z_n unrolled to Z). It is the
representative of target(p) - p in [-floor(n/2), n-1-floor(n/2)]. Then the displacements are
shifted by multiples of n until sum rho = 0: the |q| cells with the most extreme rho are moved by
n toward the middle. A lift fixes which pairs of tokens must cross: pair (x,y) with x before y
crosses exactly when rho_x - rho_y >= (distance) along the sweep. Two zeros never swap; when two
zeros "cross" they exchange displacements for free.

So each lift fixes two integer invariants:
- q_LL(lambda): the label-label crossings;
- A_j(lambda): the labels whose path crosses zero j.

The key trade-off lives here. The target rotation t decides how the cyclic shift of the labels
relative to each zero is paid. It can be paid with label-label swaps (base only) or with
label-zero swaps (2 per swap on beta_j). Example: a zero in the middle gap of an identity
rotation needs either about g(m-g) label-label swaps and A_j = 0, or A_j = min(g, m-g).

The program also has a parameter `bias` in {0, 1}. With bias 1 the lift is algebraically
the lift for t+1, but the final alignment still targets t. The final vector is then off by one
cell, and `price` rejects the word. **bias = 1 contributes no words.** This is dead code, derived by
hand.

### 1.2 Sweeps (how the cursor is routed)

Given rho, the word is a bubble sort on the cover. The cursor sits at c. An adjacent pair (c, c+1)
"must cross" when rho_c - rho_{c+1} >= 2. Crossing swaps the tokens with X (unless both are
zeros) and updates the displacements to (rho_{c+1}+1, rho_c-1). The sweep stops when all rho are 0.
Then one rotation of length min(d, n-d) aligns the cursor to t. Free cancellations
LR, RL and XX are removed. There are five modes:
- **L**: the cursor always moves one step right (letter L) and swaps whenever it can.
- **R**: the same, moving left.
- **greedy** (seed): jump to the nearest must-cross pair, and break a distance tie toward L.
- **greedy_rev** (new): the same, and break the tie toward R.
- **min_cost** (new): R-first. When a must-cross pair exists at the same distance on both sides,
  it goes to the side whose pair has fewer zero cells. This makes it greedy_rev plus a tie-break
  that avoids zeros.

The pool is every (t, sigma, mode). That is at most 5nk valid words, the 2x from bias being
void. Each word is priced by the exact Lemma 1 profile, which is a copy of the seed's `price`.

### 1.3 Selection (how it chooses among the words)

- **One word certifies.** If some word has B < T+1 and every beta_j <= s, only that word is
  returned. This happens in 63 of the 204 certificates.
- **Otherwise it returns a union of heuristic picks, at most 32 words.** The evaluator's exact
  LP finds the mixture. The picks are:
  - the support of a float Frank-Wolfe-like loop. It runs 99 steps, each adding the word that
    minimizes beta at the currently worst coordinate j, with a penalty of 5 times the base
    excess. This is not an LP, and its weights are discarded;
  - for each j, the 3 lowest-beta_j words, plus the 2 lowest-beta_j words among those with
    B <= T+1;
  - the 10 lowest by max_j beta_j, and the 6 lowest by B;
  - pairs from the top 24 by max slope, ranked by max_j(beta1_j + beta2_j);
  - fill-ups by sum beta, then by max beta.
- **Truncation.** The union is cut with `list(set)[:32]`, in set iteration order. String hashing is
  randomized per process, and the worker environment does not set PYTHONHASHSEED. So the
  returned set is nondeterministic whenever the union exceeds 32. Finalize confirmed this: the
  same source certified 204 development families in the campaign and 201 in finalize (see
  section 9). A certificate stays valid because the evaluator checks the words themselves, but
  a rerun can change the score.

### 1.4 The Lemma 1 cost of each word type

For a word from lift lambda and mode mu:

    B = q_LL(lambda) + sum_j A_j(lambda) + sum_s |d_s|
    beta_j = 2 A_j(lambda) + p_j(lambda, mu)

Here d_s is the net cursor travel between consecutive X letters, including the final
alignment. p_j = sum_s |cz_{s,j}| counts the net passes of the cursor over zero j within
segments, plus the macro boundary terms.

The crossing part (q and A) depends on the lift only. **The mode changes only the travel term
in B and the pass term p_j.** For each mode:
- **L and R.** Travel is monotone, so every segment has one sign and same_sign holds. p_j is the
  number of full sweeps that pass zero j. That is roughly the largest remaining displacement,
  up to about n/2 for reversal-type orders. This is why the L and R words have large slopes.
- **greedy, greedy_rev and min_cost.** Each segment is one monotone jump of at most floor(n/2)
  steps, so p_j <= 1 per segment. The three modes differ in which of two equally near pairs they
  take first. That changes the later jumps, and so which zeros get passed. min_cost prefers
  pairs that are not zero-label pairs. That postpones zero crossings, but it does not change
  A_j.

The per-word bounds that follow from this structure are loose:
- B <= q + (q+1) floor(n/2);
- beta_j <= 2 A_j + (number of segments whose jump or final alignment spans zero j).

## 2. What changed relative to the seed, and why it helped

1. **The pool is larger, by two cursor-routing modes.** greedy_rev and min_cost add new words,
   while the lifts, and so q and A_j, stay the same. Their pass vectors p are different and
   often mirrored. Of the 204 certificates, 145 have at least one support word that is outside
   the seed pool (checked with trusted `bound_control_sweep.pool`). That covers 38 of 46
   rev_rot, 34 of 37 near_rev and 12 of 18 refl certificates. The new words carry the gain.
   Control (b) runs an exact LP over the seed pool and still certifies 57 fewer families, so a
   better selection from the old pool would not explain the gain.
2. **The selection is complementary rather than a single ranking.** The seed kept the 16 words
   with the lowest (max beta, B). That keeps words that are all bad on the same zero. The new
   picks keep, for each zero j, the words best on that zero. Mixtures can then average a "tent"
   profile of A_j and p_j with its mirror. Example: m9 reversal with k = 10, where the two
   support words have A = (2,1,2,3,4,4,3,2,1,2) and (4,5,3,2,1,0,1,2,3,4).
3. **A single-word shortcut and 32 words instead of 16.**

The worst gap fell from 4 (control b) and 8 (seed) to 11/4. The worst family under the seed,
reversal m9 with k = 10, went from 8 to 12/7. The new worst is a tight k = 2 family (section 5).

## 3. Uniformity in m

The program has no m-specific data. m = max(v), k = len(v) - m, and T and s follow the
TASK.md formulas. The numeric constants are search knobs, and none of them are tables:
- 32 kept words;
- 99 heuristic steps;
- top-3, 2, 10, 6 and 24 cut-offs;
- penalty weights 5.0, 0.9 and 0.1.

**This extends to m = 11 as it stands:**
- the lift and sweep pool and the Lemma 1 pricing;
- the single-word test;
- the per-coordinate picks.

The CPU cost is also safe. The worst recorded per-family CPU was 0.27 s at (m, k) = (10, 11),
against 3 s. Extrapolating to (11, 12) gives well under 3 s.

**This might not extend:**
1. **Fixed cut-offs.** The 32-word cap and the fixed top-N picks do not grow with k. At m = 11
   and k = 12, the per-coordinate picks alone can reach 5k = 60 words. The hash-order
   truncation then drops an arbitrary part of the union, so results may vary between runs and
   between m.
2. **Reversal-orbit gaps grow with m.** The per-word crossing load A_j is about half the labels
   near the middle of the reversal. Section 4 explains why that meets m-2 only by averaging.
   Whether 32 words suffice at m = 11 is unknown.
3. **m = 11 has never been evaluated.** The holdout was not run, and it must not be run here.

## 4. Bounds and class coverage

### 4.1 Hand bound on slopes

Let lambda be any lift. Then beta_j(W) >= 2 A_j(lambda) for every word W on lambda, and a mixture
satisfies betabar_j >= 2 Abar_j.

Suppose zero j sits in a gap where the cyclic label order read from the zero is not 1..m. Then
some label-zero crossings are needed, unless label-label swaps pay for the whole rotation, which
costs base. So certification requires Abar_j <= (m-2)/2 - pbar_j/2 for all j, at base
Bbar < T+1. The base headroom over m(m+1)/2 is (k-1)(m-2). That headroom is what lets lifts
replace label-zero crossings (slope) with label-label crossings (base).

No m-uniform closed-form upper bound on B or on beta_j follows from the code. The construction is
a search over lifts. The only clean per-word statements are the ones in 1.4.

### 4.2 Coverage by order class

The development records were re-tallied, not re-run. Cyclic classes were merged: refl
(2,1,m,...,3) is the reversal rotated by 2, so refl and rev_rot are the same cyclic orbit. 6 of
the 7 m = 9 tight families also lie in that orbit.

| class | m=9 cert/N | m=10 cert/N | worst gap |
|---|---|---|---|
| identity rotations | 4/4 | 6/6 | 0 |
| easy (other low-inversion orders) | 4/5 | 4/4 | 149/286 |
| uniform | 20/24 | 20/20 | 11/20 |
| high_inv | 19/23 | 26/29 | 7/15 |
| near_rev | 18/27 | 19/30 | 3/2 |
| reversal orbit (rev_rot, refl, tight) | 26/69 | 38/61 | 11/4 |
| tight, not in the orbit (217986543, {2,3}) | 0/1 | - | 16/19 |

**The program certifies:** almost all identity-like, easy, uniform and high_inv families.

**The program misses:** about half of the reversal orbit and a third of near_rev, including every
tight family.

### 4.3 CONJECTURE (not a theorem)

**CONJECTURE A (identity orbit).** Let m >= 9, and let a be a cyclic rotation of the identity. Let S
be any mask. Then the pool of sections 1.1 and 1.2 contains words whose exact mixture has
Bbar < T_m(m+k) + 1 and betabar_j <= m-2.

The evidence is 10 of 10 development families (m = 9 and 10) and the mechanism in 4.1:
- the label order is already cyclically sorted, so a lift can route each zero around the
  shorter side or pay with label-label swaps inside the base headroom;
- control (b) also certifies all identity and id_rot families in the SPEC probes at m = 9, 10
  and 11 (SPEC section 4, probe 3).

The sample is small, and no argument covers all S.

**Not conjectured.** No analogous statement is plausible for the reversal orbit from this
construction. At m = 9, 43 of 69 families are not certified, and the gap does not shrink
toward larger k. The tight families may be (7)-infeasible for every word set (SPEC section 3.7).

## 5. The five families with the largest remaining gap

All five are NO_CERTIFICATE. Each has a single binding zero, and its slope decomposes as
2 Abar_j + pbar_j at the gap-LP optimum, with Bbar pinned at exactly T+1.

| family (m, labels, gaps) | class | gap | Bbar vs T+1 | binding zero | 2 Abar + pbar | why |
|---|---|---|---|---|---|---|
| 9, 219876543, {2,6} | tight | 11/4 | 53 = 53 | gap 2 | 29/4 + 5/2 | The lifts with A_0 small have A_1 large: A = (4,0) versus (3,5). The zero in gap 2 sits at the reversal's cut, and the base is pinned. The best single-word beta_0 is 6, but those words exceed the base or the slope on the other zero. |
| 9, 987654321, {0,4} | tight (reversal) | 15/7 | 53 = 53 | gap 0 | 6 + 22/7 | A_0 = 3 on both support words, and the passes over the leading block are 1 and 4. The leading block is crossed by the final alignment rotation. |
| 9, 543219876, {0,5} | tight | 21/11 | 53 = 53 | gap 5 | 8 + 10/11 | A_1 = 4 on every support word, and 2A = 8 already exceeds s = 7. No lift in the pool routes fewer than 3 labels over that zero within base. |
| 9, 432198765, {4,8} | tight | 13/7 | 53 = 53 | gap 4 | 50/7 + 12/7 | This is the same pattern as the first family: A = (4,0) versus (3,4). |
| 9, 987654321, {0..9} (k=10) | reversal | 12/7 | 768/7 < 109 | gaps 0 and 4 | 40/7 + 16/7 | The two support words have mirrored tent profiles, and the ends (gap 0) and the middle stay above 7. The base has slack, so the pool, not the base, is the limit. This was the seed's worst family (8). |

Next is m10 2.1.10.9.8.7.6.5.4.3 with gaps {2,3,4,6,8}, at 8/5.

**Selection losses.** Four families are certified by control (b) and missed here:
- m9 321987564 {mask 927}, gap 17/88;
- m10 8.6.5.4.3.2.1.10.9.7 {1136}, gap 1/8, also certified by the seed;
- m10 7.6.5.4.3.2.1.10.9.8 {1589}, gap 269/3492;
- m10 9.8.10.7.6.4.3.5.1.2 {1023}, gap 751/3637.

All four are small gaps with the base pinned. Their words are in the pool, since its old modes
include the seed's, but the heuristic selection or the 32-cap truncation dropped them. Exact LP
support selection (the (b) mechanism) over the enlarged pool would recover them, and would
certify at least 208 of 303. That is inferred from the pool inclusion and was not run.

## 6. The EvoX finalist, and how it differs from GEPA's

This section was added after finalize. The sources are `finalists/`: REPORT.md,
holdout-results.json, audit.json and manifest.json. Nothing was re-run. The EvoX source is
`finalists/sources/evox.py`, sha256
`1031149e48768fd67907350b9f7fc1ef207a7eb33533fedbdb1466d2618d2e9a`. It was read and not
executed. Its docstring is still the seed's, and it does not describe the program.

EvoX uses the same framework as sections 1.1 to 1.4: lift, then sweep on the universal cover,
then the exact Lemma 1 price. It differs from GEPA in three ways.
1. **Richer zero routing (the lift).** The zeros are assigned to slots by any permutation pi,
   not only by a cyclic shift:
   - for k <= 4, all k! permutations;
   - for k >= 5, the 2k dihedral ones (cyclic shifts and reversed cyclic shifts).

   The zeros are interchangeable, so pi changes which zero travels where on the cover. That
   changes the A_j vector and so the per-zero slope loads, and it keeps the label-label part.
   GEPA only has the k cyclic shifts. For k = 2 the two programs coincide. For k = 3 and 4,
   EvoX sees up to 6 and 24 routings per t, against GEPA's 3 and 4.
2. **Fewer cursor modes.** EvoX uses L, R, greedy and greedy_R. greedy_R is GEPA's greedy_rev.
   EvoX has no min_cost and no dead bias loop.
3. **Selection by a vector cost.** Each word gets the cost vector
   c = (B - T, beta_0 - s, ..., beta_{k-1} - s). The picks are:
   - the best word on each coordinate;
   - multi-start Frank-Wolfe-like loops from k+2 starts, 49 steps each. Each step adds the best
     word on the currently worst coordinate, with slopes up-weighted by 1.15;
   - 30 random scalarizations with a seeded RNG (seed 42);
   - fill-ups by max violation, then by B.

   There is no single-word shortcut. The same `list(set)[:32]` truncation applies. At m = 11
   EvoX returned exactly 32 words in all 165 families, so the truncation was always active.
   GEPA returned 32 words in 133 of them.

**Why it generalized better (inference, not tested).** The binding constraint on reversal-orbit
families is the per-zero crossing load A_j (section 4.1). Permuting the zero-to-slot assignment
changes A_j directly. A new cursor mode changes only the pass term p_j. EvoX's gains are in the
rev_rot class (see section 7).

## 7. Holdout coverage (evaluated once, from holdout-results.json)

Certified out of N. Control (b) is the sweep pool with an exact LP.

| m=11 class | N | EvoX | GEPA | (b) |
|---|---|---|---|---|
| rev_rot | 44 | 28 | 26 | 15 |
| refl (the reversal orbit rotated by 2) | 22 | 12 | 12 | 6 |
| near_rev | 33 | 25 | 23 | 14 |
| high_inv | 33 | 32 | 32 | 31 |
| uniform | 22 | 21 | 21 | 21 |
| easy | 11 | 11 | 11 | 11 |
| **total** | 165 | **129** | **125** | **98** |

The worst gap at m = 11 is 4 for EvoX and GEPA, and 7 for (b).

The pattern is the same at m = 9 and 10. The per-class totals are EvoX 108 and 119, GEPA 91 and
105, and (b) 76 and 84. The reversal orbit and near_rev carry all the separation.

**Families EvoX or GEPA certify and (b) misses at m = 11: 37.** (b) certifies nothing that both
engines miss. EvoX certifies 10 that GEPA misses, and GEPA certifies 6 that EvoX misses.
Examples:
- rev_rot: 10.9.8.7.6.5.4.3.2.1.11 {mask 2569, k=4}, where (b)'s gap is 1/7;
- rev_rot: 1.11.10.9.8.7.6.5.4.3.2 {62, k=5}, where (b)'s gap is 2/3;
- refl: 5.4.3.2.1.11.10.9.8.7.6 {1604, k=4}, certified by GEPA only;
- near_rev: 5.6.4.3.2.1.11.10.9.8.7 {2225, k=5}.

**Families all three miss at m = 11: 30.** They are 28 reversal-orbit or near_rev families, 1 high_inv
family and 1 uniform family:
- near_rev: 7;
- reflection rotations: 8;
- reversal rotations: 13;
- high_inv: 11.8.9.10.3.7.4.5.2.6.1 {57};
- uniform: 9.7.4.11.10.6.2.8.1.5.3 {2464}.

The worst family for all three arms is the plain reversal 11..1 with mask 2049, where k=2 and
the zeros sit in gaps 0 and 11. The gap is exactly 4 in every arm. The two zero blocks are
cyclically adjacent but are separate atoms, and every lift has to push labels across one of
them. EvoX has 2 BOUNDARY families at m = 11: masks 3153 and 2989, both reversal rotations.

## 8. Conjecture A against the m = 11 data

**All 18 identity-rotation families in the holdout are certified by EvoX, GEPA and control (b).**
That is 6 at m = 9, 5 at m = 10 and 7 at m = 11, including the identity itself at m = 11
(mask 3551) and the all-gaps mask 4095. Together with the 10 development families, the record
is 28 of 28.

The conjecture is not specific to either engine: control (b)'s plain sweep pool already
certifies all of them. The sample is tiny next to the 11 x (2^12 - 1) = 45,045 identity-rotation
families at m = 11.

**What a human would have to prove.** Fix m and an identity rotation a. A mask S splits the
cyclic label sequence into k arcs of lengths l_0..l_{k-1}, where each arc runs from one zero
to the next and the arcs sum to m. The proof then needs three steps:
1. **Explicit words.** Give lifts and a routing, for example greedy, together with closed
   forms for q_LL, A_j and p_j in terms of the arcs and the target rotation t.
   - A zero can be passed by labels, at a cost of 2 per label on beta_j.
   - Alternatively, an arc can be rotated by label-label swaps at base cost only, about
     l(m-l) for the arc.
2. **Explicit weights.** Give weights, as functions of the arcs, with Bbar < T+1 and
   betabar_j <= m-2 for every j. Criterion (7) with m as a parameter then gives
   d <= T_m(n) for the whole family.
3. **Every composition.** Show step 2 holds for every composition of m into arcs and every k
   from 1 to m+1.

The hard cases are k = 2 with two long arcs. Each word loads roughly 2 min(l, m-l) on one
zero, and the slack in B, (k-1)(m-2), is small. This depends on the group's Lemma 1, and on
the one-line generalization of (7) to general m, which the group has not confirmed (SPEC 3.3).

## 9. Determinism

The finalize REPORT marks EvoX and GEPA as nondeterministic. The finalize test compares output
words across two screen runs.

The source of the nondeterminism, read from the code, is the same in both programs. The pool,
the pricing and every pick are deterministic, and EvoX's RNG is seeded with 42. The only
nondeterministic step is `list(selected)[:32]`. It iterates a set of strings, and Python
randomizes string hashes per process. The worker environment does not set PYTHONHASHSEED, so
the kept 32 words vary whenever the pick union exceeds 32.

The effect is visible. GEPA's development count moved from 204 in the campaign to 201 in
finalize, for the same source hash. EvoX stayed at 212 on development.

**Certificate validity does not depend on it.** Each CERTIFIED row stores its support words
and weights (`certificate.words`, `certificate.weights`). The evaluator re-derives everything
from the words, and `bound_audit` agrees on all of them: 356 of 356 EvoX and 321 of 321 GEPA
holdout claims. The nondeterminism decides only which words are emitted, and so which families
are certified in a given run. A recorded certificate can be re-checked from its words without
running the program.

The consequence is for scores, not for claims. The holdout counts, 129 for EvoX and 125 for
GEPA, are one draw. A rerun could certify a slightly different set. Fixing the hash seed in
the worker, or sorting before the truncation, would remove the variation. Both are
evaluator-side or candidate-side changes that I did not make.
