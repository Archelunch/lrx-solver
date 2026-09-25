# Reversal-orbit obstacle at m = 11 (bound-m-260925)

Date 2026-09-25. Read-only analysis: no provider calls, and no campaign directory was modified.
Every number below was recomputed with trusted code (`integrations/lrx_m.Profile`,
`lift_evaluator.mixture_lp` / `gap_lp`, `bound_evaluator.classify`, `lrx_m.leaf_criterion` /
`tree_leaves`) from the stored `output_words` in `finalists/holdout-arms/*.json`, the m=8 package
in `autoresearch/verify-m8-260924/package/`, and the exact tables `datasets/generated/dist_m{8,9}_r2`.
Lemma 1, criteria (7) and (8), and the reverse trees are the research group's (m=8 manuscript).
The main conjecture stays open. Nothing here was evaluated on the holdout beyond re-pricing words
that the holdout run had already stored.

Notation: T = T_11(11+k), s = 9, "gap" = `gap_lp` value, "min-base" = `mixture_lp` optimum
(min Bbar subject to slopes <= s + t, where t is the smallest feasible uniform slope excess).

## 1. The worst reversal-orbit misses at m = 11

The arms are EvoX, GEPA, control (b) sweep-LP, AdaEvolve and sequential.
"Union" means the LP over all distinct words from all six non-naive arms.

| family (labels, gaps) | class | T+1 | EvoX / GEPA / (b) gap-LP point | best single arm | union min-base | binding constraint |
|---|---|---|---|---|---|---|
| 11..1, {0,11} (mask 2049) | rev_rot | 76 | Bbar 77, slopes (12,11), gap 4 in all three; min-base 80 (EvoX, GEPA) and 84 (b) at slopes (9,8) | sequential: one word, B 78, slopes (9,8), gap 2 | 78 at (9,8), t = 0 | **base**. Slopes are feasible, and no word of length <= 75 exists in the union (the shortest has 76). |
| 5.4.3.2.1.11..6, {5,10} (1056) | refl | 76 | EvoX/GEPA 13/5: Bbar 76, slopes (58/5, 11/2); (b) 4 | sequential 1: Bbar 76, slopes (10, 9) | 683/8 at 75/8, t = 3/8 | **slope on gap 5**. Slopes <= 9 are infeasible, although the shortest word has length 66. |
| 4.3.2.1.11..5, {0,4,7} (145) | refl | 85 | EvoX 9/5, GEPA 25/23, (b) 7 | sequential 1: slopes (10,10,10) | 619/6 at 55/6, t = 1/6 | **slopes on all three gaps** |
| 4.3.2.1.11..5, {3,4,7,8,11} (2456) | rev_rot | 103 | EvoX 7/12, GEPA 19/28, (b) 5/2 | EvoX/AdaEvolve 7/12: slopes 115/12 on gaps 4 and 11 | 108 at 109/12, t = 1/12 | **slopes on gaps 3, 4, 8, 11** |
| 6.5.4.3.2.1.11..7, {0,2,5,6,9,10,11} (3685) | refl | 121 | EvoX 53/84, GEPA 10/11, (b) 362/209 | AdaEvolve 31/61 | 251/2 at 37/4, t = 1/4 | **slopes on gaps 0, 2, 6, 10, 11** |

Gap 4 for 11..1 {0,11} is confirmed from the stored words in EvoX, GEPA, (b) and AdaEvolve.
The gap-LP optimum is Bbar = 77 = T+2 with slopes (12, 11), so 1 + 3 = 4. Holding the slopes
at <= 9 costs a base of 80 instead, which is also excess 4.

**Pooling words across arms certifies 15 of the 30 families** that EvoX, GEPA and (b) all miss.
This was checked with `bound_evaluator.classify` on the union, and the largest support has 5 words.
The 15 that remain, by what binds:

| binding constraint (union words) | count | families |
|---|---|---|
| base binds, no word <= T at the unit corner | 1 | 11..1 {0,11} |
| slopes <= s infeasible (t > 0) | 6 | masks 1056, 134, 145, 2456, 1849, 3685 |
| slopes feasible, base binds, a word <= T exists | 8 | masks 644, 1076, 330, 3443, 4082, 2043, 4079, 4095 |

## 2. How the group certified reversal-orbit families at m = 8

The reverse file `multiset_reverse_m8_complete_certificates_20260923.json` holds 4088 families,
all 8 cyclic rotations of 8..1 times all 511 masks. It stores every family as a tree.

- **4054 of 4088 are a single root leaf.** That is a single mixture on unit-origin words,
  which is criterion (7).
- **34 need genuine splits.** They use 173 leaves, 139 splits and depth at most 7. All 173 leaves
  pass `leaf_criterion(m=8)`. 139 leaves have a finite box. 13 leaves in 12 families use
  refined-origin words, with origin coordinates 2 or 3.
- The 34 use only three rotations: 15 of 18765432, 11 of 87654321 and 8 of 21876543.
- Their masks, per rotation:
  - 87654321: {0,4}, {0,1,5}, {0,1,4,5}, {0,1,4,7} (10 leaves, depth 7) and 7 more;
  - 21876543: {2,6}, {0,2,4} and 6 more;
  - 18765432: 15 masks, all containing gap 0 or 1.

The m=8 analogues of our misses:

- **8..1 {0,8}, the analogue of 2049, is a single mixture.** Two words, B = 43 with slopes (5,4)
  and B = 41 with slopes (7,6), are weighted 1/2 each. That gives Bbar 42 < 43 and slopes (6,5).
- **5.4.3.2.1.8.7.6** with {5,7}, {0,4,6} or {3,4,6,7,8} is also a single mixture.
- **8..1 {0,4} needed a tree.** It is the m=8 analogue of the tight m=9 family (9..1){0,4}.
  - It splits on u_0 at cuts 1 and 2.
  - For u_0 <= 2, one word with B 34 and slopes (12, 0) is used on a finite box.
  - For u_0 >= 3, two refined-origin words at origin (3,1) have Bbar 54 and slopes (6, 16/3).

In the union (`checker/results/union.json`, k = 4..9), direct trees closed only 21 families, and
38831 families were closed by transfer from reverse trees. Trees were needed at scale only at low k:
37323 two-block and 639357 three-block exceptions (theorem section 7).

## 3. Extending the bound task to tree certificates

**Output schema (proposed, `bound-contract-3`).**

```json
{"tree": NODE, "note": "..."}
NODE = {"kind": "split", "axis": j, "cut": t, "left": NODE, "right": NODE}
     | {"kind": "leaf", "rows": [{"word": "LRX...", "origin": [o_0..o_{k-1}],
                                   "picks": [p_0..p_{k-1}]?, "weight": "p/q"?}]}
```

The split sends u_j <= t left and u_j >= t+1 right. Proposed limits:

- depth <= 8, leaves <= 64, rows <= 32 per leaf and <= 256 in total;
- 1 <= o_j <= 8, and o_j <= l_j of the leaf;
- word length <= 4000;
- `{"words": [...]}` stays valid and means a single root leaf with unit origins.

**Evaluator changes.** These are trusted-side, so they need a new `bound-eval-3`, new cache keys
and human review.

1. `parse_output` validates the tree shape and the limits before any Fraction is built.
2. Walk the tree with `lrx_m.tree_leaves(tree, [(1, None)] * k)`. It raises when a threshold lies
   outside its box, and it guarantees complete coverage.
3. Price each row on the refined base.
   - Build the base with `lrx_m.refine(unit_base, origin)` and price it with
     `Profile(refined, word, picks)`. Picks default to the first zero of each block.
   - Run `literal_lift_check` at the z points, and reject zero-zero swaps as before.
   - The row cost is C_i(u) = B_i + beta_i . (u - o_i).
4. Solve an exact LP per leaf that minimises the criterion (8) left-hand side.
   - The variables are w, e_j >= g_j - s on the bounded axes, and g_j <= s on the unbounded axes.
   - Check the result with `leaf_criterion(rows, box, m=m)`. Its `m` argument already exists.
   - Candidate weights are only checked, as now.
5. Assign the status.
   - CERTIFIED means every leaf has excess < 1 with feasible unbounded slopes.
   - BOUNDARY means the maximum excess over leaves is exactly 1.
   - Family gap = max over leaves of the leaf gap: min over w of
     max(0, C(l) + penalties - (T(l) + 1)) + max(0, max over unbounded j of g_j - s).
   - The bound statement is per leaf.
6. `bound_audit.py` re-checks each leaf with lrxm8 `leaf_criterion` / `tree_leaves` at M = m.

**Would lifted m=8 reverse trees close our misses? Estimate: mostly no.** This is reasoned from
structure. I ran a small exact check but no search.

- **11..1 {0,11} cannot be closed by any tree over existing words.** Every tree has a leaf whose
  box starts at the unit corner, and that leaf needs a word of length <= T = 75 for the unit base.
  The shortest in the union is 76. At m=8 the analogue did not need a tree at all.
- **The six slope-infeasible families need refined-origin words.** The all-right leaf is unbounded
  on every axis, so it needs slopes <= 9 everywhere, and that is infeasible over the unit words.
  These are new words for bases with 2-3 zeros in a block, the part that closed (8..1){0,4} at m=8.
  No such words exist in our data.
- **Base-binding families with short words:** a depth-2 tree over the union unit words fails on
  masks 644, 1076 and 330. The other five have k >= 8 and were not tried.

Trees are therefore necessary for about 7 of the 15 and are not sufficient without refined-origin
words. They do not help 2049 at all.

## 4. Single-mixture route: merge the two outer zero blocks

Label 11 crosses the zero block in one direction, and labels 1 and 2 cross it in the other.
After a fixed prefix the two outer zeros are adjacent. The inner reversal is then sorted on the
line of label cells without touching the zeros, and a fixed suffix inserts 2 across the block:

    W_m = XRXRXLXLX . L . M_m . XLXLXLX

M_m is the BFS-shortest line word that sorts m-1..3 to 3..m-1 with 1, 2 and m fixed, starting on
cell 0 and ending on cell m-2. For every m, A = (3,3) and slopes = (7,6).

| m | T+1 | s | W_m length = B | slopes | status | best arm so far |
|---|---|---|---|---|---|---|
| 8 | 43 | 6 | 41 | (7,6) | NO (slope 7 > 6); this is the group's second word | group mixture certifies |
| 9 | 53 | 7 | **51** | (7,6) | **CERTIFIED** | BOUNDARY (53) in every dev arm |
| 10 | 64 | 8 | 64 | (7,6) | BOUNDARY | gap 1 |
| 11 | 76 | 9 | 78 | (7,6) | NO, gap 2 | gap 4 (EvoX, GEPA, (b)), gap 2 (sequential, same B) |

The m=9 word is

    XRXRXLXLXLLLLXLXRXRXLXLXLXRXRXRXRXLXLXLXLXLLXLXLXLX

It passes Profile, the literal lift and `classify`, which returns CERTIFIED. Its length equals the
exact d(unit) = 51 from the (9,2) table. An exhaustive enumeration of all 1080 words of length
<= 52 (the table admits no others) gives only four (B, slopes) pairs: 51 with (7,6), 51 with (9,8),
52 with (8,7) and 52 with (10,9). All four have A = (3,3).

The variant that sorts 2 on the line as well is the group's other m=8 word, B = 43 with (5,4).
It grows faster: 55, 70 and 86 at m = 9, 10, 11.

**Conclusion.** The merged-block route closes the m=9 dev family, but not m=11. The slopes stay
at (7,6), while the base excess B - T is -1, +1 and +3 at m = 9, 10, 11. The line-sort middle grows
by about 2m per step, and T grows by m+1.

Spending the slope slack does not help. Allowing up to 2 extra passes over the zero block in the
middle gives the same 78 at m = 11 and 64 at m = 10.

A certificate at m = 11 needs a word of length <= 75 that sweeps the ring. Such a word passes the
block about m/2 times, which is the main cost. Whether d(unit) <= 75 at m = 11 is unknown, because
no (11,2) table exists.

## Addendum (orchestrator, 2026-09-25)

An exact (11,2) table would settle whether any word of length <= 75 sorts
the m=11 reversal with two outer zeros (unit base n=13, T=75). The build
estimate is 15.6 GB (3.1e9 states plus frontier), above this machine's safe
limit while campaigns run; deferred. Until then the base-bound gap 4 for that
family is a construction limit, not a proved obstruction.
