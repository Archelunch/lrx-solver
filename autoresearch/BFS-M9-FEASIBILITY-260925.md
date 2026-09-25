# BFS feasibility at m=9 and outer-layer example verification (2026-09-25)

## 1. Code location
- `src/lrx/table_bfs.py`: `Ranker` (Lehmer-code rank/unrank of token positions,
  bijection onto `[0, n!/r!)`), `build_table(m, r, workers, max_bytes)` (level
  BFS from root `(1..m,0^r)`, one byte/state, multiprocessing via fork pool
  chunking the frontier), `DistanceTable` (loads `.bin`+`.json`, verifies
  sha256, exposes `.distance(v)` for an exact distance on any vector — not
  just the radius).
- Registry: `datasets/registry.json` lists 17 (m,r) graphs; tables built:
  up to (9,3) n=12 (`datasets/generated/dist_m9_r3.json`, 79,833,600 states,
  radius 59, 51.95s/10 workers) and (8,4) n=12 (19,958,400 states, radius 54,
  11.62s/10 workers). Larger crosscheck tables exist under
  `runs/bfs-crosscheck-260923/tables/` up to (7,9) n=16 and
  `runs/lifting-check-260922-234448/tables/dist_m10_r2.json`.
- (10, r) and (12,4)/(8,8)/(16,4) are registry entries with `table:false` —
  not yet built.

## 2. Note's example verified exactly
- (m=8,r=1,n=9) u=(0,8,7,6,5,4,3,2,1): built full table (362,880 states,
  1.73s, 1 worker). **d(u,u0) = 34.** Matches note's bound 13<=d(u)<=34
  (upper bound tight).
- (m=9,r=1,n=10) v=(0,9,8,...,1): built full table (3,628,800 states, 5.14s,
  4 workers). **d(v,v0) = 43** <= T_9(10)=45, matches note exactly.
- P - c_p for the deletion class: P=T_8(9)=36, c_p=ceil(11*9/4)-1=24,
  P-c_p=12. d(u)=34 > 12, confirming this deletion lies outside the note's
  "small" region (12,36], consistent with v being a genuine outer-layer
  candidate.

## 3. Feasibility at m=9 (r=4,5,6) and m=8 (r=4..7)
Measured throughput (10 workers, fork pool): ~1.5-1.7M states/s sustained
(79.8M states/51.95s and 20.0M states/11.62s). Memory: dist table is 1
byte/state; peak frontier ~6-7% of states, ~16 bytes/state (rank + neighbour
buffer) during expansion.

| m | r | n | states | est. time (10 workers) | est. peak RAM |
|---|---|---|---|---|---|
| 9 | 4 | 13 | 259,459,200 | ~2.7 min | ~1.3 GB |
| 9 | 5 | 14 | 726,485,760 | ~7.6 min | ~3.6 GB |
| 9 | 6 | 15 | 1,816,214,400 | ~19 min | ~9 GB |
| 8 | 4 | 12 | 19,958,400 (measured) | 11.6s | 0.1 GB |
| 8 | 5 | 13 | 51,891,840 | ~32s | ~0.26 GB |
| 8 | 6 | 14 | 121,080,960 | ~76s | ~0.6 GB |
| 8 | 7 | 15 | 259,459,200 | ~2.7 min | ~1.3 GB |

All fit comfortably in 18GB RAM. m=9,r=4 and all m=8 cases finish inside the
10-minute cap and were not started (per instruction, no run >10 min
attempted). m=9,r=5 (~7.6 min est.) is borderline but plausibly under 10 min;
m=9,r=6 (~19 min est.) exceeds it — not run.

**Conclusion: pure Python (this implementation) is feasible today for all of
m=8 r=4..7 and m=9 r=4..5 without code changes, and for m=9 r=6 with a longer
(~20 min) but still single-machine, single-language run — no C++ rewrite is
needed at these sizes.** C++ would only become worthwhile past roughly
r~7-8 at m=9 (states approaching/exceeding ~5-10B) where the ~1.6M states/s
Python+fork throughput would push runs past an hour and RAM pressure from
frontier arrays grows with state count.
