# bound-m-c2-260925 finalists

Every CERTIFIED family (a,S) is a machine-checked bound d(v) <= T_m(n) for all its block lengths, conditional on the group's Lemma 1 and criterion (7) with m as a parameter. A miss, crash or timeout proves nothing. Finalists were chosen by validation (c1 holdout m=11) only; the holdout (m=12 and fresh m=11) was evaluated once after freeze. Gap = development certified % minus holdout certified %.

## Per arm (one finalist per seed)

| arm | n | validation % mean (SD) [min, max] | holdout % mean (SD) [min, max] | gap mean (SD) |
|---|---|---|---|---|
| gepa | 3 | 80.2 (3.5) [78.2, 84.2] | 80.3 (0.5) [80.0, 80.9] | -8.6 (2.5) |
| sequential | 3 | 79.8 (6.3) [72.7, 84.8] | 76.4 (6.9) [68.4, 80.9] | -2.4 (6.6) |
| adaevolve | 3 | 87.3 (3.8) [84.2, 91.5] | 84.7 (4.4) [81.8, 89.8] | -4.3 (0.3) |
| evox | 3 | 86.7 (2.2) [84.8, 89.1] | 83.1 (0.8) [82.7, 84.0] | -5.0 (1.3) |

## Per finalist and control

| key | candidates | validation % | dev % | holdout % | holdout C/N per m | gap | incomplete | audit disagreements | deterministic | m-literals | finalist is seed | run pool dev certified |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| adaevolve-s1 | 12 | 86.1 | 78.2 | 82.7 | m11:53/60 m12:133/165 | -4.4 | 0 | 0 | True | 0 | False | 249 |
| adaevolve-s2 | 10 | 91.5 | 85.8 | 89.8 | m11:54/60 m12:148/165 | -4.0 | 0 | 0 | True | 0 | False | 263 |
| adaevolve-s3 | 4 | 84.2 | 77.2 | 81.8 | m11:52/60 m12:132/165 | -4.6 | 0 | 0 | True | 0 | False | 234 |
| evox-s1 | 12 | 86.1 | 78.9 | 82.7 | m11:52/60 m12:134/165 | -3.8 | 0 | 0 | True | 0 | False | 240 |
| evox-s2 | 8 | 84.8 | 76.2 | 82.7 | m11:52/60 m12:134/165 | -6.4 | 0 | 0 | True | 0 | False | 236 |
| evox-s3 | 13 | 89.1 | 79.2 | 84.0 | m11:52/60 m12:137/165 | -4.8 | 0 | 0 | True | 0 | False | 249 |
| gepa-s1 | 2 | 78.2 | 70.0 | 80.0 | m11:51/60 m12:129/165 | -10.0 | 0 | 0 | True | 0 | True | 244 |
| gepa-s2 | 2 | 78.2 | 70.0 | 80.0 | m11:51/60 m12:129/165 | -10.0 | 0 | 0 | True | 0 | True | 242 |
| gepa-s3 | 2 | 84.2 | 75.2 | 80.9 | m11:52/60 m12:130/165 | -5.6 | 0 | 0 | True | 0 | False | 229 |
| sequential-s1 | 9 | 81.8 | 74.9 | 80.9 | m11:51/60 m12:131/165 | -6.0 | 0 | 0 | True | 0 | False | 257 |
| sequential-s2 | 7 | 84.8 | 73.6 | 80.0 | m11:48/60 m12:132/165 | -6.4 | 0 | 0 | True | 0 | False | 237 |
| sequential-s3 | 15 | 72.7 | 73.6 | 68.4 | m11:45/60 m12:109/165 | 5.2 | 27 | 0 | True | 0 | False | 245 |
| naive | 0 | 0.0 | 0.0 | 0.0 | m11:0/60 m12:0/165 | 0.0 | 0 | 0 | True | 0 | None | - |
| sweeplp-b | 0 | 59.4 | 49.8 | 59.6 | m11:39/60 m12:95/165 | -9.7 | 0 | 0 | None | 0 | None | - |
| gepa-c1 | 0 | 74.5 | 67.7 | 72.9 | m11:47/60 m12:117/165 | -5.2 | 0 | 0 | True | 0 | None | - |
| seed-evox-c1 | 0 | 78.2 | 70.0 | 80.0 | m11:51/60 m12:129/165 | -10.0 | 0 | 0 | True | 0 | None | - |

An arm claims progress only if its mean holdout certified % over seeds beats both control (b) (sweeplp-b) and the seed (seed-evox-c1); single-seed wins are reported, not claimed.
