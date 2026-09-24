# A new confirmed six-block family relative to the frozen controls

The held-out case `k6-mask221-order731` has visible labels `(1,3,2,4,6,8,7,5)` and retained gaps `0,2,3,4,6,7`. Its states have the cyclic form

\[
0^a\,1\,3\,0^b\,2\,0^c\,4\,0^d\,6\,8\,0^e\,7\,0^f\,5,
\qquad a,b,c,d,e,f\ge1.
\]

The one-shot [independent audit receipt](independent-audit.json) records three exact direct-word profiles. The first two are materialized and repriced fixed-catalog words; the third came from the complete Grok response that the broker rejected for the native GEPA run. The verifier executed that saved source separately under macOS Seatbelt on the frozen confirmation set. The exact support is:

| Origin | Weight | Base | Slopes | Complete unit word |
| --- | ---: | ---: | --- | --- |
| Catalog | `3/19` | 48 | `[4,8,11,9,3,0]` | `LLXRXLLXLXRXRXRRRXLXLXLXLXLXLXLLXLXLLXRXRXRRRRRR` |
| Catalog | `9/19` | 76 | `[7,1,2,5,11,9]` | `XRRXRXRRXRXLLXLLLXRXRXRRXLXLLXLLLXRXRXRXRXRRXRRRXLXLXLLXLLLLLLLLXLXLXLXLLXRR` |
| Broker-rejected Grok | `7/19` | 61 | `[5,11,9,6,0,3]` | `RXLXLXLXRXRXRRRXLXLXLXLXLXLXRXRXLLLLXRXRXLLLLXLXRRXLXRRXRRRRR` |

Exact rational recomputation gives weighted base \(1255/19=66+1/19<67\) and slopes

\[
\left(\frac{110}{19},\frac{110}{19},6,6,\frac{108}{19},\frac{102}{19}\right)\le(6,6,6,6,6,6).
\]

For \(n=8+a+b+c+d+e+f\), put \(d_j=\ell_j-1\). The general direct-word triangle expansion bounds each support word at arbitrary positive lengths by its base plus \(\sum_j\gamma_jd_j\). Their weighted average is at most \(1255/19+6\sum_jd_j<67+6\sum_jd_j\). At least one expanded word therefore has integer length at most \(66+6\sum_jd_j=6n-18\). This proves the stated upper bound for **all positive six-block lengths in this arrangement**, subject to the general direct-word expansion argument; it does not prove the main LRX conjecture.

The separate [read-only auditor](../audit-confirmation-one-shot.py) checks frozen source and result hashes, the three words' direct resources and unit replay, exact support weights/base/slopes, and three literal nonunit expansions per support word. Across all three confirmation arms it checked 252 fixed profiles, 843 accepted words, 117 support profiles, and 351 literal expansions. The [selection](selection-frozen.json) and [run receipts](run-receipts.json) show this was a single consumed 16-case confirmation with no subsequent model access.

For a precise finite-pool comparison, the catalog plus deterministic all-cuts pool has 29 direct columns for this case. An exact dual with nonnegative slope multipliers \((0,0,1,59/12,1/12,0)\) and intercept \(207/2\) has nonnegative reduced cost on every old column and gives lower bound \(135/2=67.5>67\). Thus that frozen pool cannot satisfy the universal six-slope mixture criterion. The new Grok word has reduced cost \(-4\) against this dual and permits the certificate above. This is novelty **relative to those frozen controls only**; it is not a literature novelty claim and was not accepted by the live GEPA run; the same source text was separately accepted in a zero-provider offline native GEPA replay.
