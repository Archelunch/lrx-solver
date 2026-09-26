# Shortest words for the reversal with two outer zeros (m = 8..11)

Date 2026-09-26. This is a read-only analysis: no provider calls, no LLM-generated code executed, no commits.
Lemma 1, the cost formulas (4)-(6) and criteria (7)/(8) are the research group's (m=8 manuscript).
`integrations/lrx_m.py` and `integrations/bound3_evaluator.py` apply them with m as a parameter.
The main conjecture stays open.

The state is u_m = (0, m, m-1, ..., 1, 0) with n = m+2. It is the unit base of family (m..1){0,m},
mask 1 | 1<<m, with budget T = T_m(n) = m(m+1)/2 + m - 2 and slope bound s = m-2.
A word sorts the state to (1..m, 0, 0) under `lrx_m.run_naive`, where L is the left rotation of the
vector, R = L^-1, and X swaps v1 and v2. Every word quoted here was replayed with both `run_naive`
and `run`.

- Data: `checks/reversal-words-m8-11.json`. It holds all shortest words for m = 4..11, Lemma 1
  classes, generator words, rotation distances, radius states, table checks and evaluator rows.
- Reproduce with `PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_words.py`.
  The script refuses to overwrite.

## 1. Tables

(10,2) was built for this note with `tools.table_bfs_lowmem.build_table_lowmem(10, 2, workers=4)`.
It is in `datasets/generated/m10-r2-260926/` (gitignored) and took 409 s.
An independent in-memory rebuild with `src.lrx.table_bfs.build_table(10, 2, workers=4)` gave the
same sha256 and the same layer sizes.

The checks below were run by `reversal_words.py`:

- the sha256 of the .bin matches the metadata;
- the byte histogram equals `layer_sizes`;
- no byte lies above the radius, and no byte is 255;
- on 20,000 random states, every L/R/X neighbour differs by at most 1, and every non-root state
  has a neighbour at d-1.

| (m,2) | states | radius | table sha256 (prefix) | all checks |
|---|---|---|---|---|
| (8,2) | 1,814,400 | 42 | 0be75f62 | pass, 0 violations |
| (9,2) | 19,958,400 | 52 | 8148ceab | pass, 0 violations |
| (10,2) | 239,500,800 | 63 | 3f9ad500 | pass, 0 violations; the in-memory rebuild is identical |
| (11,2) | 3,113,510,400 | 75 | 1c3f4915 | pass, 0 violations |

The (4..7, 2) tables in `datasets/generated` also pass. They are used only for the small-m rows below.

## 2. Exact distances and all shortest words

All shortest words were enumerated by DFS on the geodesic DAG, so every letter lowers the table
distance by 1. Every enumerated word replays to the root.

| m | n | T | d_m | d_m - T | # shortest words | X per word | rotation letters |
|---|---|---|---|---|---|---|---|
| 4 | 6 | 12 | 11 | -1 | 3 | 5 | 6 |
| 5 | 7 | 18 | 17 | -1 | 4 | 8 | 9 |
| 6 | 8 | 25 | 24 | -1 | 14 | 11 | 13 |
| 7 | 9 | 33 | 32 | -1 | 18 | 15 | 17 |
| **8** | 10 | 42 | **41** | -1 | **108** | 19 | 22 |
| **9** | 11 | 52 | **51** | -1 | **132** | 24 | 27 |
| **10** | 12 | 63 | **62** | -1 | **1104** | 29 | 33 |
| **11** | 13 | 75 | **74** | -1 | **1296** | 35 | 39 |

- **Distance.** d_m = T_m(m+2) - 1 = m(m+1)/2 + m - 3 exactly, for every m = 4..11.
- **Swaps.** Every shortest word at a given m has the same number of swaps: floor((m+1)^2/4) - 1
  for m = 4..11. The rest of the word is rotation letters.
- **Canonical word.** The canonical word is the lexicographically least in L < R < X, chosen
  greedily on the DAG. At m = 11 it is exactly the word stored in `checks/m11-r2-reversal-words.json`.

```
m=8   LLXLXRXRXLXLXLXRXRXRXRRRXRXRXLXLXLXRXRXLX
m=9   LLXLXRXRXLXLXLXRXRXRXRRRXRXRXRXLXLXLXLXRXRXRXLXLXRX
m=10  LLLXLXRXRXLXLXLXRXRXRXRXLXLXLXLXLLLXLXLXRXRXRXLXLXLXLXRXRXRXLX
m=11  LLLXLXRXRXLXLXLXRXRXRXRXLXLXLXLXLLLXLXLXLXRXRXRXRXLXLXLXLXLXRXRXRXRXLXLXRX
```

### Lemma 1 classes of the shortest words

Every shortest word is same-sign (checked for m = 4..11). At m = 8..11 each has A = (a, a) with a in {3, 4, 5}.
B is the word length, since every word is same-sign.

| m | s = m-2 | (beta, A): count |
|---|---|---|
| 8 | 6 | (7,6),A3: 24; (8,7),A3: 20; (9,8),A3: 36; (10,9),A3: 28 |
| 9 | 7 | (7,6),A3: 24; (9,8),A3: 36; (9,8),A4: 24; (11,10),A4: 20; (13,12),A4: 28 |
| 10 | 8 | (9,8),A4: 192; (10,9),A4: 168; (11,10),A4: 160; (12,11),A4: 360; (13,12),A4: 224 |
| 11 | 9 | (9,8),A4: 192; (11,10),A4: 160; (11,10),A5: 192; (13,12),A4: 224; (13,12),A5: 168; (15,14),A5: 360 |

The minimum slope over the shortest words is (7,6) at m = 8, 9 and (9,8) at m = 10, 11.
So at m = 11, 192 shortest words satisfy beta <= s = 9 on their own. At m = 8 and m = 10 none does.

## 3. Structure

**Notation.** Split a word at its X letters into rotation segments. A sweep is a maximal run of
nonempty segments in one direction. `L4(1,1,5,1)` means four swaps going right, with rotation
segments of lengths 1, 1, 5, 1 before the successive X letters. Plain `L4` means all segments have
length 1, that is (LX)^4. A segment longer than 1 steps over cells without swapping; the triple
step RRR/LLL crosses the adjacent zero pair.

The physical picture is the same at every m, as seen by tracing the words on fixed cells with a cursor.

1. A short prefix makes the two outer zeros adjacent.
2. Zigzag sweeps of growing size grow a sorted core in the middle of the label run. Each sweep
   carries one label across the core.
3. One long sweep of m-2 swaps carries the remaining labels across the zero block.
4. Zigzag sweeps of shrinking size finish the sort.

Three shapes occur among the shortest words, and each has an m-uniform generator (section 4).

| shape | m = 8 | m = 9 | m = 10 | m = 11 |
|---|---|---|---|---|
| **E** (grow, long, shrink) | L2(2,1) R2 L3 R6(1,1,1,3,1,1) L3 R2 L1 | L2(2,1) R2 L3 R7(1,1,1,3,1,1,1) L4 R3 L2 R1 | L1(3) R1 L2 R3 L4 R8(1,1,1,1,3,1,1,1) L4 R3 L2 R1 | L2(3,1) R2 L3 R4 L5 R9(1,1,1,1,1,3,1,1,1) L4 R3 L2 R1 |
| **A** (grow, long R, tail L4) | not shortest (43) | R2 L4(1,1,4,1) R2 L3 R8(1,1,1,2,1,1,1,1) L4 | R2 L3(1,1,5) R1 L2 R3 L4 R9(1,1,1,1,2,1,1,1,1) L4 | R2 L4(1,1,5,1) R2 L3 R4 L5 R10(1,1,1,1,1,2,1,1,1,1) L4 |
| **B** (grow, long L) | R2 L3(1,1,4) R1 L2 R3 L7(1,1,1,2,1,1,1) | R2 L4(1,1,4,1) R2 L3 R4 L8(1,1,1,1,2,1,1,1) | not shortest (64) | not shortest (78) |

A and B both start with a leading X, which is not shown in the sweep notation.

**Run-length pattern of E.** E has three parts.

- A head L^p X is followed by a growing zigzag with sweep sizes 1..K1; the last head sweep goes L.
- The long sweep is R with K1 + K2 = m - 2 swaps and one triple step after the K1-th swap.
- A shrinking zigzag K2, K2-1, ..., 1 starts with L.

The sizes are balanced: K1 + K2 = m - 2 and |K1 - K2| <= 1 for m = 8..11, with (K1, K2) =
(3,3), (3,4), (4,4), (5,4). The E words at m = 8 and m = 9 are also the canonical lexmin words.

**Closed forms.** The E, A and B lengths were checked by replay for every m from 6 (from 8 for E)
to 200. Exactness holds only where a table exists.

| quantity | formula | exact (tables) | replay range |
|---|---|---|---|
| d_m | T_m - 1 | m = 4..11 | E gives <= T_m - 1 for m = 8..200 |
| X per shortest word | floor((m+1)^2/4) - 1 | m = 4..11 | not applicable |
| E(m) | T_m - 1 | m = 8..11 shortest | m = 8..200 |
| A(m) | T_m - 1 + floor((m-10)^2/2) | shortest at m = 9, 10, 11 | m = 6..200 |
| B(m) | T_m - 1 + floor((m-8)^2/2) | shortest at m = 7, 8, 9 | m = 6..200 |

A and B are parabolas that touch T-1 at three values of m each. Their line-sort core costs about
m^2 letters against T ~ m^2/2, so each works only near its centre. E keeps both zigzags balanced
and stays at exactly T_m - 1 for every m checked.

The Lemma 1 slopes behave differently.

- A has beta = (9,8) for every m = 6..60, with A = (4,4).
- B has beta = (7,6) for every m = 6..60, with A = (3,3).
- E has beta = (3a+1, 3a) with a = A_j = 3, 4, 4, 4, 5, 6, 6, 6, 7, ... Its slope grows like 3m/2,
  so it exceeds s = m - 2 at every m checked (8..40, and every 20th m up to 200).

## 4. Generators

These are pure functions of m, using the stdlib only. They are copied verbatim from
`checks/reversal_words.py`.

```python
def zigzag(K, last):
    """Sweeps of 1, 2, ..., K swaps, alternating direction, the size-K sweep going `last` (L or R)."""
    other = 'R' if last == 'L' else 'L'
    return ''.join(((last if (K - s) % 2 == 0 else other) + 'X') * s for s in range(1, K + 1))


def zigzag_down(K):
    """Sweeps of K, K-1, ..., 1 swaps, alternating direction, the size-K sweep going L."""
    return ''.join((('L' if (K - s) % 2 == 0 else 'R') + 'X') * s for s in range(K, 0, -1))


def word_E(m):
    """m >= 8: L^p X, zigzag up to K1, long R sweep of m-2 swaps with one triple step, zigzag down from K2, R^t."""
    K1 = m // 2 - 1 if m % 2 == 0 else 2 * ((m - 2) // 4) + 1
    K2 = m - 2 - K1
    return ('L' * ((m + 2) // 4) + 'X' + zigzag(K1, 'L') + 'RX' * K1 + 'RRRX' + 'RX' * (K2 - 1)
            + zigzag_down(K2) + 'R' * (m // 4 - 2))


def word_A(m):
    """Merge the zeros, zigzag up to m-6, long R sweep through the zero block, (LX)^4. Slopes (9,8)."""
    K = m - 6
    return 'XRXRXLXLX' + 'L' * (m // 2) + 'X' + zigzag(K, 'L') + 'RX' * K + 'R' + 'RX' * 5 + 'LX' * 4


def word_B(m):
    """Merge the zeros, zigzag up to m-5, long L sweep (W_m of REVERSAL-OBSTACLE.md s.4). Slopes (7,6)."""
    K = m - 5
    return 'XRXRXLXLX' + 'L' * (m // 2) + 'X' + zigzag(K, 'R') + 'LX' * K + 'L' + 'LX' * 4
```

**Replay checks.** "Shortest" means the word is a member of the enumerated set of all shortest words.

| m | T | E: len, shortest | A: len, shortest | B: len, shortest |
|---|---|---|---|---|
| 8 | 42 | 41, yes | 43, no | 41, yes |
| 9 | 52 | 51, yes | 51, yes | 51, yes |
| 10 | 63 | 62, yes | 62, yes | 64, no |
| 11 | 75 | 74, yes | 74, yes | 78, no |

- **word_E is the requested m-uniform generator.** It reproduces a shortest word exactly at
  m = 8, 9, 10, 11.
- **It does not work below m = 8.** word_E does not sort u_m at m = 6 and m = 7; the trailing R^t
  and the head presuppose m >= 8.
- **word_E(m) for m = 8..200.** It sorts u_m, by both executors, with exactly T_m - 1 letters.
  This is an upper bound certified by replay, not a distance.
- **Consequence for the rotated state.** R·u_m = (0,0,m,...,1) is the state at the radius. Hence
  "L" + word_E(m) sorts it in T_m letters, for m = 8..200.

The parameters (p, K1, t) of E were found by brute force over p < m, 1 <= K1 <= m-3 and |t| <= 4
for m = 6..27. Each m in 8..27 had exactly one parameter triple giving T-1. The closed forms
p = (m+2)//4, t = m//4 - 2, and K1 as coded were read off those rows and then verified by replay
up to m = 200.

## 5. Lift test (criterion (7) on the single root leaf)

`bound3_evaluator.score_output(family, {"words": [...]})` was run for (m..1){0,m}. This runs
Profile, the literal lift at the z points and at the box points of the support, and the exact LP.
Every CERTIFIED row was re-checked with `lrx_m.mixture_criterion(m=m)`, and all agree.

| m | T | s | E | A | B | best pool | status | support (weight, B, beta) |
|---|---|---|---|---|---|---|---|---|
| 8 | 42 | 6 | 41 (10,9) | 43 (9,8) | 41 (7,6) | A+B+E | NO, gap 1 (slope) | (1, 41, (7,6)) |
| 9 | 52 | 7 | 51 (13,12) | 51 (9,8) | 51 (7,6) | B | **CERTIFIED** | (1, 51, (7,6)) |
| 10 | 63 | 8 | 62 (13,12) | 62 (9,8) | 64 (7,6) | A+B | **CERTIFIED**, lhs 0 | (1/2, 62, (9,8)), (1/2, 64, (7,6)) |
| 11 | 75 | 9 | 74 (13,12) | 74 (9,8) | 78 (7,6) | A | **CERTIFIED** | (1, 74, (9,8)) |
| 12 | 88 | 10 | 87 (16,15) | 89 (9,8) | 95 (7,6) | A+E | **CERTIFIED**, lhs 5/7 | (6/7, 89, (9,8)), (1/7, 87, (16,15)) |
| 13 | 102 | 11 | 101 (19,18) | 105 (9,8) | 113 (7,6) | A+E | NO, gap 6/5 | (4/5, 105), (1/5, 101) |
| 14 | 117 | 12 | 116 (19,18) | 124 (9,8) | 134 (7,6) | A+E | NO, gap 18/5 | |
| 15 | 133 | 13 | 132 (19,18) | 144 (9,8) | 156 (7,6) | A+E | NO, gap 13/3 | |
| 16 | 150 | 14 | 149 (22,21) | 167 (9,8) | 181 (7,6) | A+E | NO, gap 59/9 | |

- **m = 11.** The family (11..1){0,11}, mask 2049, is CERTIFIED by the single 74-letter shortest
  word A(11), which has B = 74 < 76 and beta = (9,8) <= 9. That word is:

  ```
  XRXRXLXLXLLLLLXLXRXRXLXLXLXRXRXRXRXLXLXLXLXLXRXRXRXRXRXRRXRXRXRXRXLXLXLXLX
  ```

  This closes the family that REVERSAL-OBSTACLE.md reported with gap 4. It needs no tree and no
  refined origin. Like every certificate here, it is conditional on the group's Lemma 1.
  The canonical lexmin word stored earlier has slopes (15,14) and would not have certified.
- **m = 10.** w(m) alone does not certify. A alone has gap 1 because slope 9 > 8. B alone is
  BOUNDARY because 64 = T+1. No shortest word has beta <= 8, so no mixture of shortest words alone
  works. The mixture 1/2·A + 1/2·B gives Bbar = 63 = T and beta = (8,7). That is CERTIFIED
  (lhs 0 < 1), and it uses the base slack of 1.
- **m = 9.** B alone certifies, as already recorded in REVERSAL-OBSTACLE.md section 4.
- **m = 12.** The pool A+E certifies, with the weights in the table. This is outside the requested
  range and is recorded as a side result.
- **What binds for m >= 13 with this pool.** A's excess floor((m-10)^2/2) - 1 grows, and E's slope
  3m/2 exceeds s. The LP pays both: at m = 13 the gap is 6/5, with lhs 11/5 at slopes <= s.
  Certifying further needs short words with slope near 9, which none of the three shapes provides.
- **Trees were not run.** At m = 9, 10, 11 a single root leaf already certifies, so
  `bound3_control_revtree` refined-origin trees are not needed for this family.
- **m = 8.** Neither the generator pool nor any single shortest word certifies; the best slope is
  7 > 6. The group certified it with the mixture (43,(5,4)) + (41,(7,6)).

## 6. Rotations and the (m,2) radius

These are distances of the n rotations u[i:] + u[:i], i = 0..n-1.
(0,0,m..1) is the rotation i = n-1, so its list is the same list shifted by one.

| m | T | radius | rotations of u_m, i = 0..n-1 | states at radius | states at radius-1 |
|---|---|---|---|---|---|
| 8 | 42 | 42 | 41,40,39,40,39,40,41,42,41,42 | 2 | 13 |
| 9 | 52 | 52 | 51,50,49,49,49,50,51,51,52,51,52 | 2 | 7 |
| 10 | 63 | 63 | 62,61,60,59,60,59,60,61,62,63,62,63 | 2 | 10 |
| 11 | 75 | 75 | 74,73,72,71,71,71,72,73,74,74,75,74,75 | 2 | 8 |

At each of m = 8, 9, 10, 11 the radius of (m,2) equals T. It is attained by exactly two states:
(0,0,m,...,1), which is rotation i = n-1, and (2,1,0,0,m,...,3), which is rotation i = n-3.
The m = 11 observation therefore holds at m = 8, 9 and 10 too.

- The reversal with outer zeros, i = 0, is at T-1 each time.
- The full states at radius-1 are in the JSON.
- For context, the (5,2) radius is 19 = T+1, as already in claims.md. The (4,2), (6,2) and (7,2)
  radii equal T.

## 7. Conjectures (not proved; separated from the computed facts above)

1. d(u_m) = T_m(m+2) - 1 for all m >= 4. This is exact for m = 4..11. For m = 8..200 the upper
   bound is certified by replaying word_E. The lower bound beyond m = 11 is unknown; (12,2) has
   4.4e10 states.
2. Every shortest word for u_m has floor((m+1)^2/4) - 1 swaps. This is exact for m = 4..11.
3. The radius of (m,2) is T_m(m+2) for m >= 8, attained only at the two rotations above. This is
   exact for m = 8..11. At m = 6 and 7 the radius is T but there are three radius states, and at
   m = 4 there are four. For m = 8..200 the upper bound d <= T at (0,0,m,...,1) comes from "L" +
   word_E(m); the other radius state and every other state are unchecked beyond m = 11.
4. The family (m..1){0,m} needs, for m >= 13, words of length about T with Lemma 1 slopes about 9,
   and the E, A and B shapes do not provide them. A plausible route is a hybrid that keeps E's
   balanced zigzags but crosses the zero block only a bounded number of times, as A does. This
   is untested.

## 8. Limitations

- Distances are exact only where a complete table exists, which is m <= 11. Beyond that, word
  lengths are replay-certified upper bounds.
- The certificates in section 5 are conditional on the group's Lemma 1 and criterion (7) with m as
  a parameter. They cover this one family only.
- The E parameters were fitted from m = 8..27 search rows. The closed form is verified by replay
  only up to m = 200.
