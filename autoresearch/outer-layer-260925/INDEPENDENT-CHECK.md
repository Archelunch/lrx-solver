# Independent re-check of outer-layer-260925 REPORT.md (m=9, r=1..5)

All checks below use fresh, self-written code (`DistanceTable`/`Ranker` from
`src/lrx/table_bfs.py` only, plus numpy); `enumerate_class.py`, `check_class.py`,
`build_tables.py` were never imported or executed. No commits, no provider calls.

| # | Check | Result |
|---|---|---|
| 1a | 11 tables: sha256 (via `DistanceTable`'s own verify), states=n!/r!, radius=T_m(n), root d=0 | **PASS**, all 11 |
| 1b | Fully independent dict-BFS (own L/R/X, no Ranker) for (8,1),(9,1),(8,2): state count + every distance | **PASS**, 0/362,880+3,628,800+1,814,400 mismatches |
| 1c | Triangle check d(nbr)∈{d-1,d,d+1}, 5000×3 random, for (8,3),(8,4),(8,5),(8,6),(9,2),(9,3),(9,4),(9,5) | **PASS**, 0 violations on all 8 tables |
| 2a | Full re-enumeration C(9,1) (3,628,800 states) and C(9,2) (19,958,400) | **PASS**, exact match: class 3,401,742/19,007,424, Thm2-proved 227,058/950,976 |
| 2b | r=3,4,5: 2,000,000-sample class fraction vs report; no d_q>P | **PASS**: 95.72%/94.46%/94.47% vs report 95.72/94.46/94.47; 0 deletions >P in any sample |
| 3 | K = max(d − min_q d_q): exact for r=1,2; sampled max for r=3,4,5 | r=1: **14** (exact match). r=2: **15** (exact match). r=3: sample max 17 = report's exact 17. r=4: sample max 17 ≤ report's exact 18 (consistent, no violation). r=5: sample max 19 ≤ report's exact 20 (consistent, no violation). |
| 4 | Extremal states d=T_9(n): re-scan tables, list, replay word with own executor | **PASS**: counts 1,2,5,1,6 match; all 15 vectors match report's listing exactly (same order); all 15 replayed words return to root with length=d |
| 5 | Note's example v=(0,9,...,1), r=1 | **PASS**: d(v,v0)=43, all 9 deletions give u=(0,8,...,1), d(u)=34 — reproduced independently, including the deletion/renumbering convention |

## Notes

- Deletion convention verified: remove the entry with value q, renumber values >q
  down by 1, keep zeros; equivalently, shift positions >p_q down by 1 in the
  (m-1,r) rank space. My independent vectorized formula for this and for rank()
  (cross-checked against `Ranker.rank` on 2000 random states) matches
  `DistanceTable.distance` on explicit vector deletion for every case tested,
  including the note's worked example.
- c_p = ceil(11p/4) − 1 with p=n−1 recomputed independently reproduces the
  report's P−c_p thresholds (12,15,18,22,25) exactly.
- No discrepancies found anywhere. r=4/r=5 K are the only items not verified to
  the exact value (report used full enumeration for K there too, we only sampled
  2M as scoped); nothing in the sample contradicts the report's claimed exact
  maxima.

## (9,6) and (10,3): sort-m9-260925 tables

Fresh code again (`DistanceTable`/`Ranker` + numpy only, no scripts from that
directory), tables from `datasets/generated/sort-m9-260925/`. No commits.

| # | Check | Result |
|---|---|---|
| 1 | sha256 (own hashlib over loaded bytes) | (9,6): `4f8cc2c236511a5f0fe3f7462c8a32180050132edca41ec567d4c892ddcee6dd` — matches. (10,3): `6deed7ea4ad9ea199a12877fe8c50485207f39d35814b9ff591d2a4fa505285f` — matches |
| 2 | layer_sizes sum = n!/r! | (9,6): 1,816,214,400 = 1,816,214,400. (10,3): 1,037,836,800 = 1,037,836,800. Both **PASS** |
| 3 | max distance, T_m(n), # at max | (9,6): max=**79**, T_9(15)=80 (strict gap confirmed), **26** states at 79, 0 bytes equal to 80 anywhere in the table (explicit scan). (10,3): max=**71**=T_10(13), **4** states at max. Both **PASS**, match claims |
| 4 | states at 79 for (9,6), listed | 26 states enumerated by table scan (list in this run's transcript); count matches |
| 5 | triangle consistency, 20,000×3 random | 0 violations on both tables |
| 6 | replay 3 states at max, own L/R/X executor | All 6 (3 per table) replay to root with word length = d. **PASS** |
| 7 | (9,6) partial independent recompute: reversal (0^6,9,...,1) and reflection (2,1,0^6,9,...,3) | Both give d=73 (< 79, not extremal), both replay to root correctly with own executor, word length 73 each |

No discrepancies. Both new claims (strict gap radius=79<T=80 at (9,6), and radius=71=T with 4 extremal states at (10,3)) independently confirmed.
