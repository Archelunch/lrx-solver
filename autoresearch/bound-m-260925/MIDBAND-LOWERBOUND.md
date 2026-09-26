# Middle band: exact root-leaf LP by an exhaustive oracle (m = 5..11)

Date 2026-09-26. Offline. There were no provider calls, no LLM-generated code was executed, and nothing was committed.
No BFS table was read from disk. Lemma 1, its bookkeeping and criteria (7)/(8) are the research group's (m=8
manuscript). `lrx_m`, `bound3_evaluator` and `bound3_audit` apply them with m as a parameter. The main conjecture
stays open. Every positive statement below is conditional on that Lemma and those criteria. Every negative rests only
on Lemma 1's pricing (`lrx_m.Profile`) and the form of criterion (7) at the unit origin.

The task was to turn "the base binds in the middle band" into proofs. The exact oracle shows that the premise is
**false at m = 10 {0,5} and m = 11 {0,6}**: both roots are certifiable, and certificates are stored. It is **true at
m = 11 {0,5}**: a portable dual certificate proves that no root-leaf certificate exists there. It is also true at
m = 7 {0,3}, 8 {0,4} and 9 {0,4}. m >= 12 is out of reach for this oracle.

## 1. Results

| instance | T+1 | root verdict | how | exact root LP value V | dual (lambda_0, lambda_1) |
|---|---|---|---|---|---|
| 10 {0,5} | 64 | **CERTIFIED** (lhs 1/2) | mixture 1/4, 1/2, 1/4 of three oracle words | **127/2 exactly** | (11/4, 1/4) |
| 11 {0,5} | 76 | **NO ROOT-LEAF CERTIFICATE** | every word has 5B + 13 beta_0 >= 497 = 5(T+1) + 13s | >= 76 | (13/5, 0) |
| 11 {0,6} | 76 | **CERTIFIED** (lhs -1) | mixture 1/2, 1/2 of two oracle words | **74 exactly** | (2, 0) |
| 12 {0,5}, {0,6} | 89 | out of reach | capped exact search INCOMPLETE (section 5) | | |
| 13 {0,6}, {0,7} | 103 | out of reach | capped exact search INCOMPLETE (section 5) | | |
| 14 {0,7}, {0,8}, {0,9} | 118 | out of reach | capped exact search INCOMPLETE (section 5) | | |

- **m = 10 {0,5}.** REVERSAL-MIDBAND.md and REVERSAL-CARRY.md list it as not found. The earlier best was root lhs 3/2
  and u0 = 3, 4 leaves failing.
  - The words are (69, (6,8)), (63, (8,10)) and (59, (10,4)). None was in any stored pool.
  - Mixed 1/4, 1/2, 1/4 they give Bbar = 127/2 < 64 and betabar = (8, 8).
  - `score_output`: CERTIFIED, lhs 1/2. `audit_claim`: (True, 'ok'). Replay under `run` and `run_naive`: ok.
  - The staircase of trees (u0 = 3, 4) is no longer needed.
- **m = 11 {0,6}.** It was also not found before; the restricted pools gave lhs 8/7.
  - The words are (76, (8,10)) and (72, (10,4)), mixed 1/2, 1/2: Bbar = 74, betabar = (9, 7).
  - `score_output`: CERTIFIED, lhs -1. `audit_claim`: (True, 'ok'). Replay: ok.
- **m = 11 {0,5}: exact negative.** Every accepted sorting word of (0,11,..,7,0,6,..,1) has 5B + 13 beta_0 >= 497.
  - A root mixture needs Bbar < 76 and betabar_0 <= 9, i.e. 5 Bbar + 13 betabar_0 < 497. So no word set and no
    weights certify the root leaf, and every certificate of this family must split the box.
  - The exact minimum of 5B + 13 beta_0 lies in [497, 511]. The upper end comes from pool words (71, (12,3)) and
    (84, (7,10)). The unbounded search at these multipliers hit the 25M-node cap, so the exact value is not claimed.
  - This is the second exact root-leaf negative in the repository, after m = 9 {0,4} (Session 29), and the first at m > 9.
- **Smaller m** (section 4). The exact root LP is below T+1 for every g at m = 5, 6 and m = 10, except where noted.
  It is >= T+1, so the root leaf is impossible, exactly at m = 7 {0,3}, m = 8 {0,4} and m = 9 {0,4}. Among these,
  m = 7 {0,3} and m = 8 {0,4} are new negatives; both sit on the boundary V = T+1.

Files, all new, under `autoresearch/bound-m-260925/negcert/`:

| file | role | sha256 |
|---|---|---|
| `negcert_general.py` | the checker: stdlib only, no repository imports, reads only the JSON it is given | `5e703d2f…` |
| `negcert-m11-05.json` | refutation certificate, m = 11 {0,5} | `abd088e5…` |
| `lpcert-m10-05.json` | exact root LP value 127/2, m = 10 {0,5} (dual side; `refutes: false`) | `ab0c0d96…` |
| `lpcert-m11-06.json` | exact root LP value 74, m = 11 {0,6} (dual side) | `7e13b917…` |
| `midband-certified.json` | the two positive root certificates (words, weights) | `1799b571…` |
| `midband_positive_check.py` | re-checks the positives with `score_output`, `audit_claim`, replay and `mixture_criterion` | |
| `validate_general.py` | cross-checks `profile_cost` against `lrx_m.Profile` (refined origins, random picks) | |
| `midband_colgen.py`, `midband_driver.py`, `midband_pool.py`, `midband_summary.py` | exploration: column generation, single oracle runs, seed harvesting, tables | |
| `midband-runs/` | logs and JSON of every run, including the small-m sweep and the refutations m = 7 {0,3}, 8 {0,4}, 9 {0,4} | |

`negcert_check.py`, `negcert-m9-04.json` and `NEGCERT.md` are untouched.

## 2. The checker and the certificate format

`negcert_general.py` extends `negcert_check.py` in three ways.

1. **Functional.** F_W = wB·B + w0·beta_0 + w1·beta_1 with nonnegative integer weights. A rational multiplier
   lambda_j is w_j / wB.
2. **Context.** It has two weighted zeros, so the context is (kind, f_0, f_1), with kind in {S, X, L, R} and one flag
   per weighted zero. That gives 12 contexts; with one weighted zero there are 6, exactly those of `negcert_check.py`.
   - Lemma C's six-case table applies to each zero separately, because the letter sequence is shared and each zero's
     cz_j depends only on it.
   - Lemma R holds per zero: |a+b| <= |a|+|b|, and A_j drops by 0 or 2.
   - Unweighted zeros and zeros of refined blocks that are not picked all get one code.
3. **Bounded search.** The certificate states a claim K. A* with the verified consistent pattern-table heuristic
   prunes every node with g + h >= K. If no root is reached below K, every reduced sorting word has F_W >= K, and by
   Lemma R so does every accepted one. Exhausting the node cap raises INCOMPLETE and never yields a bound.

The completeness argument is written out in the docstring, as in `negcert_check.py`.

**Certificate fields.**

| field | meaning |
|---|---|
| `m`, `labels`, `mask`, `base` | the family; the unit base is recomputed and compared |
| `origin`, `picks` | optional refined origin and picks (not used by the stored certificates) |
| `T`, `s` | T = T_m(m+2) and s = m-2, recomputed |
| `weights` | [wB, w0, w1] |
| `lambda` | the multipliers, for the reader |
| `claim_min` | K: the proven lower bound on F_W over all accepted sorting words |
| `exact` | true when some witness attains K, making K the exact minimum |
| `refutation_threshold` | wB(T+1) + s(w0+w1) |
| `kind`, `refutes` | a root certificate fails unless K >= threshold, except when `refutes` is false |
| `lp_value` | when present, must equal (K - s(w0+w1))/wB, the implied lower bound on the root LP |
| `abstractions` | label partitions for the pattern tables |
| `witnesses` | words with their (B, beta) re-priced by the letter-by-letter Profile transcription |

**The iff.** If some (l0, l1) >= 0 has min F >= T+1 + s(l0+l1), then no root mixture exists; the checker prints
this. Conversely, if the root LP value V is >= T+1, LP duality over the (B, beta) points gives such multipliers.
Column generation (below) found them in every refuted case. Only the first direction is used as a proof.

**Exact LP values.** A pool mixture gives V <= V_P. A bounded search at the pool's multipliers with K = the pool's
F value, returning nothing below K, gives V >= V_P. `lpcert-*.json` is that second half; the mixture is the first.

**Column generation** (`midband_colgen.py`, exploration only):
1. Take a pool of words, seeded from every LRX string in `checks/**` and earlier runs (`midband_pool.py`), plus
   optional exact seeds at lambda = (0,0), (3,0), (0,3).
2. Solve the pool LP exactly in Fractions by vertex enumeration of the dual.
3. Call the oracle at the pool's multipliers.
4. Either no word is below the bound, which gives a refutation or exactness, or the optimal word joins the pool.
   Repeat.

## 3. Observed outputs and timings

Timings are wall clock on the lab Mac, Python 3.12.8, shared with other agents (load 5 to 8).

**`python3 -I negcert_general.py lpcert-m11-06.json`** (isolated copy): VERIFIED in 577 s.

```
statement: m=11 state=[0, 11, 10, 9, 8, 7, 6, 0, 5, 4, 3, 2, 1]  min over accepted sorting words of 1*B + 2*beta_0 + 0*beta_1 >= 92
pattern table [[11, 10, 9], [8, 7, 6], [5, 4, 3], [2, 1]]: 14414400 abstract vectors, 86486400 nodes, 172233600 edges, consistent; max h 85; bound at start 80 (472.7 s)
bounded A* (prune f >= 92): no sorting word below 92; 9477482 expansions, 9477482 stored (101.9 s)
witness RXLXRXRXRXLXLXLXLLLXLXLXLLXLXRRXLXRRXRXRXLXLXLXRRXLXRXRXRXLXLXLXLXLXLLXLLXLX: B=76 beta=[8, 10] F=92 ok
witness RXRXRRXLXLXLXLLLXLXLXLXLLXRXRRXRXRXLXLXLXRRXLXRXRXRXLXLXLXLXLXLLLXLXLXRX: B=72 beta=[10, 4] F=92 ok
exact minimum 92 (lower bound by search, attained by a witness)
implied lower bound on the root LP value min{Bbar : betabar_j <= s}: (92 - 9*2)/1 = 74 (T+1 = 76)
VERIFIED
```

**`python3 -I negcert_general.py lpcert-m10-05.json`**: VERIFIED in 136 s (144 s on the first run). The bounded
search proves 4B + 11 beta_0 + beta_1 >= 350. Three witnesses attain it: (69, (6,8)), (63, (8,10)) and (59, (10,4)).
The implied LP bound is (350 - 96)/4 = 127/2.

**`python3 -I negcert_general.py negcert-m11-05.json`**: VERIFIED in 743 s, 6.3 GB peak.

```
statement: m=11 state=[0, 11, 10, 9, 8, 7, 0, 6, 5, 4, 3, 2, 1]  min over accepted sorting words of 5*B + 13*beta_0 + 0*beta_1 >= 497
pattern table [[11, 10, 9], [8, 7, 6], [5, 4, 3], [2, 1]]: 14414400 abstract vectors, 86486400 nodes, 172233600 edges, consistent; max h 453; bound at start 431 (482.6 s)
bounded A* (prune f >= 497): no sorting word below 497; 23907926 expansions, 23907926 stored (259.3 s)
witness LXLXRXRXLXLXLXRXRXRXRRRRRXRXLXLXRXRXLLLXRXRXRXRRXLXLXLXLXLXLXRXRXRXRXRX: B=71 beta=[12, 3] F=511 ok
witness RXLLLLLXLLXRXRXRXLXLXLLXRXRXRXRXRXLXLXLXLXLLXRXRXRXRXRXRXRXLXLXLXLXLXLXLLLXLXRXLLXRX: B=84 beta=[7, 10] F=511 ok
witness LLXRXLXLXRXRXRXLXLXLXLXRXRXRXRXRRRRXRXLXLXRXRXRXLXLXLXLXRXRXRXRX: B=64 beta=[15, 0] F=515 ok
root mixture needs Bbar < T+1 = 76 and betabar_j <= s = 9, so 5 Bbar + 13 betabar_0 + 0 betabar_1 < 497; every word, hence every mixture, has >= 497: NO ROOT-LEAF CERTIFICATE
total 742.0 s
VERIFIED
```

**Colgen run, m = 11 {0,5}** (`midband-runs/colgen-m11-g5.log`): pool LP from 7 seed words 394/5 at lambda = (13/5, 0).
The oracle with W = (5,13,0) and K = 497 proved "no word below 497" in one call: table 477 s, search 229 s,
23,907,926 expansions. The unbounded search for the exact value at the same multipliers then stopped at the 25M cap
(INCOMPLETE, 436 s). Total 1,572 s.

**Colgen run, m = 11 {0,6}** (`midband-runs/colgen-m11-g6.log`, mode exact): three oracle calls, 1,803 s in total,
most of it table builds under load (290 to 1,035 s each).

| lambda | K | result | expansions | search |
|---|---|---|---|---|
| (3/2, 0) | 176 | new column (67, (13,1)), F = 173 | 14.7M | 56 s |
| (9/5, 0) | 452 | new column (72, (10,4)), F = 450; pool LP 74 < 76 | 14.2M | 81 s |
| (2, 0) | 92 | no word below 92: exact V = 74 | 9.5M | 42 s |

An earlier single call with W = (3,7,0) produced the first column (76, (8,10)) at F = 284 < 291, in 9.2M expansions
and 36 s. It used the same 14.4M-vector table (`probe-m11-g6-bigtable.log`, 4.5 GB peak).

**Colgen runs, m = 10 {0,5}**: the refute run took 68 s. One oracle call returned (63, (8,10)), and the pool LP
dropped to 1215/19 < 64. The exact run took 578 s and three oracle calls, of 2.8M to 3.8M expansions each.

**Coarse tables fail at m = 11.** With 4-class tables (1.8M vectors), m = 11 {0,6} hit the 30M cap after 950 s, and
m = 11 {0,5} hit the 12M cap. Weighted A* column generation (omega = 3, 2, 1.5, 3M expansions each) found nothing.
The logs are kept as `*.small-table-attempt.*` and `*.weighted-attempt.*` and `*.exact-attempt.*`.

**Regression.** `negcert_general.py` on the m = 9 {0,4} statement (W = (1,3,0), K = 75, witness (48, (9,3))) gives
VERIFIED. The bounded search takes 0.7 s after a 17 s table build.

**Validation.**
- `--selftest` (9 s, isolated copy): VERIFIED.
  - 898 random sorting words at five weight vectors, including a refined block of two zeros: reduction never
    increases F, and the model equals the transcription.
  - 28 small exact cases at m = 5, 6: A* equals a raw Dijkstra over (vector, last letter, cz_0, cz_1), equals the
    witness price, and the bounded search is tight at K = F and K = F+1.
  - 6 refined-origin cases with picks first and second atom.
  - The m = 9 witnesses re-price as in `negcert-m9-04.json`.
- `validate_general.py` (48 s, imports the repository on purpose): 1,100 words at m = 4..6 over origins (1,1),
  (2,1), (1,2), (3,1) with random picks. `profile_cost` equals `lrx_m.Profile` on all of them: VALIDATED.
- **Negative test.** `lpcert-m10-05.json` with `claim_min` raised to 351 fails in 162 s (isolated copy). The search
  finds a word with F = 350 < 351, the witness and `lp_value` checks fail, and the checker ends with `FAILED`.
- `midband_positive_check.py`: both positives CERTIFIED, audit ok, replay ok, stored weights pass
  `mixture_criterion`. It prints `problems: none`.

## 4. Exact root LP over all words, m = 5..10 (item 2 data)

These come from exact column generation in every case: the last oracle call proved no word below the pool value.
Columns:
- d = min B;
- min B + 3 beta_0 and min B + 3 beta_1 are the exact minima from the seed calls;
- V is the exact root LP value min {Bbar : betabar_j <= s};
- "dual" is the multiplier that proves V.

All values are shown minus T. The root leaf is impossible iff V - T >= 1.

| m | g | T | d - T | min B+3b0 - T | min B+3b1 - T | V - T | dual (l0, l1) | root |
|---|---|---|---|---|---|---|---|---|
| 5 | 1 | 18 | -3 | 6 | -3 | -3 | (0, 0) | certifiable |
| 5 | 2 | 18 | -5 | 9 | -5 | 0 | (5/3, 0) | certifiable |
| 5 | 3 | 18 | -5 | 8 | -5 | 0 | (2, 0) | certifiable |
| 5 | 4 | 18 | -2 | 5 | -1 | -4/3 | (1/3, 0) | certifiable |
| 6 | 1 | 25 | -3 | 8 | -1 | -2 | (1, 0) | certifiable |
| 6 | 2 | 25 | -6 | 11 | -6 | -2/3 | (8/3, 0) | certifiable |
| 6 | 3 | 25 | -6 | 12 | -6 | 0 | (3/2, 0) | certifiable |
| 6 | 4 | 25 | -5 | 9 | -5 | -3 | (2/3, 0) | certifiable |
| 6 | 5 | 25 | -2 | 6 | 0 | -2 | (0, 0) | certifiable |
| 7 | 1 | 33 | -3 | 10 | 1 | -3 | (0, 0) | certifiable |
| 7 | 2 | 33 | -5 | 13 | -5 | -2 | (3, 0) | certifiable |
| 7 | 3 | 33 | -7 | 16 | -7 | 1 | (3, 0) | REFUTED |
| 7 | 4 | 33 | -7 | 13 | -7 | -2/3 | (5/3, 0) | certifiable |
| 7 | 5 | 33 | -5 | 10 | -5 | -3 | (1, 0) | certifiable |
| 7 | 6 | 33 | -2 | 9 | 3 | -2 | (0, 0) | certifiable |
| 8 | 1 | 42 | -3 | 13 | 5 | -2 | (1, 0) | certifiable |
| 8 | 2 | 42 | -6 | 14 | -4 | -4 | (1, 0) | certifiable |
| 8 | 3 | 42 | -7 | 17 | -7 | -1 | (2, 0) | certifiable |
| 8 | 4 | 42 | -8 | 17 | -8 | 1 | (2, 0) | REFUTED |
| 8 | 5 | 42 | -8 | 14 | -8 | -2 | (2, 0) | certifiable |
| 8 | 6 | 42 | -5 | 11 | -3 | -3 | (2/3, 0) | certifiable |
| 8 | 7 | 42 | -2 | 12 | 6 | -2 | (0, 0) | certifiable |
| 9 | 1 | 52 | -3 | 16 | 7 | -3 | (0, 0) | certifiable |
| 9 | 2 | 52 | -5 | 17 | -1 | -4 | (1, 0) | certifiable |
| 9 | 3 | 52 | -7 | 20 | -7 | -1 | (3, 0) | certifiable |
| 9 | 4 | 52 | -9 | 23 | -9 | 2 | (3, 0) | REFUTED |
| 9 | 5 | 52 | -9 | 20 | -9 | -1 | (5/3, 0) | certifiable |
| 9 | 6 | 52 | -7 | 17 | -7 | -4 | (1, 0) | certifiable |
| 9 | 7 | 52 | -5 | 14 | -1 | -3 | (1, 0) | certifiable |
| 9 | 8 | 52 | -2 | 15 | 9 | -2 | (0, 0) | certifiable |
| 10 | 1 | 63 | -3 | 19 | 11 | -2 | (1, 0) | certifiable |
| 10 | 2 | 63 | -6 | 19 | 2 | -4 | (1, 0) | certifiable |
| 10 | 3 | 63 | -7 | 21 | -5 | -3 | (2, 0) | certifiable |
| 10 | 4 | 63 | -10 | 24 | -10 | 0 | (5/2, 0) | certifiable |
| 10 | 5 | 63 | -10 | 24 | -10 | 1/2 | (11/4, 1/4) | certifiable |
| 10 | 6 | 63 | -9 | 21 | -9 | -3 | (2, 0) | certifiable |
| 10 | 7 | 63 | -8 | 18 | -6 | -6 | (1/2, 0) | certifiable |
| 10 | 8 | 63 | -5 | 17 | 3 | -3 | (2/3, 0) | certifiable |
| 10 | 9 | 63 | -2 | 18 | 12 | -2 | (0, 0) | certifiable |
| 11 | 5 | 75 | -11 (from REVERSAL-MIDBAND.md) | | | >= 1 | (13/5, 0) | REFUTED |
| 11 | 6 | 75 | -11 (from REVERSAL-MIDBAND.md) | | | -1 | (2, 0) | certifiable |

Observations:

- **The binding multiplier is almost always on the gap-0 zero alone** (lambda_1 = 0). The only exception is
  m = 10 {0,5}, with lambda = (11/4, 1/4).
- **Root-impossible cases.** The root is impossible exactly at m = 7 {0,3}, 8 {0,4}, 9 {0,4} and 11 {0,5}, and at no
  other (m, g) with m <= 10. For m = 11 only g = 5, 6 were computed.
  - These are g = (m-1)/2 for odd m (7, 9, 11) and g = m/2 at m = 8.
  - At m = 10 the peak is g = 5 with V - T = 1/2, which is certifiable.
- **Peak of V - T over g**: 0, 0, 1, 1, 2, 1/2 at m = 5..10.
  - The peak is not monotone in m.
  - At m = 10 the whole band is root-certifiable, and so is m = 11 {0,6}.
- **Restricted pools overstate the base excess.**

  | instance | stored pools (seed LP - T) | exact V - T |
  |---|---|---|
  | 10 {0,5} | 9/5 | 1/2 |
  | 11 {0,6} | 4/3 | -1 |
  | 11 {0,5} | 19/5 | >= 1 |

  - The optimal words, of types (B, (8,10)) and (B, (10,4)), carry both zeros at slopes near s. None of the stored
    generators (word_S, word_K, word_M, word_C, shortest words) produces them.
  - So the "minimum base excess 16, 16, 30, 46, 64, 84 at g = m/2, m = 14..24" in REVERSAL-CARRY.md is an excess over
    restricted pools only. It is not evidence that the base binds.
- **min B + 3 beta_0 - T** grows with m at the band centre: 9, 12, 16, 17, 23, 24 at m = 5..10. The unit distance
  d - T stays in [-10, -2].

### 4a. What can be proved in general, and why it is not enough

**Lemma (arc crossings).** Let w be an accepted sorting word of the unit base of (m..1){0,g}. Then
A_0 + A_1 >= min(g, m-g), hence beta_0 + beta_1 >= 2 min(g, m-g).

*Proof.* Zeros never swap with each other, so the cyclic order of Z0 and Zg is fixed. Their two arcs hold
A = {m..m-g+1} and B = {m-g..1}. A label changes arc only in an X with a zero, and each such X counts once in A_0
or A_1. At the root the two zeros are adjacent, so one arc is empty. If it is A's arc, each of the g labels of A made
an odd number of label-zero swaps, so A_0 + A_1 >= g; otherwise A_0 + A_1 >= m - g. Finally beta_j >= 2 A_j by
definition. ∎

This is the only m-general inequality obtained. It cannot refute a root leaf: in the band 2 min(g, m-g) <= m < 2s,
so slopes alone never bind. Every exact negative above needs the base-slope trade-off B + lambda beta_0, and no
m-general lower bound for that functional was found. The one-sided-crossing model of REVERSAL-CARRY.md (3 per
crossing) cannot be made into a lemma: the optimal words at m = 10, 11 beat the model by carrying labels past both
zeros.

## 5. Out of reach: m >= 12 (item 1, remaining instances)

The capped exact searches run at the seed-pool multipliers, with the bound at the refutation threshold. "f reached" is
the A* frontier when the cap hit; the search must reach K to decide.

| instance | W = (wB, w0, w1) | K | tables (vectors, start bound, build) | cap | f reached | search |
|---|---|---|---|---|---|---|
| 12 {0,5} | (3,4,0) | 307 | 4+4+4 classes (6.3M, 222, 132 s) | 10M | 259 | 64 s |
| 12 {0,6} | (3,4,0) | 307 | three tables: 3.4M (194), 3.4M (182), 6.3M (231) | 25M | 277 | 1,020 s, 8.4 GB |
| 13 {0,6} | (3,7,0) | 386 | 6+5+2 classes (7.6M, 255, 228 s) | 10M | 299 | 53 s |
| 13 {0,7} | (3,7,0) | 386 | 6+5+2 classes (7.6M, 262, 229 s) | 10M | 303 | 67 s |
| 14 {0,7} | (7,25,1) | 1138 | 7+6+1 classes (5.8M, 717, 344 s) | 10M | 847 | 58 s |
| 14 {0,8} | (1,3,0) | 154 | 7+6+1 classes (5.8M, 93, 126 s) | 10M | 110 | 52 s |
| 14 {0,9} | (1,3,0) | 154 | 7+6+1 classes (5.8M, 96, 134 s) | 10M | 112 | 46 s |

All seven are INCOMPLETE; none decides anything. The multipliers are those of the stored-pool LP, which section 4
shows can be far from the exact ones. At the cap, the remaining gap K - f is 16, 10, 29, 28, 42, 44 and 42 in units of B.
For comparison, the m = 11 {0,5} refutation closed a gap of 66/5 (start bound to K) in 24M expansions.

- **The bottleneck is the heuristic.**
  - At m = 11, the 3-class table (14.4M abstract vectors, about 8 minutes to build and 4.5 GB) turns a failed 30M
    search into a 9M to 24M search.
  - At m = 12 the analogous table has 67M vectors (4 classes of 3) and does not fit this Python implementation.
  - The m = 12 probe with three smaller tables reached f = 277 of 307 after 25M expansions, 1,020 s and 8.4 GB.
- **Not attempted.** Refined origins at m = 10 were not run: the root certificate makes the u0 = 3, 4 staircase moot.

## 6. Item 3: boundary cases with excess 1

| case | status |
|---|---|
| m = 10 {0,5}, u0 = 4 | moot: the root leaf is CERTIFIED (lhs 1/2), so no tree is needed. The exact root LP value is T + 1/2. |
| m = 16 {0,10}, 19 {0,8}, 23 {0,14}, 24 {0,10} | out of reach (18 to 26 cells). No exact computation was made; the stored "excess 1" is over restricted pools only. After section 4, it should be read as an upper bound on the true root LP excess, which may be lower, possibly below 1. |

## 7. Conjectures (data only, not proved)

**Conjecture 1 (odd centre).** For odd m >= 7, the root leaf of (m..1){0,(m-1)/2} has no certificate: the root LP
value is >= T+1, with a dual multiplier on beta_0 alone.
- Evidence: exact at m = 7, 9, 11.
- Duals: (3, 0), (3, 0), (13/5, 0).
- V - T: 1, 2, and >= 1 at m = 11.
- Consistent with REVERSAL-CARRY.md, where no certificate is known at 13 {0,6}, 15 {0,7}, 17 {0,8}, 19 {0,9},
  21 {0,10} or 23 {0,11}.

**Conjecture 2 (even centre certifiable from m = 10).** For even m >= 10, every root leaf in the band is certifiable.
Evidence: m = 10 exact, all g; V - T at g = m/2 is 1 at m = 8 and 1/2 at m = 10. This is weaker. It rests on one m,
and m = 12 is out of reach.

**Conjecture 3 (no base barrier away from the odd centre).** For m >= 10 and g != (m-1)/2, the exact root LP
excess V - T is <= 1/2.
- Evidence: m = 10, all nine g; m = 11 {0,6}.
- It would make the m >= 14 middle band a search problem for richer word families, of the (8,10) and (10,4) types
  found here, rather than an impossibility.

**Open question.** Is there an m-general lower bound on min_w B + lambda beta_0 that reproduces the odd-centre
refutations? The data give min B + 3 beta_0 - T = 16, 23 at m = 7, 9 and min 5B + 13 beta_0 >= 497 at m = 11. No
formula was fitted.

## 8. Limitations

- **Conditionality.** The positives are conditional on Lemma 1 with refinement and criteria (7)/(8) at general m,
  as applied by `bound3_evaluator` and `bound3_audit`. The negatives assume only that `profile_cost` is the
  group's Lemma 1 bookkeeping (validated against `lrx_m.Profile`) and the form of criterion (7) at the unit origin.
  Words that swap two zeros are outside the Profile domain and are not covered.
- **Checked by the author only.** The isolated re-runs above were made by the author. The reviewers have not re-run
  anything.
- **Exact minimum at the refuting multipliers of m = 11 {0,5}** is not known, only the interval [497, 511].
- **CPU.** About 3.5 CPU hours in total.
  - The m = 11 runs took about 2 h including table builds, and the m = 12..14 probes about 1 h.
  - The per-instance budget of about 20 minutes was exceeded at m = 11 {0,6}: 30 minutes, for the exact LP value
    after the certificate was already found.
- **Git.** Nothing was committed. `negcert/` is not under the ignored `checks/`.
