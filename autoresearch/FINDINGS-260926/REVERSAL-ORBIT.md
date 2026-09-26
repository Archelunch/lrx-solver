# Reversal orbit beyond (m..1){0,m}: insertion-core words, trees, and a hand count for word_C

Date 2026-09-26. Offline construction. There were no provider calls, no tables, no LLM-generated code and no commits.
Lemma 1 (with refinement), the cost formulas (4)-(6) and criteria (7)/(8) are the research group's (m=8 manuscript).
`integrations/lrx_m.py`, `bound3_evaluator.py` and `bound3_audit.py` apply them with m as a parameter.
The main conjecture stays open. Every certificate below is conditional on that Lemma and those criteria.

- Verification script: `checks/reversal_orbit.py`. It does not search. It re-scores every stored output, audits
  it, replays it, builds the closed-form rows and writes `checks/reversal-orbit-words.json`. It refuses to overwrite
  and runs in 2.4 s.
- Search scripts, exactly as run: `checks/reversal_orbit_search/` (`gen.py`, `fast.py`, `engine.py`, `survey.py`,
  `regen.py`, `local.py`, `formula.py`, `params.py`). Their raw results and logs are copied there unchanged.
- Reproduce the checks with `PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_orbit.py`.

## 1. Results

**111 stored certificates, all CERTIFIED by `score_output`, all confirmed `[True, 'ok']` by `audit_claim`, and every
leaf word replays to the root under `run_naive` and `run`.** In addition, one new closed-form word certifies the family
(m..1){1,m} at every m = 9..40.

### (a) The reversal m..1 with k = 2 zeros

| target | certified | how | binding constraint where not certified |
|---|---|---|---|
| {0,m} (mask 4097 at m=12) | m = 9..40 | word_C, REVERSAL-M13.md. The search here re-finds the m=12 pair (87, (11,10)) and (89, (9,8)), weights 1/2 each | none |
| {1,m} (mask 4098 at m=12) | **m = 9..40** by evaluator and audit, m = 41..200 by replay and criterion (7) only | **one closed-form word word_R1(m)**, section 2 | none |
| {0,4} | **m = 10..16** | m=10, 11: two-leaf tree. m = 12..16: root leaf | **m = 9 not certified.** The root LP has min Bbar - T = 7/3 with slopes feasible, so the base binds. Trees with origins (2,1), (1,2), (3,1), (1,3), (2,2), depth <= 3 and thresholds <= 5 found nothing |
| all C(m+1,2) masks, m = 9 | 42 of 45 | root leaf, 1 to 3 words | {0,4}, {0,5}, {5,9}: root min Bbar - T = 7/3, 4, 1; slopes feasible; trees as above found nothing |
| all C(m+1,2) masks, m = 10 | 53 of 55 | 51 root leaves, {0,4} 2 leaves, {6,10} 3 leaves | {0,5}, {0,6}: root min Bbar - T = 17/4, 4; slopes feasible; no tree found |
| all masks, m = 11..16 | **not run** | CPU budget | only {0,m}, {1,m} and {0,4} were run at these m |

**Why "the base binds" matters.** Every miss has slopes <= m-2 feasible at the root (t = 0). Only the mixture base
is too large. So the failures are in the word pool, not an obstruction; a tree with refined origins lowers the
effective base, but the origins tried were not enough.

The trees, as returned by `score_output`. The format is box, origins, then support (weight, base, beta).

- **{0,4}, m = 10.** Leaf u_0 = 1: one word, (1, 53, (12,0)), lhs -10. Leaf u_0 >= 2 with origin (2,1):
  (1/5, 63, (12,0)) and (4/5, 74, (7,9)), lhs 4/5.
- **{0,4}, m = 11.** Leaf u_0 = 1: (1, 66, (12,0)), lhs -9. Leaf u_0 >= 2 with origin (2,1): (2/5, 76, (12,0))
  and (3/5, 90, (7,9)), lhs 2/5.
- **{6,10}, m = 10.** Three unit-origin leaves:
  - u = (1,1): (1, 55, (1,11));
  - u_0 = 1, u_1 >= 2 with origin (1,2): (1, 71, (4,8)), lhs 0;
  - u_0 >= 2: (1, 65, (4,8)).
- **{0,4}, m = 12..16, root leaf.**

  | m | T | support | lhs |
  |---|---|---|---|
  | 12 | 88 | (3/5, 80, (12,0)), (2/5, 100, (7,9)) | 0 |
  | 13 | 102 | (4/5, 97, (12,0)), (1/5, 120, (7,9)) | -2/5 |
  | 14 | 117 | (1, 115, (12,0)) | -2 |
  | 15 | 133 | (1/2, 128, (14,2)), (1/2, 136, (12,0)) | -1 |
  | 16 | 150 | (1, 148, (14,2)) | -2 |

  The words with slope (12,0) never cross the zero at gap 4. From m = 14 on, a single word certifies.

### (b) The reversal m..1 with k = 3 zeros

**Not run as a class.** The CPU budget went to (a) and (c). The k = 3 families that were run are all rotations or
perturbations of the reversal, from list (c). Three of them certified:

- 4.3.2.1.12..5 {0,4,12}: root leaf, (5/6, 86, (1,11,0)) and (1/6, 120, (7,5,8)), lhs -19/3 at T = 98;
- 2.1.12..3 {2,5,10}: a two-leaf tree;
- 4.3.2.1.11..5 {0,4,7} at m = 11.

### (c) The 14 families all arms miss at m = 12, and the m = 11 misses

| family | k | arms' gaps (Ada-s2 / EvoX-s3 / seed / (b)) | here | certificate or binding constraint |
|---|---|---|---|---|
| 12..1 {0,12} (4097) | 2 | 5 / 5 / 5 / 5 | **CERTIFIED** | root: (1/2, 87, (11,10)), (1/2, 89, (9,8)). This is word_C's support |
| 12..1 {1,12} (4098) | 2 | 3 / 3 / 3 / 3 | **CERTIFIED** | root: word_R1(12), (1, 86, (8,10)) |
| near_rev 11..3.1.2.12 {4,11} (2064) | 2 | 13/16 / 5/14 / 1 / 27/8 | **CERTIFIED** | root: (1/3, 74, (0,14)), (2/3, 96, (6,8)), lhs 2/3 |
| near_rev 1.12.10.11.9..2 {1,7} (130) | 2 | 25/11 / 25/11 / 7/3 / 7/3 | not found | base binds: root min Bbar - T = 74/15, slopes feasible. The tree search with 5 origins found nothing |
| 4.3.2.1.12..5 {0,4,12} (4113) | 3 | 10/11 / 0 / 10/7 / 10/7 | **CERTIFIED** | root, see (b) |
| 2.1.12..3 {2,5,10} (1060) | 3 | 4 / 5 / 5 / 5 | **CERTIFIED** | tree: u_0 = 1 gets (1, 93, (16,7,8)), lhs -5; u_0 >= 2 with origin (2,1,1) gets (1/2, 105, (11,15,0)) and (1/2, 111, (9,0,15)), lhs 0 |
| near_rev 1.12..7.5.6.4.3.2 {0,6,10} (1089) | 3 | 13/11 / 7/3 / 7/3 / 29/9 | **CERTIFIED** | root: (1, 92, (10,9,3)), lhs -6 at T = 98 |
| 3.2.1.12..4 {1,4,8,12} (4370) | 4 | 1 / 37/35 / 37/35 / 9/5 | **CERTIFIED** | root, 3 words, lhs -107/43 |
| 10..1.12.11 {2,7,10,12} (5252) | 4 | 4/3 / 16/11 / 16/11 / 103/33 | **CERTIFIED** | root, 4 words, lhs 11/91 |
| near_rev 12..4.2.3.1 {0,2,5,7} (165) | 4 | 5/3 / 1 / 17/7 / 59/16 | **CERTIFIED** | root, 3 words, lhs 10/21 |
| 12..1 mask 7300 | 5 | 5/7 on all four | not found | base binds: root min Bbar - T = 37838/6993, about 5.41, slopes feasible. Origins with one coordinate 2 found nothing |
| refl 12..1 {4,5,6,7,8,12} (4592) | 6 | 19/23 / 1489/11821 / 1 / 44/27 | **CERTIFIED** | root, 3 words, lhs -179/33 |
| refl 2.1.12..3 mask 6309 | 6 | 48/73 on three arms | **not completed** | the tree search was stopped for CPU |
| 2.1.12..3 mask 3534 | 8 | 38/287 / 69/202 / 69/202 / 410/423 | **not completed** | the tree search was stopped for CPU |
| m=11 5.4.3.2.1.11..6 {5,10} (1056) | 2 | REVERSAL-OBSTACLE.md | not found | base binds: root min Bbar - T = 2, slopes feasible. Earlier arm pools had slopes infeasible (t = 3/8); this pool removes that obstruction. No tree was found |
| m=11 4.3.2.1.11..5 {0,4,7} (145) | 3 | | **CERTIFIED** | root: (1/3, 81, (1,11,12)), (2/3, 85, (12,8,1)), lhs -1/3 at T = 84 |
| m=11 4.3.2.1.11..5 {3,4,7,8,11} (2456) | 5 | | not found | base binds: root min Bbar - T = 9/2, slopes feasible |
| m=11 6.5..1.11..7 {0,2,5,6,9,10,11} (3685) | 7 | | **not completed** | stopped for CPU |

In total, 10 of the 14 m=12 misses and 1 of the 4 m=11 misses are certified here. For the 12 fixed-m rows, only m = 12
or m = 11 was run. They are not m-uniform: section 2 gives the generator and its parameters, but not per-family
formulas.

## 2. Generator sources

**The insertion-core word** is a pure stdlib function of the state and the parameters (t, cores, fin). It is copied
verbatim from `checks/reversal_orbit.py`. The search used the equivalent `reversal_orbit_search/gen.py:core_word`
and `fast.py:gen_pool`. The two were compared on 3000 random (state, parameter) draws plus word_R1 at m = 9..80,
with 0 mismatches.

```python
def core_word(state, t, cores, fin):
    n = len(state)
    m = sum(1 for x in state if x)
    order = list(range(t + 1, m + 1)) + [0] + list(range(1, t + 1))
    rk = {x: i for i, x in enumerate(order)}
    cell, w, c = list(state), [], 0

    def goto(p):
        nonlocal c
        f, b = (p - c) % n, (c - p) % n
        w.append('L' * f if f <= b else 'R' * b)
        c = p

    def srt():
        i = cell.index(1)
        return [cell[(i + x) % n] for x in range(m)] == list(range(1, m + 1))

    for seed, sweeps, side in cores:
        lo = hi = seed
        ln, cnt = 1, 0
        while ln < n and (not srt() if sweeps is None else cnt < sweeps):
            if side == 'r':
                j = (hi + 1) % n
                s = 0
                while s < ln and rk[cell[(hi - s) % n]] > rk[cell[j]]:
                    s += 1
                if s:
                    goto(hi)
                    w.append('X' + 'RX' * (s - 1))
                    v = cell[j]
                    for i in range(s):
                        cell[(j - i) % n] = cell[(j - i - 1) % n]
                    cell[(j - s) % n] = v
                    c = (j - s) % n
                hi = j
            else:
                j = (lo - 1) % n
                s = 0
                while s < ln and rk[cell[(lo + s) % n]] < rk[cell[j]]:
                    s += 1
                if s:
                    goto(j)
                    w.append('X' + 'LX' * (s - 1))
                    v = cell[j]
                    for i in range(s):
                        cell[(j + i) % n] = cell[(j + i + 1) % n]
                    cell[(j + s) % n] = v
                    c = (j + s - 1) % n
                lo = j
            ln += 1
            cnt += 1
            side = 'l' if side == 'r' else 'r'
    if not srt():
        return None
    p = cell.index(1)
    w.append('L' * ((p - c) % n) if fin == 'L' else 'R' * ((c - p) % n))
    return ''.join(w)


def word_R1(m):
    st = C.base_vector(list(range(m, 0, -1)), 2 | 1 << m)
    return core_word(st, (m - 3) // 4, [(0, m // 2, 'l'), (m // 2 + 1, None, 'r' if m % 4 == 1 else 'l')], 'R')
```

**How the generator works.** It uses the physical model of lrx_m: a cursor on a cycle, L = +1, R = -1, and X swaps
the cursor cell with the next cell.

- **Target cut t.** The cut fixes a linear target order, labels t+1..m, then the zeros (tied), then 1..t.
- **Core growth.** A core is an arc grown from one seed cell, alternately at its two ends. Each growth step inserts the
  new neighbour into the sorted core by carrying it across the core elements it must pass. A full carry is word_C's
  sweep. Zeros are tied, so a zero is never swapped with a zero.
- **Two cores.** Core 1 takes k1 steps. Core 2 grows until the cycle is cyclically sorted. A final walk ends on
  label 1.
- **Search.** The pool enumerates every t, seed, k1, side and final walk. A fast Lemma 1 pricer, `fast.py:fast_profile`,
  keeps the Pareto front of (base, beta). It is used for pruning only, and every front word is re-priced by
  `lrx_m.Profile` with an assert.
- **Leaf LP.** The LP is `bound3_evaluator.leaf_lp`, over the root leaf or a memoized tree search. The tree search
  has depth <= 3, thresholds <= 5, and origins with total excess <= 2 (k <= 3) or one coordinate 2 (k >= 4).
- **word_C.** word_C grows its cores the same way with full carries. It is not claimed to be a special case of
  `core_word`.

**word_R1, the family (m..1){1,m}.** The state is (m, 0, m-1, ..., 1, 0). The word uses cut (m-3)//4.
Core 1 starts at cell 0 with m//2 steps, left first. Core 2 starts at cell m//2+1, right first iff m = 1 mod 4.
The word ends with an R walk. One word, weight 1, is the whole certificate.

| m mod 4 (m >= 11) | length - T | beta |
|---|---|---|
| 0 | -2 | (m-4, m-2) |
| 1, 3 | -2 | (m-5, m-3) |
| 2 | 0 | (m-6, m-4) |

At m = 9 the word has length T-2 and beta (4,6). At m = 10 it has length T and beta (4,6). The parameters were found by
intersecting the certifying parameter sets over m = 9..20 (`formula.py`). They repeat with period 4 in m.

```
m=9  (50)  RXRXLXLXLXRXRXRXRRRRXRXLXLXRXRXRXLXLXLXLXRXRXRXRXR
m=12 (86)  RXRXLXLXLXRXRXRXRXLXLXLXLXLXRXRXRXRXRXRRRRRXLXRXRXLXLXLXRXRXRXRXLXLXLXLXLXRXRXRXRXRXRR
```

The words at m = 9..40 and all fixed-m certificates, words and trees are in `checks/reversal-orbit-words.json`,
under `formula_R1` and `stored`.

## 3. Exact replay checks (all run by `reversal_orbit.py`)

- **Stored outputs, 111 families.** `score_output` re-verifies each one: Profile with picks, no zero-zero swap,
  literal lifts, box points and the exact LP. `audit_claim`, the independent lrxm8 checker at M = m with the affine
  map to m = 8, returned `[True, 'ok']` for all 111. Every leaf word was also replayed on its refined base with
  `run_naive` and `run`.
- **word_R1.** At m = 9..40, `score_output` gives CERTIFIED and `audit_claim` agrees. At m = 9..200, the word
  replays and satisfies `lrx_m.mixture_criterion(m=m)` with weight 1. There were 0 failures.
- **word_C closed forms at m = 5..60, 1 <= a <= m-2.** The length equals the hand count of section 4 and the
  T-form in every case.
  - The slopes are (2a+1, 2a) in every case except a = 1 with m even, which gives (4,3).
  - These 28 rows are the exceptions REVERSAL-M13.md already noted, and section 4 explains them.

## 4. Proof sketch for word_C (Task 2). A sketch, not a proof

**Assumptions.**

- **Executor.** The executor is `lrx_m`: n = m+2 cells on a cycle, cursor c starting at 0, L: c+1, R: c-1, and X swaps
  cells c and c+1. The state is read from the cursor at the end.
- **word_C.** word_C is exactly the code in REVERSAL-M13.md section 3. That includes the tie rule of `goto`, which
  goes L when both directions are equally long.
- **Lemma 1, as `lrx_m.Profile` implements the group's statement.** Split the word at its X letters into segments.
  - The base is B = #X + sum over segments of |L - R|.
  - The slope of zero atom j is beta_j = 2 A_j + sum over segments of |cz_j|.
  - A_j is the number of X that swap a label with zero j.
  - cz_j is the segment's net signed count of cursor passes over zero j. An L leaving j's cell counts +1, and an R
    arriving on it counts -1.
  - An X with zero j at the cursor adds +1 to the current segment. An X with zero j at c+1 starts the next segment at -1.
- **Scope.** The sketch counts letters and those terms. It does not re-derive Lemma 1, and does not show that
  B and beta_j are the correct lift costs. That is the group's result.

**Setup.** Cell 0 and cell n-1 hold the zeros, zero 0 (gap 0) and zero 1 (gap m). Cell j (1 <= j <= m) holds
label m+1-j. Let q = ceil(a/2), p = floor(a/2) and r = m - a. The sketch assumes 1 <= a <= m-2, so r >= 2.

**(i) Length.**

1. **Sweep cost.** A sweep over a core of length l is X (RX)^(l-1) or X (LX)^(l-1). That is 2l - 1 letters and
   l swaps.
2. **Cursor after a sweep.** An 'r' sweep ends with the cursor on the core's left end lo. An 'l' sweep ends on hi - 1.
   In both cases the next sweep, of the other side, starts one cell away: at lo - 1, or at the new right end hi.
   So every sweep after the first in a core costs a 1-letter walk.
3. **Core 1.** Core 1 starts as the zero block (length 2) and makes a sweeps. The first sweep needs no walk, since
   the cursor is on cell 0 = hi. Sweep i has core length i+1, so core 1 costs
   sum_{i=1..a} (2i+1) + (a-1) = a^2 + 3a - 1.
4. **Core 2.** Core 2 makes r-1 sweeps of lengths 1..r-1, costing (r-1)^2 + (r-2) plus the entry walk W0.
5. **Entry walk W0.** After core 1, the cursor is at n-1-p if a is odd (last sweep 'r'), and at q-1 if a is even.
   The code's start cell makes core 2 end exactly on cells q+1..n-2-p. Its first sweep starts at `start`
   (side 'r' iff r is even) or at `start - 1`. The shorter cyclic walk is:
   - W0 = r/2 + 1 if r is even;
   - W0 = (r+3)/2 if a and r are both odd;
   - W0 = (r+1)/2 if a is even and r is odd.

   It is strictly shorter than n/2 unless a = 1 and m is even, where the two directions tie.
6. **Final walk Wf.** The last sweep of core 2 is always 'r'. With r-1 sweeps alternating from the first side,
   'r' comes last in both parities. So the cursor ends on q+1. Core 1 has reversed its arc
   (p..1, 0, 0, m..m-q+1) into (m-q+1..m, 0, 0, 1..p), so label 1 sits on cell q - p + 1. The final R walk therefore
   has Wf = (q + 1) - (q - p + 1) = p letters.
7. **Total.** len = (a^2 + 3a - 1) + ((r-1)^2 + r - 2) + W0 + floor(a/2). Substituting the three cases of W0 and
   T = m(m+1)/2 + m - 2 gives len - T = 2(a - (m-2)/2)^2 - 1 - (m mod 2)/2. That is REVERSAL-M13.md conjecture 2 on
   1 <= a <= m-2. The case a = m-1 has r = 1 and no core 2, and is excluded. This is why the conjecture fails at
   a = 2 floor(m/2) for odd m, where r = 1. For even m that value is a = m, so r = 0.
8. **Base equals length.** Every segment is a walk in one direction, so B = len.

**(ii) Slopes beta = (2a+1, 2a).**

1. **The 2A_j term.** Every sweep of core 1 carries a label across the whole core, and the zero block lies inside
   the core. So each of the a carried labels is swapped once with each zero: A_0 = A_1 = a. Core 2 and the walks
   never swap a zero. So the 2A_j term is 2a for both zeros.
2. **Crossing terms inside a sweep.** Take an 'r' sweep. If the carried label reaches zero j at cell c, the preceding
   R arrived on j's cell (-1), and the X has j at the cursor (+1). Net 0 in that segment.
   Take an 'l' sweep. The X with j at c+1 opens the next segment at -1, and the following L leaves j's cell (+1).
   Net 0.
3. **Where a term fails to cancel.** A term survives only where a zero is the first element touched by a sweep,
   with no preceding R in the segment. The only such place is the first X of the word. There the cursor already
   stands on zero 0 at cell 0, so |cz_0| = 1.
4. **The 'l'-sweep boundary case.** At the end of an 'l' sweep whose last swap is with a zero (for example a = 2),
   the -1 is cancelled by the one-step L walk into the next sweep, which leaves that zero's cell.
5. **Walks.** W0 goes R from n-1-p (a odd), or L from q-1 (a even). In both cases it stays within the labels between
   the two cores, so it passes no zero. Core 2's sweeps and walks stay inside cells q+1..n-2-p. Wf goes R from q+1 to
   label 1 and stops before the zeros.
6. **Total.** beta_0 = 2a + 1 and beta_1 = 2a.
7. **The exception a = 1, m even.** Here W0 = n/2 is a tie, and `goto` goes L across both zeros. That adds 1 to each
   |cz_j|, giving (4,3), as observed in the 28 rows of section 3. The certificate uses a >= 3, where this cannot
   happen.

**What remains to check before this is a proof.**

- An induction making "the core cells hold the reversed arc, and the cursor ends where stated" precise for every
  sweep, including the cyclic wrap of core 1 across cell 0.
- The parity bookkeeping of `start` and `right` in core 2, showing that core 2 covers exactly q+1..n-2-p.
- The claim that the cells passed by W0 and Wf contain no zero, for every m and a, not just by the positional argument
  above.
- The first-sweep and boundary cancellations at small a (a = 1, 2), written out once.
- Lemma 1 and criterion (7) themselves, which are the group's.

The numeric check in section 3 confirms both closed forms at m = 5..60. REVERSAL-M13.md's replay confirms the
certificate values at m = 9..200.

## 5. Conjectures (not proved; separate from the computed facts above)

1. **word_R1 for all m >= 9.** word_R1(m) certifies (m..1){1,m} for every m >= 9, with length T-2 (T when m = 2 mod 4)
   and slopes below m-2. It is verified by the evaluator and audit to m = 40, and by replay and criterion (7) to
   m = 200. A hand count like section 4 should apply, because the word is a two-core word with a cut.
2. **{0,4} for all m >= 14 by one word.** A single word with slopes (12,0) or (14,2), base T-2, never crosses the zero at
   gap 4. At m = 14 and 16 it alone certifies. A closed form was not extracted.
3. **The remaining k = 2 misses need better pools, not new criteria.** Every k = 2 miss here, at m = 9 ({0,4}, {0,5},
   {5,9}) and m = 10 ({0,5}, {0,6}), has the slopes feasible at the root, with t = 0. The obstruction is the base,
   exactly as for 11..1 {0,11} before word_C. The m = 8 group certified 8..1 {0,4} with refined origins (3,1). Deeper
   trees or three-core words are the untested next step.
4. **Insertion cores generalize word_C.** Every reversal-orbit family certified here is certified by at most four one- or
   two-core insertion words per leaf. Whether per-family parameters follow closed forms in m, as for {0,m} and {1,m},
   was checked only for those two.

## 6. Limitations

- **Conditional scope.** Certificates are conditional on the group's Lemma 1 with refinement and criteria (7)/(8)
  with m as a parameter. A CERTIFIED family covers all block lengths of that one family.
- **Uniformity.** m-uniform results are word_C (REVERSAL-M13.md) and word_R1 (here). {0,4} is certified at m = 10..16
  by per-m search output, not by a formula. The fixed-m rows of (c) are single m values.
- **Coverage not run.** Not run:
  - the all-mask k = 2 survey at m = 11..16;
  - the k = 3 reversal class;
  - trees with depth > 3, thresholds > 5 or larger origins;
  - three-core words.
- **Stopped jobs.** Three tree searches were stopped for CPU: m=12 masks 6309 and 3534, and m=11 mask 3685. The
  misses run kept its results in memory until the end, so the 15 finished rows were first recovered from the log. The
  11 certified ones were then regenerated in `regen-results.jsonl`, all but 4098, which word_R1 covers.
- **CPU.** CPU use was about 70 minutes, over the 40-minute budget. Most of the excess was the three stopped
  high-k tree searches, which ran about 10 minutes each before they were stopped.
- **Search script paths.** The search scripts hard-code `sys.path` to this checkout. `survey.py` was edited between
  the two runs, adding the k >= 4 origin rule. That rule does not change k = 2 runs.
- **Git.** `autoresearch/bound-m-260925/.gitignore` ignores `checks/`. The new script, the JSON and the search
  directory must be force-added if they are to be committed. Nothing was committed.
