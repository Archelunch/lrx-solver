# Reversal m..1 with three zeros (k = 3): the first class survey, and a closed form on the corner band

Date 2026-09-26. Offline construction. There were no provider calls, no tables, no LLM-generated code and no commits.
Lemma 1 (with refinement), the cost formulas and criteria (7)/(8) are the research group's (m=8 manuscript).
`integrations/lrx_m.py`, `bound3_evaluator.py` and `bound3_audit.py` apply them with m as a parameter.
The main conjecture stays open. Every certificate below is conditional on that Lemma and those criteria.

- Re-check script: `checks/reversal_k3.py`. It never searches. With no arguments it re-checks the stored JSON and
  writes nothing. It re-scores, re-audits and replays every stored certificate, and re-derives every word letter by
  letter from its stored generator parameters. It also re-runs the closed form. `--build` assembles the JSON from the
  search outputs and refuses to overwrite it. Each mode runs in about 2 s. Last run: `problems: none`.
- Data: `checks/reversal-k3-words.json`. Searches, raw results and logs: `checks/reversal_k3_search/`.
- Reproduce: `PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_k3.py`.

Notation. (m..1){g0,g1,g2} is the reversal with one zero in each of the gaps g0 < g1 < g2 (mask 2^g0 + 2^g1 + 2^g2).
The unit base has n = m + 3 cells. T = T_m(m+3) = m(m+1)/2 + 2(m - 2) is `lrx_m.budget(m, 3)`.
j = floor(m/4) and r2 = m - g2. "Base excess" is the root LP minimum of B̄ - T with weighted slopes <= m-2. A value
below 1 certifies.

"All masks" means all C(m+1,3) masks of the reversal m..1 itself. No quotient by symmetry was taken, and rotated
reversals such as 4.3.2.1.11..5 are separate families that were not re-run. The one known k = 3 rotation result,
4.3.2.1.11..5 {0,4,7}, is certified in REVERSAL-ORBIT.md. The unrotated 11..1 {0,4,7} is a miss here.

## 1. Results

| m | masks | root leaf | trees | certified | not certified |
|---|---|---|---|---|---|
| 9 | 120 | 106 | 6 (2 unit-origin, 4 refined-origin) | **112** | 8 |
| 10 | 165 | 147 | 1 (unit-origin) | **148** | 17 |
| 11 | 220 | 193 | 2 (unit-origin) | **195** | 25 |
| 12 | 286 | **not run** | | 3 by word_W only | CPU cut, see section 6 |

- **Checks on all 455 certificates.** Every one is CERTIFIED by `score_output` and confirmed `(True, 'ok')` by
  `audit_claim`. Every leaf word replays to the root under `run_naive` and `run` on its refined base. Every word is
  re-derived from its stored parameters.
- **Support sizes.** Root leaves use 1 word (200 families), 2 words (165), 3 words (73) or 4 words (8). Nine are trees.
- **Where the misses sit.** Every mask with all three zeros in gaps 1..m-1 certified at the root at m = 9, 10, 11.
  Every miss has a zero in gap 0 or gap m.
- **Every miss has feasible slopes.** The root LP has slope excess t = 0 in all 50 misses, so the base binds.
- **Closed form.** word_W(m, g1, g2) is one two-core word, a function of (m, g1, g2) only. It certifies
  (m..1){0,g1,g2} on a corner band that grows with m (section 3):
  - 122 rows at m = 12..24 by evaluator, audit and replay;
  - 728 rows at m = 25..40 by replay and criterion (7) with weight 1;
  - 0 failures.

### 1b. The misses (root, full two-core pool)

"Base" is the root minimum base excess with slopes feasible. The binding constraint is the base in every row.

| m | miss (gaps: base excess) |
|---|---|
| 9 | {0,1,5} 11/2; {0,1,6} 2; {0,2,7} 1; {0,3,6} 3; {0,4,5} 29/7; {0,4,9} 1; {0,5,8} 11/7; {0,5,9} 3 |
| 10 | {0,1,5} 7/6; {0,1,6} 92/29; {0,2,6} 44/21; {0,2,7} 101/39; {0,3,6} 37/21; {0,3,7} 2; {0,3,8} 2; {0,4,5} 3; {0,4,6} 30/7; {0,5,6} 3; {0,5,9} 3; {0,5,10} 2; {0,6,9} 11/7; {0,6,10} 7/2; {1,6,10} 9/5; {1,7,10} 5/3; {5,6,10} 1 |
| 11 | {0,1,6} 3; {0,1,7} 3; {0,2,7} 67/20; {0,2,8} 39/16; {0,3,8} 2; {0,3,9} 13/5; {0,4,6} 3; {0,4,7} 9/2; {0,4,8} 1; {0,4,9} 17/7; {0,5,6} 5; {0,5,7} 10/3; {0,5,9} 2; {0,5,10} 3/2; {0,5,11} 2; {0,6,7} 5/3; {0,6,9} 1; {0,6,10} 4; {0,6,11} 3; {0,7,10} 1; {0,7,11} 3; {1,7,11} 11/4; {2,8,11} 11/7; {5,6,11} 29/17; {6,10,11} 1 |

What was tried on the misses:

- **Unit-origin trees (all 59 root misses at m = 9..11).** Depth <= 3, thresholds <= 5, over the root front. These
  certified 5 families: m = 9 {0,3,7} and {0,4,8}, m = 10 {0,4,8}, m = 11 {0,3,7} and {0,4,5}.
- **Refined-origin trees (the 12 remaining misses at m = 9 only).** Origins (1,1,1), (2,1,1), (1,2,1) and (1,1,2),
  with first and last picks. Two-core pools are regenerated on each refined base. Depth <= 3, thresholds <= 5.
  These certified 4 more families: {0,2,5}, {0,3,5}, {1,6,9} and {4,5,9}.
- **Not run on the m = 10, 11 misses.** Refined-origin trees were skipped there for CPU.
- **Extended pools (diagnostic only, 3 masks at m = 9).** Three extensions were tried:
  - zero-free turns;
  - one cut per core with core 1 seeded on a zero;
  - three cores with cores 1 and 2 seeded on zeros.

  None certified. Root base excess at m = 9, per extension:

  | mask | two-core | zero-free | per-core cut | three cores |
  |---|---|---|---|---|
  | {0,1,5} | 11/2 | 11/2 | 11/3 | 13/4 |
  | {0,4,9} | 1 | 1 | 1 | 1 |
  | {0,1,6} | 2 | 1 | 2 | 1 |

  The three-core pool costs about 20 CPU s per mask at m = 9, so it was not run on all misses.

The tree certificates are in the JSON under `certified` (source, leaves, lhs). For example:

- **m = 9 {0,2,5}.** The leaf u_0 = 1 has lhs -7. The leaf u_0 >= 2 at origin (2,1,1) has lhs 1/6.
- **m = 11 {0,4,5}.** A 4-leaf unit-origin tree. Its lhs values are -17, -11, -1 and 0.

## 2. Generator

The generator is `core_word3` in `checks/reversal_k3.py`. It is the insertion-core word of REVERSAL-ORBIT.md section 2,
generalized three ways:

- **Cores.** There are up to three cores (seed, sweeps or None, first side, cut). The last core grows until the cycle
  is sorted.
- **Cuts.** There is one cut per core, as in word_K of REVERSAL-CARRY.md.
- **Zero-free turns.** Optionally, absorbing a zero cell keeps the side, as in word_K's core-2 schedule.

With one shared cut, no zero-free turns and at most two cores, it equals `core_word` letter by letter. That was checked
on 3000 random parameter draws with 0 mismatches.

The search pool (`reversal_k3_search/gen3.py`) generates the same words. It prices them with the fast_profile
bookkeeping as they are built, so shared prefixes and the two final walks are priced once:

- **Agreement with the old pool.** Its two-core front equals `reversal_orbit_search/fast.gen_pool` +
  `front_fast` on 6 test bases. One of them is refined, with picks.
- **Random words.** 5067 random three-core, per-core-cut and zero-free words were re-priced by `lrx_m.Profile` and
  replayed, with 0 disagreements (`validate.py`).
- **Front words.** Every front word used in an LP is re-priced by `lrx_m.Profile` with an assert.
- **Speed.** It is about 1.6 times faster than the old pool.

## 3. Closed form word_W on the corner band

**Definition.** word_W(m, g1, g2) acts on the unit base of (m..1){0,g1,g2}: cells (0, m..m-g1+1, 0, ..., 0, m-g2..1),
n = m+3. It is a two-core word with final walk R:

- **Cut.** t = (m-3)//4 + dt.
- **Core 1.** Seeded at cell 0, on the gap-0 zero. It makes k1 = m//2 + dk sweeps, first side d1.
- **Core 2.** Seeded at the middle of the complement arc, mid = nr + 1 + (n - k1 - 1)//2. Here nr = ceil(k1/2) if
  d1 = 'r' and floor(k1/2) otherwise. It grows until the cycle is sorted, first side d2.

| m mod 4 | (dt, dk, d1, d2) | band (j = floor(m/4), r2 = m - g2) |
|---|---|---|
| 0 | (0, 1, l, r) | 2 <= g1 <= j-1, 0 <= r2 <= j-1 |
| 1 | (0, 0, r, l) | 3 <= g1 <= j-1, 0 <= r2 <= j-1 |
| 2 | (1, 0, l, l) | 2 <= g1 <= j-1, 0 <= r2 <= j |
| 3 | (-1, 1, r, r) | 3 <= g1 <= j, 0 <= r2 <= j-1 |

The band is a rectangle: g1 near the gap-0 zero on one side, g2 near it on the other side (cyclically, gap m is
adjacent to gap 0). It is empty at m <= 11 and at m = 13, and starts at m = 12 with {0,2,10}, {0,2,11}, {0,2,12}. Its
size is about (j-2)^2: 8 masks at m = 16, 24 at m = 24, 80 at m = 40.

**Verified.**

- **m = 9..24.** All 122 band rows are CERTIFIED by `score_output`, `(True, 'ok')` by `audit_claim`, and replay under
  `run_naive` and `run`.
- **m = 25..40.** All 728 band rows replay and satisfy `lrx_m.mixture_criterion(m=m)` with weight 1.
- **Values.** B - T lies in [-18, 0]. Every slope is at most m - 2. beta_0 = m - 2 in the rows inspected at
  m = 36..39, so the gap-0 zero is exactly at the bound.

```
word_W(12, 2, 12)  (94 letters)
XRXRXLXLXLXRXRXRXRXLXLXLXLXLXRXLLLLLLXRXLXLXRXRXRXLXLXLXLXRXRXRXRXRXLXLXLXLXLXLXRXRXRXRXRXRXRR
```

**How it was found.** The rule was read off search data, not derived by hand.

1. **fitscan3.py.** At m = 9..11, it listed every single two-core word that meets criterion (7) alone on
   {0,g1,g2}. Such words exist mainly where all three zeros are cyclically close to gap 0.
2. **cornerscan.py.** A parametric scan in word_G-style coordinates covered g1 in {1,2}, r2 in {0,1} at m = 9..20.
   Its hits were intersected per m mod 4.
3. **cornerfit.py.** It evaluated the 28 surviving tuples on g1 <= j+2, r2 <= j+2 at m = 9..40. The best tuple per
   residue covers the rectangles above. It also covers a few cells outside them, for example g1 = 1 with r2 = 0 or
   r2 >= 2. Those cells are not claimed.

Other attempts gave nothing. word_G's rules applied to the three-zero state certify 2 masks in m = 9..24.
Relative-coordinate tuples harvested from the LP supports cover at most 4 masks each.

## 4. Observations (not proved)

1. **Interior masks are easy.** Every three-zero mask with all zeros in gaps 1..m-1 has a root certificate among
   two-core words at m = 9..11. This is the k = 3 analogue of REVERSAL-K2.md conjecture 3.
2. **The misses have a zero in gap 0 or gap m.** Most are {0,g1,g2} with g1 or g2 in the k = 2 middle band, around
   m/2. That matches the k = 2 picture: the gap-0 zero carries about 2 min(g, m-g) in slope in cheap plans
   (REVERSAL-K2.md section 3, REVERSAL-CARRY.md section 2).
3. **The base binds.** Every miss has feasible slopes, and 7 of them sit exactly at base excess 1 (the boundary).
   As at k = 2, the obstruction is in the word pool or the origins. No exact negative was computed for k = 3.
4. **word_W for all m >= 12.** word_W certifies every band mask. This is checked by evaluator and audit to m = 24,
   and by replay and criterion (7) to m = 40.

## 5. Search scripts (`checks/reversal_k3_search/`, as run)

| script | what it does | output |
|---|---|---|
| `gen3.py` | the pool generator with fused pricing | |
| `validate.py` | agreement checks against the old pool and generators | |
| `survey3.py` | all C(m+1,3) masks at one m, root leaf over the full two-core pool; root passes are scored and audited in the job | `survey-m{9,10,11}.jsonl` and `.log` |
| `misses3.py` | stages `tree` (unit-origin tree), `ext` (extended root pool), `orig` (refined-origin trees) | see below |
| `diag_ext.py` | the extended-pool diagnostic of section 1b | not saved; numbers above |
| `harvest.py`, `gtest.py`, `fitscan3.py`, `corner.py`, `cornerscan.py`, `cornerfit.py` | the closed-form search of section 3 | `harvest-top.json`, `fit-hits.json` and `.log`, `corner-eval.json`, `cornerscan.json`, `cornerfit.json` |

The `misses3.py` outputs:

- `misses-tree.jsonl` and `misses-orig-m9.jsonl`: the first runs.
- `misses-tree-b.jsonl` and `misses-orig-m9b.jsonl`: re-runs of the 9 certified jobs. The first runs keyed the
  generator parameters by word only, and equal letters recur on different refined bases. So 2 of the 9 trees did not
  re-derive, although their score, audit and replay passed. The re-runs key the parameters by (origin, word). They
  produced the same certified families, and the JSON uses only them. The first-run files are kept unchanged.

## 6. Limitations

- **Conditional scope.** The certificates are conditional on the group's Lemma 1 with refinement and criteria (7)/(8)
  at general m.
- **m = 12 was cut.** The full root survey would have cost about 31 CPU minutes (about 6.5 s per mask over 286 masks).
  The instruction was to cut m = 12 first. The only m = 12 certificates are the three word_W rows.
- **Trees.** Refined-origin trees ran only at m = 9. The origins had one coordinate equal to 2. m = 10 and 11 misses
  had unit-origin trees only.
- **Pools.** Three-core and per-core-cut pools were a 3-mask diagnostic, not a survey stage. A miss here proves
  nothing beyond "not found in these pools".
- **Closed form.** word_W is read off search data. Its band is verified by evaluator and audit only to m = 24, and by
  replay and criterion (7) to m = 40. There is no hand count and no proof.
- **CPU.** About 50 CPU minutes in total, under the 60-minute budget.
  - Recorded job CPU was 2041 s: surveys 1423 s, trees 618 s.
  - The rest is estimated from wall times: the fit scans about 8 min, validation, timing and diagnostics about
    8 min, and the check script 2 s.
- **Git.** `autoresearch/bound-m-260925/.gitignore` ignores `checks/`. The new script, JSON and search directory must
  be force-added to be committed. Nothing was committed.
