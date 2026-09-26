# Vendored dependencies of the re-check scripts

Plain byte-identical copies of the repository files that `checks/reversal_k2.py`, `checks/reversal_midband.py`,
`checks/reversal_m13.py`, `checks/reversal_orbit.py` and `checks/reversal_midband_search/mb.py` import. The paths
below are both the origin path in the repository and the path under this folder. Each copy was checked
byte-identical to `git show 9c1cf30:<path>` when the package was built; the package is committed at `f99d129`,
which does not change these origin files. All 19 were compared again with `git show f163e74:<path>` for version 3
and are unchanged. The layout mirrors the repository because `integrations/lift_audit.py` locates the m=8 checker at
`../autoresearch/verify-m8-260924/checker/lrxm8.py` relative to its own folder.

The closure was found by running each script from a copy outside the repository with `PYTHONPATH` set to this
folder only and listing every loaded module that came from the repository. numpy is never imported on these paths,
including `reversal_midband.py --tables`. The checks added in version 3 were traced the same way:
`checks/wordr1_proof_check.py`, `checks/wordg_formula_check.py` and `checks/reversal_carry.py` load only files
already listed here (plus `checks/reversal_orbit.py`, `reversal_k2.py` and `reversal_m13.py` of the package), and
`negcert/negcert_check.py` loads nothing from the repository. No file was added. Nothing here is modified; the only edited file in the package is
`checks/reversal_midband_search/mb.py`, whose table root is now a parameter.

Use: `PYTHONPATH=<package>/vendor python checks/<script>.py`, or `run_checks.sh` / `run_checks.py` at the package
root. sha256 over file bytes.

| path (origin = copy) | bytes | why it is needed | sha256 |
|---|---|---|---|
| `autoresearch/verify-m8-260924/checker/lrxm8.py` | 18217 | stdlib m=8 checker, loaded by lift_audit with M = m | 193d522eaf7dd1ebedbf1c9edb8fe9504a7ace0ca10645ecba21bf2d5e9924ba |
| `integrations/__init__.py` | 0 | package marker | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| `integrations/bound3_audit.py` | 7340 | audit_claim, the independent audit; imported by all four scripts | 72f1de7661ec382da9e545d895a52e3afbc848615cb0a55950cc19cc47dad50f |
| `integrations/bound3_evaluator.py` | 25006 | score_output, evaluator with exact LP; imported by all four scripts | 5b184d55852a68d68b22f5b98e0218425e6253f874f605f3c3745b70bee1e48e |
| `integrations/bound3_task.py` | 5001 | imported by bound3_evaluator | f8f90a0be3d98443b7bfd1129669d21992b7823d558b972e7102b1e9ef220489 |
| `integrations/bound_evaluator.py` | 38582 | imported by bound3_evaluator | 368c92f60c6edda62c185867d8faf67a3f5ec6645ee64d1ef21395b01aa49775 |
| `integrations/bound_task.py` | 2485 | make_family; imported by all four scripts | f1ba35b7d20b8995d6901ca5c52dfd3dabf0931898e62e768fe38413a324e029 |
| `integrations/lift_audit.py` | 4311 | loads the m=8 checker below by path; imported by bound3_audit | e338e5391a1ce4551bacaabf7df1ce0c1eca99fc96d5ad0603288221f98b37bb |
| `integrations/lift_evaluator.py` | 19016 | gap_lp, mixture_lp, simplex; imported by the evaluators and by mb.py | e4fdd49aa2d2b291b374b48517fe30ffb4b925c7d09424b844bd5d0eac97489a |
| `integrations/lift_task.py` | 4861 | imported by bound_task and lift_evaluator | 9e8baf19f5641388ec2a7c410a9f6a4076faa3312e492c450ffa78ac2daa7f14 |
| `integrations/lrx_m.py` | 18685 | executor, Profile (Lemma 1 pricing), base_vector; imported by all four scripts and mb.py | e88b7da137964fb998e721a8fb4e6b320c10746887125fc0f208c4e5763659db |
| `integrations/mixture_lp.py` | 3695 | imported by program_evaluator | 62d6bff37c05e2e0dedebd34e3cc17ab533c86719a7f42f4ababaa73c1ace61d |
| `integrations/program_evaluator.py` | 29118 | imported by bound_evaluator and lift_evaluator | 79118e040faaa3b9380c73194ac3506c74fc79c45951ebfd84336c9dd8239713 |
| `integrations/program_sandbox.py` | 2727 | imported by the three evaluators | cbade932ca485fed52b5bd8847885bd3213c9fc48f9196bbbca357df12dac7e9 |
| `integrations/projected_mixtures.py` | 7070 | imported by program_evaluator | 781b3257e5b66c9eb7c034291ab05ddd816b9eb5e0f06504e5153ca3a2c7e633 |
| `src/lrx/__init__.py` | 92 | package marker | 712f9fa3ccab4d1e90e7529de582614a8b2bf130a726c0d9243d2e36d7f5c416 |
| `src/lrx/certificates.py` | 12939 | imported by program_evaluator | e029f82c4ab1b914420ce5158bd6922a42efe2e16e322a27da075030fd3f98aa |
| `src/lrx/state.py` | 4652 | imported by certificates | b3b818ddc0b6523220b1c358f236aa84e07a9c5b808aea6d9ddd00225652e7dd |
| `src/lrx/table_bfs.py` | 7561 | Ranker; imported only by mb.py (reversal_midband.py --tables) | abe5746ef2130507411f9aebe1c18663810c6badff050c3e112c1bb54157a476 |
