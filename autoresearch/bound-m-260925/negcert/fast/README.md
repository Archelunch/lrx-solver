# fast/: C port of the exact middle-band oracle

Date 2026-09-26. Offline. There were no provider calls and no commits. No new dependencies: the system `cc`
(Apple clang 17) builds one C file, and the Python drivers use the standard library only. No LLM-generated code
was executed. `negcert_general.py` stays the reference and is unchanged. Results are in `../../MIDBAND-M12-14.md`.

## What it is

`lrxfast.c` is a port of the search core of `../negcert_general.py`. It keeps the same model, the same abstraction
and the same proof.

- **Model.** A state is (vector, context). The vector is the encoded cyclic state with the cursor cell first, and
  the context is one of the 12 (kind, f_0, f_1) contexts of Lemma C. `step()` transcribes `make_step` line by line.
- **Encoding.** The symbols are renumbered for 4-bit packing: label x becomes x-1 and the zero of block j becomes
  m+j. A state is one 64-bit word for n = m+2 <= 16. With both zero weights 0, the two zeros keep distinct symbols.
  That graph is a double cover of the Python graph, with the same minimum.
- **Abstraction (Lemma A).** Labels map to class codes, and zeros keep their identity. Abstract vectors are ranked
  as multiset permutations, so the table is a flat `u16` array of N x (number of contexts) entries.
  - The table is built by backward Dijkstra from the abstract roots. The build is level-synchronous and
    multi-threaded, with an atomic min on the entries.
  - `table_verify()` then checks consistency independently of the build, on every abstract node and every letter:
    h(u,c) <= w + h(t,c'), h(root,c) <= final(c), and no node is unreached. This check is also multi-threaded.
- **Search (Theorem).** A* uses the max over the verified tables, integer f buckets, a dense node pool and a
  fingerprinted open-addressing index. It prunes every node with g + h >= K.
  - If the bucket loop ends without a terminal below K, every reduced word, and hence every accepted sorting word,
    has F_W >= K. The completeness argument is the one in the `negcert_general.py` docstring, unchanged.
  - Node-store or bucket memory exhaustion prints `RESULT INCOMPLETE` and never a bound.
  - A capped run still certifies min F >= p, where p is the frontier bucket it stopped in. Buckets are processed in
    increasing f, so every node with f < p was expanded, and a terminal below p would have been popped.
    `MIDBAND-M12-14.md` uses this for the lower ends of its intervals.
- **Weighted passes** (`--omega b/a`, `--anytime`) use priority a*g + b*h and generate columns only. They print
  `WEIGHTED NOTFOUND` or `WEIGHTED INCOMPLETE` and never `RESULT NONE`.

## Files

| file | role |
|---|---|
| `lrxfast.c`, `build.sh` | the C oracle; `./build.sh` builds `lrxfast` |
| `fastoracle.py` | driver: encodes the family, runs `lrxfast`, re-prices every returned word with `negcert_general.price` and asserts the reported F |
| `fast_check.py` | certificate checker for the `negcert_general.py` JSON format, with the search delegated to `lrxfast` |
| `fast_colgen.py` | column generation (the exact Fraction LP helpers of `../midband_colgen.py`); exploration only |
| `make_cert.py` | writes a refutation certificate from a REFUTED column-generation result |
| `fast_positive_check.py` | re-checks positives with `score_output`, `audit_claim`, replay and `mixture_criterion`, as `../midband_positive_check.py` |
| `crosscheck_small.py`, `validate_lp.py` | validation against the Python reference |
| `probe.py`, `probes-m13.sh`, `colgen-m14.sh`, `summarize.py` | single calls, run scripts, log summaries |
| `negcert-m12-05.json`, `negcert-m12-06.json` | the two new refutation certificates |
| `runs/` | every log and JSON, including the killed, buggy and paused attempts, named as such |

## Validation (all agree)

| check | C port | reference |
|---|---|---|
| 48 small cases, m = 5..7, gaps 2..4, six weight vectors including (1,0,0) and (3,4,5) (`crosscheck_small.py`) | exact minimum, witness price, bounded K = F gives NONE, K = F+1 gives F | `raw_dijkstra` (uncompressed cz, no table) = Python A* = transcription; the table statistics (vectors, nodes, edges, max h, start bound) are identical except for (1,0,0), where the counts double by design |
| m = 9 {0,4}, W = (1,3,0), partition {9,8},{7,6},{5,4},{3,2,1} | table 831,600 vectors, 9,918,720 edges, max h 71, start bound 67; exact minimum **75** (word of B = 48, beta = (9,3)); bounded at 75: NONE | NEGCERT.md: same table figures, 75, same (48,(9,3)) type |
| m = 10 {0,5}, `lpcert-m10-05.json` | NONE at K = 350 (3,799,703 expansions); K = 351 gives F = 350, word (63,(8,10)) | 350 |
| m = 11 {0,6}, `lpcert-m11-06.json` | NONE at 92 with **9,477,482** expansions; K = 93 gives F = 92 | 9,477,482 expansions |
| m = 11 {0,5}, `negcert-m11-05.json` | table 14,414,400 vectors, 172,233,600 edges, max h 453, start bound 431; NONE at **497** with **23,907,926** expansions | identical figures, 23,907,926 expansions |

Expansion counts agree exactly. A bounded search that finds nothing expands exactly the nodes with g* + h < K,
which is a deterministic set.

## Timings

Measured on an Apple M3 Pro with 18 GB, macOS 15.5 and Python 3.12.8. The host was shared: load 10 to 32, and
swap 11 to 12 of 13 GB was in use by other workloads.

| task | Python reference | C port |
|---|---|---|
| m = 11 table (14.4M vectors), build + verify | 473 to 483 s | 35 + 2 s (single-thread build), 27 + 2 s (parallel) |
| m = 11 {0,5} bounded search, 23.9M expansions | 229 to 259 s, 6.3 GB | 21.7 s, under 1 GB |
| m = 11 {0,5} whole certificate | 743 s | 59 s (21 s search on the final binary, quieter host) |
| m = 12 table, 4 x 3 classes (67.3M vectors, 404M nodes) | out of reach (about 67M vectors in Python) | 43 to 130 s build, 3 to 6 s verify, 0.8 GB |
| m = 13 table, 4+3+3+3 classes (252M vectors, 1.5G nodes) | | 159 to 236 s, 3.2 GB |
| m = 12 {0,5} refutation, 197,072,746 expansions | out of reach | 234 s search, 280 s total, 5.3 GB (isolated copy) |

On an idle host, search throughput is about 0.8M to 1.1M expansions/s. When the host swaps it falls to
0.02M to 0.2M. The memory cost is about 22 to 30 bytes per stored node, plus the tables.

## How to run

```
cd autoresearch/bound-m-260925/negcert/fast
./build.sh
python3 crosscheck_small.py                         # 48 cases vs the Python reference
python3 validate_lp.py                              # m = 10, 11 certificates
python3 fast_check.py negcert-m12-05.json --mem 7   # C-backed certificate check
python3 fast_colgen.py 12 6 --classes '12,11,10|9,8,7|6,5,4|3,2,1' --omega 3/2 --omega 1/1 --anytime --mem 6.5
```

## Limits

- **Pure-Python verification of the m = 12 refutations is infeasible.** They need the 67.3M-vector table and
  about 197M expansions. The Python reference stores a dict entry per abstract vector and per search node. It
  handled 14.4M vectors and 24M nodes in 6.3 to 8.4 GB. The C checker `fast_check.py` is the verifier. It runs
  the same completeness argument, with the Python cross-checks above on m <= 11.
- **Supported families.** Only unit bases with two one-zero blocks (the middle-band families), n <= 16 (m <= 14),
  and fewer than 2^32 table nodes and search nodes.
- **Authorship of checks.** The checks were run by their author, the fast-oracle agent. No independent re-run has
  been made.
