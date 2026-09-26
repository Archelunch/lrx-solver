---
name: lrx-table
description: Build or look up an exact LRX distance table for (m, r) - pick the in-memory or low-memory builder, run sanity checks, store it under datasets/generated, record its sha256. Use when a claim needs exact distances or a radius.
---

# lrx-table

Tables hold one byte per visible state (distance from the sorted root);
there are `n!/r!` states with `n = m + r`. Files: `dist_m{m}_r{r}.bin` and a
`.json` sidecar with `radius`, `layer_sizes`, `complete`, `table_sha256`.

## 1. Look it up first

```sh
find datasets/generated -name 'dist_m*_r*.json'
```

Existing tables (2026-09-26): registry tables in `datasets/generated/`;
(8,1), (8,4..6), (9,1), (9,4), (9,5) in `outer-layer-260925/`; (9,6), (10,3)
in `sort-m9-260925/`; (10,2) in `m10-r2-260926/`; (11,2) in `m11-260925/`.
Their hashes are in `research/claims.md` (Sessions 13, 18, 19).

```python
from src.lrx.table_bfs import DistanceTable        # checks sha256, refuses incomplete tables
t = DistanceTable('datasets/generated/m11-260925', 11, 2)
t.radius, t.distance(v)
```

## 2. Build

Pick by size (`math.perm(m + r, m)` states):

| states | builder | command |
|---|---|---|
| registry set | in-memory | `python -m src.lrx.cli table build-registry --workers 8` |
| fits in RAM at about 5 bytes per state (default cap 2 GiB, about 430 million states; raise with `--max-bytes`) | in-memory | `python -m src.lrx.cli table build M R --out datasets/generated/<name>-<yymmdd> --workers 8 --max-bytes B` |
| does not fit | low-memory, numpy memmaps on disk | see below |

```sh
python -c "from tools.table_bfs_lowmem import build_table_lowmem as b; \
m = b(M, R, 'datasets/generated/<name>-<yymmdd>', workers=4); print(m['radius'], m['table_sha256'])"
```

Both builders give byte-identical files and refuse to overwrite. Recorded
low-memory times with 4 workers: (10,2) 409 s; (11,2) 3.2 h for 3.1 billion
states. Free disk must exceed the table size plus frontier bitmaps. (12,2),
about 4.4e10 states, is out of reach here. A build longer than a few minutes
is a long job: say so and get approval before starting.

## 3. Sanity checks before use

- `complete` is true and `reached == states`.
- `sum(layer_sizes) == states`; radius = `len(layer_sizes) - 1`.
- `DistanceTable(...)` loads without a hash error.
- Extracted shortest words replay with `integrations.lrx_m.run_naive`.
- For a new large table also sample the triangle inequality under L, R, X
  (claims Session 18 used 20,000 states).
- Compare the radius with `T_m(n) = m(m+1)/2 + (r-1)(m-2)` and report both.

## 4. Record, never commit

- `datasets/generated/` is gitignored. Never `git add -f` a table.
- Put the sha256, state count, radius, builder, workers and wall time in the
  claims Session entry (see lrx-claims).
- An interrupted or refused build is INCOMPLETE. It proves nothing about the
  radius and is never recorded as infinity.
