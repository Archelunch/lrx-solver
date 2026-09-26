# word_C: proof of the length and Lemma 1 slope formulas, all m, both parities

Date 2026-09-26. Pen-and-paper proof, no provider calls, no code changes outside the new check script.
It closes the gaps listed in REVERSAL-ORBIT.md section 4 ("what remains to check before this is a proof")
and answers item 2 of the external review (downloads/lrx-solver-review-2900/REVIEW.md): "close the
inductive invariants of word_C for both parities".

The object of the proof is the Python function `word_C(m, a)` in `checks/reversal_m13.py` exactly as
written, including the tie rule of `goto`. B, beta_j, A_j and cz_j are the quantities computed by
`integrations/lrx_m.Profile`. Lemma 1, the cost formulas (4)-(5) and criterion (7) are the research
group's (m = 8 manuscript, applied with m as a parameter). The main conjecture stays open.

Mechanical companion: `checks/wordc_proof_check.py` rebuilds every intermediate claim below from the
closed formulas of this note and compares it with the literal execution of word_C. Its output is in
section 9.

## 0. Statement

**Theorem.** Let m >= 3 and 1 <= a <= m-2 be integers. (The request is m >= 9; nothing below uses more
than m >= 3.) Put n = m+2 and T = T_m(n) = m(m+1)/2 + m - 2. Then:

1. word_C(m, a) sorts u = (0, m, m-1, ..., 1, 0) to (1, ..., m, 0, 0).
2. Its length is T + 2(a - (m-2)/2)^2 - 1 - (m mod 2)/2.
3. Every segment of the word (the letters between two consecutive X) consists of one repeated letter,
   so the Lemma 1 base is B = length.
4. A = (a, a), and the Lemma 1 slopes are beta = (2a+1, 2a), except for a = 1 with m even, where
   beta = (4, 3).

**Corollary.** Let m >= 9.

- Odd m: the single word a = (m-3)/2 has B = T - 1 and beta = (m-2, m-3).
- Even m: a = (m-2)/2 has (B, beta) = (T-1, (m-1, m-2)), and a = (m-4)/2 has (B, beta) = (T+1, (m-3, m-4)).
  The mixture with weights 1/2, 1/2 has Bbar = T and betabar = (m-2, m-3).

Proof of the corollary from the theorem. Odd m: a - (m-2)/2 = -1/2, so length - T = 1/2 - 1 - 1/2 = -1.
The exception needs m even, so beta = (2a+1, 2a) = (m-2, m-3). Even m, a = (m-2)/2: a - (m-2)/2 = 0, so
length - T = -1, and beta = (m-1, m-2). Even m, a = (m-4)/2: the difference is -1, so length - T = 2 - 1 = 1,
and beta = (m-3, m-4). The exception a = 1 would need m = 4 or m = 6, and m >= 10 here. Both a lie in
[1, m-2]. The averages are (T-1 + T+1)/2 = T and ((m-1)+(m-3))/2, ((m-2)+(m-4))/2 = (m-2, m-3). QED.

## 1. Definitions

**Cells and executor.** Cells are the residues 0..n-1 mod n. All cell arithmetic below is mod n. The
state is a map from cells to contents. The cursor c starts at 0. L sets c := c+1. R sets c := c-1. X
swaps the contents of cells c and c+1. The visible vector is read from the cursor: (cell c, cell c+1, ...).
This is `lrx_m.run`. It equals `run_naive` on the visible vector, and it is also the model inside
word_C's own `step` and inside `Profile`.

**Initial state.** Cell 0 holds the zero Z0, cell j holds label m+1-j for 1 <= j <= m, and cell n-1 holds
the zero Z1. The zeros are distinguishable atoms. In `Profile`, Z0 is block 0 (gap 0) and Z1 is block 1
(gap m). Both are picks.

**Arcs.** For cells x, y, the arc [x..y] is x, x+1, ..., y (mod n). Its length is ((y-x) mod n) + 1.
"Reading an arc" lists contents from x upward.

**Lemma 1 terms, exactly as `Profile` computes them.** Number the X letters X_1..X_Q. Segment g
(0 <= g <= Q) is the set of letters strictly between X_g and X_{g+1}. X_0 is the start and X_{Q+1} is
the end. Each segment has a displacement d (+1 per L, -1 per R) and a vector cz = (cz_0, cz_1). They
receive contributions as follows.

- (P-L) An L executed while the cursor cell holds Z_j adds +1 to cz_j of its segment. The cell is read
  before moving.
- (P-R) An R whose destination cell holds Z_j adds -1 to cz_j of its segment. The cell is read after
  moving.
- (P-X1) If X_g has Z_j at the cursor and a label at c+1, then A_j += 1 and cz_j of segment g-1 (the
  segment ending at X_g) gets +1.
- (P-X2) If X_g has a label at c and Z_j at c+1, then A_j += 1 and cz_j of segment g (the segment
  starting after X_g) gets -1.
- An X with two zeros raises an error. An X with two labels contributes nothing.

Then B = Q + sum_g |d_g| and beta_j = 2 A_j + sum_g |cz_j(g)|.

**goto.** `goto(t)` from cursor c computes f = (t-c) mod n and b = (c-t) mod n. It emits L^f if f <= b,
otherwise R^b. `goto(t, 'R')` emits R^b. Note the tie rule: on f = b it goes L.

**word_C restated.** Let r = m - a (so r >= 2), q = ceil(a/2), p = floor(a/2), q + p = a, and
delta = q - p (0 if a is even, 1 if a is odd). Note n - 2 = m = p + q + r.

- A *sweep* of `grow` on an arc [lo..hi] of length l is one of:
  - an **r-sweep**: `goto(hi)`, then X (RX)^(l-1), then hi := hi+1;
  - an **l-sweep**: `goto(lo-1)`, then X (LX)^(l-1), then lo := lo-1.
- **Core 1** is `grow(n-1, 0, 'r', a)`: a sweeps on the arc starting at [n-1..0], sides r, l, r, l, ...
  Sweep k (1 <= k <= a) is an r-sweep iff k is odd.
- **Core 2** runs only because r > 1. It is `grow(start, start, first, r-1)` with first = 'r' if r is
  even and 'l' if r is odd, right = (r-1 + [first = 'r']) // 2 and start = n-2-p-right. Sweep i
  (1 <= i <= r-1) has side first when i is odd and the other side when i is even.
- The walk emitted by the first `goto` of core 2 is called **W0**.
- **Wf** is `goto(position of label 1, 'R')`.

## 2. The sweep lemma

**Lemma S.** Let [lo..hi] be an arc of length l with 1 <= l <= n-2, and let x_0, ..., x_{l-1} be the
contents of lo, ..., hi.

(r) Suppose the cursor is on hi, e is the content of hi+1, and the letters X (RX)^(l-1) are executed.
For t = 1..l, just before X_t the following hold:
  - the cursor is on lo+l-t, which holds x_{l-t};
  - cell lo+l-t+1 holds e;
  - cells lo+l-t+2 .. hi+1 hold x_{l-t+1} .. x_{l-1};
  - cells lo .. lo+l-t-1 hold x_0 .. x_{l-t-1}.

Afterwards, the arc [lo..hi+1] reads (e, x_0, ..., x_{l-1}), the cursor is on lo, and no other cell has
changed.

(l) Suppose the cursor is on lo-1, e is the content of lo-1, and the letters X (LX)^(l-1) are executed.
For t = 1..l, just before X_t the following hold:
  - the cursor is on lo+t-2, which holds e;
  - cell lo+t-1 holds x_{t-1};
  - cells lo-1 .. lo+t-3 hold x_0 .. x_{t-2};
  - cells lo+t .. hi hold x_t .. x_{l-1}.

Afterwards, [lo-1..hi] reads (x_0, ..., x_{l-1}, e), the cursor is on hi-1, and cell hi-1 holds x_{l-1}.

*Proof.* Since l <= n-2, the l+1 cells involved are distinct residues, so the bookkeeping is unambiguous.

- (r), t = 1: this is the hypothesis.
- (r), step: X_t swaps x_{l-t} (cursor) with e (cursor+1). Now e is on lo+l-t and x_{l-t} on lo+l-t+1.
  If t < l, the next letter R moves the cursor to lo+l-t-1, which holds x_{l-t-1}. That is the claim for
  t+1. After X_l, e is on lo, x_0..x_{l-1} are on lo+1..hi+1, and the cursor is on lo.
- (l), t = 1: this is the hypothesis.
- (l), step: X_t swaps e (cursor) with x_{t-1} (cursor+1). Now x_{t-1} is on lo+t-2 and e on lo+t-1.
  If t < l, the next letter L moves the cursor to lo+t-1, which holds e. That is the claim for t+1.
  After X_l, x_{l-1} is on lo+l-2 = hi-1, e is on hi, and the cursor is on hi-1. QED.

**Corollary S (Lemma 1 terms of a sweep).** Assume e is a label. Then:

- (S1) Every X of the sweep swaps e with exactly one arc element, and each arc element exactly once.
  So no X swaps two zeros, and A_j grows by exactly 1 iff Z_j lies in the arc.
- (S2) Every segment strictly inside the sweep, between X_t and X_{t+1}, is a single letter and has
  cz = 0.
  - r-sweep: X_t has e at c+1, so there is no (P-X2) term. The R arrives on a cell holding x_{l-t-1},
    giving -1 if that is Z_j. X_{t+1} has x_{l-t-1} at the cursor, giving +1 by (P-X1) if that is Z_j.
    The sum is 0.
  - l-sweep: X_t has x_{t-1} at c+1, giving -1 by (P-X2) if that is Z_j. The L leaves cell lo+t-2,
    which now holds x_{t-1}, giving +1 if that is Z_j. X_{t+1} has e at the cursor, so there is no
    (P-X1) term. The sum is 0.
- (S3) Boundary terms.
  - r-sweep: the first X adds +1 to cz_j of the segment before the sweep iff x_{l-1} = Z_j, since
    x_{l-1} is the content of hi. The last X has e at c+1, so it adds nothing to the segment after.
  - l-sweep: the first X has e at the cursor, so it adds nothing to the segment before. The last X adds
    -1 to cz_j of the segment after the sweep iff x_{l-1} = Z_j, and afterwards the cursor cell hi-1
    holds x_{l-1}.

**Lemma W (inter-sweep walks).** Assume n >= 3.

- After an r-sweep the cursor is on lo, and the next l-sweep calls `goto(lo-1)`. Then f = n-1 > 1 = b,
  so the walk is exactly one R, arriving on lo-1.
- After an l-sweep the cursor is on hi-1, and the next r-sweep calls `goto(hi)`. Then f = 1 <= n-1 = b,
  so the walk is exactly one L, leaving hi-1.

## 3. Lemma A (core 1)

For 0 <= k <= a, put q_k = ceil(k/2), p_k = floor(k/2) (so q_k + p_k = k), lo_k = n-1-p_k,
hi_k = q_k, and

    S_k = (m-q_k+1, ..., m, Z1, Z0, 1, ..., p_k)      (length q_k + 2 + p_k = k+2).

**Lemma A.** After the first k sweeps of core 1 (each with its preceding walk):

- (A1) The variables of `grow` are lo = lo_k and hi = hi_k. The arc [lo_k..hi_k] has length k+2.
- (A2) The arc [lo_k..hi_k] reads S_k.
- (A3) The cells j = q_k+1, ..., n-2-p_k form an integer range with no wrap. There are m-k >= 2 of them,
  and each still holds its initial label m+1-j. These cells and the arc partition all n cells.
- (A4) The cursor is on 0 if k = 0, on lo_k if k is odd, and on hi_k - 1 = q_k - 1 if k >= 2 is even.
- (A5) For k >= 1, the letters of step k are w_k followed by the sweep. The walk w_k is empty for
  k = 1, one R for even k, and one L for odd k >= 3. The sweep is X (RX)^k for odd k and X (LX)^k for
  even k.

*Proof by induction on k.*

**Base, k = 0.** lo = n-1 and hi = 0. The arc [n-1..0] has length 2 and reads (Z1, Z0) = S_0. Cells
1..n-2 are untouched, and the cursor is on 0.

**Arc length.** The code sets ln = ((hi-lo) mod n) + 1. With hi_k - lo_k = q_k + p_k + 1 - n = k+1-n and
0 <= k+1 < n, this gives ln = k+2. So sweep k+1 has l = k+2 and 2l-1 = 2k+3 letters, which is (A5) for
k+1. Also l = k+2 <= a+1 <= m-1 = n-3, so Lemma S applies.

**Step k -> k+1, k even (sweep k+1 is an r-sweep).**

- The walk is `goto(hi_k)`. If k = 0 the cursor is already on 0 = hi_0, so the walk is empty. If
  k >= 2 the cursor is on hi_k - 1 by (A4), so by Lemma W the walk is one L.
- The carried element is e = content of hi_k + 1 = q_k + 1. This cell is in the range of (A3), because
  q_k + 1 <= n-2-p_k is equivalent to m - k >= 1. So e = m - q_k, a label.
- By Lemma S(r), the arc [lo_k..hi_k+1] reads (m-q_k, S_k), and the cursor is on lo_k.
- Now q_{k+1} = q_k + 1 and p_{k+1} = p_k. So lo_{k+1} = lo_k, hi_{k+1} = hi_k + 1, and
  (m-q_k, S_k) = S_{k+1}. This is (A1), (A2) and (A4) for the odd index k+1.
- The range of (A3) loses exactly its lowest cell q_k+1. No other cell was touched.

**Step k -> k+1, k odd (sweep k+1 is an l-sweep).**

- The cursor is on lo_k by (A4). The walk `goto(lo_k - 1)` is one R by Lemma W.
- The carried element is e = content of lo_k - 1 = n-2-p_k. This cell is the top of the range of (A3),
  and the range is nonempty. So e = m+1-(n-2-p_k) = p_k + 1, a label.
- By Lemma S(l), the arc [lo_k - 1..hi_k] reads (S_k, p_k+1), and the cursor is on hi_k - 1.
- Now p_{k+1} = p_k + 1 and q_{k+1} = q_k. So lo_{k+1} = lo_k - 1, hi_{k+1} = hi_k, and
  (S_k, p_k+1) = S_{k+1}. The cursor is on q_{k+1} - 1, which is (A4) for the even index k+1.
- The range of (A3) loses exactly its top cell. QED.

**The cyclic wrap.** The arc [lo_k..hi_k] is {n-1-p_k, ..., n-1} together with {0, ..., q_k}. It always
contains the edge between n-1 and 0. The proof never compares cells as integers across this edge. It only
uses Lemma S, which is stated mod n and needs l <= n-2, and the executor, whose X at cursor n-1 swaps
cells n-1 and 0 (`j = (c+1) % n`) and whose R at 0 goes to n-1. The only integer ranges used are those of
(A3), which lie inside 1..m.

**Explicit end state of core 1 (k = a).** Write q = q_a and p = p_a.

- a even (delta = 0):
  - cells n-1-p .. n-2 hold m-p+1 .. m;
  - cell n-1 holds Z1, and cell 0 holds Z0;
  - cells 1 .. p hold 1 .. p;
  - the cursor is on p-1.
- a odd (delta = 1):
  - cells n-1-p .. n-1 hold m-p .. m;
  - cell 0 holds Z1, and cell 1 holds Z0;
  - cells 2 .. p+1 hold 1 .. p;
  - the cursor is on n-1-p.
- In both parities, the region R2 = cells q+1 .. n-2-p holds its initial labels m-q, ..., p+1 (cell j
  holds m+1-j). R2 has r cells, is an integer range inside 1..m, and contains no zero. In compact form:
  Z1 is on delta-1, Z0 is on delta, and label i (1 <= i <= p) is on delta+i.

**Zero boundary terms of core 1 (from Corollary S).** Every carried element is a label, so S1-S3
apply. The element x_{l-1} is the last entry of S_{k-1}, which is the content of hi before sweep k. It is
p_{k-1} if p_{k-1} >= 1 and Z0 if k-1 <= 1.

- Sweep 1 (r, arc S_0 = (Z1, Z0)): its first X adds +1 to cz_0 of segment 0.
- Sweep 2 (l, arc S_1 = (m, Z1, Z0)): its last X adds -1 to cz_0 of the segment that follows. After it,
  the cursor cell hi_2 - 1 = 0 holds Z0.
- Every other sweep has boundary terms 0.

Since the zero block lies in every arc, (S1) gives **A_0 = A_1 = a** from core 1.

## 4. Lemma B (core 2)

**Bookkeeping of first, right and start.** Sides alternate starting from first, over r-1 sweeps.

- **r even.** Then first = r. The sides are r, l, ..., r, since r-1 is odd. There are r/2 r-sweeps and
  r/2 - 1 l-sweeps. The code gives right = (r-1+1)//2 = r/2.
- **r odd.** Then first = l. The sides are l, r, ..., r, since r-1 is even. There are (r-1)/2 sweeps of
  each side. The code gives right = (r-1)//2 = (r-1)/2.

In both cases right is the number of r-sweeps, and the **last sweep is an r-sweep**. Let rho_i and
lambda_i be the numbers of r-sweeps and l-sweeps among the first i sweeps, and set
lo'_i = start - lambda_i and hi'_i = start + rho_i. Then:

- hi'_{r-1} = start + right = n-2-p;
- lo'_{r-1} = start - (r-1-right) = n-2-p-(r-1) = q+1, using n-2 = p+q+r.

So core 2 ends exactly on R2 = [q+1..n-2-p]. Since lo'_i is non-increasing and hi'_i is non-decreasing,
q+1 <= lo'_i <= start <= hi'_i <= n-2-p for every i. In particular start is in R2, because
right <= r-1. Every core-2 arc is an integer sub-range of R2, and no index wraps.

**Lemma B.** For 0 <= i <= r-1, after i sweeps of core 2:

- (B1) The variables of `grow` are lo = lo'_i and hi = hi'_i. The arc has length i+1.
- (B2) Cell j in [lo'_i..hi'_i] holds m+1-(lo'_i + hi'_i - j). So the arc reads the increasing
  consecutive labels m+1-hi'_i, ..., m+1-lo'_i.
- (B3) The cells of R2 outside the arc hold their initial labels. The cells outside R2 hold exactly what
  they held at the end of core 1.
- (B4) For i >= 1, the cursor is on lo'_i if sweep i is an r-sweep and on hi'_i - 1 if it is an l-sweep.
- (B5) For i >= 1, sweep i has length l = i and letters X (RX)^(i-1) or X (LX)^(i-1). For i >= 2 it is
  preceded by one R if sweep i-1 was an r-sweep and one L if it was an l-sweep. Sweep 1 is preceded by
  W0.

*Proof by induction on i.*

**Base, i = 0.** The arc is the single cell start, which holds m+1-start. This matches (B2) with
lo' = hi' = start.

**Step i -> i+1.** The length is l = i+1 <= r-1 <= n-2, so Lemma S applies. The walk for i >= 1 is
given by Lemma W.

- **r-sweep.** Here hi'_i + 1 = hi'_{i+1} <= n-2-p, so the cell hi'_i + 1 is in R2 and outside the arc.
  It holds e = m - hi'_i. By Lemma S(r), the arc [lo'_i..hi'_i + 1] reads
  (m-hi'_i, m+1-hi'_i, ..., m+1-lo'_i). This is (B2) with hi' raised by 1. The cursor is on lo'_i.
- **l-sweep.** Symmetrically, the cell lo'_i - 1 = lo'_{i+1} >= q+1 holds e = m+2-lo'_i. The arc
  [lo'_i - 1..hi'_i] reads (m+1-hi'_i, ..., m+1-lo'_i, m+2-lo'_i). This is (B2) with lo' lowered by 1.
  The cursor is on hi'_i - 1.
- No cell outside the arc and its new neighbour was touched. QED.

**End state of core 2.** The cursor is on lo'_{r-1} = q+1. Cell j of R2 holds
m+1-(q+1+n-2-p-j) = j - delta. With the end state of core 1, cells delta+1, ..., delta+m hold labels
1, ..., m in order:

- delta+1 .. delta+p hold 1..p;
- q+1 .. m-p hold p+1 .. m-q;
- m-p+1 .. m+delta hold m-q+1 .. m.

Cells delta-1 and delta hold Z1 and Z0.

**Terms of core 2.** Every element of every core-2 arc, and every carried element, is a label of R2. By
(S1)-(S3) the core-2 sweeps contribute nothing to A and nothing to any cz. By Lemma W and (B3), every
inter-sweep walk of core 2 moves only between cells of R2, which hold labels, so it contributes nothing.

## 5. Lemma C (the walks W0 and Wf)

Let c0 be the cursor after core 1: c0 = n-1-p if a is odd, and c0 = p-1 if a is even. The first `goto`
of core 2 targets t = start if first = r (r even), and t = start - 1 if first = l (r odd). In each case
below, f = (t - c0) mod n and b = (c0 - t) mod n = n - f. The contents of cells are those at the end of
core 1 (section 3).

**Case C1: a odd, r even.**
- t = n-2-p-r/2, so b = c0 - t = r/2 + 1, and 0 < b < n.
- f - b = n - 2b = n - r - 2 = a > 0, so the walk goes R.
- W0 = R^(r/2+1). It arrives on n-2-p, ..., t.
- t - (q+1) = (r-1) - r/2 = r/2 - 1 >= 0, so every arrival cell is in R2 and holds a label.
- There are no zero terms.

**Case C2: a odd, a >= 3, r odd.**
- t = start - 1 = n-3-p-(r-1)/2, so b = (r+3)/2.
- f - b = n - r - 3 = a - 1 >= 2 > 0, so the walk goes R.
- W0 = R^((r+3)/2). It arrives on n-2-p, ..., t.
- t - (q+1) = (r-3)/2 >= 0, since r is odd and >= 2, hence >= 3. So the arrivals lie in R2.
- There are no zero terms.

**Case C3: a = 1, r odd (equivalently a = 1, m even).**
- Here p = 0, q = 1, n = r + 3, c0 = n-1, and t = n-3-(r-1)/2, so b = (r+3)/2 = n/2 = f.
- This is a **tie**, so `goto` goes L. W0 = L^((r+3)/2).
- It leaves the cells n-1, 0, 1, ..., (r-1)/2. Since r >= 3, this list contains both 0 and 1.
- After core 1, cell n-1 holds m, cell 0 holds Z1, cell 1 holds Z0, and cells 2..m hold labels.
- So W0 adds **+1 to cz_1** (leaving cell 0) and **+1 to cz_0** (leaving cell 1), and nothing else.
- Its length equals the non-tie length b = (r+3)/2.

**Case C4: a even, r even.**
- Here c0 = p-1 >= 0 and t = n-2-p-r/2 <= n-2-p, so t - c0 = n-1-a-r/2 = r/2 + 1 = f with no wrap.
- 2f = r + 2 < n, so f < b and the walk goes L. W0 = L^(r/2+1).
- It leaves the cells p-1, p, ..., p-1+r/2.
- Cell p-1 holds Z0 if p = 1, because it is cell 0. It holds label p-1 if p >= 2.
- Cell p holds label p.
- Cells p+1 .. p-1+r/2 lie in R2 = [p+1..n-2-p], because r/2 - 1 <= r - 1.

**Case C5: a even, r odd.**
- t = n-3-p-(r-1)/2, so f = t - c0 = n-2-a-(r-1)/2 = (r+1)/2 >= 2.
- 2f = r + 1 < n, so the walk goes L. W0 = L^((r+1)/2).
- It leaves the cells p-1, p, ..., p-2+(r+1)/2. The analysis is the same as in C4.

**Lemma C.**

- (C-len) W0 has r/2 + 1 letters if r is even, (r+3)/2 if a and r are both odd, and (r+1)/2 if a is
  even and r is odd.
- (C-dir) W0 is one repeated letter: R in C1 and C2, and L in C3, C4 and C5.
- (C-zero) W0 passes a zero only in two cases:
  - a = 2 (C4 or C5 with p = 1): its first letter leaves cell 0, which holds Z0, giving +1 to cz_0.
  - a = 1 with r odd (C3): it gives +1 to cz_1 and +1 to cz_0.
- (C-f) Wf = R^p ends on label 1 and passes no zero, as shown below.

**Proof of (C-f).** After core 2, the cursor is on q+1 by (B4), since the last sweep is an r-sweep.
Label 1 is on cell delta+1 = q-p+1 (for p = 0 this is q+1 itself). So `goto(delta+1, 'R')` emits
R^((q+1-(q-p+1)) mod n) = R^p. It arrives on q, q-1, ..., q-p+1, which hold p, ..., 1. With the cursor
on delta+1, the visible vector is (label 1, ..., label m, Z1, Z0) = (1, ..., m, 0, 0), because cells
delta+m+1 = delta-1 and delta+m+2 = delta (mod n) hold Z1 and Z0. This proves part 1 of the theorem.

## 6. Lemma D (letter count)

By (A5), core 1 has walks 0, 1, ..., 1 (a-1 ones) and sweeps of 2k+1 letters for k = 1..a:

    core 1 = sum_{k=1..a} (2k+1) + (a-1) = a^2 + 3a - 1.

By (B5), core 2 without W0 has sweeps of 2i-1 letters for i = 1..r-1 and r-2 one-letter walks:

    core 2 = (r-1)^2 + r - 2.

So the total is

    len = a^2 + r^2 + 3a - r - 2 + W0 + p.

The four cases of W0 give:

| case | W0 | p | len |
|---|---|---|---|
| a even, r even (m even) | r/2+1 | a/2 | a^2 + r^2 + 7a/2 - r/2 - 1 |
| a odd, r odd (m even) | (r+3)/2 | (a-1)/2 | a^2 + r^2 + 7a/2 - r/2 - 1 |
| a odd, r even (m odd) | r/2+1 | (a-1)/2 | a^2 + r^2 + 7a/2 - r/2 - 3/2 |
| a even, r odd (m odd) | (r+1)/2 | a/2 | a^2 + r^2 + 7a/2 - r/2 - 3/2 |

So len = a^2 + r^2 + 7a/2 - r/2 - 1 - epsilon, where epsilon = (m mod 2)/2. Substitute r = m - a:

    len = 2a^2 - 2am + m^2 + 4a - m/2 - 1 - epsilon.

With T = m^2/2 + 3m/2 - 2 this gives

    len - T = 2a^2 - 2am + 4a + m^2/2 - 2m + 1 - epsilon.

On the other side,

    2(a - (m-2)/2)^2 = 2a^2 - 2a(m-2) + (m-2)^2/2 = 2a^2 - 2am + 4a + m^2/2 - 2m + 2.

Hence len - T = 2(a - (m-2)/2)^2 - 1 - epsilon. This is part 2 of the theorem.

The number of swaps is Q = sum_{k=1..a} (k+1) + sum_{i=1..r-1} i = a(a+3)/2 + r(r-1)/2.

## 7. Lemma E (segments and cz accounting)

By (A5), (B5) and Lemma C, the word is the concatenation

    w_1 S_1 w_2 S_2 ... w_a S_a  W0  S'_1 w'_2 S'_2 ... w'_{r-1} S'_{r-1}  Wf

Here each sweep S begins and ends with X and has exactly one letter between consecutive X's. w_1 is empty,
the other w's are single letters, and W0 and Wf are powers of one letter. So the maximal X-free pieces,
which are the segments, are exactly:

- (E0) the empty segment before X_1;
- (E1) the single letter inside a sweep;
- (E2) a core-1 walk w_k, k >= 2;
- (E3) W0;
- (E4) a core-2 walk w'_i;
- (E5) Wf, which is empty if p = 0.

Each segment is one repeated letter, so |d_g| is its letter count and B = Q + sum |d_g| = len. This is
part 3 of the theorem. (Also d_g and every nonzero cz_j(g) below have the same sign, so `Profile`
reports same_sign.)

**The cz of each segment.** Every term comes from (P-L), (P-R), (P-X1) at the X ending the segment, and
(P-X2) at the X starting it.

- **(E0)** X_1 is the first X of core-1 sweep 1. The cursor is on 0, which holds Z0, and cell 1 holds the
  label m. So cz = (+1, 0). This is the single surviving +1.
- **(E1)** cz = 0, by (S2) for both cores.
- **(E2), k even >= 2.** This is the walk R after r-sweep k-1, before l-sweep k.
  - The last X of an r-sweep adds nothing (S3).
  - The R arrives on lo_{k-1} - 1, the top cell of the (A3) range, which holds a label.
  - The first X of an l-sweep adds nothing (S3).
  - So cz = 0.
- **(E2), k odd >= 5.** This is the walk L after l-sweep k-1, before r-sweep k.
  - The last X of l-sweep k-1 adds -1 to cz_j iff the last entry of S_{k-2} is Z_j. That entry is
    p_{k-2} >= 1, a label, because k-2 >= 3.
  - The L leaves hi_{k-1} - 1, which holds that same entry. So its term is +1 iff that entry is Z_j.
  - The first X of r-sweep k has the cursor on hi_{k-1}, which holds the last entry of S_{k-1}, the
    label p_{k-1} >= 2.
  - So cz = 0. The walk touches no zero.
- **(E2), k = 3.** This is the walk L after l-sweep 2, before r-sweep 3.
  - The last X of sweep 2 adds -1 to cz_0, because the last entry of S_1 = (m, Z1, Z0) is Z0.
  - The L leaves cell hi_2 - 1 = 0, which holds Z0, giving +1 to cz_0.
  - The first X of sweep 3 has the cursor on hi_2 = 1, which holds the label 1 = p_2.
  - So cz = (-1+1, 0) = 0. This is the "l-sweep boundary case" of the sketch, written out.
- **(E3) W0.** There are three sources of terms.
  - The last X of core 1. If a is odd, it is an r-sweep and adds nothing. If a is even, it adds -1 to
    cz_0 iff the last entry of S_{a-1} is Z0, that is iff p_{a-1} = 0, that is iff a = 2.
  - The first X of core 2 adds nothing, since its arc and carried element are labels (S3).
  - The walk itself contributes per (C-zero).

  Summing:
  - a = 2: cz = (-1+1, 0) = 0.
  - a = 1, r odd: cz = (+1, +1).
  - all other (a, r): cz = 0.
- **(E4)** cz = 0 (section 4, terms of core 2).
- **(E5)** The last X of core 2 is in an r-sweep and adds nothing. The arrivals are on labels by (C-f).
  So cz = 0.

**A.** By section 3, core 1 gives A = (a, a). Core 2 and the walks contain no X involving a zero.

**Slopes.**

    beta_j = 2 A_j + sum_g |cz_j(g)|.

The only nonzero cz are (E0), with (1, 0), and in the case a = 1, m even, (E3), with (1, 1). Hence
beta = (2a+1, 2a) in general, and beta = (2+1+1, 2+1) = (4, 3) for a = 1, m even. This is part 4 of the
theorem. QED.

**Small cases, written out once.**

- **a = 1.** Core 1 is one r-sweep X RX over (Z1, Z0), carrying m. Then:
  - if r is even (m odd), W0 = R^(r/2+1) and beta = (3, 2);
  - if r is odd (m even), W0 is the tie L^(r/2+3/2) and beta = (4, 3);
  - Wf is empty.
- **a = 2.** Core 1 is XRX, then R, then XLXLX. The last X has Z0 at c+1, giving -1. W0 starts with an
  L out of cell 0, which holds Z0, giving +1. Then Wf = R.

## 8. What this proof does NOT cover

- **Lemma 1 itself.** The proof computes B and beta exactly as `lrx_m.Profile` defines them. It does not
  prove that B + beta . z bounds the length of a sorting word for the stretched states. That is the
  group's Lemma 1 with formulas (4)-(5), applied at general m.
- **Criterion (7).** The numbers of the corollary satisfy the inequalities that
  `lrx_m.mixture_criterion` encodes: Bbar < T + 1 and betabar_j <= m - 2. The claim that these
  inequalities imply d(v) <= T_m(n) for every state of the family at every block length is criterion (7),
  which is the group's. So "the mixture certifies (m..1){0,m} for all m >= 9" follows from this proof
  **only together with** Lemma 1 and criterion (7) at general m. Neither is proved here.
- **Other parameter values.** a = m-1 (r = 1, no core 2) and a = m (r = 0) are not covered. The
  conjectured length formula is known to fail at a = 2 floor(m/2).
- **Other code.** The proof is about the function word_C as it stands in `checks/reversal_m13.py`. A
  change to `goto`'s tie rule would change case C3.
- **Minimality.** The proof gives no statement that these words are shortest, and no distance or radius.

## 9. Mechanical check

`checks/wordc_proof_check.py` (stdlib; imports word_C and lrx_m; writes nothing) predicts from the
formulas above, without calling grow or goto:

- the block decomposition of the word into w_k, S_k, W0, S'_i, w'_i and Wf, compared as strings with
  word_C(m, a);
- the full cell map and cursor after every sweep of both cores (Lemmas A and B);
- the zeros passed by every walk: none, except Z0 in w_3, Z0 in W0 for a = 2, and Z1 then Z0 in W0 for
  the tie;
- the end cursor of W0 and Wf, the final state (1..m, Z1, Z0), and the replay with run_naive;
- the letter counts of Lemma D, the length formula, and Q;
- the segment count, unidirectionality and |d| = letter count;
- the cz of every segment, from its own executor and from lrx_m.Profile;
- A, B, beta and same_sign from lrx_m.Profile;
- the right/start formulas of the code;
- the corollary values for m >= 9.

Before it was finalized, two mutations were each detected: shifting one core-1 cursor gave 45
mismatches, and dropping the tie exception gave 12.

    $ PYTHONPATH=. python autoresearch/bound-m-260925/checks/wordc_proof_check.py
    m = 9..40, pairs (m, a) with 1 <= a <= m-2: 720
    mismatches (Lemmas A-E, theorem): 0
    corollary failures: 0 []

    $ PYTHONPATH=. python autoresearch/bound-m-260925/checks/wordc_proof_check.py 3 8
    m = 3..8, pairs (m, a) with 1 <= a <= m-2: 21
    mismatches (Lemmas A-E, theorem): 0
    corollary failures: 0 []

A first version of the script asserted that no inter-sweep walk and no W0 ever passes a zero. That is
stronger than the proof. It reported exactly the two predicted, cancelled passes: w_3 in every a >= 3
row, and W0 at a = 2. The script was then aligned with the proof's exact statements (E2, k = 3) and
(C-zero). The proof text was not changed. The script run is a finite check. The proof above is what
covers all m.

`checks/` is gitignored in this directory. The script must be force-added if it is to be committed.
