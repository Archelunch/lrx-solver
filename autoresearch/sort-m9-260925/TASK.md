# sort-m9-260925: evolve a uniform LRX sorting program for m=9

User-approved step 3 of the outer-layer plan (`autoresearch/outer-layer-260925/REPORT.md`).
Offline scaffold only: no provider call, no `payload-approved.sha256`, no commits.
The main conjecture stays open. A valid word certifies an upper bound for its state only.

## Candidate and score

A candidate is a Python program exposing `sort_word(v: list[int]) -> str`. `v` holds labels
1..m once and r >= 1 zeros. The word over L, R, X must sort `v` to `(1..m, 0^r)`. The source is
stdlib only and at most 64 KiB. Each call has 2 s and returns at most 1000 letters.

`integrations/sort_evaluator.py` (trusted, coordinator side) runs the candidate in the Seatbelt
sandbox, one process per batch of 100 states. The batch has a per-state SIGALRM in
`integrations/sort_worker.py` and a wall limit of 2 s x 100 + 5 s. Every word is replayed with
`src/lrx/certificates.replay_visible`. Per state:

- valid iff the replay ends at the root;
- within budget iff valid and `len(word) <= T_m(n) = m(m+1)/2 + (r-1)(m-2)`;
- excess `len(word) - d(v)`, where d(v) is the exact BFS distance frozen with the state.

Aggregate: `combined_score = within/N + 0.5/(1 + mean excess over valid) - invalid/N`.
Crash, time limit, bad letters, over 1000 letters or a killed batch count as invalid.
They are never evidence about d(v).

## Sets (`frozen/`, built by `build_frozen.py`, seed 260925)

Per table, 300 states. All states at the table radius go to development. 180 are spread over
the top 10 layers and 120 over layers 1..radius-10, in equal per-layer shares with water-filling.
Development and holdout come from one draw per layer, so they are disjoint.

- development: m=9, r=1..5, 1500 states. It is the only set engines load.
- holdout: m=9, r=1..5 disjoint (1500), m=9 r=6 (300) and m=10 r=3 (300), scored with T_10(n).
  It is evaluated once, after finalist freeze, by a human-run
  `python -m integrations.sort_evaluator --holdout ...`.

The (9,6) and (10,3) tables are built by `build_tables.py` with unmodified
`src/lrx/table_bfs.build_table` into `datasets/generated/sort-m9-260925/`. See `build_log.jsonl`.
Hashes and per-layer counts are in `frozen/manifest.json`.

## Controls (development)

- (a) `integrations/sort_control_naive.py`: bubble sort in the fixed frame. It is the campaign seed.
- (b) `integrations/sort_control_sweep.py`: cyclic sweeps on the ring with lifted displacements.
  Zeros swap roles for free, so zero blocks act as buffers. It takes the best over rotations,
  zero assignments and sweep modes.
- (c) `controls/reference-optimal-development.json`: shortest words by table descent.
  It is the reference upper bound, not a candidate.

Scores are in `controls/*.json`.

## Engines

`integrations/sort_backends.py` mirrors `corr_backends.py`. It reuses `lift_backends.py`'s fixed
plumbing: rejection notes, per-arm ledgers and sub-caps, `min(3, n)` minibatch, EvoX strategy
evolution off below 100 iterations, and the sandbox launcher. The GEPA dataset has one example,
the whole development set.

The packet (`SORT_PACKET_V1`, at most 2000 chars) carries totals, per-(m,r) within-budget rate
and mean excess, and the best so far recomputed from the evaluation manifest. It also shows up
to 3 worst states with vector, T, exact d, status and length. Each of those states gets the
first step leaving every shortest path and the first step after which T is unreachable (both
from the exact tables, mmap), or the final vector if the word is not sorted. The outer-layer
structural facts close the packet.

`campaign-config.json` sets iterations to gepa 60, sequential 60, adaevolve 50 and evox 40.
`broker-config.json` is copied from `lift-m9-260924/broker-config.next.json` (gemini-3.8-flash,
8192 output tokens). It sets a fresh ledger `broker-ledger-sort.json` and max_usd 38.4. The
conservative reservation formula gives a shared pool of 230 contacts. Sub-caps are 65/65/55/45,
each arm's iterations plus 5 as a margin for retries and SkyDiscover connectivity probes.

Smokes: `smoke-{gepa,sequential,adaevolve,evox}/` run through the offline `mock_api.py`.
`first-prompt.md` / `first-prompt.sha256` hold the captured first GEPA prompt.
`approval-material.json` is hashed by `python -m integrations.sort_backends approval-hash`.

## Measured (2026-09-25, offline)

New tables (complete, `build_log.jsonl`). These are finite exact results for these two cases only.

| m | r | states | radius | T_m(n) | states at T | BFS s | sha256 |
|---|---|---|---|---|---|---|---|
| 10 | 3 | 1,037,836,800 | 71 | 71 | 4 | 1157 | `6deed7ea4ad9ea199a12877fe8c50485207f39d35814b9ff591d2a4fa505285f` |
| 9 | 6 | 1,816,214,400 | 79 (independently verified 2026-09-25) | 80 | 0 | 1522 | `4f8cc2c236511a5f0fe3f7462c8a32180050132edca41ec567d4c892ddcee6dd` |

Frozen sets: development 1500 (`f4dd4752...3346`), holdout 2100 (`c281643a...4565`),
manifest `c98fd613...ca4e`.

The (9,6) radius is 79, one below T_9(15) = 80, independently verified 2026-09-25
(`autoresearch/outer-layer-260925/INDEPENDENT-CHECK.md`). Because of it, the (9,6) holdout's top layer is 79 and has no state at T.

Development scores (Seatbelt, `sort_evaluator`):

| control | within budget | mean excess | max excess | invalid | combined |
|---|---|---|---|---|---|
| (a) naive (seed) | 128/1500 | 51.80 | 146 | 0 | 0.0948 |
| (b) sweep | 1356/1500 | 1.83 | 8 | 0 | 1.0810 |
| (c) BFS-optimal reference | 1500/1500 | 0 | 0 | 0 | 1.5000 |

Control (b) within-budget rate by r=1..5: 0.997, 0.960, 0.893, 0.840, 0.830.
Smokes: all four arms `COMPLETE` through the mock. The approval hash (`approval-material.json`)
covers the sha256 of `lift_backends.py` and `official_backends.py`. It is recomputed once those
files are final (see below).

## Version 2 (2026-09-25, after attempt 1 was stopped)

Attempt 1 (`live-gepa-260925-120053`, 7 GEPA iterations) produced per-state state-space search.
Its best candidates timed out on 745-1083 of 1500 states and were near-optimal on the rest. That
cannot become a lemma. Its log is `live-all-console.attempt1-search-exploit.log`, and the v1
sources, configs and approval files are preserved in `v1/` (`v1/SHA256SUMS`).

Changes in v2 (`sort-eval-2`, `sort-contract-2`):

- Each call gets 0.2 s of CPU (ITIMER_PROF) and 1 s of wall time (ITIMER_REAL). Module import
  gets 0.5 s of CPU. Batches hold 10 states, and the kernel RLIMIT_CPU caps each batch at
  10 x 0.2 + 1.5 CPU s even if a candidate disables the alarms. The parent re-checks the recorded
  CPU and wall time. Timeouts count as invalid.
- The score is `within/N + 0.5 x (worst per-r within rate) + 0.25/(1 + mean excess) - invalid/N`.
- The prompt asks for a construction that is uniform in r and m and stays within T. It names
  the 0.2 s limit and says that search times out.
- The seed is the cyclic-sweep control.
- The packet shows per-r within and timeout counts for the candidate and the seed, plus the 3
  worst states with d, T, length and the first wrong prefix.
- Live runs are `live-v2-*`, ledgers are `broker-ledger-sort-v2.<engine>.json`, and finalize
  reads only `live-v2-*`. The budget stays at max_usd 38.4, a pool of 230, and sub-caps 65/65/55/45.

Development scores under v2 (Seatbelt, `controls/v2-*-development.json`):

| program | within | worst-r rate | timeouts | mean excess | combined |
|---|---|---|---|---|---|
| cyclic sweep (seed) | 1356/1500 | 0.830 (r=5) | 0 | 1.83 | 1.4075 |
| naive bubble | 128/1500 | 0.067 (r=5) | 0 | 51.80 | 0.1234 |
| plain BFS probe (`controls/search_bfs.py`) | 213/1500 | 0.107 | 1287 | 0 | -0.4127 |
| bidirectional BFS probe (`controls/search_bidir.py`) | 284/1500 | 0.143 | 1216 | 0 | -0.2997 |

The seed's within-budget counts per r are r=1 299, r=2 288, r=3 268, r=4 252, r=5 249.
The search probes finish only near the root: max solved d is 20 for BFS and 28 for
bidirectional BFS, against T = 45..73. Smokes are in `smoke-v2-*`; all four are `COMPLETE`.

First-prompt guards (v2, all four arms). Each arm's first proposer prompt was captured twice
through the mock, in independent 1-iteration runs under `first-prompt-capture-v2/`. Both
captures gave identical hashes, and all four are folded into the approval hash.

| arm | file | messages sha256 | guard |
|---|---|---|---|
| gepa | `first-prompt.sha256` | `7a8240ac...aa30` | pre-send (existing client guard) |
| sequential | `first-prompt-sequential.sha256` | `c0ec902d...52de` | pre-send, status `FIRST_PROMPT_MISMATCH` |
| adaevolve | `first-prompt-adaevolve.sha256` | `fb0b7a84...6493` | post-run check of the first ledger solution request |
| evox | `first-prompt-evox.sha256` | `bc70f531...20e6` | post-run check of the first ledger solution request |

AdaEvolve/EvoX need a post-run check because SkyDiscover's client has no pre-send hook. A
solution request is one that is not strategy or variation meta-search and that contains
`sort_word`, which excludes connectivity probes. The research broker refuses a non-HTTPS
upstream, so the post-run check was exercised on receipts built from the captured request
bodies, not through the broker. With a wrong hash the EvoX run was marked
`FIRST_PROMPT_MISMATCH` and raised.

## AdaEvolve first-prompt mismatch (v2 live run)

AdaEvolve's parent-selection mode is drawn from an RNG that our sky config leaves unseeded
(`random_seed` unset in `lift_backends._sky_config`). Its first prompt's "PARENT SELECTION
CONTEXT" paragraph therefore varies at random, and the live arm failed the post-run guard,
although the system message, program and packet matched the approved capture byte for byte.
`sort_finalize` admits such an arm only when its own diff shows that paragraph as the sole
difference, and it records the diff and both hashes in `finalists/manifest.json`. The fix for
future campaigns is to set `random_seed` in `_sky_config`, which plumbing-fix owns; that needs a
new approval hash. Details are in `GUARD-NOTE.md`.
