# Manifest, autoresearch/FINDINGS-260926 (2026-09-26)

sha256 computed over file bytes. Total files: 27.

| file | bytes | description | sha256 |
|---|---|---|---|
| `BEST-C2-CONSTRUCTION.md` | 14206 | What the campaign-2 evolved finalists changed relative to the seed | bf8ebfb224022dead25138804368c8c08617f1fe4f774d2fa1faa09c40056fdd |
| `CLAIMS-SESSIONS-10-23.md` | 29031 | Verbatim excerpt of research/claims.md, Sessions 10 to 23 | 116c6f7071737b69abe917424fd2c9a3c6e9c89e632a96b8c06518c04615c916 |
| `FINDINGS.md` | 39686 | Main findings report (RU summary, exact results, conditional certificates with generator source, proof sketch, engine results, conjectures, requests, verification) | 157c9dc3444fee99e53322137c4a4e96793d0c7718ca2b3d6937dda7d8761213 |
| `REPORT-FOR-AGENTS-260926.md` | 13537 | Status report for collaborating agents (2026-09-26) | b403983786367802511e11a4540927c8242e3916f8a601a0d5e239c68ad16784 |
| `REVERSAL-K2.md` | 11713 | word_G closed form for the outer band of k=2 masks; root survey to m=13 | bc1225978e69081727338d57d44155c99a8bc86611765a9e1cc6c4424b62c574 |
| `REVERSAL-M13.md` | 12744 | Two-core word_C: closed-form certificate of (m..1){0,m} at m=9..40 | 23ea45be60591bc647291efecb324363ae7012811551c574dd2e1b0011086fcd |
| `REVERSAL-MIDBAND.md` | 12602 | Middle band mined from exact tables; exact negative for m=9 {0,4}; word_S | 77a5b280133bdb558bbac169469fe0f99e03039bfc15fe07f1029cbb8ddfef64 |
| `REVERSAL-OBSTACLE.md` | 11426 | Why the reversal orbit blocked the engines; addenda on the (11,2) table | d6c9651fd79c22065e9f8f73a62ccd9e632b8b5ce703ca7e6f9034812dac5fb2 |
| `REVERSAL-ORBIT.md` | 21758 | Insertion-core generator, word_R1, 111 certified families, proof sketch of word_C | 412d9aaf9f65c6d985d1c67b8fd0a8c0c0e1ebff49baecca2b0dc36ac02fab54 |
| `REVERSAL-WORDS.md` | 15963 | Shortest words for (0,m..1,0) at m=8..11; generators word_E/A/B; certificates to m=12 | b159a4eedd280df4be6b310d5f61efa062735bdcff53a49b3dd277fa32b03080 |
| `VERIFY.md` | 5250 | Offline verification recipe with observed outputs and table hashes | f0d0ecac844258db0db7fe7997657ba28b281e74ce769f2fa7def041d29f6435 |
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
| `checks/reversal_midband_search/mb.py` | 13605 | Exact A* oracle that reversal_midband.py --tables imports; line 11 hard-codes the repository root | 83bfe903e6bb133ab433e9dec94b3ecb2eeb61db3f6b92ba128c2d8c255a2d3e |
| `checks/reversal_orbit.py` | 11116 | core_word and word_R1; re-scores the 111 stored certificates and checks the word_C closed forms | 0a1344900a43ed38e879f9a7d89b1e63cf32605fc353f5ad76662f44bafe16d4 |
| `checks/reversal_orbit_search/k2-m9-10-results.json` | 64128 | Stored k=2 search results at m=9 and 10, read by reversal_orbit.py | 07c04cb423776300434b9f4a12fe9203b19897001fbe5569d66c5fc6f3f4d0fd |
| `checks/reversal_orbit_search/regen-results.jsonl` | 11569 | Regenerated fixed-m certificates, read by reversal_orbit.py | 25a8ea8cc3d1b389024be5f1040792b1478c098bb7df51ce350a7d237c2a325c |
| `checks/reversal_words.py` | 9924 | Builder behind REVERSAL-WORDS.md; needs tables and refuses to overwrite | 09b66219738ba0f5809b1dccb6a8e78d23c1f67abda4fe14808950a5593b7b0c |
