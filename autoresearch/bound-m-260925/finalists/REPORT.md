# bound-m-260925 finalists

Every CERTIFIED family (a,S) is a machine-checked bound d(v) <= T_m(n) for all its block lengths, conditional on the group's Lemma 1 and criterion (7) with m as a parameter. It says nothing about other families. A miss, crash or timeout proves nothing.

| arm | holdout certified (m=9/10/11) | holdout W (m=9/10/11) | dev certified (m=9/10) | beats (b) | audit disagreements | deterministic | m-literals |
|---|---|---|---|---|---|---|---|
| adaevolve | 127/111/100 | 5/2/4000/4000 | 114/119 | yes | 0 | True | 0 |
| evox | 108/119/129 | 5/2/17/7/4 | 94/118 | yes | 0 | False | 0 |
| gepa | 91/105/125 | 31/12/17/7/4 | 91/110 | yes | 0 | False | 0 |
| sequential | 124/114/109 | 95/91/4000/4000 | 109/121 | yes | 0 | True | 0 |
| naive-control | 0/0/0 | 211/264/319 | 0/0 | no | 0 | True | 0 |
| sweep16-control | 61/57/60 | 43/8/37/6/8 | 51/60 | no | 0 | True | 0 |
| sweeplp-control-b | 76/84/98 | 17/5/305/62/7 | 66/85 | no | 0 | - | 0 |

An engine claims progress only if it beats control (b) on the holdout (strictly more certified).

