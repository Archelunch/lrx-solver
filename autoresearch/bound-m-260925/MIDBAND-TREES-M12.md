# Middle band: tree certificates at m = 11, 12 with the exact oracle on refined leaves

Date 2026-09-26. Offline. There were no provider calls, no commits and no new dependencies. No LLM-generated code
was executed; the C oracle and the drivers below were written in this session and compiled with the system cc.
Lemma 1 (with refinement and picks), formula (6) and criterion (8) are the research group's (m=8 manuscript,
general-m audit in Session 27). The main conjecture stays open. Nothing under src/, tests/, integrations/ or
tools/ was changed.

## 1. Result per family

| family | verdict | tree |
|---|---|---|
| m = 11 {0,5} | **CERTIFIED** (tree, 4 leaves; evaluator CERTIFIED, audit agrees, replay ok) | below |
| m = 12 {0,5} | **not certified**: BOUNDARY, gap 0; 4 of 5 leaves certified, one leaf open at lhs exactly 1 | below |
| m = 12 {0,6} | **not certified**: BOUNDARY, gap 0; 3 of 4 leaves certified, one leaf open at lhs exactly 1 | below |

m = 11 {0,5} was root-refuted (Session 33). With this tree it is certified: d(v) <= T_11(n) for every state
(0^u0, 11..7, 0^u1, 6..1), u0, u1 >= 1, conditional on Lemma 1 with refinement and criterion (8) at m = 11.

For m = 12 the whole difficulty sits on the stripe u1 = 1, u0 large. Every other part of both families is
certified by the leaves below. The open leaf is exactly at the boundary (lhs 1) with the best words found.

## 2. The trees

Leaves are listed as box, origin, picks, T(l), lhs of criterion (8), and support (B, beta, weight). All picks are
(0,0), the first atom of each block. Splits: u0 <= 1 | u0 >= 2, then (for u0 >= 2) u1 <= 1 | u1 >= 2, then the
stripe u1 = 1 is cut along u0.

**m = 11 {0,5}**, T = 75, s = 9, depth 3.

| box (u0, u1) | origin | T(l) | lhs | support |
|---|---|---|---|---|
| {1} x [1,inf) | (1,1) | 75 | -11 | (64, (15,0)) x 1 |
| {2} x {1} | (2,1) | 84 | -7 | (77, (13,2)) x 1 |
| [3,inf) x {1} | (3,1) | 93 | **1/2** | (95, (8,13)) x 3/4, (89, (12,3)) x 1/4 |
| [2,inf) x [2,inf) | (2,1) | 93 | **2/3** | (91, (7,10)) x 2/3, (77, (13,2)) x 1/3 |

The word (89, (12,3)) at origin (3,1) came from a weighted oracle pass (omega 5/4, 40M expansions). It beats the
lift of the corresponding root word, (95, (12,3)), by 6 in B. Without it the stripe leaf sat at lhs 1.

**m = 12 {0,5}**, T = 88, s = 10, depth 4.

| box (u0, u1) | origin | T(l) | lhs | support |
|---|---|---|---|---|
| {1} x [1,inf) | (1,1) | 88 | -11 | (77, (16,1)) x 1 |
| {2} x {1} | (2,1) | 98 | -3 | (95, (12,3)) x 1 |
| {3} x {1} | (3,1) | 108 | -1 | (107, (12,3)) x 1 |
| **[4,inf) x {1}** | (3,1) | 118 | **1 (open)** | (107, (12,3)) x 5/12, (111, (8,15)) x 7/12 |
| [2,inf) x [2,inf) | (2,1) | 108 | -3 | (95, (12,3)) x 1/2, (105, (8,7)) x 1/2 |

**m = 12 {0,6}**, T = 88, s = 10, depth 3.

| box (u0, u1) | origin | T(l) | lhs | support |
|---|---|---|---|---|
| {1} x [1,inf) | (1,1) | 88 | -12 | (76, (18,0)) x 1 |
| {2} x {1} | (2,1) | 98 | -4 | (94, (16,2)) x 1 |
| **[3,inf) x {1}** | (3,1) | 108 | **1 (open)** | (109, (8,13)) x 7/10, (109, (14,3)) x 3/10 |
| [2,inf) x [2,inf) | (2,1) | 108 | -2 | (99, (10,7)) x 1 |

The words and weights are in `checks/midband-trees-m12.json` (raw outputs, per-leaf supports and points).

## 3. Exact leaf refutations

Each line is a real negative statement: no certificate exists at that leaf with that origin and those picks,
whatever words are used. The argument is weak duality of the leaf LP (in `negcert/tree/leaf_colgen.py`): for
0 <= lambda_j <= h_j - l_j (bounded axis) and lambda_j >= 0 (unbounded axis), every feasible mixture has
lhs + T(l) >= min_w [B + (l - o + lambda).beta] - lambda.s.

**Computed by the oracle (re-run by the check script with identical expansion counts).**

| family | leaf | origin, picks | statement | expansions |
|---|---|---|---|---|
| 11 {0,5} | [2,inf) x {1} | (2,1), (0,0) | every word has B + 2 beta_0 >= 103 = T(l)+1+2s | 52,824,541 |
| 11 {0,5} | [2,inf) x {1} | (2,1), (1,0) | every word has B + 2 beta_0 >= 103 | 52,487,139 |

This is why the m = 11 stripe needed origin (3,1). The same inequality also refutes origin (2,1) on every
sub-box [a,inf) x {1} with a <= 4, taking lambda_0 = 4 - a. It also refutes [2,b] x {1} for every b >= 4.

**Implied by the stored root certificates (no new computation).** `negcert-m12-05.json` (every unit word has
B + 3 beta_0 >= 119) and `negcert-m12-06.json` (B + 2 beta_0 >= 109) refute origin (1,1) on:
- {0,5}: every upper leaf [a,inf) x J with a <= 4 (lambda_0 = 4 - a), in particular the open leaf [4,inf) x {1};
  and every lower leaf [1,b] x J with b >= 4 (lambda_0 = 3);
- {0,6}: every upper leaf [a,inf) x J with a <= 3, in particular the open leaf [3,inf) x {1}; and every lower
  leaf [1,b] x J with b >= 3.

In both lists J must have lower end 1. For a larger lower end, the budget grows by s per unit while beta_1 can
stay small, and the root inequality no longer reaches the threshold.

So the open m = 12 leaves need origin (2,1) or (3,1). Origin (4,1) and deeper do not fit the 4-bit packing
(n = m + 4 > 16).

## 4. What remains open at m = 12, with the certified lower ends

Every exact search below stopped at the node-store cap (5 GB, hash table 2^27 entries). A capped run still proves
min F >= p for the bucket p where it stopped (fast/README.md).

| family, leaf | origin | multipliers W, needed K | proved | weighted passes (no word below K) |
|---|---|---|---|---|
| 12 {0,5}, [2,inf) x {1} | (2,1) | (1,2,0), 119 | min F >= 108 | 3/2 x 20M; 2/1, 4/1 x 40M, both picks |
| 12 {0,5}, [3,inf) x {1} | (3,1) | (1,1,0), 119 | min F >= 105 | 5/4, 2/1 x 40M; 6/5, 4/3, 3/2 x 40M for each pick 0,1,2; 5/4, 3/2 x 100M (5,5,2 table) |
| 12 {0,6}, {3} x {1} | (3,1) | (1,0,0), 109 | min B >= 92 | 3/2, 3/1 x 40M |
| 12 {0,6}, {3} x {1} | (2,1) | (1,1,0), 109 | min F >= 96 | 3/2 x 20M |

- **{0,5}.** The pool LP at the open leaf has a unique dual optimum, lambda_0 = 1. A certificate needs one
  word with B + beta_0 <= 118 at origin (3,1). The best found are exactly 119, all of them lifts.
- **{0,6}.** At the single point (0^3, 12..7, 0, 6..1) the shortest word found has length 109 = T + 1. No
  word of length <= 108 was found; the exact search proves only >= 92.
  - This is a search limit, not evidence against the conjecture. The point is certified as soon as any sorting
    word of length <= 108 exists.
  - The {0,6} stripe [3,inf) x {1} needs such a point word, plus a mixture with betabar_0 <= 10 on the tail.
- **Mechanism.** Lifting a leaf mixture by one zero on axis 0 adds betabar_0 = s to the cost and s to the
  budget. So the root boundary (V = T+1 at both m = 12 roots) propagates unchanged along the u0 stripe. Only
  words that use the extra zeros can move it: at m = 11 one such word appeared at depth (3,1), and none was
  found at m = 12.

## 5. Tools

All tools are in `negcert/tree/`.
- **`lrxtree.c`.** A copy of `fast/lrxfast.c` generalized to refined origins, with lrxfast.c unchanged.
  - The picked zero of block j gets symbol m+j. Every other zero, and a picked zero of weight 0, gets m+2. This
    is exactly the ZO code of `negcert_general.encode`.
  - The abstract roots are all arrangements of the zero symbols after the labels (`roots_of`).
  - Unweighted zeros are interchangeable: the step cost and the zero-zero test read only zero-ness and the
    picked symbols.
  - Supports n <= 16 and at most 4 zeros. Everything else (table verification, bounded A*, INCOMPLETE on
    resource exhaustion) is lrxfast.c.
- **`treeoracle.py`.** The driver. It re-prices every returned word with `negcert_general.price` (with picks)
  and asserts the reported F.
- **`crosscheck_tree.py`.** 220 small cases (m = 5, 6; origins (1,1), (2,1), (1,2), (2,2), (3,1); all picks
  variants; five weight vectors). Each case checks that the C minimum equals `raw_dijkstra` (uncompressed, no
  table), the Python table-guided A* and the `lrx_m.Profile` price of the word. The bounded search gives NONE
  at K = F and F at K = F+1. Result: **CROSSCHECK OK**, before and after the weight-0 merge
  (`runs/crosscheck-tree*.log`).
- **`leaf_colgen.py`.** Column generation for one leaf. The primal is `bound3_evaluator.leaf_lp`, and the dual
  is vertex enumeration with lambda capped by the box widths (16 on unbounded axes).
  - Pricing is at W = den (1, l - o + lambda) with K = ceil(den (T(l) + 1 + lambda.s)).
  - Validated on m = 9 {0,4}: u0 = 1 gives lhs -9, and origin (2,1) gives 4/5, the known exact optimum
    (Session 23).
- **Other scripts.** `lift_seeds.py` and `lift_refined.py` produce seeds (Lemma 1 lifts), `probe.py` makes
  single calls, and `assemble_trees.py` assembles the trees and scores them. `runs/` holds every log and leaf
  JSON, including the incomplete runs.

## 6. Verification (actual output)

```
$ python3 autoresearch/bound-m-260925/checks/midband_trees.py --refutations
m11-mask33-... (m=11, zeros in gaps [0, 5]): stored status CERTIFIED
  score_output: CERTIFIED, gap 0, 4 leaves, lhs ['-11', '-7', '1/2', '2/3']
  audit_claim: agree (ok)
  replay: 6 leaf words sort their refined bases
m12-mask33-... (m=12, zeros in gaps [0, 5]): stored status BOUNDARY
  score_output: BOUNDARY, gap 0, 5 leaves, lhs ['-11', '-3', '-1', '1', '-3']
  not certified: open leaves [[[4, 'inf'], [1, 1]]] (no audit; a miss proves nothing)
  replay: 7 leaf words sort their refined bases
m12-mask65-... (m=12, zeros in gaps [0, 6]): stored status BOUNDARY
  score_output: BOUNDARY, gap 0, 4 leaves, lhs ['-12', '-4', '1', '-2']
  not certified: open leaves [[[3, 'inf'], [1, 1]]] (no audit; a miss proves nothing)
  replay: 5 leaf words sort their refined bases
  expansions 52824541 (stored 52824541)
  refutation 11 {0,5} origin [2, 1] picks [0, 0] box [[2, 'inf'], [1, 1]]: oracle NONE at W=[1, 2, 0] K=103 -> VERIFIED
  expansions 52487139 (stored 52487139)
  refutation 11 {0,5} origin [2, 1] picks [1, 0] box [[2, 'inf'], [1, 1]]: oracle NONE at W=[1, 2, 0] K=103 -> VERIFIED
ALL OK
```

The data file `checks/midband-trees-m12.json` has sha256 `37bf1db6…7448f`. The check log is
`negcert/tree/runs/midband-trees-check.log`.

## 7. Limits

- **Authorship.** Every check was run by its author, this agent. No independent re-run has been made.
- **Refutation soundness.** The refutations rest on lrxtree's completeness over reduced words, which is the
  `negcert_general.py` argument with extra unweighted zeros. They also rest on the 220-case cross-check. The
  refined-origin case has no independent pure-Python check at m = 11 scale.
- **Host.** Timings were taken on a shared host. Every oracle ran alone at nice 19 with a 5 GB cap. Total oracle
  time was about 1.5 h.
- **One incident.** One run's leaf file was overwritten by a run that finished in the same second under the same
  name. That run was the m = 11 pick (0,0) refutation, and its verdict survives in `runs/m11g5-split-u1.log`. It
  was re-run, and the file names now include the box and refuse to overwrite.
