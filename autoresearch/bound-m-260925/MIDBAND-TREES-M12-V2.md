# Middle band m = 12, v2: wide tree oracle; both m = 12 families certified by trees

Date 2026-09-26. Offline. There were no provider calls, no commits and no new dependencies (system cc and the
Python standard library only). No LLM-generated code was executed. The oracle and drivers below were written in
this session. Lemma 1 (with refinement and picks), formula (6) and criterion (8) are the research group's (m=8
manuscript, general-m audit in Session 27). The main conjecture stays open. Nothing under src/, tests/,
integrations/ or tools/ was changed. `lrxtree.c` and `lrxfast.c` are unchanged. This note continues
`MIDBAND-TREES-M12.md` (v1).

## 1. Result

| family | v1 (Session 35) | v2 |
|---|---|---|
| m = 12 {0,5} | BOUNDARY, open leaf [4,inf) x {1} at lhs 1 | **CERTIFIED**, 6 leaves, evaluator + audit + replay |
| m = 12 {0,6} | BOUNDARY, open leaf [3,inf) x {1} at lhs 1 | **CERTIFIED**, 5 leaves, evaluator + audit + replay |
| m = 11 {0,5} | CERTIFIED | unchanged (re-checked) |

With these trees, d(v) <= T_12(n) holds for every state (0^u0, 12..8, 0^u1, 7..1) and every state
(0^u0, 12..7, 0^u1, 6..1), u0, u1 >= 1. This is conditional on Lemma 1 with refinement and criterion (8) at m = 12.
Data: `checks/midband-trees-m12-v2.json` (same format as v1; v1 is untouched). Re-check:
`checks/midband_trees.py --data checks/midband-trees-m12-v2.json` (no new check script was needed).
sha256 of the data file: `4c67dda88955b69bc5e8122dd5e01032582a3c9f6a4e2bb063697be92bced505`.

Two single-state distances fall out on the way. They are upper bounds, certified by replay:

| state | n | T_12(n) | v1 best word | v2 word |
|---|---|---|---|---|
| (0^4, 12..8, 0, 7..1) | 17 | 118 | 119 | **115** |
| (0^3, 12..7, 0, 6..1) | 16 | 108 | 109 | **105** |

The v1 remark that these were search limits, not evidence against the conjecture, was right. The v1 "mechanism"
paragraph (the root boundary propagating unchanged along the u0 stripe) described the word pools, not the
states. Both points sit 3 below T.

## 2. How the open leaves closed

1. **The tails need no new word.** Splitting each open leaf at one point, the tail leaf at origin (3,1) is
   certified by a single stored origin-(3,1) word with slope beta_0 = 8 < s = 10:
   - {0,5}, [5,inf) x {1}: (111, (8,15)) costs 111 + 2*8 = 127 <= T = 128, lhs -1;
   - {0,6}, [4,inf) x {1}: (109, (8,13)) costs 109 + 8 = 117 <= T = 118, lhs -1.
   This already reduced each family to one point leaf at lhs exactly 1
   (`negcert/tree/assemble_v2.py`, evaluator output BOUNDARY with that single open leaf).
2. **A point leaf is a pure distance question.** On a box {l}, lhs = Cbar(l) - T(l), so the leaf passes iff some
   sorting word of that state has length <= T. The oracle runs at W = (1,0,0), with all zeros one symbol.
3. **{0,6} point, suffix re-optimization** (`negcert/tree/suffix_opt.py`, n = 16). For every stored word w and
   position i, the exact oracle searched from the intermediate state s_i for a completion shorter than
   K_i = T + 1 - i (batch mode, one verified table). Of 430 searched states, 17 gave shorter completions. The
   best splice has length 105 (from a 117-letter word, i = 59); others have length 107. Total 67 s after the table.
4. **{0,5} point, prefix re-optimization** (`negcert/tree/prefix_opt.py`, n = 17, needs the wide oracle).
   - Suffixes gave nothing, and they are exactly optimal. 527 states with K <= 76 were searched: 517 NONE,
     0 FOUND, and 10 INCOMPLETE at the 25M cap, each interrupted one bucket below K. A re-run with an 80M cap
     over the K = 75..76 states (10 NONE, the 11th stopped) turned 4 of the 10 INCOMPLETE states into NONE.
     In total 521 NONE and 6 INCOMPLETE.
   - So every stored 119-word already has an optimal tail from letter 43 on. The oracle's new `--target` mode
     then searched from s_i back to the point state, with K_i = T + 1 - (L - i).
   - 49 of 553 searched states gave shorter prefixes. The best word has length 115, with 35 to 37 new letters
     replacing the first 38 to 41. Total 309 s after the table.

Deeper origins as leaf origins: (4,1) is used by the {0,5} point leaf (n = 17, only reachable with the wide
oracle). Origin (5,1) and finer splits (points u0 = 5 and a tail u0 >= 6) turned out unnecessary, so they were not
run.

## 3. The trees

Leaves: box, origin, T(l), lhs, support (B, beta) x weight. All picks are (0,0).

**m = 12 {0,5}**, T = 88, s = 10, depth 5.

| box (u0, u1) | origin | T(l) | lhs | support |
|---|---|---|---|---|
| {1} x [1,inf) | (1,1) | 88 | -11 | (77, (16,1)) x 1 |
| {2} x {1} | (2,1) | 98 | -3 | (95, (12,3)) x 1 |
| {3} x {1} | (3,1) | 108 | -1 | (107, (12,3)) x 1 |
| **{4} x {1}** | **(4,1)** | 118 | **-3** | **(115, (16,1)) x 1, new** |
| **[5,inf) x {1}** | (3,1) | 128 | **-1** | (111, (8,15)) x 1 |
| [2,inf) x [2,inf) | (2,1) | 108 | -3 | (95, (12,3)) x 1/2, (105, (8,7)) x 1/2 |

**m = 12 {0,6}**, T = 88, s = 10, depth 4.

| box (u0, u1) | origin | T(l) | lhs | support |
|---|---|---|---|---|
| {1} x [1,inf) | (1,1) | 88 | -12 | (76, (18,0)) x 1 |
| {2} x {1} | (2,1) | 98 | -4 | (94, (16,2)) x 1 |
| **{3} x {1}** | (3,1) | 108 | **-3** | **(105, (14,3)) x 1, new** |
| **[4,inf) x {1}** | (3,1) | 118 | **-1** | (109, (8,13)) x 1 |
| [2,inf) x [2,inf) | (2,1) | 108 | -2 | (99, (10,7)) x 1 |

The two new words, written verbatim in the data file:
- {0,5} point, origin (4,1), 115 letters: `negcert/tree/runs-wide/point-m12-g5-u4-o41-best.txt`
- {0,6} point, origin (3,1), 105 letters: `negcert/tree/runs-wide/point-m12-g6-u3-o31-best.txt`

## 4. The wide oracle

`negcert/tree/lrxtree_wide.c` (build: `build_wide.sh`; driver `treeoracle_wide.py`, which patches treeoracle's
binary and size check so `leaf_colgen.py` / `probe.py` run unchanged via `python3 treeoracle_wide.py leaf_colgen ...`).

- **Same model, abstraction and proof as lrxtree.c.** The vector lives in an unsigned __int128, still 4 bits
  per cell. Symbols 0..m+2 fit a nibble for m <= 13, so the oracle takes n <= 20 and at most 8 zeros.
  - The search key is 80 bits: n-1 cells plus the context in bits 76..79. It is stored as u64 + u16, so an entry
    grows from 12 to 14 bytes.
  - The abstract-root array is 256 entries, bounds-checked. It was 24.
  - The source was produced from lrxtree.c by an asserted, scripted list of replacements (type changes only).
    Search order, tie-breaking, bucket structure, table build and verify() are unchanged.
- **Additions** (new options only; single runs without them take the same path as lrxtree.c):
  - `--batch FILE` / `--batch-stop N` build and verify the tables once, then run the same passes from many start
    vectors, each with its own K.
  - `--target t` accepts only unit weights. Its terminal is the single vector t, and the tables are rooted at the
    abstraction of t, then built and verified the same way. A NONE K there proves d(start, t) >= K. The graph
    is undirected and reversal preserves reduced words.
- **Limits.** Node ids are u32, so a table must have fewer than 2^32 nodes. At n = 17 with unit weights, the
  [4,4,4] table has 214,414,200 vectors (643M nodes, 1.25 GB). It took 139 to 268 s to build and 16 to 21 s to
  verify on the loaded host.

### Validation (actual outputs; logs under `negcert/tree/runs/` and `negcert/tree/runs-wide/`)

VALIDATION_TABLE

The three stored-count differences are runs made at 18:35 to 18:36, before the 18:44 lrxtree build that merged
weight-0 picked zeros into the ordinary zero symbol. Their stored tables were 2, 6 and 2 times larger
(831,600 / 9,979,200 / 67,267,200 vectors, against 415,800 / 1,663,200 / 33,633,600 now). In all three, narrow
and wide agree exactly with each other. `crosscheck_wide.py` now compares a stored count only when the table
size matches, and prints the reason otherwise.

## 5. Per-leaf outcomes, timings, memory

| leaf | origin, n | outcome | oracle work | wall (host load 8 to 11 on 12 cores) | peak RSS |
|---|---|---|---|---|---|
| 12 {0,6}, [4,inf) x {1} | (3,1), 16 | CERTIFIED by a stored word, lhs -1 | none | n/a | n/a |
| 12 {0,5}, [5,inf) x {1} | (3,1), 16 | CERTIFIED by a stored word, lhs -1 | none | n/a | n/a |
| 12 {0,6}, {3} x {1} | (3,1), 16 | **CERTIFIED**, word 105 <= 108, lhs -3 | suffix batch: 430 states, 79M expansions | 37 s table + 67 s | 0.53 GB |
| 12 {0,5}, {4} x {1} | (4,1), 17 | **CERTIFIED**, word 115 <= 118, lhs -3 | suffix batches: 538 states, 1.16G expansions, 0 found; prefix batch: 553 states, 40M expansions, 49 found | 10 + 6 + 5 min, plus 3 table builds of 2.5 to 4.5 min | 1.34 GB |

Memory cap 5 GB on every run. Every oracle ran at nice 19, one attack at a time; the cross-checks used under
2 GB. Total attack wall time was about 35 min, well inside the 3 h budget.

Exact negative statements on the way (each is about one intermediate state, not a family):
- {0,5} point: 521 distinct states s_i on the stored words have d(s_i) >= T + 1 - i (NONE): 517 in the first
  suffix run, plus 4 more from the 80M re-run.
- {0,6} point: 412 suffix states and, for {0,5}, 503 prefix states are NONE.

These are recorded in the run JSONs but are not needed by the certificates.

## 6. What remains

- The middle band at m = 13 ({0,6}, {0,7}) and m = 14 ({0,7}, {0,8}, {0,9}) is still open. The roots are
  INCOMPLETE (Session 34), and no trees have been tried yet. The wide oracle now reaches refined origins there:
  n = m + r <= 20, m <= 13 for the nibble packing. m = 14 needs 5-bit cells (symbols up to 16).
- The recipe that worked here may transfer:
  1. certify tails with lifted stored words;
  2. reduce the rest to point leaves;
  3. shorten point words by suffix and prefix re-optimization against the exact oracle.
- Suffix/prefix optimality is local: NONE results say nothing about d(v) itself. No lower bound on the two point
  distances was computed, and none is needed for the certificates.
- Independent re-run: none. All checks were run by their author, this agent. The certificate itself does not
  depend on the oracle: evaluator, audit and replay are the trusted re-check. The oracle only found the words.

## 7. Verification (actual output)

```
$ python3 autoresearch/bound-m-260925/checks/midband_trees.py --data autoresearch/bound-m-260925/checks/midband-trees-m12-v2.json --refutations
m11-mask33-labels11.10.9.8.7.6.5.4.3.2.1 (m=11, zeros in gaps [0, 5]): stored status CERTIFIED
  score_output: CERTIFIED, gap 0, 4 leaves, lhs ['-11', '-7', '1/2', '2/3']
  audit_claim: agree (ok)
  replay: 6 leaf words sort their refined bases
m12-mask33-labels12.11.10.9.8.7.6.5.4.3.2.1 (m=12, zeros in gaps [0, 5]): stored status CERTIFIED
  score_output: CERTIFIED, gap 0, 6 leaves, lhs ['-11', '-3', '-1', '-3', '-1', '-3']
  audit_claim: agree (ok)
  replay: 7 leaf words sort their refined bases
m12-mask65-labels12.11.10.9.8.7.6.5.4.3.2.1 (m=12, zeros in gaps [0, 6]): stored status CERTIFIED
  score_output: CERTIFIED, gap 0, 5 leaves, lhs ['-12', '-4', '-3', '-1', '-2']
  audit_claim: agree (ok)
  replay: 5 leaf words sort their refined bases
  expansions 52824541 (stored 52824541)
  refutation 11 {0,5} origin [2, 1] picks [0, 0] box [[2, 'inf'], [1, 1]]: oracle NONE at W=[1, 2, 0] K=103 -> VERIFIED
  expansions 52487139 (stored 52487139)
  refutation 11 {0,5} origin [2, 1] picks [1, 0] box [[2, 'inf'], [1, 1]]: oracle NONE at W=[1, 2, 0] K=103 -> VERIFIED
ALL OK
```

Repository checks (nothing under src/ or tests/ changed): `python -m unittest discover -s tests -p 'test_*.py'`
reports `Ran 618 tests ... OK (skipped=4)`; `python -m compileall -q src tests` exits 0; `python -m src.lrx.cli
smoke` passes.

## 8. Files

- `negcert/tree/lrxtree_wide.c`, `build_wide.sh`, `treeoracle_wide.py`: wide oracle and driver.
- `negcert/tree/crosscheck_wide.py`, `crosscheck_wide_n17.py`, `crosscheck_target.py`: validation.
- `negcert/tree/suffix_opt.py`, `prefix_opt.py`: point-word re-optimization (FOUND words re-verified with
  lrx_m.Profile before they are reported).
- `negcert/tree/assemble_v2.py`: builds the v2 trees from v1 plus the point words and scores them.
- `negcert/tree/runs-wide/`: batch files, run JSONs and logs, word pools (`words-*.txt`, `seeds-*.txt`), point
  words (`point-*.txt`), validation logs, and `midband-trees-v2-check.log`.
- `checks/midband-trees-m12-v2.json`: the v2 data.
