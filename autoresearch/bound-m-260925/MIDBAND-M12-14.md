# Middle band at m = 12..14 with the C oracle

Date 2026-09-26. Offline. There were no provider calls, no commits and no new dependencies. No LLM-generated code
was executed. Lemma 1, its bookkeeping and criteria (7)/(8) are the research group's (m=8 manuscript). The main
conjecture stays open.

Every negative below rests only on Lemma 1's pricing (`lrx_m.Profile`, transcribed in
`negcert_general.profile_cost`) and on the form of criterion (7) at the unit origin. This note continues
MIDBAND-LOWERBOUND.md. Code, certificates and logs are in `negcert/fast/`, and its README.md has the port,
the validation table and the timings.

## 1. Verdicts

The seven instances are root leaves of the unit bases of (m..1){0,g}. V is the exact root LP value
min{Bbar : betabar_j <= s} over all accepted sorting words. The root leaf is certifiable iff V < T+1.

| instance | T+1 | verdict | V | proof |
|---|---|---|---|---|
| 12 {0,5} | 89 | **NO ROOT-LEAF CERTIFICATE** | **89 exactly** | `negcert-m12-05.json`: every word has B + 3 beta_0 >= 119 = (T+1) + 3s; a 1/2, 1/2 mixture attains 89 |
| 12 {0,6} | 89 | **NO ROOT-LEAF CERTIFICATE** | **89 exactly** | `negcert-m12-06.json`: every word has B + 2 beta_0 >= 109 = (T+1) + 2s; one word (89, (10,7)) attains 89 |
| 13 {0,6} | 103 | open (INCOMPLETE) | 97 <= V <= 326/3 | lower: capped exact search at lambda = 3; upper: seed pool |
| 13 {0,7} | 103 | open (INCOMPLETE) | 96 <= V <= 317/3 | lower: capped search at lambda = 3; upper: seed pool |
| 14 {0,7} | 118 | open (INCOMPLETE) | 678/7 <= V <= 865/7 | lower: capped search at W = (7,25,1) |
| 14 {0,8} | 118 | open (INCOMPLETE) | 96 <= V <= 121 | lower: capped search at lambda = 3 |
| 14 {0,9} | 118 | open (INCOMPLETE) | 93 <= V <= 118 | lower: capped search at lambda = 3 |

No positive root certificate was found. `fast_positive_check.py` is in place but has nothing to check.

**Both m = 12 roots sit on the boundary V = T+1**, like m = 7 {0,3} and m = 8 {0,4}. The best mixtures miss
criterion (7) by equality, not by a margin.

- **m = 12 {0,5}.** The words (83, (12,3)) and (95, (8,15)), mixed 1/2 and 1/2, give Bbar = 89 and betabar = (10, 9).
- **m = 12 {0,6}.** The single word (89, (10,7)) has B = T+1 with both slopes <= s = 10.

**Consequences for MIDBAND-LOWERBOUND.md section 7.**

- **Conjecture 2 is false at m = 12.** It said that for even m >= 10 every root leaf in the band is certifiable, but
  m = 12 {0,6} is not.
- **Conjecture 3 is false at m = 12.** It said that for m >= 10 and g != (m-1)/2 the excess V - T is at most 1/2.
  Both m = 12 gaps have V - T = 1.
- **Conjecture 1 (odd centre) is untested.** m = 13 {0,6} stays open: its interval [97, 326/3] contains T+1 = 103.
- **Excess sequence.** The peak excess over the computed gaps is V - T = 1, 1, 2, 1/2, >= 1, 1 at m = 7..12.

## 2. The two refutations

Both are in the `negcert_general.py` certificate format. `make_cert.py` wrote them from the REFUTED
column-generation results.

| file | W | claim_min = threshold | exact | witnesses (B, beta) | sha256 |
|---|---|---|---|---|---|
| `negcert-m12-05.json` | (1,3,0) | 119 | yes | (95,(8,15)), (83,(12,3)) | `85bbd621…` |
| `negcert-m12-06.json` | (1,2,0) | 109 | yes | (93,(8,13)), (89,(10,7)), (81,(14,3)) | `31807da1…` |

**How they were found** (`fast_colgen.py`, runs in `fast/runs/`). Column generation started from the stored seed
pools plus words from earlier attempts. Each C call built the 4 x 3 table (67.3M vectors) for the current
multipliers, ran two anytime weighted passes of 30M expansions each, then the exact bounded A*.

**m = 12 {0,5}** (`colgen-m12-g5.log`). The pool of 11 words had LP value 89 at lambda = (3,0). The exact search
at W = (1,3,0) and K = 119 found no word in 197,072,746 expansions (310 s), which gives REFUTED.

Two columns that led there came from earlier attempts:
- (97,(8,7)) at W = (5,21,0), from the anytime weighted pass.
- The optimum of 2B + 7 beta_0, which is exactly 246 < 248, from the word (95,(8,15)). This took 196M
  expansions in 965 s (`exact-m12-g5-W270-K248.log`).

**m = 12 {0,6}** (`colgen-m12-g6.log`), four oracle calls in 1,194 s:

| lambda | W, K | result | expansions |
|---|---|---|---|
| 13/6 | (6,13,0), 664 | optimum 662, column (93,(8,13)) | 193M |
| (34/13, 7/13) | (13,34,7), 1567 | optimum 1546, column (89,(10,7)) | 136M |
| 11/6 | (6,11,0), 644 | optimum 640, column (81,(14,3)) | 219M |
| 2 | (1,2,0), 109 | **no word below 109** | 198,380,011 |

**Verification.** `fast_check.py` was run from an isolated copy in the scratchpad, containing only
`negcert_general.py`, `lrxfast.c`, `build.sh`, `fastoracle.py`, `fast_check.py` and the certificates, with a fresh
build and `python3 -I`.

```
negcert-m12-05.json: table 67267200 vectors, 804249600 edges, consistent, max h 109, start bound 101
  bounded A* (prune f >= 119): no sorting word below 119; 197072746 expansions
  witnesses (95,(8,15)) and (83,(12,3)) re-price to 119; exact minimum 119
  root mixture needs Bbar < 89 and betabar_j <= 10 ...: NO ROOT-LEAF CERTIFICATE; implied LP bound 89
  VERIFIED  (280 s on the first run, 5.3 GB; 165 s on the final binary)
negcert-m12-06.json: table 67267200 vectors, consistent, max h 99, start bound 92
  bounded A* (prune f >= 109): no sorting word below 109; 198380011 expansions (109 s)
  three witnesses re-price to 109; exact minimum 109; NO ROOT-LEAF CERTIFICATE; implied LP bound 89
  VERIFIED  (152 s, 5.35 GB)
```

**Negative tests** (isolated copy). Each certificate with `claim_min` raised by 1 must FAIL, and both do.

| certificate + 1 | what fails |
|---|---|
| m12-05 at 120 | the search returns a word with F = 119 < 120; witness, exactness and `lp_value` checks fail |
| m12-06 at 110 | the search hits the memory cap inside bucket 109 (it proves only >= 109), so it is INCOMPLETE; witness, exactness and `lp_value` checks fail |

The expansion counts of the isolated runs equal those of the column-generation runs. The bounded search expands a
deterministic set.

**Pure-Python verification is infeasible.** `negcert_general.py` would have to build the 67.3M-vector table as a
Python dict. The 14.4M-vector m = 11 table already took 480 s and 4.5 GB. It would then have to run about 197M
A* expansions; its m = 11 runs managed 24M nodes in 6.3 to 8.4 GB. On this 18 GB host, which swaps with other
workloads, that is not possible in an hour. The C checker is the verifier. Its completeness argument is the one in
the `negcert_general.py` docstring, and it was cross-checked against the Python reference on m <= 11 (README,
Validation):
- 48 small cases against `raw_dijkstra` and the Python A*;
- m = 9 {0,4} = 75;
- m = 10 {0,5} = 350;
- m = 11 {0,6} and {0,5} with the Python expansion counts reproduced exactly (9,477,482 and 23,907,926).

## 3. What remains out of reach, and the certified intervals

**Why the lower ends are proved.** A capped exact A* processes f buckets in increasing order. When it stops inside
bucket p, every node with f < p has been expanded, and a terminal below p would have been popped. So min F >= p is
proved.

The C program now prints this bound. Runs before the fix printed p+1 as "frontier", and the table below uses the
corrected p. The implied root LP bound is V >= (p - s(w0+w1))/wB.

| instance | table | W | K needed | proved min F >= p | V >= | expansions at cap |
|---|---|---|---|---|---|---|
| 13 {0,6} | 4+3+3+3 (252M) | (1,2,0) | 125 | 117 | 95 | 116M |
| 13 {0,6} | same | (1,3,0) | 136 | 130 | **97** | 120M |
| 13 {0,7} | same | (1,2,0) | 125 | 117 | 95 | 112M |
| 13 {0,7} | same | (1,3,0) | 136 | 129 | **96** | 113M |
| 13 {0,7} | same | (3,7,0) | 386 | 364 | 287/3 | 113M |
| 14 {0,7} | 5+5+4 (60.5M) | (7,25,1) | 1138 | 990 | **678/7** | 147M |
| 14 {0,8} | same | (1,3,0) | 154 | 132 | **96** | 144M |
| 14 {0,9} | same | (1,3,0) | 154 | 129 | **93** | 145M |

- **Memory stops every run, not time.** Each run hit the node-store cap of 7.5 GB, after 65 to 120 s of search.
- **Remaining gap.** m = 13 is 6 to 8 f-levels short at lambda = 2, 3. m = 14 is 22 to 25 levels short at lambda = 3.
- **For comparison.** The m = 12 refutations closed gaps of 18 and 17 levels from the start bound, in about 197M
  expansions each.
- **Upper ends.** They come from the seed pools. They are pool LP values: mixtures of stored words with slopes <= s.
  No weighted pass (3 x 40M expansions at the pool multipliers) found a word below the refutation threshold at
  m = 13 or 14.
  - m = 14 {0,9} has pool LP 118 = T+1 exactly, with lambda = 3.

**What would be needed.**
- **Stronger tables.** At m = 13 the next finer partition has 1.0G to 1.5G abstract vectors, beyond both u16
  storage in 12 GB and 32-bit node ids.
- **More memory.** The search costs about 22 to 30 bytes per stored node. A 60 GB machine would give roughly 8 times
  the frontier.
- **A different lower-bound method.** An example is a dual table certificate, route A of NEGCERT.md.

The host had 5 to 8 GB free throughout, and swap was 11 to 12 of 13 GB used by other workloads. Two concurrent
searches thrashed at 0.02M to 0.2M expansions/s against about 1M alone. From then on every instance ran alone.

## 4. Process notes (failed or superseded attempts, all kept in `fast/runs/`)

- **Bugs fixed in the port.**
  - The oversized sparse hash of the first version was compressed by the kernel, so the search ran in 568 s
    instead of 22 s. A dense pool with a growing index replaced it.
  - In weighted mode, children whose priority fell below the current bucket were dropped. The search then printed
    `RESULT NONE` after 12 expansions (`colgen-m12-g6.weighted-bug.log`).
    - The driver never used a weighted result as a bound.
    - Weighted passes now clamp the priority, and they print only `WEIGHTED NOTFOUND` or `WEIGHTED INCOMPLETE`.
  - The capped report printed the interrupted bucket + 1. It now prints the bucket, and section 3 uses the
    corrected values.
- **Operator errors.**
  - A misdirected kill stopped the m = 12 {0,5} search at W = (2,7,0) (`colgen-m12-g5.attempt3.log`, result
    ERROR). It was rerun alone.
  - An orphaned m = 12 {0,6} search competed for memory for about 30 minutes.
  - One m = 13 launch never started because it was chained behind a failing script.
- **Killed probe.** The m = 12 {0,6} probe at the stale multipliers W = (3,4,0) was stopped at f = 297 after 134M
  expansions, under memory pressure (`probe-m12-g6-W340.killed.log`). Its W is not the refuting one.

## 5. Limits

- **Checked by the author only.** The certificates were checked by their author, the fast-oracle agent, from an
  isolated copy. No independent re-run was made, and no orchestrator re-run.
- **Scope.** As in MIDBAND-LOWERBOUND.md, words that swap two zeros are outside the Profile domain, and picks are
  unit picks. The claims are about these root leaves only; trees (refined origins) were not attempted.
- **CPU.** About 6 hours of wall clock on a shared, swapping host.
  - Column generation and probes: about 3 CPU hours.
  - Validation and verification: about 30 minutes.
  - The per-instance budget of about 60 minutes held for each m = 12 instance counted alone: 395 s + 965 s for
    {0,5} and 1,194 s for {0,6}. The m = 13 and 14 attempts are counted in section 3.
