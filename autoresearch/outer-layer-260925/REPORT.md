# Outer-layer class C(9,r) at m=9, r=1..5: exact enumeration (2026-09-25)

Source of the definitions: `downloads/recent/lrx_multiset_linear_outer_layer.pdf`
(note "Удаление метки: общая оценка расстояния и линейный внешний слой", 25 Sep 2026).
Theorem 1, Theorem 2 and necessary condition (6) are **the note's results**; nothing
here proves or refutes them. This report computes the class those results leave open,
at m=9, by complete exact BFS tables. The main conjecture stays open; finite
computations here cover m=9, r<=5 only.

Definitions used (note §2-3): n=9+r, p=n-1, P=T_8(n-1)=C(8,2)+2+6r=30+6r,
c_p=ceil(11p/4)-1, T_9(n)=P+p. delta_q v deletes label q and renumbers labels >q
downward; d_q(v)=d(delta_q v, u0) in the (8,r) graph. "Proved by Theorem 2" means
min_q d_q(v) <= P-c_p. Class C(9,r) = {v : P-c_p < d_q(v) <= P for all q=1..9}.
All distances are to the canonical root (sorting radius), never graph diameter.

## 1. Tables

Built with `src/lrx/table_bfs.build_table` unmodified (10 workers, `nice -n 5`,
fork pool) by `build_tables.py` in this directory; log in `build_log.jsonl`.
New tables live in `datasets/generated/outer-layer-260925/` (git-ignored, the
directory `DistanceTable` takes as argument); `registry.json` and
`tables.lock.json` were **not** edited. Every table is complete (reached = states),
and every radius equals T_m(n). The rebuilt (8,4) table has the same sha256 as the
locked copy. (9,5) took 611 s, slightly above the 7.6 min estimate in
`BFS-M9-FEASIBILITY-260925.md`, with other agents loading the machine.

| m | r | n | states | radius | T_m(n) | BFS s | table sha256 | location |
|---|---|---|---|---|---|---|---|---|
| 8 | 1 | 9 | 362,880 | 36 | 36 | 1.172 | `d99e27fe352ad2d3991b66076fb4512b520c20f38bcd44c0729d4d45a9aea0d1` | built here (outer-layer-260925/) |
| 8 | 2 | 10 | 1,814,400 | 42 | 42 | 1.764 | `0be75f620d07b4cf6138385d89345c61d6d16c0b0fa02441e77b3a2222c1002a` | existing, locked (datasets/generated/) |
| 8 | 3 | 11 | 6,652,800 | 48 | 48 | 4.479 | `6a48de40674df45663b9d5d79e5ff3c76b7f0ee01ffa7a8bd1376ffb9a2db502` | existing, locked (datasets/generated/) |
| 8 | 4 | 12 | 19,958,400 | 54 | 54 | 12.358 | `6e1ce2a2d7a9d21b5aa4f5ca4868d7b1efd77f9dbb4402036489894dfd6cb431` | built here (outer-layer-260925/); identical to locked datasets/generated copy |
| 8 | 5 | 13 | 51,891,840 | 60 | 60 | 32.24 | `bc7b8ea9f91f57c9596ebedfb62e6ee852736dfa521e4b50f0cdae7cdbe5d1b5` | built here (outer-layer-260925/) |
| 8 | 6 | 14 | 121,080,960 | 66 | 66 | 79.556 | `a54a2f14a36910833f58f2c04c9b91c32b574b42883e9bd2e31006fcdd0a5682` | built here (outer-layer-260925/) |
| 9 | 1 | 10 | 3,628,800 | 45 | 45 | 3.365 | `47667d74c3a7d271cdd81d5e67b82589905e6283918669d2fe5cf4fd331921f9` | built here (outer-layer-260925/) |
| 9 | 2 | 11 | 19,958,400 | 52 | 52 | 12.564 | `8148ceab1f053d8e7431d4db188717ba30773cd9b6ea3e697eee57d9e337befd` | existing, locked (datasets/generated/) |
| 9 | 3 | 12 | 79,833,600 | 59 | 59 | 51.954 | `1f3a24f5d85fb295adfb9020416eaa43f5488115067f63da3286c631932daf1d` | existing, locked (datasets/generated/) |
| 9 | 4 | 13 | 259,459,200 | 66 | 66 | 298.319 | `fc31a30e284298887425b73d9ebe714e1111f6001a8a5ce6672811bd12de8789` | built here (outer-layer-260925/) |
| 9 | 5 | 14 | 726,485,760 | 73 | 73 | 610.907 | `f3465b5f24c9e997b72529c8341346bc310a205b35beefa6fda3de6d1d8a58cb` | built here (outer-layer-260925/) |

## 2. Class sizes (complete enumeration of every rank, all five r)

`enumerate_class.py r` streams all n!/r! ranks in 2^21 blocks over 10 processes,
computes the nine deletion distances from the (8,r) table and d(v,v0) from the (9,r)
table. r=5 (726,485,760 states) finished in 207 s, so **no sampling was needed**.
Outputs: `class_m9_r{r}_full.json` (histograms of min_q d_q, max_q d_q, joint
(min_q d_q, d) histogram, d-histograms of the class and of the proved set, extremal
states) and class bitmaps `datasets/generated/outer-layer-260925/class_bitmap_m9_r{r}.bin`
(np.packbits over ranks, sha256 in the JSON).

| r | P | c_p | P-c_p | T_9(n) | states | proved by Thm 2 | class C(9,r) | class % | max d over class | # attaining | max d over proved | max_q d_q > P | max(d - min_q d_q) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 36 | 24 | 12 | 45 | 3,628,800 | 227,058 | 3,401,742 | 93.74 | 45 | 1 | 25 | 0 | 14 |
| 2 | 42 | 27 | 15 | 52 | 19,958,400 | 950,976 | 19,007,424 | 95.24 | 52 | 2 | 29 | 0 | 15 |
| 3 | 48 | 30 | 18 | 59 | 79,833,600 | 3,416,268 | 76,417,332 | 95.72 | 59 | 5 | 34 | 0 | 17 |
| 4 | 54 | 32 | 22 | 66 | 259,459,200 | 14,362,698 | 245,096,502 | 94.46 | 66 | 1 | 39 | 0 | 18 |
| 5 | 60 | 35 | 25 | 73 | 726,485,760 | 40,184,798 | 686,300,962 | 94.47 | 73 | 6 | 44 | 0 | 20 |

Reading the table:
- The (8,r) radius equals P for every r=1..5, so max_q d_q(v) <= P holds for every v.
  Therefore C(9,r) is exactly the complement of the set proved by Theorem 2.
- The class is 93.7-95.7% of the graph. Theorem 2 alone certifies 5.3-6.3% of states.
- Every Theorem-2-proved state is far from the budget: its maximum d(v,v0) is
  25/29/34/39/44, against T_9(n) = 45/52/59/66/73.
- Every class member satisfies d(v,v0) <= T_9(n). This is automatic, because the (9,r)
  radius equals T_9(n); the class maximum is the radius itself.
- Last column: the exact best additive pointwise constant K with
  d(v,v0) <= min_q d_q(v) + K for all v. K = 14,15,17,18,20 exceeds n-1 = 9..13,
  consistent with the note's remark that the pointwise "+(n-1)" bound is false.
  K is attained only at small min_q d_q (0..9), near the root.

Slack T_9(n) - d(v,v0) over the class; full histograms are in the JSON:

| r | slack 0 | slack 1 | slack 2 | slack 3 | min slack over class |
|---|---|---|---|---|---|
| 1 | 1 | 3 | 6 | 21 | 0 |
| 2 | 2 | 7 | 44 | 170 | 0 |
| 3 | 5 | 51 | 245 | 875 | 0 |
| 4 | 1 | 34 | 324 | 1,724 | 0 |
| 5 | 6 | 95 | 804 | 4,113 | 0 |


## 3. Extremal class states (all states with d(v,v0) = T_9(n))

```
r=1, d(v,v0)=45:
    v=(2, 1, 0, 9, 8, 7, 6, 5, 4, 3)  d_q=[35, 35, 36, 36, 36, 36, 36, 36, 36]
r=2, d(v,v0)=52:
    v=(2, 1, 0, 0, 9, 8, 7, 6, 5, 4, 3)  d_q=[41, 41, 42, 42, 42, 42, 42, 42, 42]
    v=(0, 0, 9, 8, 7, 6, 5, 4, 3, 2, 1)  d_q=[42, 42, 42, 42, 42, 42, 42, 42, 42]
r=3, d(v,v0)=59:
    v=(2, 1, 0, 0, 0, 9, 8, 7, 6, 5, 4, 3)  d_q=[47, 47, 48, 48, 48, 48, 48, 48, 48]
    v=(4, 1, 3, 2, 0, 0, 0, 9, 8, 7, 6, 5)  d_q=[47, 46, 46, 47, 46, 46, 46, 46, 46]
    v=(2, 3, 1, 0, 0, 0, 9, 8, 7, 6, 5, 4)  d_q=[47, 48, 48, 46, 46, 46, 46, 46, 46]
    v=(3, 2, 1, 0, 0, 0, 8, 9, 7, 6, 5, 4)  d_q=[47, 47, 47, 48, 48, 48, 48, 47, 47]
    v=(0, 0, 0, 9, 8, 7, 6, 5, 4, 3, 2, 1)  d_q=[48, 48, 48, 48, 48, 48, 48, 48, 48]
r=4, d(v,v0)=66:
    v=(2, 1, 0, 0, 0, 7, 0, 9, 8, 6, 5, 4, 3)  d_q=[52, 52, 53, 53, 53, 53, 52, 52, 52]
r=5, d(v,v0)=73:
    v=(2, 1, 0, 0, 0, 0, 9, 8, 7, 6, 0, 5, 4, 3)  d_q=[58, 58, 59, 59, 59, 60, 60, 60, 60]
    v=(2, 0, 1, 0, 0, 0, 9, 8, 7, 0, 6, 5, 4, 3)  d_q=[60, 59, 60, 60, 60, 60, 57, 57, 57]
    v=(4, 3, 2, 1, 0, 0, 0, 0, 9, 8, 7, 6, 0, 5)  d_q=[60, 60, 60, 60, 59, 58, 58, 58, 58]
    v=(0, 5, 4, 3, 2, 1, 0, 0, 0, 0, 9, 8, 7, 6)  d_q=[58, 58, 58, 58, 58, 58, 58, 58, 58]
    v=(7, 6, 0, 5, 4, 3, 2, 1, 0, 0, 0, 0, 9, 8)  d_q=[59, 59, 59, 59, 59, 57, 57, 58, 58]
    v=(0, 0, 0, 0, 9, 8, 7, 6, 0, 5, 4, 3, 2, 1)  d_q=[59, 59, 59, 59, 59, 59, 59, 59, 59]
```

Structure (observed on these 15 states, not proved):
- 10 of 15 have the cyclic label order exactly reversed (9,8,...,1 read cyclically),
  with the zeros in one block or split into two blocks.
- The reflection image of the root, (2,1,0^r,9,8,...,3), is extremal for r=1,2,3.
  It has d = 65 at r=4, one below T.
- The full reversal (0^r,9,...,1) is extremal for r=2,3. It has d = 43 at r=1 and
  d = 65 at r=4.
- All extremal states have every deletion in the top 3-4 layers of the (8,r) graph,
  with min_q d_q >= P-3. The joint histogram shows no state at d=T with small min_q d_q.

Symmetry test (`check_class.py`): I tested 4n candidate maps
v -> L^k(kappa^c(psi^f(v))). Here L^k is rotation, psi is the position reflection
i -> 1-i mod n, which conjugates L<->R and fixes X, and kappa is the complement
relabeling i -> 10-i. The test covered all states at r=1,2 and random samples at
r=3, r=4 and r=5 (5M, 3M and 3M states, seed 260925).
**Only the identity preserves d(v,v0) on every tested state, and only the identity
maps the class onto itself.** Non-identity rotations preserve d on at most 57% of
states. The high class-to-class fractions (98-99%) come from the class being 95% of
the graph, not from a symmetry. This is expected: kappa∘psi is a graph automorphism,
but it sends the root to L^7 v0, so it does not fix the root.

## 4. Independent cross-checks

- **Deletion identity.** The vectorized deletion rank uses the identity
  c'_i = c_i - [p_i > p_q] for i<q and c'_i = c_i for i>q. At each r, 3000 random
  states are checked against pure-Python `Ranker` plus `DistanceTable.distance` on
  explicit deleted vectors. There were 0 mismatches.
- **Class members.** For each r, 1000 random class members are drawn from the bitmap
  (seed 260925). Their nine d_q are recomputed from sha256-verified reloads through the
  pure-Python path. All lie in (P-c_p, P], with 0 violations.
- **Dictionary BFS.** For r=1, a separate dictionary BFS with `state.apply_L/R/X`
  reproduces every entry of the (8,1) and (9,1) tables. The state counts are 362,880
  and 3,628,800, with 0 mismatches.
- **Word replay.** Every extremal state has a shortest sorting word, found by descent
  in the (9,r) table. `certificates.replay_visible` replays each word literally to v0,
  with word length equal to d. The 15/15 words are in `check_m9_r{r}.json`.

## 5. The note's example

v = (0,9,8,...,1) at r=1: all nine deletions give u = (0,8,...,1), with exact
d(u,u0) = 34. The note's interval was 13 <= d(u) <= 34, so its upper bound is exact.
34 lies in (12,36], so v is in C(9,1).
d(v,v0) = 43 exactly, with slack 2 against T_9(10) = 45. A shortest word, replayed to
the root:
`LLLXLXRXRXLXLXLXRXRXRXRRXRXRXRXLXLXLXRXRXLX` (43 letters).
It is not the extremum of C(9,1). The unique state at 45 is (2,1,0,9,8,...,3).

## 6. Limitations

- These are finite exact results for m=9, r=1..5 only. The m=9 conjecture for r>=6
  and the general case remain open. The radius equalities E_r(n) = T_9(n) for r<=5
  are finite computations, not a proof for all r.
- Because the (9,r) radius equals T here, a counterexample at m=9, r<=5 is excluded
  directly. The class computation shows condition (6) is not restrictive at m=9:
  about 95% of states satisfy it. It gives no information about how to route those
  states.
- The symmetry tests at r=3..5 are sampled, so "closed only under the identity" is
  exact for r=1,2 only. At r>=3 no nontrivial map passed on the sample, which is
  sufficient to refute closure but not a census.
- The structural patterns in §3 are observations on 15 states, not theorems.
- No commits, no provider calls, and `src/lrx` is unmodified.

## Reproduce

    python autoresearch/outer-layer-260925/build_tables.py 8,1 9,1 8,4 8,5 8,6 9,4 9,5   # refuses to overwrite
    python autoresearch/outer-layer-260925/enumerate_class.py R          # R=1..5
    python autoresearch/outer-layer-260925/check_class.py 1 --dict-bfs
    python autoresearch/outer-layer-260925/check_class.py 2
    python autoresearch/outer-layer-260925/check_class.py R --symmetry-sample 3000000   # R=3..5 (r=3 used 5000000)
