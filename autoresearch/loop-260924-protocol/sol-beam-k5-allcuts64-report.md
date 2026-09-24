# One wider Sol beam follow-up: frozen development only

The [source](sol-beam-k5-allcuts64.py), SHA-256 `29df962327cba31c254964f34c8318e7d14b2652237abd7d676e756f5c41b271`, is a bounded Sol-authored follow-up to the narrower beam, not Grok/GEPA output. It tries all 13 cuts with width 64, ranks complete words globally by the maintained dual-weighted resource cost, retains one completion per cut for diversity, and includes the earlier verified word. The returned list is capped at 32.

The [strict Seatbelt development evaluation](sol-beam-k5-allcuts64-eval-01/29df962327cba31c-evaluation.json) completed all 16 cases; the unresolved k5 case accepted 32 words without a rejection in 0.503 seconds. Its best new direct profile has base `50`, slopes `[9,12,8,2,7]`, and exact old-pool reduced cost `-33/7`. The exact feasible mixture base improved from frozen incumbent `24149/392` to `1223/20`. It remains `3/20` above the strict threshold 61, so 15/16 certificates are inherited and there is **no new whole-family certificate**. The secondary score is `129723/3649280`.

The feasible mixture has slopes `[28/5,6,6,6,6]`. It strengthens the separate conditional inequality: for first block length \(\ell_1\ge2\), its surplus relative to the strict integer threshold is \(3/20-(2/5)(\ell_1-1)\le-1/4\). The unit-block case remains a miss. This is a development-set result and a Sol hypothesis; confirmation was not accessed.

The independent saved-output auditor checked the source hash, 423 fixed direct profiles, 32 accepted direct profiles, exact primal and dual diagnostics, 48 support profiles for inherited certificates, and 144 nonunit literal replays. The LP output is an exact feasible witness, not a separately certified global optimum. Audit command:

```sh
python autoresearch/loop-260924-protocol/audit-development.py --program autoresearch/loop-260924-protocol/sol-beam-k5-allcuts64.py --evaluation autoresearch/loop-260924-protocol/sol-beam-k5-allcuts64-eval-01/29df962327cba31c-evaluation.json
```
