# One Sol-authored beam constructor: frozen development only

This is one independent local hypothesis, not model output. [The source](sol-beam-k5.py), SHA-256 `5eebd52cd158f497ba0b609c23d9396b14c192d843f5df8fc5f707ec5418908b`, searches complete adjacent-inversion words for the unresolved k5 case. It keeps 16 partial words per cut across four fixed cuts, ranks them by dual-weighted accumulated rotation/swap resources and a one-step travel bound, and returns at most 32 complete words. It returns `[]` for the other 15 development cases; the trusted evaluator supplies their frozen incumbent profiles.

[Strict Seatbelt evaluation](sol-beam-k5-eval-01/5eebd52cd158f497-evaluation.json) completed all 16 cases without execution or format failures. The hard case accepted 23 words. Its strongest new direct profile is base `52`, slopes `[9,12,8,2,7]`, with exact reduced cost `-19/7` against the verified old-pool dual. The exact feasible five-profile mixture has weights `3/40`, `2/5`, `23/70`, `1/10` on fixed profiles and `27/280` on that new profile. Its slopes are `[28/5,6,6,6,6]`, and its base is `2147/35`. The frozen incumbent feasible base was `24149/392`, so the improvement is `513/1960`; the new base is still `12/35` above the strict threshold `61`.

Thus the result remains 15/16 development certificates, all inherited, with **zero new certificates**. The evaluator's secondary score is `60325/2057536` (combined score `0.02931904958163551`). The negative reduced cost and feasible mixture are exact diagnostics for this finite pool, not a proof of the missing family or of global LP optimality.

The independent saved-output auditor verified the source hash, 423 fixed direct profiles, 23 accepted words, exact mixture weights/base/slopes and reduced-cost diagnostic, 48 certificate support profiles, and 144 nonunit literal replays. The auditor read neither confirmation cases nor any model API. Audit command:

```sh
python autoresearch/loop-260924-protocol/audit-development.py --program autoresearch/loop-260924-protocol/sol-beam-k5.py --evaluation autoresearch/loop-260924-protocol/sol-beam-k5-eval-01/5eebd52cd158f497-evaluation.json
```
