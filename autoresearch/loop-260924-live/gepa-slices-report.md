# Post-hoc cap repair of first GEPA proposal

The original generated source is
`gepa-low/verified/evaluations/candidate-0020.py`, SHA-256
`4fc49ae8d742e6118602f1e9a08ea66f70a3a598a5ae245a7cbcf56175419499`.
It emits up to 56 words per case and fails the evaluator's 32-word cap. It is
an **invalid official proposal**. The following two derivative files were
tested only as bounded post-hoc orchestrator repairs; the original was not
edited. Neither repair is an official GEPA result.

| Repair | Source SHA-256 | Development certificates | New vs four-cut seed |
|---|---|---:|---:|
| `gepa-slice-0-32.py` | `1e3f8a59297cdff510b023ec6c87de199cfd2837078832b3901433f11f2ac359` | 14/16 | 0 |
| `gepa-slice-32-64.py` | `aef37006bb2fb775f4f7cecb84c14ae83e3dc36fc3bf8b0f32fb1b71d6bdf150` | 12/16 | 0 |

Both were evaluated once under strict macOS Seatbelt on the frozen 16
development cases. Artifacts are respectively
`gepa-slice-0-32-evaluation/1e3f8a59297cdff5-evaluation.json` and
`gepa-slice-32-64-evaluation/aef37006bb2fb775-evaluation.json`.
Independent artifact audits recomputed exact support resources and rational
mixtures and replayed 132 and 114 nonunit literal expansions. No confirmation
case or model call was used.

Neither repair changes the two hard-case LP minima from the fixed direct
catalog: `k5-mask302-order15713` remains 24149/392 (strict threshold 61),
and `k6-mask315-order31970` remains 1817/27 (strict threshold 67). For the
first slice, the minimum reduced costs of its generated words against the
old exact duals are 1135/49 (k5) and 55/9 (k6); for the second slice they
are 11873/196 and 260/9. All are positive, so these words cannot improve
the current finite-pool optima. This is no statement about ungenerated words
or infeasibility.

The separate deterministic all-cuts control reaches 15/16 on the same
development set. It was tried after live prompts began and remains a post-hoc
control, not a frozen baseline or paid-engine gain.
