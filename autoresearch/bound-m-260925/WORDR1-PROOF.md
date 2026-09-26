# word_R1: proof of the length and Lemma 1 slope formulas, all m >= 9, the four residues of m mod 4

Date 2026-09-26. Pen-and-paper proof, no provider calls, no code changes outside the two new check scripts.
It proves REVERSAL-ORBIT.md conjecture 1 (section 5) as far as the word itself goes: the length and the Lemma 1
numbers of word_R1(m) for every m >= 9. The model is WORDC-PROOF.md, whose sweep lemma is reused.

The object of the proof is the Python function `word_R1(m)` in `checks/reversal_orbit.py` exactly as written,
which calls `core_word` with its partial-carry rule, its stopping test `srt()` and the tie rule of `goto`. B, beta_j,
A_j and cz_j are the quantities computed by `integrations/lrx_m.Profile`. Lemma 1, the cost formulas (4)-(5) and
criterion (7) are the research group's (m = 8 manuscript, applied with m as a parameter). The main conjecture stays
open.

Mechanical companion: `checks/wordr1_proof_check.py` rebuilds every intermediate claim below from the closed
formulas of this note and compares it with the literal execution of word_R1. Its output is in section 10.

Section 11 is the requested short note on word_G. It lists the parameter cases and the closed forms that
`checks/wordg_formula_check.py` confirms on the data. It is not a proof.

## 0. Statement

Write m = 4u + rho with rho in {0, 1, 2, 3}. Put n = m + 2 and T = T_m(n) = m(m+1)/2 + m - 2.

**Theorem.** Let m >= 9 (so u >= 2; the proof uses only u >= 2, which also admits m = 8). Then:

1. word_R1(m) sorts the unit base u_R1 = (m, 0, m-1, ..., 1, 0) of (m..1){1,m} to (1, ..., m, 0, 0).
2. Its length is T - 2 if rho is 0, 1 or 3, and T if rho = 2.
3. Every segment of the word (the letters between two consecutive X) consists of one repeated letter, and every
   cz_j(g) is 0. So the Lemma 1 base is B = length, and `Profile` reports same_sign.
4. A = (K-2, K-1) and beta = (2K-4, 2K-2), where K = 2u if rho is 0, 1 or 2 and K = 2u+1 if rho = 3.
   Coordinate 0 is the zero in gap 1 and coordinate 1 is the zero in gap m. By residue:

| m mod 4 | K | length - T | beta |
|---|---|---|---|
| 0 | m/2 | -2 | (m-4, m-2) |
| 1 | (m-1)/2 | -2 | (m-5, m-3) |
| 2 | (m-2)/2 | 0 | (m-6, m-4) |
| 3 | (m-1)/2 | -2 | (m-5, m-3) |

At m = 9 this gives (T-2, (4,6)), and at m = 10 it gives (T, (4,6)). These are the two rows REVERSAL-ORBIT.md lists
separately. They are instances of the general rows, not exceptions.

**Corollary (the numbers criterion (7) needs).** For every m >= 9, the single word word_R1(m), weight 1, has
B <= T < T + 1 and beta_0, beta_1 <= m - 2. Equality beta_1 = m - 2 holds exactly when m = 0 mod 4.

Proof of the corollary from the theorem: read the table. For weight 1 the mixture is the word itself, so these are
the inequalities that `lrx_m.mixture_criterion` encodes. QED.

## 1. Definitions

**Cells and executor.** These are as in WORDC-PROOF.md section 1: cells 0..n-1 mod n, cursor c starting at 0, L:
c := c+1, R: c := c-1, X swaps cells c and c+1. This is `lrx_m.run`, and it is also the model inside `core_word`.

**Initial state.** Cell 0 holds label m, and cell 1 holds the zero Z0 (gap 1). Cell j holds label m+1-j for
2 <= j <= m, and cell n-1 holds the zero Z1 (gap m). In `Profile`, Z0 is block 0 and Z1 is block 1, and both are
picks. This is `base_vector(m..1, 2 | 1<<m)`.

**Arcs and Lemma 1 terms.** These are exactly as in WORDC-PROOF.md section 1, rules (P-L), (P-R), (P-X1), (P-X2).
B = Q + sum_g |d_g| and beta_j = 2 A_j + sum_g |cz_j(g)|.

**core_word, restated for this call.** The call is `core_word(u_R1, t, [(0, k1, 'l'), (s2, None, d2)], 'R')`.

- **Rank.** The cut is t = floor((m-3)/4). The rank is rk(x) = x - t - 1 for a label x > t, rk(Z) = m - t for
  both zeros, and rk(x) = m - t + x for a label x <= t. So the order is t+1, ..., m, then the zeros (tied), then
  1, ..., t.
- **A growth step** on an arc [lo..hi] of length ln is one of two kinds.
  - **r-step.** Let j = hi+1 and e = content of j. The code computes s as the largest s <= ln such that the s
    cells hi, hi-1, ..., hi-s+1 all have rank > rk(e), scanning from hi. If s > 0 it emits `goto(hi)` and then
    X (RX)^(s-1). It then moves e to cell j-s, shifts the s cells one step right, and sets c := j - s. Finally
    hi := j.
  - **l-step.** Let j = lo-1 and e = content of j. The code computes s as the largest s <= ln such that the cells
    lo, ..., lo+s-1 all have rank < rk(e). If s > 0 it emits `goto(j)` and then X (LX)^(s-1). It then moves e to
    cell j+s, shifts the s cells one step left, and sets c := j + s - 1. Finally lo := j.
  - If s = 0, **nothing is emitted and no cell or cursor changes**. Only lo or hi moves.
  - Sides alternate from the given first side. Each step raises ln by 1.
- **Core 1** is seeded at cell 0 with first side 'l' and runs exactly k1 = floor(m/2) steps.
- **Core 2** is seeded at cell s2 = k1 + 1, with first side d2 = 'r' if rho = 1 and 'l' otherwise. It runs while
  ln < n and srt() is false. srt() is true iff reading m cells cyclically from the cell of label 1 gives 1, ..., m.
- **Wf** is 'R' * ((c - pos(1)) mod n).
- **goto(t')** emits L^f if f <= b and R^b otherwise, where f = (t'-c) mod n and b = (c-t') mod n. On a tie it
  goes L.

**Code model = executor.** The code decides s from its own cell array, not from the letters. When s = ln the code's
update is exactly the result of Lemma S (below) applied to the emitted letters: the arc [lo..hi+1] reads
(e, x_0, ..., x_{l-1}) with the cursor on lo (r), or [lo-1..hi] reads (x_0, ..., x_{l-1}, e) with the cursor on hi-1
(l). When s = 0 both do nothing. Lemma P shows that every step of word_R1 has s in {0, ln}. So by induction over the
steps, the code's (cell, c) equals the executor's state after the letters emitted so far. From here on "the state"
means both.

**Parameters.** From m = 4u + rho:

| rho | t | k1 | K (last full step) | p = ceil(K/2) | q = floor(K/2) | N2 = m+1-K | s2 | d2 |
|---|---|---|---|---|---|---|---|---|
| 0 | u-1 | 2u | 2u | u | u | 2u+1 | 2u+1 | l |
| 1 | u-1 | 2u | 2u | u | u | 2u+2 | 2u+1 | r |
| 2 | u-1 | 2u+1 | 2u | u | u | 2u+3 | 2u+2 | l |
| 3 | u | 2u+1 | 2u+1 | u+1 | u | 2u+3 | 2u+2 | l |

Here K = k1 except for rho = 2, where K = k1 - 1. In every row **t = p - 1**: the cut equals the number of small
labels core 1 carries. R2 denotes the cell range [q+1 .. n-1-p], which has N2 cells.

## 2. The sweep lemma (from WORDC-PROOF.md)

Lemma S (the r and l sweeps, with their cell and cursor invariants), Corollary S (S1)-(S3) and Lemma W (the
one-letter inter-sweep walks) are used verbatim from WORDC-PROOF.md section 2. They are statements about the
executor alone:

- a full r-carry of e across an arc of length l <= n-2, starting from the cursor on hi;
- a full l-carry, starting from the cursor on lo-1;
- the walk that follows.

The letters `core_word` emits for a full carry are exactly those of Lemma S: `goto(hi)` then X (RX)^(l-1), or
`goto(lo-1)` then X (LX)^(l-1). Its cursor after the carry is j - s = lo (r) or j + s - 1 = hi - 1 (l), as in
Lemma S. So Lemma W applies unchanged: after an r-step the next l-step's walk is one R, and after an l-step the next
r-step's walk is one L. This holds whenever both steps are full carries.

## 3. Lemma P (the carry counts)

**Lemma P.** The carry counts s of word_R1(m) are:

- core 1, step 1: s = 1 = ln;
- core 1, step 2: s = 0;
- core 1, step k for 3 <= k <= K: s = ln = k;
- core 1, step K+1 when rho = 2: s = 0;
- core 2, step i for 1 <= i <= N2-1: s = ln = i.

In particular every step is a full carry or empty. The partial carries that `core_word` allows in general, with
0 < s < ln, never occur in word_R1.

*Proof.* The contents used here are those of Lemma A and Lemma B, which are proved by the joint induction below.
Each step's s depends only on the state before that step.

- **Step 1** (l, arc = cell 0 = (m), ln = 1). Here e = Z1 on cell n-1, and rk(m) = m-t-1 < m-t = rk(Z1). So s = 1.
- **Step 2** (r, arc [n-1..0] = (m, Z1), ln = 2). Here e = Z0 on cell 1. The scan starts at cell hi = 0, which
  holds Z1, and rk(Z1) = rk(Z0) is not > rk(Z0). So s = 0.
- **Step k, 3 <= k <= K, k odd (l-step).** Here e = p_{k-1} = (k-1)/2 (Lemma A). Since e <= p_K - 1 = t, e is a
  small label with rk(e) = m - t + e. The arc S_{k-1} holds three kinds of element:
  - big labels, with rank <= m-t-1;
  - the zeros, with rank m-t;
  - the small labels 1..e-1, with ranks m-t+1..m-t+e-1.

  All of these are < rk(e), so the scan runs to s = ln.
- **Step k, 4 <= k <= K, k even (r-step).** Here e = m - q_k + 1 >= m - u + 1 > t, a big label with
  rk(e) = e - t - 1. The arc S_{k-1} holds three kinds of element:
  - the big labels e+1..m, with larger ranks;
  - the zeros, with rank m-t > e-t-1 because e <= m;
  - small labels, with rank > m-t.

  All of these are > rk(e), so s = ln.
- **Step K+1, rho = 2 (l-step).** Here e is the content of cell n-1-u, which is untouched and holds u = t+1. So
  rk(e) = 0. The first cell scanned is lo_K, which holds m-u+1 with rank m-2u+1 > 0. That rank is not < 0, so
  s = 0.
- **Core 2.** Every label of R2 lies in [p, m-q], and p = t+1 (parameter table), so all are big and rank is
  increasing in the label. By Lemma B the core-2 arc holds increasing consecutive labels. The new cell holds the
  next smaller label (r-step) or the next larger label (l-step). So every arc element has a larger rank (r) or a
  smaller rank (l), and s = ln. QED.

## 4. Lemma A (core 1)

For k >= 2, put p_k = ceil(k/2) and q_k = floor(k/2), which are the numbers of l-steps and r-steps among steps
1..k. Put lo_k = n - p_k (mod n), hi_k = q_k and

    S_k = (m-q_k+1, ..., m, Z1, Z0, 1, ..., p_k-1)      (q_k + 2 + p_k - 1 = k+1 entries).

**Lemma A.** For 2 <= k <= K, after the first k steps of core 1:

- (A1) The variables of `core_word` are lo = lo_k and hi = hi_k. The arc [lo_k..hi_k] has length k+1.
- (A2) The arc [lo_k..hi_k] reads S_k.
- (A3) The cells j = q_k+1, ..., n-1-p_k form an integer range with no wrap. There are m+1-k >= 2 of them, and each
  still holds its initial label m+1-j, which lies in [p_k, m-q_k]. These cells and the arc partition all n cells.
- (A4) The cursor is on lo_k if k is even (including k = 2), and on hi_k - 1 = q_k - 1 if k >= 3 is odd.
- (A5) Step 1 emits R X. Step 2 emits nothing. For 3 <= k <= K, step k emits w_k followed by the sweep. The walk
  w_k is one R for odd k and one L for even k. The sweep is X (LX)^(k-1) for odd k and X (RX)^(k-1) for even k,
  with 2k-1 letters.

*Proof by induction on k.*

**Step 1.** Here lo = hi = 0, and step 1 is an l-step with s = 1 (Lemma P).
- `goto(n-1)` from c = 0 has f = n-1 > 1 = b, so it emits one R. Then it emits X.
- The executor moves to n-1 and swaps cells n-1 and 0: cell n-1 holds m and cell 0 holds Z1.
- The code sets c = j + s - 1 = n-1 and lo = n-1.

**Step 2, the base case k = 2.** Step 2 is an r-step with s = 0 (Lemma P). It emits nothing, the cursor stays on
n-1, and hi := 1.
- The arc [n-1..1] reads (m, Z1, Z0) = S_2, with p_2 = q_2 = 1, so lo_2 = n-1 and hi_2 = 1.
- Cells 2..n-2 = q_2+1..n-1-p_2 are untouched and hold m+1-j.
- The cursor is on n-1 = lo_2. This is (A4) for even k.

So after step 2 the state looks as if an r-sweep had just ended. This is why the next walk is an R.

**Step k -> k+1, k even, 2 <= k < K (step k+1 is an l-step).**
- The cursor is on lo_k by (A4). `goto(lo_k - 1)` has f = n-1 > 1 = b, so it emits one R (Lemma W; for k = 2 this is
  the same computation from n-1 to n-2).
- The carried element is e = content of lo_k - 1 = n-1-p_k, the top cell of the (A3) range. So
  e = m+1-(n-1-p_k) = p_k = p_{k+1} - 1, a label.
- By Lemma P, s = ln = k+1. By Lemma S(l), the arc [lo_k - 1..hi_k] reads (S_k, p_k) = S_{k+1}, and the cursor is
  on hi_k - 1 = q_{k+1} - 1.
- The (A3) range loses its top cell. The sweep is X (LX)^k.

**Step k -> k+1, k odd, 3 <= k < K (step k+1 is an r-step).**
- The cursor is on hi_k - 1 by (A4). `goto(hi_k)` has f = 1 <= n-1 = b, so it emits one L (Lemma W).
- The carried element is e = content of hi_k + 1 = q_k + 1, the bottom cell of the (A3) range. So
  e = m - q_k = m - q_{k+1} + 1, a label.
- By Lemma P, s = ln = k+1. By Lemma S(r), the arc [lo_k..hi_k + 1] reads (m - q_{k+1} + 1, S_k) = S_{k+1}, and the
  cursor is on lo_k = lo_{k+1}.
- The (A3) range loses its bottom cell. The sweep is X (RX)^k.

In both cases l = k+1 <= K+1 <= n-2, so Lemma S applies. The count m+1-k >= m+1-K >= 2 follows from K <= m/2. QED.

**The cyclic wrap.** From step 1 on, the arc contains the edge between cells n-1 and 0. As in WORDC-PROOF.md, only
Lemma S (stated mod n) and the executor's mod-n moves are used across it. The only integer ranges used are (A3) and
R2, which lie inside 2..m.

**The empty step K+1 when rho = 2.** By Lemma P, s = 0. Nothing is emitted, no cell changes, and the cursor stays
on lo_K. Only `core_word`'s variable lo moves, to n-1-u, and that variable is not used again, because core 2 is
seeded afresh. Label u stays on its initial cell n-1-u. This is the top cell of R2 (p = u for rho = 2).

**Explicit end state of core 1.** The state after step K, and after the empty step for rho = 2, is:

- the arc [n-p..q] reads (m-q+1, ..., m, Z1, Z0, 1, ..., p-1). So label i (1 <= i <= p-1) is on cell q-p+1+i,
  Z0 is on q-p+1 and Z1 is on q-p (mod n);
  - rho = 0, 1, 2 (p = q): Z1 on cell 0, Z0 on cell 1, label i on cell i+1;
  - rho = 3 (p = q+1): Z1 on cell n-1, Z0 on cell 0, label i on cell i;
- R2 = [q+1..n-1-p] holds its initial labels, decreasing from m-q down to p;
- the cursor c1 is on lo_K = n-u if K is even (rho = 0, 1, 2), and on q-1 = u-1 if K is odd (rho = 3).

**A-terms of core 1.** Step 1 swaps with Z1 at the cursor and label m at c+1, which gives A_1 += 1. Each sweep
k = 3..K carries a label across S_{k-1}, which contains both zeros. By (S1) this gives A_0 += 1 and A_1 += 1.
Hence **A = (K-2, K-1)** from core 1.

## 5. Lemma B (core 2) and the stopping rule

**Side counts.** Core 2 must end on R2 = [q+1..n-1-p]. Starting from s2, that needs s2 - (q+1) l-steps and
n-1-p-s2 r-steps, N2 - 1 steps in total. The sides alternate from d2:

| rho | l-steps needed | r-steps needed | N2-1 | sides from d2 | l, r in that sequence | last side |
|---|---|---|---|---|---|---|
| 0 | u | u | 2u | l, r, ..., l, r | u, u | r |
| 1 | u | u+1 | 2u+1 | r, l, ..., r | u, u+1 | r |
| 2 | u+1 | u+1 | 2u+2 | l, r, ..., l, r | u+1, u+1 | r |
| 3 | u+1 | u+1 | 2u+2 | l, r, ..., l, r | u+1, u+1 | r |

The counts match in all four residues, and **the last core-2 step is always an r-step**. Let rho_i and lambda_i be
the numbers of r-steps and l-steps among the first i core-2 steps, and put lo'_i = s2 - lambda_i and
hi'_i = s2 + rho_i. Both are monotone, and after N2-1 steps they reach q+1 and n-1-p. So

    q+1 <= lo'_i <= s2 <= hi'_i <= n-1-p    for 0 <= i <= N2-1.

Every core-2 arc is an integer sub-range of R2, with no wrap.

**Lemma B.** For 0 <= i <= N2-1, after i core-2 steps:

- (B1) lo = lo'_i and hi = hi'_i. The arc has length i+1.
- (B2) Cell j of the arc holds m+1-(lo'_i + hi'_i - j). So the arc reads the increasing consecutive labels
  m+1-hi'_i, ..., m+1-lo'_i.
- (B3) The cells of R2 outside the arc hold their initial labels, and the cells outside R2 are as at the end of
  core 1.
- (B4) For i >= 1, the cursor is on lo'_i after an r-step and on hi'_i - 1 after an l-step.
- (B5) Step i has s = i. Its letters are X (RX)^(i-1) or X (LX)^(i-1). For i >= 2 it is preceded by one R (the
  previous step was r) or one L (the previous step was l). Step 1 is preceded by W0.

*Proof.* This is WORDC-PROOF.md Lemma B with start = s2 and R2 = [q+1..n-1-p], word for word. The one new ingredient
is that `core_word` decides s by ranks, and Lemma P gives s = i. QED.

**The stopping rule.** Core 2's loop runs while ln < n and srt() is false. It runs exactly N2 - 1 steps:

- ln = i+1 <= N2 - 1 < n for every step, so the ln < n test never stops it.
- **srt() is false before each step.** Suppose i < N2 - 1, so the arc is not all of R2.
  - If hi'_i < n-1-p, then cells hi'_i and hi'_i+1 both lie in R2. They hold m+1-lo'_i and m-hi'_i < m+1-lo'_i.
  - Otherwise lo'_i > q+1. Then cells lo'_i - 1 and lo'_i hold m+2-lo'_i and m+1-hi'_i < m+2-lo'_i.

  Either way two adjacent cells hold labels with a descent. If srt() were true, the m labels would fill m
  consecutive cells from label 1 with each label one more than its left neighbour, and the two remaining cells
  would hold the zeros. So every pair of adjacent label cells would be an ascent by 1. Hence srt() is false. At
  i = 0 the arc is one cell and N2 >= 2, so the same argument applies.
- **srt() is true after step N2 - 1.** This is shown below.

**End state of core 2.** The cursor is on lo'_{N2-1} = q+1, because the last step is r. R2 holds p, p+1, ..., m-q
in increasing order, since cell j of R2 holds j - q - 1 + p. With the end state of core 1, reading from the cell of
label 1 (cell q-p+2) gives:

- 1..p-1 on cells q-p+2..q;
- p..m-q on R2;
- m-q+1..m on cells n-p..n-p+q-1;
- then Z1 and Z0.

So srt() is true, and the final test of `core_word` passes.

**Terms of core 2.** Every arc element and every carried element of core 2 is a label of R2. By (S1)-(S3) the
core-2 sweeps contribute nothing to A and nothing to any cz. By (B3) and Lemma W the inter-sweep walks of core 2
move between cells of R2, so they contribute nothing either.

## 6. Lemma C (the walks W0 and Wf)

W0 is the `goto` of core 2's first step. It targets t0 = s2 if d2 = r (rho = 1), and t0 = s2 - 1 if d2 = l. It
starts from c1 (section 4). Put f = (t0 - c1) mod n and b = n - f.

**Case rho = 0** (m = 4u, n = 4u+2, u >= 3).
- c1 = n-u = 3u+2 and t0 = 2u. So b = u+2 and f = 3u.
- f > b because u > 1, so the walk goes R. **W0 = R^(u+2).**
- It arrives on cells 3u+1, 3u, ..., 2u. R2 = [u+1..3u+1] contains all of them, because 2u >= u+1.

**Case rho = 1** (m = 4u+1, n = 4u+3).
- c1 = 3u+3 and t0 = 2u+1. So b = u+2 and f = 3u+1 > b.
- **W0 = R^(u+2).**
- It arrives on 3u+2, ..., 2u+1, which all lie in R2 = [u+1..3u+2].

**Case rho = 2** (m = 4u+2, n = 4u+4).
- c1 = 3u+4 and t0 = 2u+1. So b = u+3 and f = 3u+1.
- f > b because u > 1. **W0 = R^(u+3).**
- It arrives on 3u+3, ..., 2u+1, which all lie in R2 = [u+1..3u+3]. Cell 3u+3 = n-1-u holds label u, the label
  left in place by the empty step.

**Case rho = 3** (m = 4u+3, n = 4u+5).
- c1 = u-1 and t0 = 2u+1. So f = u+2 and b = 3u+3 > f.
- **W0 = L^(u+2).**
- It leaves cells u-1, u, ..., 2u.
  - Cells u-1 and u hold labels u-1 and u, because label i is on cell i for rho = 3. Also u-1 >= 1 because u >= 2.
  - Cells u+1..2u lie in R2 = [u+1..3u+3].

**Lemma C.**

- (C-len) W0 has u+2 letters for rho = 0, 1, 3 and u+3 letters for rho = 2.
- (C-dir) W0 is one repeated letter: R for rho = 0, 1, 2 and L for rho = 3. No case is a tie.
- (C-zero) W0 passes no zero in any residue.
- (C-f) Wf = R^(p-1) ends on label 1 and passes no zero.
  - After core 2, the cursor is on q+1, and label 1 is on q-p+2.
  - So Wf has (q+1 - (q-p+2)) mod n = p-1 letters: u-1 for rho = 0, 1, 2, and u for rho = 3.
  - It arrives on cells q, q-1, ..., q-p+2, which hold p-1, ..., 1.
  - The visible vector is then (1, ..., m, Z1, Z0), by section 5. This proves part 1 of the theorem.

## 7. Lemma D (letter count)

By (A5), core 1 has 2 letters for step 1, 0 for step 2, and 2k letters for each step k = 3..K:

    core 1 = 2 + sum_{k=3..K} 2k = K(K+1) - 4.

By (B5), core 2 without W0 has sweeps of 2i-1 letters for i = 1..N2-1, plus N2-2 one-letter walks:

    core 2 = (N2-1)^2 + N2 - 2.

The total is

    len = K(K+1) - 4 + (N2-1)^2 + N2 - 2 + W0 + (p-1).

| rho | K | N2 | W0 | p-1 | len | T | len - T |
|---|---|---|---|---|---|---|---|
| 0 | 2u | 2u+1 | u+2 | u-1 | (4u^2+2u-4) + (4u^2+2u-1) + 2u+1 = 8u^2+6u-4 | 8u^2+6u-2 | -2 |
| 1 | 2u | 2u+2 | u+2 | u-1 | (4u^2+2u-4) + (4u^2+6u+1) + 2u+1 = 8u^2+10u-2 | 8u^2+10u | -2 |
| 2 | 2u | 2u+3 | u+3 | u-1 | (4u^2+2u-4) + (4u^2+10u+5) + 2u+2 = 8u^2+14u+3 | 8u^2+14u+3 | 0 |
| 3 | 2u+1 | 2u+3 | u+2 | u | (4u^2+6u-2) + (4u^2+10u+5) + 2u+2 = 8u^2+18u+5 | 8u^2+18u+7 | -2 |

The T column is T = m(m+1)/2 + m - 2 with m = 4u + rho. For example, rho = 3 gives
(4u+3)(2u+2) + 4u + 1 = 8u^2 + 18u + 7. This proves part 2 of the theorem.

At m = 9 (u = 2, rho = 1) the length is 50 = T - 2. At m = 12 (u = 3, rho = 0) it is 86 = T - 2. Both agree with the
words printed in REVERSAL-ORBIT.md.

The number of swaps is Q = 1 + (K(K+1)/2 - 3) + N2(N2-1)/2.

## 8. Lemma E (segments and cz accounting)

By (A5), (B5) and Lemma C, the word is the concatenation

    R X_1 . w_3 S_3 . w_4 S_4 ... w_K S_K . W0 . S'_1 w'_2 S'_2 ... w'_{N2-1} S'_{N2-1} . Wf

where X_1 is the single X of step 1, each S begins and ends with X with one letter between consecutive X's, each w
is one letter, and W0, Wf are powers of one letter. The segments are:

- (E0) the letter R before X_1;
- (E1) w_3 = R;
- (E2) the single letters inside sweeps;
- (E3) w_4 = L;
- (E4) w_k for 5 <= k <= K;
- (E5) W0;
- (E6) the core-2 walks w'_i;
- (E7) Wf.

Each segment is one repeated letter, so |d_g| is its letter count and B = Q + sum |d_g| = len. This proves the
first half of part 3.

**The cz of each segment.** Every term comes from four sources: (P-L), (P-R), (P-X1) at the X that ends the
segment, and (P-X2) at the X that starts it.

- **(E0)** The R arrives on cell n-1, which holds Z1. That gives -1 to cz_1 by (P-R). X_1 has Z1 at the cursor and
  label m at c+1. That gives +1 to cz_1 by (P-X1), and A_1 += 1. So cz = (0, -1+1) = 0.
  - This is where word_R1 differs from word_C. In word_C the first X stands on a zero with no preceding R, and its
    +1 survives. Here the opening walk arrives on that zero and cancels it.
- **(E1)** X_1 has a label at c+1, so there is no (P-X2) term. The R arrives on cell n-2, which holds label 1. The
  first X of S_3 has the cursor on n-2, which holds e = 1, and cell n-1 holds m. So cz = 0.
- **(E2)** cz = 0 by (S2), in both cores.
- **(E3)** The L after l-sweep 3 and before r-sweep 4. Three terms contribute:
  - The last X of S_3 adds -1 to cz_0, because the last entry of S_2 = (m, Z1, Z0) is Z0 (S3).
  - The L leaves cell hi_3 - 1 = 0, which holds Z0, giving +1 to cz_0.
  - The first X of S_4 has the cursor on hi_3 = 1, which holds label 1, giving nothing.

  So cz = (-1+1, 0) = 0.
- **(E4)** Take 5 <= k <= K.
  - If k is odd, w_k is an R after an r-sweep. The last X of an r-sweep and the first X of an l-sweep add nothing
    (S3). The R arrives on the top cell of the (A3) range, which holds a label.
  - If k is even (k >= 6), w_k is an L after the l-sweep k-1. The last X of that sweep adds -1 iff the last entry of
    S_{k-2} is a zero. That entry is p_{k-2} - 1 >= 1, a label, since k-2 >= 4. The L leaves cell hi_{k-1} - 1,
    which holds that same label. The first X of the r-sweep has the cursor on hi_{k-1}, which holds the label
    p_{k-1} - 1 >= 1.
  - So cz = 0.
- **(E5)** W0 has three possible sources of terms.
  - The last X of core 1. If K is even (rho = 0, 1, 2), it ends an r-sweep and adds nothing. If K is odd (rho = 3),
    it ends an l-sweep and adds -1 iff the last entry of S_{K-1} is a zero. That entry is p_{K-1} - 1 = u - 1 >= 1,
    a label.
  - The walk passes no zero, by (C-zero).
  - The first X of core 2 involves only labels of R2.

  So cz = 0.
- **(E6)** cz = 0 (section 5, terms of core 2).
- **(E7)** The last X of core 2 ends an r-sweep and adds nothing. The arrivals are on labels by (C-f). So cz = 0.

Every cz is 0, which proves the second half of part 3. Since every cz vanishes, same_sign holds.

**Slopes.** By sections 4 and 5, A = (K-2, K-1): core 2 and all walks contain no X involving a zero. Hence

    beta_j = 2 A_j + sum_g |cz_j(g)| = 2 A_j,   beta = (2K-4, 2K-2).

Substituting K from the parameter table gives the table of part 4. QED.

**Small steps, written out once (m = 9).** Core 1 is R X, then nothing, then R XLXLX, then L XRXRXRX. That is 16
letters, and the arc (8, 9, Z1, Z0, 1) sits on cells 9, 10, 0, 1, 2. W0 is R^4. Core 2 on R2 = [3..8] is
X, R XLX, L XRXRX, R XLXLXLX, L XRXRXRXRX, and Wf is R. In total this is 16 + 4 + 29 + 1 = 50 letters, which matches
the printed word. Only two zero passes occur:

- the first R arrives on Z1, and X_1 cancels it;
- the L of w_4 leaves Z0, cancelling the -1 of S_3's last X.

## 9. What this proof does NOT cover

- **Lemma 1 itself.** The proof computes B and beta exactly as `lrx_m.Profile` defines them. It does not prove that
  B + beta . z bounds the length of a sorting word for the stretched states. That is the group's Lemma 1 with
  formulas (4)-(5), applied at general m.
- **Criterion (7).** The corollary shows that the numbers satisfy the inequalities that `lrx_m.mixture_criterion`
  encodes: B < T + 1 and beta_j <= m - 2. The claim that these inequalities imply d(v) <= T_m(n) for every state of
  (m..1){1,m} at every block length is criterion (7), which is the group's. So "word_R1 certifies (m..1){1,m} for all
  m >= 9" follows from this proof **only together with** Lemma 1 and criterion (7) at general m. Neither is proved
  here.
- **The evaluator and the audit.** `score_output` and `audit_claim` were run on this word at m = 9..40 only
  (REVERSAL-ORBIT.md). The proof replaces the replay at every m >= 9, but not those checkers' own steps (picks,
  literal lifts, box points).
- **Other code.** The proof is about `core_word` and `word_R1` as they stand in `checks/reversal_orbit.py`. A
  change to `goto`'s tie rule would not matter here, because no walk of word_R1 is a tie. A change to the rank rule
  or the carry rule would matter.
- **m <= 7.** u = 1 is outside the proof. There t = 0 when rho != 3, so label 1 is not a small label and Lemma P
  changes, and at m = 6 a zero-crossing term survives. The proof itself needs only u >= 2, and the mechanical check
  also passes at m = 8. The statement is for m >= 9, as requested.
- **Minimality.** The proof says nothing about whether these words are shortest, and gives no distance or radius.

## 10. Mechanical check

`checks/wordr1_proof_check.py` (stdlib; imports word_R1 and lrx_m; writes nothing) predicts the following from the
formulas above, without calling core_word:

- the block decomposition of the word into step 1, the empty step 2, the w_k and S_k, the empty step K+1 (rho = 2),
  W0, the S'_i and w'_i, and Wf, compared as strings with word_R1(m);
- the carry count s of every growth step (Lemma P). It compares this with core_word's rank-comparison loop
  evaluated on the executed cells at each step boundary;
- the full cell map, cursor, lo and hi after every core-1 step (Lemma A), and the no-op of the empty step;
- the full cell map, cursor, lo' and hi' after every core-2 step (Lemma B), the side counts, and srt() false before
  each core-2 step and true at the end;
- the zeros passed by every walk: Z1 in the first R, Z0 in w_4, none elsewhere, and none in W0 or Wf;
- the start and end cursor of W0, its direction as goto would choose it, its length, and the end of Wf on label 1;
- the final state (1..m, Z1, Z0), and the replay with run_naive and run;
- the letter counts of Lemma D, the length by residue, and Q;
- the segment count, unidirectionality, |d| = letter count, and every cz = 0 from its own executor and from
  lrx_m.Profile;
- A = (K-2, K-1), B = length, beta by residue and same_sign from lrx_m.Profile;
- the corollary: B <= T, beta <= m-2, and mixture_criterion with weight 1.

Before it was finalized, three mutations were each detected. Shifting the core-1 cursor after step 5 gave 50
mismatches. Predicting s = 1 at step 2 gave 52. Dropping the (P-R) term from the executor gave 910.

    $ PYTHONPATH=. python autoresearch/bound-m-260925/checks/wordr1_proof_check.py
    m = 9..60: 52 values of m
    mismatches (Lemmas P, A-E, theorem, corollary): 0

    $ PYTHONPATH=. python autoresearch/bound-m-260925/checks/wordr1_proof_check.py 9 200
    m = 9..200: 192 values of m
    mismatches (Lemmas P, A-E, theorem, corollary): 0

    $ PYTHONPATH=. python autoresearch/bound-m-260925/checks/wordr1_proof_check.py 8 8
    m = 8..8: 1 values of m
    mismatches (Lemmas P, A-E, theorem, corollary): 0

The script run is a finite check. The proof above is what covers all m >= 9.

`checks/` is gitignored in this directory. The script must be force-added if it is to be committed.

## 11. word_G: what a proof would need

word_G(m, g) (REVERSAL-K2.md section 2, `checks/reversal_k2.py`) is `core_word` on the base
(0, m, ..., m-g+1, 0, m-g, ..., 1) of (m..1){0,g}. It has parameters (dt, s1, dk, d1, ds2, d2) chosen by m mod 4 and a
first-match rule on g or r = m - g. The rule table was read off data, not derived. **No proof is attempted here.**
This section gives the group exact statements to prove.

**What differs from word_R1, and so what a proof needs beyond sections 2-8.**

- **Genuine partial carries.** In 1509 of the 1600 words at m = 9..80, core 1 contains a step with 0 < s < ln:
  1492 words have one such step and 17 have two. 1508 of those 1526 partial carries move a zero, and 18 move a
  label. All are in core 1.

  So Lemma S needs a partial-carry version, where a sweep stops after s < l swaps. Corollary S (S3) also needs
  boundary terms at the stop cell. The surviving cz terms, such as the slopes m-5 or m-10-g, come from these stops.
- **A per-row Lemma P.** In each row, the cut t = (m-3)//4 + dt decides which carries stop and where. This must be
  computed row by row, as in section 3.
- **Core-2 seed and stopping.** The seed is the middle of the complement arc plus ds2. Core 2 need not end on a
  clean integer range as R2 does here, so the stopping-rule argument of section 5 must be redone per row.
- **Small-m rows.** The rows g = j at m = 9 and m = 11 do not follow the general formula, so they need separate
  treatment.

**The parameter cases.** There are 20 rule rows. Three rows in residue 0 and one row in each of residues 1, 2 and 3
split further at one end. That gives 28 cases, listed below with the closed forms that
`checks/wordg_formula_check.py` confirms. Here j = floor(m/4), r = m - g, and beta = (zero in gap 0, zero in
gap g).

| m mod 4 | rule row (dt,s1,dk,d1,ds2,d2) | case | length - T | beta |
|---|---|---|---|---|
| 0 | g=1: (-1,1,-1,r,-1,r) | g = 1 | -1 | (m-2, m-5) |
| 0 | 2<=g<=j-1: (0,0,-1,r,-1,r) | 2 <= g <= j-2 | 2-g | (m-2, m-4-g) |
| 0 | | g = j-1 | -g | (m-3, m-5-g) |
| 0 | g=j, j>=4: (-2,2,-2,l,0,l) | g = j | 2-g | (m-2, m-10-g) |
| 0 | 1<=r<=j-2: (-1,0,-1,r,-1,r) | 1 <= r <= j-2 | 1-r | (m-2, m-3-r) |
| 0 | r=j-1: (0,0,-1,l,-1,r) | r = j-1 | 1-r | (m-4, m-5-r) |
| 0 | r=j: (1,-1,-1,l,-1,r) | r = j | 1-r | (m-2, m-7-r) |
| 1 | g=1: (0,1,0,l,-1,r) | g = 1 | -3 | (m-2, m-5) |
| 1 | 2<=g<=j-1: (1,0,0,l,-1,r) | 2 <= g <= j-2 | 2-g | (m-2, m-2-g) |
| 1 | | g = j-1 | 1-g | (m-3, m-3-g) |
| 1 | g=j: (-1,1,-1,r,0,l) | g = j, j >= 3 | -g | (m-2, m-8-g) |
| 1 | | g = j = 2 (m = 9) | 0 | (7, 1) |
| 1 | 0<=r<=j-1: (0,0,0,l,-1,r) | r = 0 | -1 | (m-2, m-3) |
| 1 | | 1 <= r <= j-1 | 1-r | (m-2, m-3-r) |
| 1 | r=j: (1,-1,0,r,-1,r) | r = j | -1-r | (m-2, m-5-r) |
| 2 | g=1 or g=j: (0,1,-1,l,0,l) | g = 1 | -1 | (m-3, m-6) |
| 2 | | g = j | -2-g | (m-2, m-6-g) |
| 2 | 2<=g<=j-1: (1,0,-1,r,0,l) | 2 <= g <= j-1 | 2-g | (m-2, m-4-g) |
| 2 | 1<=r<=j-1: (0,0,-1,r,0,l) | 1 <= r <= j-1 | 1-r | (m-2, m-3-r) |
| 2 | r=j: (1,-1,-1,r,0,l) | r = j | 1-r | (m-3, m-6-r) |
| 3 | g=1: (0,1,0,l,0,l) | g = 1 | -3 | (m-2, m-5) |
| 3 | 2<=g<=j-1: (1,0,0,l,0,l) | 2 <= g <= j-1 | 2-g | (m-2, m-2-g) |
| 3 | g=j: (-2,1,0,r,0,r) | g = j, j >= 3 | -g | (m-2, m-8-g) |
| 3 | | g = j = 2 (m = 11) | 0 | (9, 3) |
| 3 | 0<=r<=j: (0,0,0,l,0,l) | r = 0 | -1 | (m-2, m-3) |
| 3 | | 1 <= r <= j-1 | 1-r | (m-2, m-3-r) |
| 3 | | r = j | -r | (m-3, m-4-r) |
| 3 | r=j+1, j>=3: (1,-2,-1,r,-1,r) | r = j+1 | 3-r | (m-2, m-9-r) |

In every case B = length, and in every case length <= T and beta <= m - 2. A proof of any one row therefore gives,
with Lemma 1 and criterion (7), the certificate of (m..1){0,g} for that row at all m.

**Unified statements that hold on the data.**

- (C2) On the g-interval rows with 2 <= g <= j-2, in all four residues: length - T = 2 - g and
  beta = (m-2, m-2-g-2[m even]).
- (C4) On the r-interval rows with 1 <= r <= j-2, in all four residues: length - T = 1 - r and
  beta = (m-2, m-3-r).

**Statements that fail on the data**, as the script shows:

- (C1) "length - T = 2 - g on the whole row 2 <= g <= j-1" fails at g = j-1 for m = 0 and 1 mod 4.
- (C3) "length - T = 1 - r on the whole r-interval row" fails at r = 0 for m = 1 and 3 mod 4, and at r = j for
  m = 3 mod 4.
- (C5) "beta_0 = m - 2" fails on the rows listed with m-3 or m-4.

**Script output.** The 1600 rows at m = 9..80 are the same set as REVERSAL-K2.md's 390 + 1210. The formulas were
read off m <= 80. The run on m = 81..120 is out of sample. There, all 26 hypotheses with a nonempty domain hold with
0 exceptions. The two single-m rows, m = 9 and m = 11, have empty domains.

    $ PYTHONPATH=. python autoresearch/bound-m-260925/checks/wordg_formula_check.py   (excerpt: first line, row hypotheses, coarse block)
    word_G rows m = 9..80: 1600
    row hypotheses (formulas in m, g; j = floor(m/4), r = m-g):
      0.g1      g=1:            len-T = -1,   beta = (m-2, m-5)      n=  18 exceptions=0 
      0.g       2<=g<=j-2:      len-T = 2-g,  beta = (m-2, m-4-g)    n= 153 exceptions=0 
      0.g-top   g=j-1:          len-T = -g,   beta = (m-3, m-5-g)    n=  18 exceptions=0 
      0.gj      g=j (j>=4):     len-T = 2-g,  beta = (m-2, m-10-g)   n=  17 exceptions=0 
      0.r       1<=r<=j-2:      len-T = 1-r,  beta = (m-2, m-3-r)    n= 171 exceptions=0 
      0.rj-1    r=j-1:          len-T = 1-r,  beta = (m-4, m-5-r)    n=  18 exceptions=0 
      0.rj      r=j:            len-T = 1-r,  beta = (m-2, m-7-r)    n=  18 exceptions=0 
      1.g1      g=1:            len-T = -3,   beta = (m-2, m-5)      n=  18 exceptions=0 
      1.g       2<=g<=j-2:      len-T = 2-g,  beta = (m-2, m-2-g)    n= 136 exceptions=0 
      1.g-top   g=j-1:          len-T = 1-g,  beta = (m-3, m-3-g)    n=  17 exceptions=0 
      1.gj      g=j, j>=3:      len-T = -g,   beta = (m-2, m-8-g)    n=  17 exceptions=0 
      1.gj9     g=j=2 (m=9):    len-T = 0,    beta = (7, 1)          n=   1 exceptions=0 
      1.r0      r=0:            len-T = -1,   beta = (m-2, m-3)      n=  18 exceptions=0 
      1.r       1<=r<=j-1:      len-T = 1-r,  beta = (m-2, m-3-r)    n= 171 exceptions=0 
      1.rj      r=j:            len-T = -1-r, beta = (m-2, m-5-r)    n=  18 exceptions=0 
      2.g1      g=1:            len-T = -1,   beta = (m-3, m-6)      n=  18 exceptions=0 
      2.gj      g=j:            len-T = -2-g, beta = (m-2, m-6-g)    n=  18 exceptions=0 
      2.g       2<=g<=j-1:      len-T = 2-g,  beta = (m-2, m-4-g)    n= 153 exceptions=0 
      2.r       1<=r<=j-1:      len-T = 1-r,  beta = (m-2, m-3-r)    n= 171 exceptions=0 
      2.rj      r=j:            len-T = 1-r,  beta = (m-3, m-6-r)    n=  18 exceptions=0 
      3.g1      g=1:            len-T = -3,   beta = (m-2, m-5)      n=  18 exceptions=0 
      3.g       2<=g<=j-1:      len-T = 2-g,  beta = (m-2, m-2-g)    n= 153 exceptions=0 
      3.gj      g=j, j>=3:      len-T = -g,   beta = (m-2, m-8-g)    n=  17 exceptions=0 
      3.gj11    g=j=2 (m=11):   len-T = 0,    beta = (9, 3)          n=   1 exceptions=0 
      3.r0      r=0:            len-T = -1,   beta = (m-2, m-3)      n=  18 exceptions=0 
      3.r       1<=r<=j-1:      len-T = 1-r,  beta = (m-2, m-3-r)    n= 171 exceptions=0 
      3.r-top   r=j:            len-T = -r,   beta = (m-3, m-4-r)    n=  18 exceptions=0 
      3.rj+1    r=j+1 (j>=3):   len-T = 3-r,  beta = (m-2, m-9-r)    n=  17 exceptions=0 
      rows not covered by any row hypothesis: 0 []
      row hypotheses with exceptions or empty domain: 0 of 28
    
    coarse / unified hypotheses:
      C1 every rule row "2<=g<=j-1" (all m mod 4): len-T = 2-g                 n= 630 exceptions=35 [(12, 2, (-2, 9, 5)), (13, 2, (-1, 10, 8)), (16, 3, (-3, 13, 8)), (17, 3, (-2, 14, 11))]
      C2 2<=g<=j-2, all m mod 4: len-T = 2-g, beta = (m-2, m-2-g-2[m even])    n= 561 exceptions=0 
      C3 every r-interval row (0<=r, 1<=r ...) incl. its ends: len-T = 1-r     n= 738 exceptions=54 [(9, 9, (-1, 7, 6)), (11, 9, (-2, 8, 5)), (11, 11, (-1, 9, 8)), (13, 13, (-1, 11, 10))]
      C4 1<=r<=j-2, all m mod 4: len-T = 1-r, beta = (m-2, m-3-r)              n= 630 exceptions=0 
      C5 beta_0 = m-2 on every row                                             n=1600 exceptions=107 [(10, 1, (-1, 7, 4)), (10, 8, (-1, 7, 2)), (11, 9, (-2, 8, 5)), (12, 2, (-2, 9, 5))]
      C6 B = length (Lemma 1 base equals the word length)                      n=1600 exceptions=0 
      C7 B <= T and beta_0, beta_1 <= m-2 (criterion (7) numbers, weight 1)    n=1600 exceptions=0 

    $ PYTHONPATH=. python autoresearch/bound-m-260925/checks/wordg_formula_check.py 81 120   (excerpt)
    word_G rows m = 81..120: 2010
      1.gj9     g=j=2 (m=9):    len-T = 0,    beta = (7, 1)          n=   0 exceptions=0 
      3.gj11    g=j=2 (m=11):   len-T = 0,    beta = (9, 3)          n=   0 exceptions=0 
      rows not covered by any row hypothesis: 0 []
      row hypotheses with exceptions or empty domain: 2 of 28
      C1 every rule row "2<=g<=j-1" (all m mod 4): len-T = 2-g                 n= 910 exceptions=20 [(81, 19, (-18, 78, 59)), (84, 20, (-20, 81, 59)), (85, 20, (-19, 82, 62)), (88, 21, (-21, 85, 62))]
      C2 2<=g<=j-2, all m mod 4: len-T = 2-g, beta = (m-2, m-2-g-2[m even])    n= 870 exceptions=0 
      C3 every r-interval row (0<=r, 1<=r ...) incl. its ends: len-T = 1-r     n= 970 exceptions=30 [(81, 81, (-1, 79, 78)), (83, 63, (-20, 80, 59)), (83, 83, (-1, 81, 80)), (85, 85, (-1, 83, 82))]
      C4 1<=r<=j-2, all m mod 4: len-T = 1-r, beta = (m-2, m-3-r)              n= 910 exceptions=0 
      C5 beta_0 = m-2 on every row                                             n=2010 exceptions=60 [(81, 19, (-18, 78, 59)), (82, 1, (-1, 79, 76)), (82, 62, (-19, 79, 56)), (83, 63, (-20, 80, 59))]
      C6 B = length (Lemma 1 base equals the word length)                      n=2010 exceptions=0 
      C7 B <= T and beta_0, beta_1 <= m-2 (criterion (7) numbers, weight 1)    n=2010 exceptions=0 

The full per-row listing, with n, the range of length - T and the slope slack per rule row, is printed by the script
itself. These are finite checks of hypotheses that were read off the data. They are not proofs.
