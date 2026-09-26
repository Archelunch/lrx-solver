# Offline verification recipe

No network, no provider calls, no generated code. Observed on 2026-09-26, commit `6e56ddf`, macOS, Python 3.12.8.

## 1. Setup

```
git clone <lrx-lab> && cd lrx-lab          # all commands run from the repository root
python --version                            # 3.12.x; runtime is stdlib, numpy only for the table builders
```

This folder is committed after `6e56ddf`. The scripts under `autoresearch/bound-m-260925/checks/` are tracked and
byte-identical to `checks/` here.

## 2. Repository checks (no tables)

| command | observed |
|---|---|
| `python -m unittest discover -s tests -p 'test_*.py' -v` | `Ran 617 tests in 63.827s` / `OK (skipped=4)` |
| `python -m compileall -q src tests` | no output, exit 0 |
| `python -m src.lrx.cli smoke` | one JSON line ending `"passed": true, "visible_states": 12}`, exit 0 |

## 3. Re-check scripts

Two scripts only re-check stored rows and write nothing:

```
PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_k2.py                   # 2.6 s, no tables
PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_midband.py              # 0.1 s, no tables
PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_midband.py --tables     # 1.0 s, tables (9,2)..(9,6)
```

Observed last lines:

```
re-checked 390 word_G rows and 150 stored rows in 2.3 s; problems: none
problems: none
exact oracle: min B + 3 beta_0 = 75 over all reduced words (8760 nodes); needed >= 74: True
exact distances m=9 re-read: ok
problems: none
```

The plain midband run prints 14 rows, each with `CERTIFIED ... audit=(True, 'ok') replay=True`. Before `problems:
none` it prints `dual certificate m=9 {0,4}: witness B=54 beta=[7, 7], B+3beta0=75 (stored min 75)`.
`--tables` imports `checks/reversal_midband_search/mb.py`, whose line 11 hard-codes the repository root as
`/Users/pavluhin/Documents/Projects/lrx-lab`. In a clone at any other path, edit that line first.

Two scripts rebuild their JSON and refuse to overwrite an existing file. Re-run them on a copy and compare:

```
REPO=$(pwd); W=$(mktemp -d); mkdir -p $W/a/b
cp -R autoresearch/FINDINGS-260926/checks $W/a/b/
rm $W/a/b/checks/reversal-m13-words.json $W/a/b/checks/reversal-orbit-words.json
(cd $W && PYTHONPATH=$REPO python a/b/checks/reversal_m13.py | tail -2)      # about 2 s
(cd $W && PYTHONPATH=$REPO python a/b/checks/reversal_orbit.py | tail -3)    # about 2.4 s, imports reversal_m13
python - "$W" <<'EOF'
import json, sys
for n in ['reversal-m13-words.json', 'reversal-orbit-words.json']:
    a = json.load(open('autoresearch/FINDINGS-260926/checks/' + n)); b = json.load(open(sys.argv[1] + '/a/b/checks/' + n))
    a.pop('seconds'); b.pop('seconds'); print(n, 'identical' if a == b else 'DIFFERENT')
EOF
```

Observed:

```
closed forms m=9..200 failures: []
wrote a/b/checks/reversal-m13-words.json 2.2 s
R1 failures m=9..200: []
word_C length failures 0 beta failures [[6, 1, [4, 3]], [8, 1, [4, 3]], ..., [60, 1, [4, 3]]]
wrote a/b/checks/reversal-orbit-words.json 2.4 s
reversal-m13-words.json identical
reversal-orbit-words.json identical
```

The 28 "beta failures" are the expected a = 1, even-m exception (4,3), documented in REVERSAL-ORBIT.md section 3.
Only the timing field differs from the stored JSON.

`checks/reversal_words.py` is the builder of REVERSAL-WORDS.md. It needs tables (4..11, 2) and refuses to overwrite
its JSON. It is not one of the four re-checks.

## 4. Tables (gitignored under datasets/generated/)

Only `reversal_midband.py --tables` and `reversal_words.py` need tables. Builder:
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

Example:

```
python -c "from tools.table_bfs_lowmem import build_table_lowmem as b; b(10, 2, 'datasets/generated/m10-r2-260926', workers=4)"
python -c "import json; print(json.load(open('datasets/generated/m10-r2-260926/dist_m10_r2.json'))['table_sha256'])"
```

`mb.py` looks for tables in `datasets/generated` and in its subfolders `outer-layer-260925`, `sort-m9-260925`,
`m10-r2-260926` and `m11-260925`.

## 5. What these checks do not establish

Every certificate is conditional on the group's Lemma 1 and criteria (7)/(8) with m as a parameter. The exact
negative rests on the oracle's completeness. The general conjecture remains open.
