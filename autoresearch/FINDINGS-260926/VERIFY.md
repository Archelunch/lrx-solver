# Offline verification recipe

No network, no provider calls, no generated code. This package is committed in the repository `lrx-lab` at commit
`f99d129`; FINDINGS.md, MANIFEST.md and this file all refer to that commit. Observed on 2026-09-26, macOS,
Python 3.12.8, on the working tree at `719ad17` plus this package's changes, which `f99d129` commits.

## 1. Self-contained re-checks (no repository, no tables, no numpy)

The package runs on its own. `vendor/` holds byte-identical copies of the 19 repository files the check scripts
import (`vendor/README.md` lists origin path, bytes and sha256). The four checks added in this version need no
further vendored file; `negcert/negcert_check.py` imports nothing from the repository at all. From the package root:

```
sh run_checks.sh        # POSIX; PYTHON=... selects the interpreter, default python3
python run_checks.py    # same steps, for Windows
```

Both set `PYTHONPATH` to `<package>/vendor` only and disable bytecode writes, so the package is left unchanged. They
run seven scripts in place, and none of them writes a file:
- `checks/reversal_k2.py` and `checks/reversal_midband.py` (no tables) re-check the stored rows;
- `checks/wordc_proof_check.py` checks every intermediate claim of `WORDC-PROOF.md` against the literal execution
  of word_C at m = 9..40;
- `checks/wordr1_proof_check.py` does the same for `WORDR1-PROOF.md` (Lemmas P, A-E, theorem, corollary) at
  m = 9..60;
- `checks/wordg_formula_check.py` tests the 28 word_G rule-row hypotheses and the unified hypotheses C1-C7 at
  m = 9..80. It exits 1 if a rule-row hypothesis fails or a row is uncovered. C1, C3 and C5 are coarse on purpose and
  are expected to fail;
- `checks/reversal_carry.py` re-checks the 59 stored carry-across certificates of `REVERSAL-CARRY.md` and the word_M
  closed form to m = 60;
- `negcert/negcert_check.py negcert/negcert-m9-04.json`, run with `python -I`, is the portable negative
  certificate for m = 9 {0,4}. It uses the stdlib only and reads no tables.

Then `reversal_m13.py` and `reversal_orbit.py`
rebuild their JSON and refuse to overwrite it, so the runners copy `checks/` to a temporary `a/b/checks/`, delete
the two JSON files there, rebuild them, and compare with the stored JSON after dropping only the `seconds` field.
Exit status is 0 only if every step passes. A tampered stored JSON was observed to give exit 1. In this version,
setting `claim_min` to 76 in a copy of `negcert-m9-04.json` made the checker print `FAILED` and `run_checks.sh`
exit 1.

Observed: the package was copied to a temporary directory outside the repository and run there with `PYTHONPATH`
unset (`cp -R autoresearch/FINDINGS-260926 $TMP/ && cd $TMP/FINDINGS-260926 && env -u PYTHONPATH sh run_checks.sh`):

```
package /private/tmp/claude-502/.../scratchpad/final3/FINDINGS-260926
python 3.12.8
$ python checks/reversal_k2.py
  re-checked 390 word_G rows and 150 stored rows in 1.9 s; problems: none
  exit 0
$ python checks/reversal_midband.py
  dual certificate m=9 {0,4}: witness B=54 beta=[7, 7], B+3beta0=75 (stored min 75)
  problems: none
  exit 0
$ python checks/wordc_proof_check.py
  m = 9..40, pairs (m, a) with 1 <= a <= m-2: 720
  mismatches (Lemmas A-E, theorem): 0
  corollary failures: 0 []
  exit 0
$ python checks/wordr1_proof_check.py
  m = 9..60: 52 values of m
  mismatches (Lemmas P, A-E, theorem, corollary): 0
  exit 0
$ python checks/wordg_formula_check.py
    C5 beta_0 = m-2 on every row                                             n=1600 exceptions=107 [(10, 1, (-1, 7, 4)), (10, 8, (-1, 7, 2)), (11, 9, (-2, 8, 5)), (12, 2, (-2, 9, 5))]
    C6 B = length (Lemma 1 base equals the word length)                      n=1600 exceptions=0 
    C7 B <= T and beta_0, beta_1 <= m-2 (criterion (7) numbers, weight 1)    n=1600 exceptions=0 
  exit 0
$ python checks/reversal_carry.py
  closed form: 160 rows scored by evaluator + audit (m <= 40), 207 rows by replay + criterion (7)
  problems: none
  exit 0
$ python -I negcert/negcert_check.py negcert/negcert-m9-04.json
  root mixture needs Bbar < T+1 = 53 and betabar_0 <= s = 7, so Bbar + 3 betabar_0 < 74; every word, hence every mixture, has >= 75: NO ROOT-LEAF CERTIFICATE
  total 16.4 s
  VERIFIED
  exit 0
$ python a/b/checks/reversal_m13.py
  closed forms m=9..200 failures: []
  wrote a/b/checks/reversal-m13-words.json 2.0 s
  exit 0
$ python a/b/checks/reversal_orbit.py
  wrote a/b/checks/reversal-orbit-words.json 2.4 s
  exit 0
reversal-m13-words.json identical
reversal-orbit-words.json identical

expected last lines (timings vary):
  re-checked 390 word_G rows and 150 stored rows in 2.3 s; problems: none
  dual certificate m=9 {0,4}: witness B=54 beta=[7, 7], B+3beta0=75 (stored min 75)
  problems: none
  m = 9..40, pairs (m, a) with 1 <= a <= m-2: 720
  mismatches (Lemmas A-E, theorem): 0
  corollary failures: 0 []
  m = 9..60: 52 values of m
  mismatches (Lemmas P, A-E, theorem, corollary): 0
  C5 beta_0 = m-2 on every row  n=1600 exceptions=107 [...]   (coarse on purpose; C1, C3, C5 are expected to fail)
  C6 B = length (Lemma 1 base equals the word length)  n=1600 exceptions=0
  C7 B <= T and beta_0, beta_1 <= m-2 (criterion (7) numbers, weight 1)  n=1600 exceptions=0
  closed form: 160 rows scored by evaluator + audit (m <= 40), 207 rows by replay + criterion (7)
  problems: none
  root mixture needs Bbar < T+1 = 53 and betabar_0 <= s = 7, ...: NO ROOT-LEAF CERTIFICATE
  total 16.5 s
  VERIFIED
  closed forms m=9..200 failures: []
  wrote a/b/checks/reversal-m13-words.json 2.2 s
  wrote a/b/checks/reversal-orbit-words.json 2.4 s
  reversal-m13-words.json identical
  reversal-orbit-words.json identical
ALL CHECKS PASSED
```

`run_checks.sh` exited 0 in 27.7 s wall time, and `run_checks.py` in the same copy exited 0 with the same nine
steps passing. No `__pycache__` was left in the copy. In the previous version, the same `run_checks.sh` also exited 0
under a fresh virtual environment without numpy, and the four scripts other than `wordc_proof_check.py` passed under
macOS `/usr/bin/python3` 3.9.6; those two runs were not repeated for this version.

The plain midband run prints 14 rows, each with `CERTIFIED ... audit=(True, 'ok') replay=True`. `reversal_orbit.py`
also prints `R1 failures m=9..200: []` and `word_C length failures 0 beta failures [[6, 1, [4, 3]], ..., [60, 1,
[4, 3]]]` before its last line. The 28 "beta failures" are the expected a = 1, even-m exception (4,3), documented in
REVERSAL-ORBIT.md section 3.

What this re-runs: the literal replay, the Lemma 1 pricing, the exact LP and the independent audit of the stored rows,
the mechanical checks of the word_C and word_R1 proofs, the word_G hypotheses, and the portable negative
certificate, with the package's own copies of that code. The proof checks are finite (m = 9..40 and m = 9..60). The
proofs in `WORDC-PROOF.md` and `WORDR1-PROOF.md` were written by a model and have not been reviewed by a human
mathematician. It does not re-run the BFS tables, the table-based A* oracle of section 2, or the campaigns.

## 2. Exact m=9 {0,4} negative, table-based oracle (needs tables (9,2)..(9,6), no numpy)

This is the earlier, table-based route. The portable checker of section 1 (`negcert/`) establishes the same minimum
75 without tables and with a written completeness argument.

```
PYTHONPATH=vendor python checks/reversal_midband.py --tables --root DIR     # or LRX_ROOT=DIR
```

`checks/reversal_midband_search/mb.py` finds the tables under a root chosen in this order: `--root DIR`, the
environment variable `LRX_ROOT`, the package's own `tables/` folder when present, and otherwise the nearest parent
folder that holds `datasets/generated` (the repository, when the package sits in it). A root that contains
`datasets/generated` is searched there. Inside the root it looks in `.`, `outer-layer-260925`, `sort-m9-260925`,
`m10-r2-260926` and `m11-260925`. If no `dist_m9_r*.bin` is found it prints a warning naming the root, and the
oracle then fails. This replaces the hard-coded absolute path of the repository original, which is left unchanged
under `autoresearch/bound-m-260925/checks/`.

Observed for the previous version (not re-run for this one; `checks/reversal_midband.py` and `mb.py` are
unchanged), from the temporary copy, with `LRX_ROOT` set to the repository, in the numpy-free environment (1.4 s):

```
dual certificate m=9 {0,4}: witness B=54 beta=[7, 7], B+3beta0=75 (stored min 75)
exact oracle: min B + 3 beta_0 = 75 over all reduced words (8760 nodes); needed >= 74: True
exact distances m=9 re-read: ok
problems: none
```

`--root <repo>/datasets/generated` gave the same last line. This re-runs the authors' oracle. Its completeness over
reduced words has not been independently checked (section 6).

## 3. Repository checks

From the repository root at `719ad17`, the tree this version was built on (this package changes nothing outside
its folder):

| command | observed |
|---|---|
| `python -m unittest discover -s tests -p 'test_*.py' -v` | `Ran 617 tests in 63.348s` / `OK (skipped=4)` |
| `python -m compileall -q src tests` | no output, exit 0 |
| `python -m src.lrx.cli smoke` | one JSON line ending `"passed": true, "visible_states": 12}`, exit 0 |

The scripts under `autoresearch/bound-m-260925/checks/` are the repository originals. Except for
`reversal_midband_search/mb.py`, the files of `checks/` here are byte-identical to them. `WORDC-PROOF.md`,
`WORDR1-PROOF.md` and `REVERSAL-CARRY.md` are copies of the notes in `autoresearch/bound-m-260925/`, `negcert/` of
`autoresearch/bound-m-260925/negcert/`, `checks-lemma1/` of `autoresearch/checks-lemma1/`, and the two LEMMA notes
of `autoresearch/LEMMA1-GENERAL-M-260926.md` and `autoresearch/LEMMA34-GENERAL-M-260926.md`. Each was compared
byte for byte with `git show HEAD:<path>` at `f163e74`, which does not differ from `719ad17` in these files. Inside the repository they also run as
`PYTHONPATH=. python autoresearch/bound-m-260925/checks/<script>.py`.

`checks/reversal_words.py` is the builder of REVERSAL-WORDS.md. It needs tables (4..11, 2) and numpy, imports
`src.lrx.table_bfs` and refuses to overwrite its JSON. It is not one of the re-checks that the runners run and is not covered by
`vendor/`.

## 3a. Optional checks, not run by the runners

These three need either the repository with its tables or several minutes. They were run for this version, with
the observed last lines below. Everything they check is finite.

| command | needs | observed last line | time |
|---|---|---|---|
| `python autoresearch/checks-lemma1/lemma1_tables_check.py` | repository root; tables (9,1)..(9,6), (10,2), (10,3); bound-campaign finalist rows | `RESULT: PASS (0 violations)` | 2.3 s |
| `python autoresearch/checks-lemma1/lemma34_tables_check.py` | same tables; imports `lemma1_tables_check.py` | `RESULT: PASS (0 violations)` | 12.7 s |
| `PYTHONPATH=vendor python negcert/validate_small.py` | no tables (BFS built in memory); vendored `lrx_m` | `VALIDATED` | 432 s (7.2 min, run beside other jobs) |

The two table checks locate the repository root two folders above their own and read the tables under
`datasets/generated/`, so they run from the repository; the copies in `checks-lemma1/` are byte-identical to the
repository files and are shipped for reading. Observed from the repository root with `PYTHONPATH` unset:
- `lemma1_tables_check.py`: 380 (family, word) pairs and 3,806 exact points with 0 violations; (7) at m = 9 on 146
  families and 1,637 block-length vectors with 0 violations.
- `lemma34_tables_check.py`: 4,555 stretched points and 90,923 comparator steps with 0 failures; the negative control
  fails to sort in all 540 cases; projection 3,766 child points and resource formula 980 zero atoms, 0 failures.

As the notes say, `d <= F` follows from "the lifted word sorts", so these tables cross-check the executor, the pricing
and the tables against each other. They are not an independent test of the lemmas beyond literal execution.

`validate_small.py` compares the negative checker with brute force priced by the vendored `lrx_m.Profile` at
m = 3..6. It was run from a package copy outside the repository with `PYTHONPATH=vendor` and exited 0; all 21
cases printed `ok`.

## 4. Tables (gitignored under datasets/generated/ in the repository, not shipped)

Only `reversal_midband.py --tables`, `reversal_words.py` and the two `checks-lemma1/` scripts need tables. Builder in the repository:
`tools.table_bfs_lowmem.build_table_lowmem(m, r, out_dir, workers)`, low memory, uses numpy, refuses to overwrite.
Its output is byte-identical to `src.lrx.table_bfs.build_table` plus `write_table`.

| table | recorded build time | builder, workers | sha256 (metadata `table_sha256`) |
|---|---|---|---|
| (9,2) | 12.6 s | in-memory, 10 | 8148ceab1f053d8e7431d4db188717ba30773cd9b6ea3e697eee57d9e337befd |
| (9,3) | 52 s | in-memory, 10 | 1f3a24f5d85fb295adfb9020416eaa43f5488115067f63da3286c631932daf1d |
| (9,4) | 298 s | in-memory, 10 | fc31a30e284298887425b73d9ebe714e1111f6001a8a5ce6672811bd12de8789 |
| (9,5) | 611 s | in-memory, 10 | f3465b5f24c9e997b72529c8341346bc310a205b35beefa6fda3de6d1d8a58cb |
| (9,6) | 1522 s | in-memory, 10 | 4f8cc2c236511a5f0fe3f7462c8a32180050132edca41ec567d4c892ddcee6dd |
| (10,2) | 409 s | low-memory, 4 | 3f9ad500d390e7e264a26f9bcbdba13c2bd90ca500352e8d4cd4d9ae6ea4563b |
| (11,2) | 11,511 s (3.2 h) | low-memory, 4 | 1c3f4915f4bea4e856d2eaed66f1c58caa4c7f43d896ae25e63475bc83192325 |

Example, from the repository root:

```
python -c "from tools.table_bfs_lowmem import build_table_lowmem as b; b(10, 2, 'datasets/generated/m10-r2-260926', workers=4)"
python -c "import json; print(json.load(open('datasets/generated/m10-r2-260926/dist_m10_r2.json'))['table_sha256'])"
```

## 5. External review

Two reviewers of the research group re-checked an earlier version of this package with their own stdlib checker.
Their summary is in FINDINGS.md section (h). The proof status after their review is in FINDINGS.md section (i). The
reviewers have not re-run the checks added in this version.

## 6. What these checks do not establish

Every certificate is conditional on the group's Lemma 1 and criteria (7)/(8) with m as a parameter. General-m
proofs of those statements, and of the word_C and word_R1 formulas, are now written, but by models, and no human
mathematician has reviewed them; the checks here are finite. word_G and word_M are unproved rules. The exact negative
rests on the completeness argument in the docstring of `negcert/negcert_check.py`, which the reviewers have not yet
checked. The radii and the
extremal-state counts rest on tables that are not shipped. The general conjecture remains open.
