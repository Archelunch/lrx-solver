# Reversal m..1 with two zeros (k = 2): a closed form for the outer gaps, and what does not certify

Date 2026-09-26. Offline construction. There were no provider calls, no tables, no LLM-generated code and no commits.
Lemma 1 (with refinement), the cost formulas and criteria (7)/(8) are the research group's (m=8 manuscript).
`integrations/lrx_m.py`, `bound3_evaluator.py` and `bound3_audit.py` apply them with m as a parameter.
The main conjecture stays open. Every certificate below is conditional on that Lemma and those criteria.

- Verification script: `checks/reversal_k2.py`. `--build` writes `checks/reversal-k2-words.json` and refuses to
  overwrite. Without arguments it re-checks the stored JSON (re-score, re-audit, replay, and re-derive every word_G
  word letter by letter) and writes nothing. Both modes run in under 4 s.
- Search scripts, as run, with their raw outputs and logs: `checks/reversal_k2_search/`. The only edits after the
  runs are a `sys.path` line (the scratch directory held identical copies of `reversal_orbit_search/fast.py`,
  `gen.py`, `engine.py`, `survey.py`), a comment in `trees.py` recording the two origin lists, and an `outer` option
  added to `survey_root.py` after the m = 11, 12 runs (it does not change the default path).
- Reproduce: `PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_k2.py`.

Notation: family (m..1){i,j} is the reversal with one zero in gap i and one in gap j (mask 2^i + 2^j).
T = T_m(m+2) = m(m+1)/2 + m - 2, s = m - 2, j = floor(m/4), r = m - g.

## 1. Results

| item | result |
|---|---|
| 1. closed form for {0,g} | **word_G(m, g)**, one two-core word, certifies (m..1){0,g} whenever min(g, m-g) is at most about m/4 (exact rule in section 2): 390 (m, g) at m = 9..40 CERTIFIED by `score_output`, `[True, 'ok']` by `audit_claim`, literal replay OK; 1210 more words at m = 41..80 pass replay and criterion (7) with weight 1. 0 failures. |
| 1. the middle band | **not certified by any closed form.** For j < g < m - j (and g = m, which word_C covers) no word_G is defined. At m = 40 that is g = 11..29, 19 of 40 masks. At m <= 13 the full two-core pool with a root LP certifies part of the band, and 4 masks per m fail (table 1b). |
| 2. known misses | **m = 9 {5,9} CERTIFIED** (5-leaf tree, new). Not certified: m = 9 {0,4}, {0,5}; m = 10 {0,5}, {0,6}; m = 12 mask 130; m = 11 mask 1056. Not run: masks 7300, 2456, 6309, 3534, 3685 (CPU). |
| 3. all-mask survey | m = 11: **59/66** root-certified; m = 12: **72/78**; m = 13: outer masks only, **18/25**; m = 14 **not run**. Every miss has a zero in gap 0 or gap m. |

All 150 stored search certificates (131 survey roots at m = 11, 12, 18 outer roots at m = 13, the m = 9 tree) are
CERTIFIED by `score_output`, `[True, 'ok']` by `audit_claim`, and every leaf word replays to the root under
`run_naive` and `run`.

### 1b. {0,g} at m = 9..13, root LP over the full two-core pool (`scan0g.py`)

Root min Bbar - T with slopes <= m-2 (t = 0 in every row, so the slopes are feasible and the base binds). A value
below 1 certifies.

| m | g = 1..m | fails |
|---|---|---|
| 9 | -3 -3 -1/5 **7/3 4** 2/3 -3 -2 -1 | g = 4, 5 |
| 10 | -2 -4 -1 **6/5 17/4 4** -2 -3 -2 0 | g = 4 (a tree certifies it, REVERSAL-ORBIT.md), 5, 6 |
| 11 | -3 -4 -3 **6/5 7/2 6 3** -1 -3 -2 -1 | g = 4, 5, 6, 7 |
| 12 | -2 -4 -2 0 **3 16/3 6 3/2** -2 -3 -2 0 | g = 5, 6, 7, 8 |
| 13 | -3 -4 -3 -2/5 **13/5 9/2 7 11/2** -1 -4 -3 -4/3 -1 | g = 5, 6, 7, 8 |

The failing band is min(g, m-g) >= about m/2 - 2 in this pool. The single-word region (`fitscan.py`, m = 9..24)
is min(g, m-g) <= about m/4, which is what word_G covers. The region in between certifies at m <= 13 only by LP
mixtures of search words, and no closed form was extracted for it.

## 2. word_G, the closed form

word_G is `core_word` (REVERSAL-ORBIT.md section 2, copied verbatim into `reversal_orbit.py`) with parameters that
are functions of (m, g) only. The state is (0, m, ..., m-g+1, 0, m-g, ..., 1), n = m + 2.

- Cut t = (m-3)//4 + dt.
- Core 1 is seeded at cell s1 (mod n), makes k1 = m//2 + dk sweeps, first side d1.
- Core 2 is seeded at the middle of the complement arc plus ds2, and grows until the cycle is sorted, first side d2.
  The middle is s1 + nr + 1 + (n-k1-1)//2, where nr = ceil(k1/2) if d1 = 'r' else floor(k1/2).
- The final walk is R.

The rule is chosen by m mod 4, then by g or by r = m - g. The first matching line applies; outside all lines word_G is
undefined.

| m mod 4 | rule: (dt, s1, dk, d1, ds2, d2) |
|---|---|
| 0 | g=1: (-1,1,-1,r,-1,r); 2<=g<=j-1: (0,0,-1,r,-1,r); g=j, j>=4: (-2,2,-2,l,0,l); 1<=r<=j-2: (-1,0,-1,r,-1,r); r=j-1: (0,0,-1,l,-1,r); r=j: (1,-1,-1,l,-1,r) |
| 1 | g=1: (0,1,0,l,-1,r); 2<=g<=j-1: (1,0,0,l,-1,r); g=j: (-1,1,-1,r,0,l); 0<=r<=j-1: (0,0,0,l,-1,r); r=j: (1,-1,0,r,-1,r) |
| 2 | g=1 or g=j: (0,1,-1,l,0,l); 2<=g<=j-1: (1,0,-1,r,0,l); 1<=r<=j-1: (0,0,-1,r,0,l); r=j: (1,-1,-1,r,0,l) |
| 3 | g=1: (0,1,0,l,0,l); 2<=g<=j-1: (1,0,0,l,0,l); g=j: (-2,1,0,r,0,r); 0<=r<=j: (0,0,0,l,0,l); r=j+1, j>=3: (1,-2,-1,r,-1,r) |

- **Coverage.** g <= j (from m = 16 also g = j when m = 0 mod 4) and r <= j, plus r = j + 1 when m = 3 mod 4.
  Per m that is about m/2 of the m masks {0,g}: 5 at m = 9, 12 at m = 24, 20 at m = 40.
- **Values.** length - T lies in [-11, 0] at m = 9..40. The slopes are at most m - 2. One word, weight 1, is the
  whole certificate.
- **How the rule was found.** `fitscan.py` enumerated every single-word certificate among two-core words with the
  core-2 seed within 2 of the complement middle, at m = 9..24. `cand.py` took the 87 most frequent parameter tuples in
  these relative coordinates and evaluated them at m = 9..40. A greedy cover per residue gave the intervals above. The
  intervals are read off the data at m = 9..40. They are not derived by hand.

```
m=9, g=1 (50 letters, T-3, beta (7,4))
XRXLXLXLXRXRXRXRRRRXRXLXLXRXRXRXLXLXLXLXRXRXRXRXR
```

## 3. Why the middle band fails in these pools (observations, not a proof)

- **The base binds, not the slopes.** Every miss in table 1b and in the surveys has t = 0 at the root.
- **The cheap words load the zero in gap 0.** In the full pool at m = 13, g = 6, the cheapest word is T-13 with
  beta (18, 0). Every front word with beta_0 <= 11 costs at least T+7, for example (10,12) at T+7 and (11,9) at
  T+10.
- **A heuristic reason.** The zero in gap 0 already sits between labels 1 and m, and the other zero must join it. In
  every cheap plan the joining uses crossings of the gap-0 zero by min(g, m-g) labels. Carrying a zero, rather than
  carrying a label past it, costs 3 per crossing instead of 2. So beta_0 is about 2 min(g, m-g) + noise, which exceeds
  m - 2 in the band.
- **Asymmetric cores did not help.** Core 1 with independent left and right step counts (`k2gen.sides`, `scan2.py`,
  `fitscan2.py`) did not lower the root minimum on the four band families tried:
  - m = 9 {0,4}: 9/4, against 7/3 for the symmetric pool;
  - m = 9 {0,5}: 4;
  - m = 13 {0,5}: 13/5;
  - m = 16 {0,5}: 0, which would certify at the root, but that output was not stored or re-verified, and no single
    word certifies;
  - m = 20 {0,7}: 3, and m = 20 {0,8}: 4.

## 4. Item 2: the known misses

| family | tried here | result | minimum root base excess (slopes feasible) |
|---|---|---|---|
| m=9 {5,9} (544) | tree, depth <= 4, thresholds <= 6, 11 origins | **CERTIFIED**, 5 leaves, audit ok | 1 at the root |
| m=9 {0,4} (17) | same | not found | 7/3 (two-core pool), 9/4 (asymmetric pool) |
| m=9 {0,5} (33) | same | not found | 4 |
| m=10 {0,5} (33) | same | not found | 17/4 |
| m=10 {0,6} (65) | same | not found | 4 |
| m=12 near_rev 1.12.10.11.9..2 {1,7} (130) | tree, depth <= 4, thresholds <= 6, 7 origins | not found | 74/15 (REVERSAL-ORBIT.md) |
| m=11 5.4.3.2.1.11..6 {5,10} (1056) | same | not found | 2 (REVERSAL-ORBIT.md) |
| m=12 masks 7300, 6309, 3534; m=11 masks 2456, 3685 | **not run** | | CPU budget |

The m = 9 {5,9} tree, as returned by `score_output`. The format is box, origins, lhs, then support
(weight, base, beta).

| leaf | box | origins | lhs | support |
|---|---|---|---|---|
| 1 | u = (1, 1) | (1,1) | -8 | (1, 44, (0,12)) |
| 2 | u_0 = 1, u_1 = 2 | (1,1) | -3 | (1, 44, (0,12)) |
| 3 | u_0 = 1, u_1 = 3 | (1,1) | 0 | (1, 50, (6,8)) |
| 4 | u_0 = 1, u_1 >= 4 | (1,4) | 1/3 | (1/3, 72, (1,11)), (2/3, 74, (7,5)) |
| 5 | u_0 >= 2 | (1,1) | 1/3 | (2/3, 50, (6,8)), (1/3, 59, (7,5)) |

What was tried and what was not:

- **(c) Refined-origin trees.** Run for all seven k = 2 misses above, with depth <= 4 and thresholds <= 6. The words
  are two-core words generated on each refined base (`survey.fronts_for`), with first and last picks. The origins were
  (2,1), (1,2), (3,1), (1,3), (2,2), (4,1), (1,4), plus (3,2), (2,3), (5,1), (1,5) for the m = 9, 10 rows.
- **(a) Three-core words.** Not run. The only extension tried was the asymmetric core 1 of section 3, which did not
  help.
- **(b) A long sweep from a rotated cut.** Not run.

## 5. Item 3: all two-zero masks at m = 11, 12, 13

Root leaf only, over the full two-core pool (`survey_root.py`, the same pool as the m = 9, 10 survey). Trees were
not run on the misses.

| m | masks run | root-certified | misses: gaps (root min Bbar - T) |
|---|---|---|---|
| 11 | all 66 | 59 | {0,4} 6/5, {0,5} 7/2, {0,6} 6, {0,7} 3, {5,11} 1, {6,11} 2, {7,11} 1 |
| 12 | all 78 | 72 | {0,5} 3, {0,6} 16/3, {0,7} 6, {0,8} 3/2, {6,12} 2, {7,12} 134/37 |
| 13 | 25 outer masks (a zero in gap 0 or 13) | 18 | {0,5} 13/5, {0,6} 9/2, {0,7} 7, {0,8} 11/2, {6,13} 2, {7,13} 3, {8,13} 65/18 |
| 14 | not run | | CPU budget; item 3 was cut first |

- **Interior masks.** Every mask with both zeros in gaps 1..m-1 certified at the root at m = 11 and 12. The same held
  at m = 9 and 10 in REVERSAL-ORBIT.md. At m = 13 the 66 interior masks were not run.
- **Where the misses sit.** Every miss is {0,g} or {g,m} with g near m/2. That is the band of section 3.

## 6. Conjectures (not proved; separate from the computed facts)

1. **word_G for all m >= 9.** word_G(m, g) certifies (m..1){0,g} wherever the rule of section 2 defines it. It is
   checked by evaluator and audit at m = 9..40, and by replay and criterion (7) at m = 41..80.
2. **The band needs refined origins or new words.** With unit origins, the band min(g, m-g) >= about m/2 - 2 has no
   root certificate in any pool built from insertion cores. The m = 8 group needed depth-7 trees with origins (3,1)
   for 8..1 {0,4}, which is consistent with this.
3. **Interior masks are easy.** Every two-zero mask with both zeros in gaps 1..m-1 has a root certificate among
   two-core words. This is checked at m = 9..12 only.

## 7. Limitations

- **Conditional scope.** The certificates are conditional on the group's Lemma 1 and criteria (7)/(8) with m as a
  parameter.
- **What is m-uniform.** Only word_G (and word_C, word_R1 from earlier notes). The survey and tree certificates are
  single-m search outputs.
- **Replay range.** Replay and criterion (7) for word_G stop at m = 80, not 200.
- **Not run.**
  - three-core words;
  - rotated-cut sweeps;
  - trees on the m = 11..13 survey misses;
  - the m = 13 interior masks;
  - all of m = 14;
  - the high-k masks 7300, 2456, 6309, 3534, 3685.
- **CPU.** About 40 CPU minutes in total, under the 60-minute budget.
  - Full-pool and asymmetric-pool scans: about 8 min.
  - The single-word scans at m = 9..24: about 6.5 min.
  - Trees: about 9.5 min.
  - Surveys: about 14 min.
  - Candidate evaluation and the verification script: under 1 min.
- **Git.** `autoresearch/bound-m-260925/.gitignore` ignores `checks/`. The new script, JSON and search directory must
  be force-added to be committed. Nothing was committed.
