# Reversal m..1 with zeros in gaps {0,g}: carry-across words for the middle band

Date 2026-09-26. Offline. There were no provider calls, no LLM-generated code, no tables built and no commits.
Lemma 1 (with refinement), the cost formulas and criteria (7)/(8) are the research group's (m=8 manuscript).
`bound3_evaluator.py` and `bound3_audit.py` apply them with m as a parameter. The main conjecture stays open.
Every certificate below is conditional on that Lemma and those criteria.

- Re-check: `checks/reversal_carry.py`. It writes nothing and runs in about 2 s. It re-scores, re-audits and replays
  all 59 stored certificates and re-derives every generator word letter by letter. It also re-runs the closed form:
  evaluator + audit for m = 14..40 and replay + criterion (7) for m = 41..60. Last run: `problems: none`.
- Data: `checks/reversal-carry-words.json`. Searches, raw results and logs: `checks/reversal_carry_search/`.
  `build.py` there refuses to overwrite the JSON.
- Reproduce: `PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_carry.py`.

Notation as in REVERSAL-MIDBAND.md: T = T_m(m+2), s = m-2, j = floor(m/4), band j < g < m-j.
Z0 is the zero in gap 0 and Zg the zero in gap g. A = labels m..m-g+1 (between Z0 and Zg), B = labels m-g..1.

## 1. Results

| item | result |
|---|---|
| carry-across block 2 as asked | **Does not give 2 per crossing.** A zero crossed from one side only costs 3 in slope, whether the zero walks or the labels are carried. After each crossing the cursor must cross the zero again to fetch the next label. This was measured, including at origins with 2 zeros per block and either pick (section 2). |
| what does give 2 per crossing | A word_C-style zero-core at Z0 that carries labels from **both** sides: q large labels leftwards and p small ones rightwards. Zg is then crossed from one side at 3 per crossing. |
| new generator word_K | Two insertion cores with one cut per core, a stdlib function of (m, g, side, p, q, s1, seed, s2, fin). side 'lo' sends Zg left (cut m in core 2); side 'hi' sends Zg right (cut p). |
| closed form word_M(m, g, side) | Parameters depend only on m mod 4 and the side. **One word certifies at the root, unit origins, on two contiguous runs of g, one at each end of the band, at every m = 14..60.** Evaluator + audit agree on 160 rows (m = 14..40); replay + criterion (7) pass on 207 rows (m = 41..60). |
| m = 14..24 | **59 CERTIFIED band masks at m >= 14** (all root leaves, audit `(True, 'ok')`, replay ok): 44 by word_M and 13 by word_K root mixtures. Before this note, none of m = 14..16 was certified. |
| open leaves m = 10..13 | **m = 11 {0,4} and m = 13 {0,5} CERTIFIED** (root). m = 10 {0,5}, 11 {0,5},{0,6}, 12 {0,5},{0,6}, 13 {0,6},{0,7}: not found. |
| middle band | **Not certified** at any m >= 14 in the table of section 4. The base binds: slopes are feasible in every miss, and the minimum base excess at g = m/2 grows 16, 16, 30, 46, 64, 84 at m = 14, 16, 18, 20, 22, 24. Trees tried at m = 14 did not close it. |

## 2. Why one-sided crossings cost 3 (measured)

Lemma 1 prices a picked zero at beta_j = 2 A_j + sum over segments |cz_j|. Traces of the priced words (`diag.py`) show:

- **Two-sided, zero inside a sweep: 2.** A label carried left across Z is cancelled by the cursor's R onto Z. A label carried right is cancelled by the L off Z. This is word_C's mechanism.
- **Zero at the right end of a core: 3.** In an 'r' sweep, the first swap is (Z, x). The cursor arrived by L, so the +1 is not cancelled. This is F2 core 2, and word_S block 1.
- **Zero at the left end of a core: 3.** The 'l' swap cancels. But the cursor must cross Z by R to reach the next insertion, adding -1. This is F3 core 2. It is also the literal "carry block 2 across Z0" variant.
- **Blocks of 2 zeros do not help.** At origin (1,2), with pick 0 or pick 1, every one-sided crossing still costs 3 (`diag` output in the session log).
  The return trip crosses the picked zero, or the LZ term is not cancelled.

Heuristic model (not a proof). Minimum label swaps split the labels into two cliques G_c and G2. Parity forces G_c to cross Z0 and fixes the Zg crossers: B_c ∪ A_2 when Zg goes left, A_c ∪ B_2 when it goes right. Z0 is crossed by about m/2 labels, so it must be two-sided at 2 each for beta_0 <= m-2. Then Zg's crossers all come from one side.
So beta_g is about 3 min(g + p - q, m - g - p + q) with p ≈ q ≈ m/4. That is <= m-2 only near the band ends, which matches the certified runs.

## 3. Generator and closed form

Source: `checks/reversal_carry.py` (`sched_word2`, `core2_canon`, `word_K`, `params_M`, `word_M`).

- **Core 1** is seeded at cell 0 (Z0) with cut p and schedule s1. It carries A_c = m..m-q+1 left across Z0 and B_c = 1..p right across it.
- **Core 2** is a zigzag seeded at `seed` over cells q+1..m+1-p, i.e. [A_2] Zg [B_2]. Its schedule strictly alternates.
  Absorbing Zg is free and does not use a turn. The schedule is extended over B_c ('lo') or A_c ('hi'), where Zg walks.
- **Finish.** A final L walk to label 1.

params_M, with j = floor(m/4):

| m mod 4 | 'lo' (p, q, seed, first) | 'hi' (p, q, seed, first) |
|---|---|---|
| 0 | (j-2, j, 2j+2, r) | (j, j-2, 2j, l) |
| 1 | (j-1, j, 2j+2, r) | (j, j-1, 2j+1, l) |
| 2 | (j-1, j, 2j+3, l) | (j, j-1, 2j+1, r) |
| 3 | (j-2, j+1, 2j+4, r) | (j+1, j-2, 2j+1, l) |

The core-1 schedule is s1 = r^(q-p)(lr)^p for 'lo' and l^(p-q)(rl)^q for 'hi'.

Observed, not proved:

- beta_0 = m-2 or m-3 throughout.
- Along each run, B - T and beta_g both rise by exactly 3 per unit step of g, from B - T = -2 (m = 14) down to -38 (m = 60) at the first band value.
- The rules were read off the m = 14..25 search optimum, not derived.

Covered band values (single word, root):

| m | band | 'lo' covers | 'hi' covers | covered / band |
|---|---|---|---|---|
| 14 | 4..10 | 4 | - | 1/7 |
| 16 | 5..11 | 5, 6 | 11 | 3/7 |
| 20 | 6..14 | 6..8 | 13, 14 | 5/9 |
| 24 | 7..17 | 7..9 | 15..17 | 6/11 |
| 30 | 8..22 | 8..10 | 20..22 | 6/15 |
| 40 | 11..29 | 11..14 | 26..29 | 8/19 |
| 50 | 13..37 | 13..17 | 34..37 | 9/25 |
| 60 | 16..44 | 16..21 | 39..44 | 12/29 |

Every m = 14..60 is stored in the JSON (`closed_form.coverage`). The runs are contiguous from the band ends.
The uncovered middle grows linearly in m.

## 4. Per (m, g) status, m = 14..24 (root leaf)

"gap" is the evaluator's root gap over the best pool run. "base" is the minimum base excess B̄ - T over mixtures whose slopes satisfy <= m-2, where it was computed. Slopes were feasible in every computed miss, so the base binds.

| m | band | CERTIFIED g | not certified: g (gap, base) |
|---|---|---|---|
| 14 | 4..10 | 4, 5, 10 | 6 (3/10, 2); 7 (3/2, 16); 8 (35/26); 9 (1/8, 4/3) |
| 15 | 4..11 | 4, 5, 6, 10, 11 | 7 (19/20, 9/2); 8 (4); 9 (2/3, 7/2) |
| 16 | 5..11 | 5, 6, 11 | 7 (3/10, 5/2); 8 (9/5, 16); 9 (2); 10 (0 boundary, 1) |
| 17 | 5..12 | 5, 6, 7, 11, 12 | 8 (1, 7); 9 (47/12); 10 (3/4, 4) |
| 18 | 5..13 | 5, 6, 7, 12, 13 | 8 (1/2, 10/3); 9 (31/14, 30); 10 (20/7); 11 (3/10, 2) |
| 19 | 5..14 | 5, 6, 7, 12, 13, 14 | 8 (0 boundary, 1); 9 (29/20, 35/2); 10 (5); 11 (5/2) |
| 20 | 6..14 | 6, 7, 8, 13, 14 | 9 (9/10, 11/2); 10 (39/14, 46); 11 (7); 12 (3/10, 5/2) |
| 21 | 6..15 | 6, 7, 8, 13, 14, 15 | 9 (15/8); 10 (29/16, 30); 11 (101/17); 12 (49/17) |
| 22 | 6..16 | 6, 7, 8, 14, 15, 16 | 9 (6); 10 (10); 11 (83/22, 64); 12 (14); 13 (10) |
| 23 | 6..17 | 6, 7, 8, 9, 15, 16, 17 | 10 (3/10, 2); 11 (11/4, 97/2); 12 (9); 13 (5); 14 (0 boundary, 1) |
| 24 | 7..17 | 7, 8, 9, 15, 16, 17 | 10 (0 boundary, 1); 11 (13); 12 (47/10, 84); 13 (17); 14 (9/10, 11/2) |

Certified by source:

- **word_M closed form.** All the runs of section 3, 44 rows.
- **word_K root mixtures** (pool v1 or v2, parameters stored in the JSON). There are 13:
  - m = 14 {0,5}, {0,10};
  - m = 15 {0,6}, {0,10};
  - m = 17 {0,7}, {0,11};
  - m = 18 {0,7}, {0,12};
  - m = 19 {0,12};
  - m = 21 {0,8}, {0,13};
  - m = 22 {0,8}, {0,14}.

Trees, m = 14 only:

- **{0,8} and {0,9} were not found.** The runs used origins up to (2,2), depth 3 and thresholds 4, and separately unit origins with depth 4 and thresholds 8.
- **The binding strip is u1 = 1, u0 >= 2.** Refined-origin pools at (2,1)..(4,1) behave like lifts of unit words.
  At {0,8} the leaf values are 0 at u0 = 2 (passes), then 3, 4, 4, 3 at u0 = 3, 4, 5, 6 (fail).
  The corner [2,inf) x [3,inf) and the strip u0 = 1 pass.

## 5. Open leaves m = 10..13 (item 2)

Pools: F2, F3, D1 and word_S at origins (1,1), (2,1), (1,2), (2,2), (3,1), (1,3), (4,1) and (3,2).
Trees: depth <= 4, thresholds <= 6 (`opentrees.py`). Best leaf values below are criterion (8) left sides; a leaf passes below 1.

| m {0,g} | status | best root / u0=3 / u0=4 / u0>=2 / u1=1 / u0=1 |
|---|---|---|
| 10 {0,5} | not found | 3/2, 2, 1, 2, 3/2, -2 |
| 11 {0,4} | **CERTIFIED**, root, lhs 0, audit ok | |
| 11 {0,5} | not found | 5/3, 2, 3, 2, 5/3, -2 |
| 11 {0,6} | not found | 8/7, 1, 0, 5/4, 8/7, -4 |
| 12 {0,5} | not found | 1 (boundary at root), 1, 1, 1, 1, -5 |
| 12 {0,6} | not found | 89/38, 3, 3, 3, 7/3, -20/11 |
| 13 {0,5} | **CERTIFIED**, root, lhs -1/6, audit ok | |
| 13 {0,6} | not found | 54/25, 18/5, 24/5, 45/16, 8/5, -5/2 |
| 13 {0,7} | not found | 15/7, 3, 3, 3, 15/7, -2 |

- **m = 10 {0,5}, u0 = 3 and u0 = 4 remain open.** The best origin-(3,1) leaf has value 2 and the best origin-(4,1) leaf has value exactly 1, which is the boundary.

## 6. Limitations

- **Conditionality.** The certificates are conditional on Lemma 1 with refinement and criteria (7)/(8) at general m.
- **Closed form.** word_M is read off search data. Its coverage is verified by evaluator + audit only to m = 40, and by replay and criterion (7) to m = 60. No proof was attempted.
- **Model.** The 3-per-crossing argument in section 2 is a model backed by traces. It is not an impossibility proof: no exact negative was computed at m >= 10.
- **Pools and trees.** They are restricted generator families. A miss proves nothing.
  - Trees were run only at m = 14 ({0,8}, {0,9}) and on the m = 10..13 leaves.
  - No tree was run at m = 15..24.
  - Band values next to the certified runs were retried with pool v2 only once. g = 9 at m = 21, 22 and g = 13 at m = 22 were not retried after their neighbours certified.
- **CPU.** About 65 CPU minutes in total, slightly over the budget. The open-leaf tree search alone took about 18 minutes, and it finished before it was stopped.
- **Git.** `.gitignore` ignores `checks/`, so the script, JSON and search directory must be force-added. Nothing was committed.
