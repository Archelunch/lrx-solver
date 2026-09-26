# Manifest, autoresearch/FINDINGS-260926 (2026-09-26)

Package committed at `PINNED_COMMIT`, the commit FINDINGS.md and VERIFY.md also name. sha256 computed over file bytes.
Total files: 51, not counting this manifest.

| file | bytes | description | sha256 |
|---|---|---|---|
| `BEST-C2-CONSTRUCTION.md` | 14206 | What the campaign-2 evolved finalists changed relative to the seed | bf8ebfb224022dead25138804368c8c08617f1fe4f774d2fa1faa09c40056fdd |
| `CLAIMS-SESSIONS-10-23.md` | 29031 | Verbatim excerpt of research/claims.md, Sessions 10 to 23 | 116c6f7071737b69abe917424fd2c9a3c6e9c89e632a96b8c06518c04615c916 |
| `FINDINGS.md` | 47330 | Main findings report (RU summary, exact results, conditional certificates with generator source, proof sketch, engine results, conjectures, requests, verification) | 831a9c4e7a79135289ff5f687dbff0d4e097e76adb808a01d698e3b4e359be4d |
| `REPORT-FOR-AGENTS-260926.md` | 13537 | Status report for collaborating agents (2026-09-26) | b403983786367802511e11a4540927c8242e3916f8a601a0d5e239c68ad16784 |
| `REVERSAL-K2.md` | 11713 | word_G closed form for the outer band of k=2 masks; root survey to m=13 | bc1225978e69081727338d57d44155c99a8bc86611765a9e1cc6c4424b62c574 |
| `REVERSAL-M13.md` | 12744 | Two-core word_C: closed-form certificate of (m..1){0,m} at m=9..40 | 23ea45be60591bc647291efecb324363ae7012811551c574dd2e1b0011086fcd |
| `REVERSAL-MIDBAND.md` | 12602 | Middle band mined from exact tables; exact negative for m=9 {0,4}; word_S | 77a5b280133bdb558bbac169469fe0f99e03039bfc15fe07f1029cbb8ddfef64 |
| `REVERSAL-OBSTACLE.md` | 11426 | Why the reversal orbit blocked the engines; addenda on the (11,2) table | d6c9651fd79c22065e9f8f73a62ccd9e632b8b5ce703ca7e6f9034812dac5fb2 |
| `REVERSAL-ORBIT.md` | 21758 | Insertion-core generator, word_R1, 111 certified families, proof sketch of word_C | 412d9aaf9f65c6d985d1c67b8fd0a8c0c0e1ebff49baecca2b0dc36ac02fab54 |
| `REVERSAL-WORDS.md` | 15963 | Shortest words for (0,m..1,0) at m=8..11; generators word_E/A/B; certificates to m=12 | b159a4eedd280df4be6b310d5f61efa062735bdcff53a49b3dd277fa32b03080 |
| `VERIFY.md` | 8678 | Offline verification recipe with observed outputs and table hashes | 31cc9d27f5da85683fab69211c80f8e70b1775b312cc1511e8c509120a86097d |
| `WORDC-PROOF.md` | 27980 | Proof of the word_C length and Lemma 1 slope formulas, all m >= 3, both parities (model-written, not yet human-reviewed) | b844bead4eaf8ac8caa0f9e00992b66e30f7c14070b2be38a8b5262368e544a1 |
| `bound-c1-finalists-REPORT.md` | 1068 | Bound campaign 1 finalize report (holdout m=11) | 7149dabebd7dca954489cca8d9eb1bc6ea84536cb622e05a28044ad4b71edb48 |
| `bound-c2-finalists-REPORT.md` | 3003 | Bound campaign 2 finalize report (holdout m=12, three seeds) | 0a74d2be61a5a3089ec9e449ed88bac4179d39a00715d61e1518b8d543831bfd |
| `checks/m11-r2-reversal-words.json` | 684 | A shortest 74-letter word for (0,11,...,1,0) | a2ea038fbebc7f4f3fe17c41a141adefe7f4791010171c89ee5400b54bcdb686 |
| `checks/reversal-k2-words.json` | 668734 | word_G rows at m=9..80 plus the 150 stored survey and tree certificates | 7ae8b587aff84b6e4a6c0162632db3149e1c19e041465c3c1263e8576bf626e9 |
| `checks/reversal-m13-words.json` | 76657 | word_C certificates at m=9..40 and closed-form replay to m=200 | 48e41d713493879664a486e17196a0199616c3a8c11a71ef5486a025ab610901 |
| `checks/reversal-midband-words.json` | 65670 | Middle-band certificates, word_S parameters, exact distances and the dual certificate | 811234bfc3c067906958c62f83d2f1d4ef00bad3855c9fa2d357e11b6952a324 |
| `checks/reversal-orbit-words.json` | 145058 | The 111 stored certificates, word_R1 rows and word_C closed-form checks | 88be9d8943f7f03ad5e8deb3f28427ca1a2ad29108b8687d82f710132b113059 |
| `checks/reversal-words-m8-11.json` | 258004 | All shortest words at m=4..11, generator words, rotation distances and radius states | 083d94d0acf28e83a810122a8f0a3f9408c584d7e4ab9c93190c18a243c67e4e |
| `checks/reversal_k2.py` | 12320 | word_G rules; re-checks 390 word_G rows and 150 stored rows | 274f994ee898494bdf09ee4d34387444ec204c973e727a4aa3a67399638d7488 |
| `checks/reversal_m13.py` | 7991 | word_C generator; rebuilds and scores reversal-m13-words.json | 24f4eede0ab857aaa6a2cb0869d028829963974ef18387228a518239c9a17f3f |
| `checks/reversal_midband.py` | 7948 | word_S; re-checks 14 certificates and the m=9 {0,4} negative | 7159c30f1ac93eb5c697ebe8ab23dd3a64256e579b52999e314505b08a4bcffd |
| `checks/reversal_midband_search/mb.py` | 14639 | Exact A* oracle that reversal_midband.py --tables imports; table root from --root, LRX_ROOT, the package tables/ dir or the repository datasets/generated (the repository original hard-codes it) | 5a6bac61c2154e224fb333563a051662488fa64f0e625f721dc05a3d12ad8aae |
| `checks/reversal_orbit.py` | 11116 | core_word and word_R1; re-scores the 111 stored certificates and checks the word_C closed forms | 0a1344900a43ed38e879f9a7d89b1e63cf32605fc353f5ad76662f44bafe16d4 |
| `checks/reversal_orbit_search/k2-m9-10-results.json` | 64128 | Stored k=2 search results at m=9 and 10, read by reversal_orbit.py | 07c04cb423776300434b9f4a12fe9203b19897001fbe5569d66c5fc6f3f4d0fd |
| `checks/reversal_orbit_search/regen-results.jsonl` | 11569 | Regenerated fixed-m certificates, read by reversal_orbit.py | 25a8ea8cc3d1b389024be5f1040792b1478c098bb7df51ce350a7d237c2a325c |
| `checks/reversal_words.py` | 9924 | Builder behind REVERSAL-WORDS.md; needs tables and refuses to overwrite | 09b66219738ba0f5809b1dccb6a8e78d23c1f67abda4fe14808950a5593b7b0c |
| `checks/wordc_proof_check.py` | 11742 | Mechanical check of every claim of WORDC-PROOF.md against literal word_C at m = 9..40; writes nothing | 6b418051659344ddb0f8288777efc4aeddea782c65a7a67eeb015813a27ce5af |
| `run_checks.py` | 3350 | Same as run_checks.sh, for Windows | 7cad13e4d07729950b3d38ab37e600f2b8426edc00daf45386d9e0936762e492 |
| `run_checks.sh` | 2645 | Runs the five re-checks with vendor/ only (POSIX shell); prints the expected last lines | 153d0ac1a798e81a994e82435b08606aef3d601ac3ae64edce00cfc3268c7987 |
| `vendor/README.md` | 4281 | Origin path, bytes and sha256 of every vendored file, and how the closure was found | 30e81f86dde959677f25fb4bcb56000e181083515a5a46ecc0c38793c4edcd4f |
| `vendor/autoresearch/verify-m8-260924/checker/lrxm8.py` | 18217 | Vendored byte-identical copy of `autoresearch/verify-m8-260924/checker/lrxm8.py` (see vendor/README.md) | 193d522eaf7dd1ebedbf1c9edb8fe9504a7ace0ca10645ecba21bf2d5e9924ba |
| `vendor/integrations/__init__.py` | 0 | Vendored byte-identical copy of `integrations/__init__.py` (see vendor/README.md) | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| `vendor/integrations/bound3_audit.py` | 7340 | Vendored byte-identical copy of `integrations/bound3_audit.py` (see vendor/README.md) | 72f1de7661ec382da9e545d895a52e3afbc848615cb0a55950cc19cc47dad50f |
| `vendor/integrations/bound3_evaluator.py` | 25006 | Vendored byte-identical copy of `integrations/bound3_evaluator.py` (see vendor/README.md) | 5b184d55852a68d68b22f5b98e0218425e6253f874f605f3c3745b70bee1e48e |
| `vendor/integrations/bound3_task.py` | 5001 | Vendored byte-identical copy of `integrations/bound3_task.py` (see vendor/README.md) | f8f90a0be3d98443b7bfd1129669d21992b7823d558b972e7102b1e9ef220489 |
| `vendor/integrations/bound_evaluator.py` | 38582 | Vendored byte-identical copy of `integrations/bound_evaluator.py` (see vendor/README.md) | 368c92f60c6edda62c185867d8faf67a3f5ec6645ee64d1ef21395b01aa49775 |
| `vendor/integrations/bound_task.py` | 2485 | Vendored byte-identical copy of `integrations/bound_task.py` (see vendor/README.md) | f1ba35b7d20b8995d6901ca5c52dfd3dabf0931898e62e768fe38413a324e029 |
| `vendor/integrations/lift_audit.py` | 4311 | Vendored byte-identical copy of `integrations/lift_audit.py` (see vendor/README.md) | e338e5391a1ce4551bacaabf7df1ce0c1eca99fc96d5ad0603288221f98b37bb |
| `vendor/integrations/lift_evaluator.py` | 19016 | Vendored byte-identical copy of `integrations/lift_evaluator.py` (see vendor/README.md) | e4fdd49aa2d2b291b374b48517fe30ffb4b925c7d09424b844bd5d0eac97489a |
| `vendor/integrations/lift_task.py` | 4861 | Vendored byte-identical copy of `integrations/lift_task.py` (see vendor/README.md) | 9e8baf19f5641388ec2a7c410a9f6a4076faa3312e492c450ffa78ac2daa7f14 |
| `vendor/integrations/lrx_m.py` | 18685 | Vendored byte-identical copy of `integrations/lrx_m.py` (see vendor/README.md) | e88b7da137964fb998e721a8fb4e6b320c10746887125fc0f208c4e5763659db |
| `vendor/integrations/mixture_lp.py` | 3695 | Vendored byte-identical copy of `integrations/mixture_lp.py` (see vendor/README.md) | 62d6bff37c05e2e0dedebd34e3cc17ab533c86719a7f42f4ababaa73c1ace61d |
| `vendor/integrations/program_evaluator.py` | 29118 | Vendored byte-identical copy of `integrations/program_evaluator.py` (see vendor/README.md) | 79118e040faaa3b9380c73194ac3506c74fc79c45951ebfd84336c9dd8239713 |
| `vendor/integrations/program_sandbox.py` | 2727 | Vendored byte-identical copy of `integrations/program_sandbox.py` (see vendor/README.md) | cbade932ca485fed52b5bd8847885bd3213c9fc48f9196bbbca357df12dac7e9 |
| `vendor/integrations/projected_mixtures.py` | 7070 | Vendored byte-identical copy of `integrations/projected_mixtures.py` (see vendor/README.md) | 781b3257e5b66c9eb7c034291ab05ddd816b9eb5e0f06504e5153ca3a2c7e633 |
| `vendor/src/lrx/__init__.py` | 92 | Vendored byte-identical copy of `src/lrx/__init__.py` (see vendor/README.md) | 712f9fa3ccab4d1e90e7529de582614a8b2bf130a726c0d9243d2e36d7f5c416 |
| `vendor/src/lrx/certificates.py` | 12939 | Vendored byte-identical copy of `src/lrx/certificates.py` (see vendor/README.md) | e029f82c4ab1b914420ce5158bd6922a42efe2e16e322a27da075030fd3f98aa |
| `vendor/src/lrx/state.py` | 4652 | Vendored byte-identical copy of `src/lrx/state.py` (see vendor/README.md) | b3b818ddc0b6523220b1c358f236aa84e07a9c5b808aea6d9ddd00225652e7dd |
| `vendor/src/lrx/table_bfs.py` | 7561 | Vendored byte-identical copy of `src/lrx/table_bfs.py` (see vendor/README.md) | abe5746ef2130507411f9aebe1c18663810c6badff050c3e112c1bb54157a476 |
