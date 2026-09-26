# Reversal m..1 with every zero in an interior gap: survey, no closed form, and a k = 4 counterexample

Date 2026-09-26. Offline construction. There were no provider calls, no tables, no LLM-generated code and no commits.
Lemma 1 (with refinement), the cost formulas and criteria (7)/(8) are the research group's (m=8 manuscript).
`integrations/lrx_m.py`, `bound3_evaluator.py` and `bound3_audit.py` apply them with m as a parameter.
The main conjecture stays open. Every certificate below is conditional on that Lemma and those criteria.

- Re-check script: `checks/reversal_interior.py`. It never searches. With no arguments it re-checks the stored JSON
  and writes nothing. `--build` assembles the JSON from the search outputs and refuses to overwrite it. Each mode runs
  in about 2 s. Last run: 837 certified rows re-checked, 14 misses stored, `problems: none`.
- Data: `checks/reversal-interior-words.json`. New searches, raw outputs and logs: `checks/reversal_interior_search/`.
- Reproduce: `PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_interior.py`.

Notation. An interior mask has all k zeros in gaps 1..m-1, so no zero lies in gap 0 or gap m. There are C(m-1, k) of
them. T = `lrx_m.budget(m, k)`. "Base excess" is the root LP minimum of B̄ - T. "Slope excess" is the LP's minimum
of max_j β̄_j - (m-2). A mask certifies at the root iff slope excess is 0 and base excess is below 1.

## 1. Results

The observation under test was that every interior mask certifies at the root with two-core words. **It holds for
k = 2 at m = 9..13 and for k = 3 at m = 9..12. It fails for k = 4 at m = 9 and m = 10.**

| k | m | certified / interior | source of the rows |
|---|---|---|---|
| 2 | 9 | 28 / 28 | REVERSAL-ORBIT.md survey |
| 2 | 10 | 36 / 36 | REVERSAL-ORBIT.md survey |
| 2 | 11 | 45 / 45 | REVERSAL-K2.md survey |
| 2 | 12 | 55 / 55 | REVERSAL-K2.md survey |
| 2 | 13 | **66 / 66** | new (`survey_int.py`) |
| 3 | 9 | 56 / 56 | REVERSAL-K3.md survey |
| 3 | 10 | 84 / 84 | REVERSAL-K3.md survey |
| 3 | 11 | 120 / 120 | REVERSAL-K3.md survey |
| 3 | 12 | **165 / 165** | new |
| 4 | 9 | **64 / 70** | new |
| 4 | 10 | **118 / 126** | new |
| 4 | 11 | not run | CPU cut |
| 3 | 13 | not run | CPU cut |

- **Checks on all 837 certificates.** The old rows were taken unchanged from the earlier survey outputs. Every row,
  old and new, is re-scored CERTIFIED by `score_output` and confirmed `(True, 'ok')` by `audit_claim`. Every word
  sorts the unit base under `run_naive` and `run`. Each (m, k) cell lists every interior mask exactly once.
- **Support sizes.** Most certificates are 1 to 3 words. At k = 4 there are 23 single words, 51 of size 2, 72 of
  size 3, 34 of size 4 and 2 of size 5.
- **Pool.** The new survey first tries the two-core pool with cuts t0-2..t0+2, where t0 = (m-3)//4. A mask that
  fails there is re-run over the full two-core pool with all cuts, the same pool as REVERSAL-K3.md. Every new miss
  is a full-pool result. Unit origins, root leaf only, no trees.

### 1b. The 14 interior misses (k = 4, full two-core pool, root)

| m | gaps | base excess | slope excess | binding |
|---|---|---|---|---|
| 9 | {1,2,5,7} | 5/6 | 1/6 | slope |
| 9 | {1,2,6,8} | 1 | 0 | base (boundary) |
| 9 | {1,3,6,8} | 1 | 1/2 | slope |
| 9 | {1,4,7,8} | 7/4 | 0 | base |
| 9 | {1,5,6,8} | 4/3 | 0 | base |
| 9 | {2,4,7,8} | -5/6 | 1/6 | slope |
| 10 | {1,2,6,9} | 2318/341 | 0 | base |
| 10 | {1,3,6,8} | 638/195 | 0 | base |
| 10 | {1,3,6,9} | 1678/269 | 49/538 | slope |
| 10 | {1,3,7,9} | 49/16 | 0 | base |
| 10 | {1,4,6,9} | 5/3 | 0 | base |
| 10 | {1,4,7,9} | 2600/313 | 53/626 | slope |
| 10 | {1,4,8,9} | 435/91 | 0 | base |
| 10 | {2,4,7,9} | 9/7 | 0 | base |

When the slope excess is positive, the base excess shown is the one the LP reports at that minimum slope excess.

- **These are the first misses where slopes bind.** 5 of the 14 have slope excess above 0, so no mixture in the pool
  meets β̄_j <= m-2 at all. Every earlier k = 2, 3 miss (REVERSAL-K2.md, REVERSAL-K3.md) had slope excess 0.
- **Where they sit.** Every miss is a wide mask: the first zero is in gap 1 or 2 and the last is in gap m-2 or
  higher. Consecutive zeros are 1 to 4 apart. Wide masks are 41 of 70 at m = 9 and 61 of 126 at m = 10. So 35 of 41
  and 53 of 61 wide masks still certify.
- **At the LP optimum the slopes sit at the bound.** For example m = 9 {1,2,6,8} has slopes (7,7,7,7) and base
  excess exactly 1. The supports are spread-out words such as β = (9,6,6,12) and (5,2,14,6). No word is cheap on
  all four zeros.
- **Not tried on the misses.** Trees, refined origins and three-core pools were not run. These misses are "not found
  in the two-core pool at the root". They are not negatives.

## 2. Closed form: none found

The goal was one word, or a fixed small mixture, word_I(m, gaps) covering every interior mask. **No such form was
found.** The data rule out a single parametric two-core word in the coordinates tried.

- **Many interior masks have no single-word certificate.** `fitscan.py` listed every two-core word (cuts t0-2..t0+2)
  that meets criterion (7) alone:

  | k | m = 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
  |---|---|---|---|---|---|---|---|---|
  | 2: masks with no single word / interior | 8/28 | 8/36 | 6/45 | 12/55 | 15/66 | 23/78 | 23/91 | 37/105 |
  | 3: same | 38/56 | 49/84 | 56/120 | 93/165 | | | | |

  With all cuts at k = 2, m = 9, only {1,6} has no single word. So the restricted cuts lose some words, but a single
  word still does not exist for every mask.
- **No parameter tuple covers a large share.** Tuples were taken in word_G coordinates: cut offset, core-1 seed,
  sweep offset, sides, core-2 seed offset and final walk. The core-1 seed was measured three ways: from label m's
  cell, from the first zero, and from the last zero. The best single tuple covers:
  - at k = 2: 10/28, 9/36, 18/45, 17/55, 13/66, 16/78, 20/91 and 13/105 masks at m = 9..16;
  - at k = 3: 10/56, 10/84, 28/120 and 34/165 masks at m = 9..12.

  The best tuple also changes from one m to the next.
- **Why a mixture form was not attempted.** 205 of the 837 root certificates, and 108 of the 182 at k = 4, need 3
  or more words. The support words change with the gap pattern. No fixed mixture was visible, and after k = 4 failed
  the target "all interior masks" is false in this pool anyway. The replay and criterion (7) checks at m = 25..40 were
  therefore not run.

## 3. Structure (conjecture with evidence, not a proof)

- **Cheap words move zeros onto each other.** In interior certificates with one or two words, a typical support word
  puts slope 0 on one zero and 3d on its neighbour, where d is the number of labels between them. Examples at
  m = 11, k = 2:
  - {5,7}: (0,6);
  - {5,8}: (0,9);
  - {6,7}: (0,3);
  - {1,4}: (9,0);
  - {3,6}: (9,0).

  This matches the REVERSAL-CARRY.md trace model: a zero crossed from one side costs 3 per label.
- **Why k = 2, 3 interior masks are easy.** Their base excess is far below 0: -3 to -21 at m = 11, 12 for k = 2.
  So LP mixtures of such merge words can trade base for slope until each zero's average slope is at most m-2.
- **The contrast with outer masks.** A zero in gap 0 or gap m sits at the cut. In the cheap words it is carried by
  about 2 min(g, m-g) labels (REVERSAL-K2.md section 3), and there the base binds.
- **Conjecture I1.** For k = 2 and k = 3, every interior mask of m..1 has a root certificate among two-core words.
  - Checked: k = 2 at m = 9..13 and k = 3 at m = 9..12. That is 655 masks with 0 misses.
  - Not checked: any larger m.
- **Conjecture I2 (the slope bound at k >= 4).** At k >= 4, the evenly spread interior masks have no root
  certificate in the two-core pool. These are masks with zeros from gap 1-2 to gap m-2..m-1 and consecutive
  distances 1 to 4. The cause is the slope bound, not only the base: every two-core word overloads at least one zero
  when the base is near T.
  - Evidence: the 14 misses above. At the LP optimum their slopes are exactly m-2 on all zeros, or above it.
  - The cheap support words have slope sums at or above the cap k(m-2). At m = 9, where the cap is 28, (9,6,6,12)
    sums to 33 and (12,6,3,9) to 30. At m = 10, where the cap is 32, (9,6,6,15) and (12,9,3,12) both sum to 36.
  - The words with smaller sums put 14 or more on a single zero, such as (5,2,14,6) at m = 9, or cost well above T.
  - This is a pattern read off LP supports. It is not a lower bound over all words, and it does not say which of the
    wide masks fail. 35 of 41 wide masks at m = 9 and 53 of 61 at m = 10 certify.

## 4. Search scripts (`checks/reversal_interior_search/`, as run)

| script | what it does | output |
|---|---|---|
| `fitscan.py` | every single two-core word meeting criterion (7) alone on each interior mask (cuts t0±2; all cuts with `CUTS=all`) | `fit-k2-m9-16.jsonl`, `fit-k3-m9-12.jsonl` and logs |
| `survey_int.py` | root LP over the two-core pool (restricted cuts, then all cuts on failure); passes scored and audited in the job | `survey-k2-m13`, `survey-k3-m12`, `survey-k4-m9`, `survey-k4-m10` (`.jsonl`, `.log`) |

Both import `reversal_k3_search/gen3.py` unchanged. The tuple-coverage analysis of section 2 was a scratch script over
the `fit-*.jsonl` files, and it was not saved here. The all-cuts m = 9 fit scan was a scratch run, and its output is
not stored.

## 5. Limitations

- **Conditional scope.** The certificates are conditional on the group's Lemma 1 and criteria (7)/(8) at general m.
- **Cut for CPU.** k = 4 at m = 11 (210 masks) and k = 3 at m = 13 (220 masks) were not run.
- **Root only.** No trees, refined origins or extended pools were run on the 14 k = 4 misses.
- **No closed form.** Section 2 is a negative for single words in the coordinates tried. It is not a proof that no
  formula exists.
- **CPU.** About 50 CPU minutes, under the 60-minute budget.
  - The single-word fit scans took about 28 min: 1174 s for k = 2 and 522 s for k = 3.
  - The surveys took about 21 min: 141 s, 439 s, 135 s and 523 s.
  - The scratch analysis and the re-check script took about 1 min.
- **Git.** `autoresearch/bound-m-260925/.gitignore` ignores `checks/`. The new script, JSON and search directory must
  be force-added to be committed. Nothing was committed.
