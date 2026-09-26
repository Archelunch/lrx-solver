# Reversal m..1 with zeros in gaps {0,g}: the middle band, mined from exact tables

Date 2026-09-26. Offline. There were no provider calls, no LLM-generated code and no commits. No table was built.
Lemma 1 (with refinement), the cost formulas and criteria (7)/(8) are the research group's (m=8 manuscript).
`bound3_evaluator.py` and `bound3_audit.py` apply them with m as a parameter. The main conjecture stays open.
Every certificate below is conditional on that Lemma and those criteria.

- Re-check script: `checks/reversal_midband.py`. It re-scores, re-audits and replays every stored certificate,
  re-derives every word_S word from its parameters, and checks the negative's dual certificate. It writes nothing.
  `--tables` also re-runs the exact oracle for the negative and re-reads the m = 9 distances. Both modes take about 1 s.
- Data: `checks/reversal-midband-words.json`. Search scripts, raw results and logs: `checks/reversal_midband_search/`.
- Reproduce: `PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_midband.py --tables`.

Notation as in REVERSAL-K2.md: T = T_m(m+2), s = m-2, j = floor(m/4), band j < g < m-j. Origin (o0,o1) puts o0
zeros in gap 0 and o1 zeros in gap g. T(o) = T_m(m+o0+o1). Picks are the first atom of each block.

## 1. Results

| item | result |
|---|---|
| exact negative | **m = 9 {0,4} has no root-leaf certificate at all.** Every sorting word of the unit base has B + 3 beta_0 >= 75, and a certifying mixture would need < 74. The exact optimum of the criterion (8) left side over all words at the root is 2. |
| m = 9 band | **all four certified.** {0,3}, {0,5}, {0,6} at the root; {0,4} by a two-leaf tree (u0 = 1; u0 >= 2 at origin (2,1)). {0,4} and {0,5} were misses in REVERSAL-K2.md. |
| generator word_S | A split-merge word, a stdlib function of (m, g, b, ds, schedule, fin). It certifies at the root m = 9 {0,5},{0,6}; 10 {0,6},{0,7}; 11 {0,7},{0,8}; 12 {0,7},{0,8}; 13 {0,8},{0,9}. New relative to REVERSAL-K2.md: m = 10 {0,6}, 11 {0,7}, 12 {0,7},{0,8}, 13 {0,8}. It certifies nothing at m = 14..16. |
| not certified | m = 10 {0,5}; m = 11 {0,4},{0,5},{0,6}; m = 12 {0,5},{0,6}; m = 13 {0,5},{0,6},{0,7}; the lower band g <= about m/3 at every m tried with word_S; all band masks at m = 14..16. |

All 14 stored certificates are CERTIFIED by `score_output`, `(True, 'ok')` by `audit_claim`, and every leaf word
replays to the root under `run_naive` and `run`.

## 2. Exact data (item 1)

### 2a. Exact distances and shortest words

Unit base, tables (9,2), (10,2), (11,2). "Shortest slopes" is the Pareto front of Lemma 1 slopes over all
shortest words (m = 9, 10: all of them; m = 11: 200 sampled from the memmap).

| m | g | d | d - T | # shortest | shortest slopes |
|---|---|---|---|---|---|
| 9 | 3 | 45 | -7 | 72 | (9,0) |
| 9 | 4 | 43 | -9 | 48 | (12,0) |
| 9 | 5 | 43 | -9 | 24 | (13,0) |
| 9 | 6 | 45 | -7 | 56 | (10,0) |
| 10 | 3 | 56 | -7 | 264 | (10,3), (11,2) |
| 10 | 4 | 53 | -10 | 48 | (12,0) |
| 10 | 5 | 53 | -10 | 24 | (16,0) |
| 10 | 6 | 54 | -9 | 204 | (12,1), (13,0) |
| 10 | 7 | 55 | -8 | 24 | (12,2) |
| 11 | 3..8 | 68, 66, 64, 64, 66, 68 | -7, -9, -11, -11, -9, -7 | not counted | (11,2), (12,0), (15,0), (16,0), (13,0), (12,2) |

- **The base never binds on its own.** The unit distance is 7 to 11 below T.
- **Shortest words have the wrong slopes.** They carry the gap-g zero completely (beta_1 about 0) and put all the
  slope on the gap-0 zero: beta_0 = 9..16, always above m-2.

### 2b. Distance minus T along the axes (m = 9, tables (9,2)..(9,6); m = 10, tables (10,2), (10,3))

| family | u0 = 1..5 (u1 = 1) | u1 = 1..5 (u0 = 1) |
|---|---|---|
| 9 {0,3} | -7, -7, -5, -3, -3 | -7, -14, -21, -28, -35 |
| 9 {0,4} | -9, -6, -3, **0**, -1 | -9, -16, -23, -30, -37 |
| 9 {0,5} | -9, -7, -5, -3, -4 | -9, -16, ... |
| 9 {0,6} | -7, -6, -6, -4, -7 | -7, -14, ... |
| 10 {0,3..7} | u0 = 1, 2: (-7,-6), (-10,-8), (-10,-7), (-9,-8), (-8,-6) | |

- **Axis 1 is free.** Along u1 the distance grows by exactly 0 per extra zero, and T grows by s.
- **Axis 0 is where the band binds.** At m = 9 {0,4} the distance grows by 10 per zero for u0 = 1..4 (T grows by 7).
  The state (0^4, 9, 8, 7, 6, 0, 5, ..., 1) is at distance exactly T. So every leaf that covers u = (4,1) must have
  average cost in [T, T+1) there.

### 2c. Exact criterion (8) optimum over all words

The oracle (`reversal_midband_search/mb.py`) minimizes wB·B + w·beta over all reduced sorting words, with exact
Lemma 1 bookkeeping. It uses A* with admissible heuristics: the table distance, the Lemma 1 lift bound
B + z·beta_j >= d(base with zero j stretched by z) from the (m, r+z) tables, and the pending-segment bound. It was
checked against brute force on 25 small cases (m = 5, 6).

Column generation with this oracle as the pricing step gives the exact optimum of the leaf LP over all words at that
origin. The optimum is exact when the Lagrangian lower bound F(λ) - sΣλ - T meets the pool value.

| m {0,g} | leaf (origin = lower corner) | exact optimum of the (8) left side | verdict |
|---|---|---|---|
| 9 {0,3} | root | -1 | certifiable |
| 9 {0,4} | root | **2** (dual λ = (3,0)) | **impossible** |
| 9 {0,4} | u0 = 1, u1 >= 1, unit origin | -4 | certifiable |
| 9 {0,4} | [2,∞) x [1,∞), origin (2,1) | 4/5 | certifiable |
| 9 {0,4} | [3,∞) x [1,∞), origin (3,1) | 4/5 | certifiable |
| 9 {0,5} | root | -1 | certifiable (single word, T-1, slopes (7,4)) |
| 9 {0,6} | root | -4 | certifiable |
| 10 {0,5}, {0,6} | u0 = 1, unit origin | -3, -5 | certifiable |
| 10 {0,5} | root; origin (2,1) | pool 17/4; 11/4 | **not proven**: pricing hit the 1.5M-node cap |
| 10 {0,6} | root; origin (2,1) | pool 25/7; 1 | not proven (cap); the root was later certified by word_S |
| 9 {0,4} | origins (1,2), (2,2) | none | pricing hit the 6M-node cap |

- **The one exact impossibility.** For m = 9 {0,4} at the root, min over all words of B + 3 beta_0 is 75. The
  witness is `RXLLLLXLLXLXRRXRXRXLXLXLXRXRXRXRXLXLXLXLXLLLXLXLXRRXLX` with B = 54 and beta = (7,7).
  - A mixture with Bbar < T + 1 = 53 and betabar_0 <= 7 would give Bbar + 3 betabar_0 < 74, which is impossible.
  - So no word set and no weights certify the root leaf. Every certificate of this family must split the box.
  - This is conditional only on Profile's pricing, which is Lemma 1's cost.
  - It is the first exact negative for a root leaf in this repository.
- **The only exact result at a refined origin is positive.** The table lower bounds by themselves never refute a
  leaf, because every distance is at most T(u) (the radius equals T here). The refutation needs the (base, slope)
  trade-off, which the oracle computes.
- **Not run at m = 11.** There is no (11,3) table for the heuristic. The oracle was not run there; only distances
  and sampled shortest words are reported.

## 3. Structure of the middle-band words (item 2)

The certifying m = 9 {0,5} word (T-1, slopes (7,4)), traced on cells 0..10:

```
      . 9 8 7 6 5 . 4 3 2 1
RX         1 crosses the gap-0 zero                  1 9 8 7 6 5 . 4 3 2 .
LLLLX ...  zigzag core sorts 8 7 6 5 in place        1 9 5 6 7 8 . 4 3 2 .
LLX RX^5   4 crosses the gap-5 zero, carried left    1 4 9 5 6 7 8 . 3 2 .
LX^4       9 carried right to the end of block 1     1 4 5 6 7 8 9 . 3 2 .
LLLX ...   block 2: 3,2,1 and the gap-0 zero         3 4 5 6 7 8 9 . . 1 2
```

- **Split and merge.** The zeros merge inside the second arc (labels m-g..1).
  - The a = m-g-b larger labels of that arc cross the gap-g zero.
  - The zero in gap 0 walks backwards through the b smallest labels.
  - So the word is two independent reversals with one zero each, on disjoint arcs: block 1 is labels m..b+1 plus
    the gap-g zero, and block 2 is labels b..1 plus the gap-0 zero.
  - The crossings split between both zeros. That is exactly what the two-core pool of REVERSAL-K2.md never does:
    its cheap words put min(g, m-g) crossings on the gap-0 zero.
- **The m = 9 {0,4} root optimum has the same shape** (a = 2, b = 3, slopes (7,7)). The exact root value there is 2,
  so this shape is optimal and still not enough at the root.
- **Generator word_S(m, g, b, ds, sc1, fin)**, in `reversal_midband.py`:
  - prefix RX;
  - a block-1 insertion core seeded at cell 1+ds with an explicit side schedule sc1 of length g+a;
  - a block-2 core seeded at cell m+2-b growing right b times;
  - cut t = b;
  - final walk fin.
- **The winning parameters are regular.** They are b = 3..5, ds = 2..3, fin = L, and sc1 = rr(lr)* or rrr(lr)* with
  an rl tail (JSON field word_S_params). A full 2^L schedule search at m = 9, 10 found nothing better than this
  restricted family. At m = 9 the restricted pool reaches the exact root optimum for g = 4, 5, 6.
- **Why it stops at m = 13.**
  - In word_S the gap-0 zero is carried through the b labels. That costs 3 per crossing, so beta_0 = 3b - 2
    (7, 10, 13, 16, 19 for b = 3..7).
  - The gap-g zero gets beta_1 = 3a + 1.
  - Both slopes then cap b and a at about m/3, and the base overshoot grows with m. The smallest root gap is 1/10
    at m = 14 ({0,9}), 1 at m = 15 ({0,10}) and 2 at m = 16 ({0,10}).
  - The fix suggested by word_C (a label carried through a zero costs 2, not 3) is to carry the b small labels
    across the gap-0 zero instead of walking the zero. That block-2 core was not written.
  - word_S is not a closed form in m: the schedule is chosen per (m, g) from the restricted family.

## 4. Per (m, g) status (item 3)

Band j < g < m-j. "K2" is the status in REVERSAL-K2.md before this note.

| m | g | status now | how | binding constraint where not certified |
|---|---|---|---|---|
| 9 | 3 | CERTIFIED | root, exact-LP words (was certified by the two-core pool) | |
| 9 | 4 | **CERTIFIED** (K2 miss) | 2-leaf tree: u0 = 1 shortest word (43, (12,0)); u0 >= 2 origin (2,1), lhs 4/5 | root proved impossible (exact value 2) |
| 9 | 5 | **CERTIFIED** (K2 miss) | root, one word, T-1, (7,4) (exact-LP and word_S) | |
| 9 | 6 | CERTIFIED | root, word_S (48, (7,1)) | |
| 10 | 3, 4, 7 | certified before (K2 / ORBIT); word_S reproduces g = 7 | | |
| 10 | 5 | not certified | leaves u0 in [1,2] and u0 >= 5 pass; u0 = 3 and u0 = 4 fail with every word tried; no (10,4) table | base at origins (3,1), (4,1) |
| 10 | 6 | **CERTIFIED** (K2 miss) | root, word_S mixture 1/3 (58,(10,1)) + 2/3 (64,(7,4)) | |
| 11 | 7 | **CERTIFIED** (K2 miss) | root, word_S mixture, lhs -5/3 | |
| 11 | 8 | CERTIFIED | root, word_S (75, (7,1)); the K2 survey had certified it too | |
| 11 | 4, 5, 6 | not certified | word_S root lhs 2, 1, 1 (gaps 5, 2, 1/7) | base |
| 12 | 7, 8 | **CERTIFIED** (K2 misses) | root, word_S single words (88,(10,4)), (85,(10,1)) | |
| 12 | 5, 6 | not certified | word_S root gaps 4, 3/2 | base |
| 13 | 8 | **CERTIFIED** (K2 miss) | root, word_S mixture, lhs 2/3 | |
| 13 | 9 | CERTIFIED | root, word_S (was certified by the survey) | |
| 13 | 5, 6, 7 | not certified | word_S gaps 6, 3, 8/7 | base |
| 14..16 | whole band | not certified | word_S gaps from 1/10 (14 {0,9}) up to 17 | base |

- **What the tables prove impossible.** Only one thing: a root leaf for m = 9 {0,4}.
  - No other (g, origin) leaf was refuted.
  - The m = 10 {0,5} root and (2,1) leaves are open: the exact pricing did not finish within the node cap.
  - At m = 11 no exact leaf computation was possible.

## 5. Limitations

- **Conditional scope.** The certificates rest on the group's Lemma 1 and criteria (7)/(8) with m as a parameter.
  The negative rests on Lemma 1's pricing (Profile).
- **Search outputs, not formulas.** The m = 9 words are exact-oracle outputs. word_S is parametric, but its
  parameters are picked per (m, g).
- **Oracle trust.** The oracle is scratch code, validated against brute force at m = 5, 6 only. The negative's
  dual inequality is re-run by `--tables`. Its witness is re-priced by lrx_m.Profile without tables.
- **Picks.** Refined leaves used picks = first atom only.
- **Origins tried.**
  - Exact origins: (1,1), (2,1), (3,1) at m = 9. The (1,2) and (2,2) runs hit the node cap.
  - m = 10: (2,1) only.
  - (3,1) and (1,3) at m = 10 and all refined origins at m = 11 need tables that do not exist. They were not built.
- **Not run.**
  - the label-carrying block-2 core;
  - trees on the m = 11..16 misses;
  - word_S at refined origins beyond the m = 10 {0,5} staircase.
- **CPU.** About 30 to 35 CPU minutes, estimated from the logs, including runs that were killed.
- **Git.** `autoresearch/bound-m-260925/.gitignore` ignores `checks/`, so the new script, JSON and search directory
  must be force-added. Nothing was committed.
