# Campaign report: uniform sorting program for m=9 (sort-m9-260925, v2)

Date 2026-09-25. Model gemini-3.8-flash, 8192 output tokens, $38.40 cap,
230 contacts, per-arm ledgers and prompt guards. Approved hash 7626d6b0.
v1 (2 s per state) was stopped after 7 iterations because candidates won by
per-state search; v2 enforces 0.2 s CPU per state so search times out
(plain BFS scores negative), and adds a worst-r uniformity term.

Task: candidate `sort_word(v)` for m=9 states; exact scoring against the
complete BFS tables; development 1500 states (r=1..5, top layers oversampled,
all radius states), holdout 2100 disjoint states including (9,6) and (10,3),
evaluated once after finalist freeze. Seed: cyclic-sweep control.

## Results (finalists/REPORT.md, independent audit 0 disagreements)

| Program | Dev within /1500 | Dev worst-r | Holdout within /2100 | Holdout worst-r | (9,6) /300 | (10,3) /300 | USD |
|---|---:|---:|---:|---:|---:|---:|---:|
| naive seed | 128 | 0.07 | 157 | 0.05 | 15 | 24 | 0 |
| cyclic sweep (control, seed) | 1356 | 0.83 | 1846 | 0.78 | 235 | 235 | 0 |
| sequential control | 1484 | 0.97 | 1918 | 0.45 | 136 | 294 | 1.21 |
| EvoX | 1470 | 0.95 | 2053 | 0.94 | 283 | 288 | 0.83 |
| AdaEvolve | 1480 | 0.96 | 2059 | 0.94 | 282 | 290 | 1.08 |
| GEPA | 1494 | 0.98 | 2080 | 0.97 | 290 | 295 | 1.46 |

Every valid within-budget word is an exact certificate d(v) <= T for that
state. Calls: GEPA 60 (0 truncated, 60 valid), sequential 60 (53 invalid,
mostly parse), AdaEvolve 55, EvoX 43. Total $4.58.

## Reading

- Operational: yes, all three native engines evolved valid programs through
  a fixed pipeline with prompt guards; AdaEvolve's post-run guard fired on
  SkyDiscover's unseeded explore/exploit text and was admitted by a verified
  diff (GUARD-NOTE.md).
- Mathematical: finite. No program meets T on all sampled states; GEPA's best
  misses 6 development near-reversals by 1-2 letters and 20 holdout states.
  BEST-GEPA-CONSTRUCTION.md: the gain is a portfolio of 14 heuristic sweep
  policies plus prefix escapes under the time limit, on top of the seed's
  construction; no length bound, slightly nondeterministic. Not a lemma.
- Comparative: descriptive only (one seed). The three native engines
  generalized to unseen r=6 and m=10 while the sequential control collapsed
  on r=6 (136/300). This is the first campaign where the engines beat the
  matched sequential control on holdout.

## Next

Seed random_seed in the SkyDiscover config (new hash); three seeds per arm;
reward bounded constructions (e.g. score the maximum excess per r, or ask for
a proof sketch scored by a checker) rather than portfolio search; extend
holdout to (9,7) and (10,4) when tables exist.
