# B1: the r = 3 over-budget vectors of the lifting statement (finite)

Statement under test (manuscript §6 candidate): A_P(v) <= P + m - 2 with
P = E_{r-1}(n-1), where A_q(v) = min over zeros j of H_q(v\j, j) and H_q is the
shortest full sorting word whose zero-deleted projection has length <= q.
For r = 3 and m >= 6 the budget P + m - 2 equals T_m(n) (P = T_m(n-1) on every
graph below), so the statement is "every vector sorts within T by a lift of a
projection of length <= P".

## Summary

1. **(12,9,3) is now independently confirmed.** The forward search
   `autoresearch/lift_forward.py` (no DP code shared with `lifting_fast` or
   `tools/verify_lift_independent.py`) gives H_52 = 61, 61, 62 for the three
   deletions of v = (2,1,0,0,0,9,8,7,6,5,4,3), with witness words replayed by
   `CertificateValidator` (projection 52, visible root reached). So
   A_P(v) = 61 > 59 = T is a two-engine result. Same tool on (11,8,3):
   H_42 = 49, 49, 49 for v = (2,1,0,0,0,7,8,6,5,4,3).
2. **On every fully computed r = 3 graph with m >= 7 exactly one vector fails at
   q = P**, and its shape alternates:

   - F1_m = (2,1,0,0,0, m, m-1, ..., 3)  fails at m = 7 and m = 9;
   - F2_m = (2,1,0,0,0, m-1, m, m-2, ..., 3)  fails at m = 8.

3. **At m = 10 neither shape fails.** F1_10 has A_P = 71 = T (tight), F2_10 has
   A_P = 68. A targeted exhaustive check found no over-budget vector among the
   529 vectors of (13,10,3) that have a zero whose deletion lies at distance
   >= P - 2 in the smaller graph (12,10,2) (one of them needed a rerun with a
   larger state cap; see "m = 10" below). On m = 7, 8, 9 the same
   neighbourhood contains the unique failing vector, and the targeted tool
   reproduces the full-sweep list there exactly.
4. **The "overrun grows 1 -> 2" reading in `research/claims.md` is not
   supported.** Overruns at q = P are 4, 1, 2 for m = 7, 8, 9 on different
   shapes, and no F-shape overruns at m = 10. With one extra projection letter
   (q = P + 1) every vector of (10,7,3), (11,8,3), (12,9,3) has A = d.

## The family, q = P

Values from `forward-family-m{M}r3.json` (m = 4..9) and
`forward-m10r3-family.json` (m = 10) in `evidence/lifting-check-260922-234448/`;
d(v) from the exhaustive sweeps `sweep-m{M}r3.json` (unknown at m = 10).
"lift cost" = H_P(u, j) - P for the three deletions j = 2, 3, 4 (all three give
the same u because the zeros are adjacent).

| m | n | P | budget = P+m-2 | T | d(u), u = F1 minus a zero | F1: A_P | F1 lift cost | F1 A-budget | d(F1) | F2: A_P | F2 A-budget | d(F2) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 7 | 12 | 14 | 14 | 12 = P | 12 | 0,0,0 | -2 | 12 | 11 | -3 | 11 |
| 5 | 8 | 19 | 22 | 21 | 19 = P | 21 | 2,2,2 | -1 | 21 | 20 | -2 | 20 |
| 6 | 9 | 25 | 29 | 29 | 25 = P | 29 | 4,4,4 | 0 | 29 | 28 | -1 | 28 |
| 7 | 10 | 33 | 38 | 38 | 33 = P | **42** | 9,9,10 | **+4** | 38 | 37 | -1 | 37 |
| 8 | 11 | 42 | 48 | 48 | 42 = P | 48 | 6,6,6 | 0 | 48 | **49** | **+1** | 47 |
| 9 | 12 | 52 | 59 | 59 | 52 = P | **61** | 9,9,10 | **+2** | 59 | 58 | -1 | 58 |
| 10 | 13 | 63 | 71 | 71 | 63 = P | 71 | 8,8,8 | 0 | <= 71 | 68 | -3 | <= 68 |

Observed structure (finite, m = 4..10 as listed):

- u_m = (2,1,0,0, m, m-1, ..., 3) is an antipode of the r = 2 graph
  (m+2, m, 2): d(u_m) = P = E_2(m+2) on all seven graphs. At m = 10 this uses
  the (12,10,2) table built this session by the trusted `table_bfs.build_table`
  (radius 63 = T_10(12), complete, 239,500,800 states).
- F1_m is an antipode of the r = 3 graph for m = 5..9: d(F1_m) = T = E_3(m+3).
  F2_m sits one below: d(F2_m) = T - 1 for m = 5..9.
- Lift cost of the antipode u_m at slack 0: exactly m - 2 for even m = 6, 8, 10
  (tight), above m - 2 for odd m = 7, 9 (9 vs 5, 9 vs 7), below at m = 5.
- q = P + 1 repairs every failure: `q_budget = q_exact = P + 1` on (10,7,3),
  (11,8,3), (12,9,3) (`autoresearch/lift-thresholds.md`).

## m = 10: targeted check

`python autoresearch/lift_targeted.py 10 3 --k 2 --workers 6 --max-states 4000000
--table-cache runs/lifting-check-260922-234448/tables` ->
`targeted-m10r3-k2.json`: far layers of (12,10,2) have 2 + 10 + 37 vectors at
distance 63, 62, 61; all 637 pairs (u, j) COMPLETE; 3 pairs have
H_P(u, j) > 71, each checked over all deletions:

| v | A_P | status |
|---|---|---|
| (0,0,10,9,8,7,6,5,4,3,2,1,0) | 71 | within budget |
| (2,1,0,0,10,8,0,9,7,6,5,4,3) | 68 | within budget |
| (3,2,1,0,0,10,9,8,0,7,6,5,4) | 66 | within budget (rerun with cap 60M) |

The third vector's deletions j = 3, 4 (distance 57, slack 6) exceeded the 4M
cap in the batch run and were reported INCOMPLETE, not cleared. The rerun
`forward-m10r3-unresolved.json` (cap 60M) is COMPLETE: H_63 = 66, 66, 73 for
j = 3, 4, 8 (about 6M states each for j = 3, 4), witnesses replayed. So every
covered vector of (13,10,3) has A_P(v) <= 71. Scope: the 529 covered vectors
only; the other ~1.04e9 visible states of (13,10,3) are unchecked.

Session 03 widened this to k = 3 (deletions at distance >= P-3 = 60):
`python autoresearch/lift_targeted.py 10 3 --k 3 --workers 5 --max-states 4000000
--flag-max-states 60000000 --table-cache runs/lifting-check-260922-234448/tables`
-> `evidence/lifting-check-260923-0838/targeted-m10r3-k3.json` (1374 s, 1.5 GB).
Far layers of (12,10,2): 2 + 10 + 37 + 138 vectors at distance 63..60; all 2431
pairs COMPLETE; 1998 covered vectors of (13,10,3). Four vectors have a pair with
H_P > 71; each was checked over all deletions, all COMPLETE, all 12 witnesses
replayed:

| v | A_P | deletions (j: d_small, H_P) |
|---|---|---|
| (0,0,10,9,8,7,6,5,4,3,2,1,0) | 71 (tight) | 0: 62, 71; 1: 62, 72; 12: 63, 71 |
| (2,1,0,0,10,8,0,9,7,6,5,4,3) | 68 | 2: 58, 68; 3: 58, 68; 6: 62, 73 |
| (3,1,0,0,10,9,0,8,7,6,5,4,2) | 68 | 2: 58, 68; 3: 58, 68; 6: 60, 72 (new at k = 3) |
| (3,2,1,0,0,10,9,8,0,7,6,5,4) | 66 | 3: 57, 66; 4: 57, 66; 8: 62, 73 |

No covered vector is over budget, unresolved or incomplete. Scope: the 1998
covered vectors only; the rest of (13,10,3) is unchecked.

Validation of the targeted method (`targeted-m{7,8,9}r3-k2.json`): on each of
(10,7,3), (11,8,3), (12,9,3) it returns exactly the full sweep's over-budget
list (F1_7, F2_8, F1_9). `tests/test_search_lift_tools.py` checks it against
`lifting_fast.lift_values` with full coverage on (6,3,3), (7,4,3), (7,3,4).

## Proof targets for the human (open)

1. d(u_m) = T_m(m+2) = C(m+2,2) - 3 for all m >= 4, i.e. u_m is an antipode of
   the r = 2 graph (true for m = 4..10).
2. d(F1_m) = T_m(m+3) for all m >= 5 (true for m = 5..9).
3. The lift cost of geodesics of u_m (a function of m with visible parity
   dependence: 0, 2, 4, 9, 6, 9, 8 for m = 4..10). If it is <= m - 2 for every
   m >= 10 the F-family stops obstructing the q = P statement.
4. A_{P+1}(F1_m) <= P + m - 2 for all m: one extra projection letter repairs
   F1 on every computed graph.

## Relation to the manuscript's Theorem 2 (r = 2 family)

Theorem 2's v_{m,k} has deletions at distance 3k - 1, far below P, and needs
projection overrun 2k - 2 over d(u); its absolute projection 5k - 3 stays
below P when m >= 8k - 1, so it does not obstruct the capped statement at
q = P. The F-family is the opposite regime: its deletions are antipodes
(slack 0 at q = P) and its failures need projection P + 1 = d(u) + 1. Both
show that lifting only geodesic projections is not enough. Neither refutes
recursion (1) or the conjecture: d(F1_m) = T on every computed graph.

## Evidence (in `evidence/lifting-check-260922-234448/`)

- `forward-m8r3-counterexample.json`, `forward-m9r3-counterexample.json`:
  independent forward values and replayed witnesses at q = P, P+1, P+2.
- `forward-family-m{4..9}r3.json`, `forward-m10r3-family.json`: F1, F2 at q = P
  (m = 10 also q = 64, 65: A unchanged, 71 and 68).
- `sweep-m{4..9}r3.json`: exhaustive A_q over q = P-3 .. P+1 or P+2.
- `targeted-m{7,8,9,10}r3-k2.json`, `forward-m10r3-unresolved.json`.
- Session 03: `evidence/lifting-check-260923-0838/targeted-m10r3-k3.json`.
- The (12,10,2) distance table (240 MB) is not published; `table_bfs.build_table`
  rebuilds it.
