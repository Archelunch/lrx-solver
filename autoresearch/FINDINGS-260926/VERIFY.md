# Offline verification recipe

No network, no provider calls, no generated code. This package is committed in the repository `lrx-lab` at commit
`8e6b8df`; FINDINGS.md, MANIFEST.md and this file all refer to that commit. Observed on 2026-09-26, macOS,
Python 3.12.8, on the working tree at `9c1cf30` plus this package's changes, which `8e6b8df` commits.

## 1. Self-contained re-checks (no repository, no tables, no numpy)

The package runs on its own. `vendor/` holds byte-identical copies of the 19 repository files the check scripts
import (`vendor/README.md` lists origin path, bytes and sha256). From the package root:

```
sh run_checks.sh        # POSIX; PYTHON=... selects the interpreter, default python3
python run_checks.py    # same steps, for Windows
```

Both set `PYTHONPATH` to `<package>/vendor` only and disable bytecode writes, so the package is left unchanged. They
run `reversal_k2.py`, `reversal_midband.py` (no tables) and `wordc_proof_check.py` in place. The last one checks
every intermediate claim of `WORDC-PROOF.md` against the literal execution of word_C at m = 9..40 and writes
nothing. `reversal_m13.py` and `reversal_orbit.py`
rebuild their JSON and refuse to overwrite it, so the runners copy `checks/` to a temporary `a/b/checks/`, delete
the two JSON files there, rebuild them, and compare with the stored JSON after dropping only the `seconds` field.
Exit status is 0 only if every step passes. A tampered stored JSON was observed to give exit 1.

Observed: the package was copied to a temporary directory outside the repository and run there with `PYTHONPATH`
unset (`cp -R autoresearch/FINDINGS-260926 $TMP/ && cd $TMP/FINDINGS-260926 && env -u PYTHONPATH sh run_checks.sh`):

```
package /private/tmp/claude-502/.../scratchpad/final2/FINDINGS-260926
python 3.12.8
$ python checks/reversal_k2.py
  re-checked 390 word_G rows and 150 stored rows in 2.3 s; problems: none
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
$ python a/b/checks/reversal_m13.py
  closed forms m=9..200 failures: []
  wrote a/b/checks/reversal-m13-words.json 2.5 s
  exit 0
$ python a/b/checks/reversal_orbit.py
  wrote a/b/checks/reversal-orbit-words.json 3.2 s
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
  closed forms m=9..200 failures: []
  wrote a/b/checks/reversal-m13-words.json 2.2 s
  wrote a/b/checks/reversal-orbit-words.json 2.4 s
  reversal-m13-words.json identical
  reversal-orbit-words.json identical
ALL CHECKS PASSED
```

`run_checks.sh` exited 0, and `run_checks.py` in the same copy exited 0. The same `run_checks.sh` also exited 0
under a fresh virtual environment without numpy (`import numpy` raises ModuleNotFoundError there). An earlier run of
the four scripts other than `wordc_proof_check.py` also passed under macOS `/usr/bin/python3` 3.9.6.

The plain midband run prints 14 rows, each with `CERTIFIED ... audit=(True, 'ok') replay=True`. `reversal_orbit.py`
also prints `R1 failures m=9..200: []` and `word_C length failures 0 beta failures [[6, 1, [4, 3]], ..., [60, 1,
[4, 3]]]` before its last line. The 28 "beta failures" are the expected a = 1, even-m exception (4,3), documented in
REVERSAL-ORBIT.md section 3.

What this re-runs: the literal replay, the Lemma 1 pricing, the exact LP and the independent audit of the stored rows,
and the mechanical check of the word_C proof, with the package's own copies of that code. The proof check is finite
(m = 9..40). The proof in `WORDC-PROOF.md` was written by a model and has not been reviewed by a human mathematician. It does not re-run the BFS tables, the A* oracle, or the campaigns.

## 2. Exact m=9 {0,4} negative (needs tables (9,2)..(9,6), no numpy)

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

Observed from the temporary copy, with `LRX_ROOT` set to the repository, in the numpy-free environment (1.4 s):

```
dual certificate m=9 {0,4}: witness B=54 beta=[7, 7], B+3beta0=75 (stored min 75)
exact oracle: min B + 3 beta_0 = 75 over all reduced words (8760 nodes); needed >= 74: True
exact distances m=9 re-read: ok
problems: none
```

`--root <repo>/datasets/generated` gave the same last line. This re-runs the authors' oracle. Its completeness over
reduced words has not been independently checked (section 6).

## 3. Repository checks

From the repository root at `8e6b8df`:

| command | observed |
|---|---|
| `python -m unittest discover -s tests -p 'test_*.py' -v` | `Ran 617 tests in 72.435s` / `OK (skipped=4)` |
| `python -m compileall -q src tests` | no output, exit 0 |
| `python -m src.lrx.cli smoke` | one JSON line ending `"passed": true, "visible_states": 12}`, exit 0 |

The scripts under `autoresearch/bound-m-260925/checks/` are the repository originals. Except for
`reversal_midband_search/mb.py`, the files of `checks/` here are byte-identical to them, and `WORDC-PROOF.md` is a
copy of `autoresearch/bound-m-260925/WORDC-PROOF.md`. Inside the repository they also run as
`PYTHONPATH=. python autoresearch/bound-m-260925/checks/<script>.py`.

`checks/reversal_words.py` is the builder of REVERSAL-WORDS.md. It needs tables (4..11, 2) and numpy, imports
`src.lrx.table_bfs` and refuses to overwrite its JSON. It is not one of the re-checks that the runners run and is not covered by
`vendor/`.

## 4. Tables (gitignored under datasets/generated/ in the repository, not shipped)

Only `reversal_midband.py --tables` and `reversal_words.py` need tables. Builder in the repository:
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

Two reviewers of the research group re-checked the previous version of this package with their own stdlib checker.
Their summary is in FINDINGS.md section (h).

## 6. What these checks do not establish

Every certificate is conditional on the group's Lemma 1 and criteria (7)/(8) with m as a parameter. The exact
negative rests on the oracle's completeness, which has not been independently checked. The radii and the
extremal-state counts rest on tables that are not shipped. The general conjecture remains open.
