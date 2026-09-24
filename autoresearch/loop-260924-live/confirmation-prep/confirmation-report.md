# Frozen one-shot confirmation, 2026-09-24

Root froze the [selection](selection-frozen.json) after model traffic ended. The same eight frozen confirmation families and direct fixed-catalog baseline were evaluated once for each of five source snapshots under macOS Seatbelt. No confirmation feedback was sent to any model or optimizer. The [run receipts](results/run-receipts.json) and [independent exact audit](confirmation-audit.json) retain the complete evidence; [audit-confirmation.py](audit-confirmation.py) checks saved output without executing candidate code again.

| Arm | Attribution | Exact certificates | New over catalog | Candidate executions |
| --- | --- | ---: | ---: | --- |
| Fixed catalog only | control | 6/8 | 0 | 8/8 `ok` |
| Original four-cut seed `c27df808` | deterministic control; official selected best | 6/8 | 0 | 8/8 `ok` |
| All-cuts seed `3fcc0f0d` | post-hoc deterministic control | 6/8 | 0 | 8/8 `ok` |
| AdaEvolve `a5712e6b` | valid generated candidate | 6/8 | 0 | 8/8 `ok` |
| EvoX `aa416e9c` | valid generated candidate | 6/8 | 0 | 8/8 `ok` |

All five arms certify the same six named families: `k4-mask54-order38858`, `k4-mask216-order39181`, `k5-mask412-order38747`, `k5-mask472-order19117`, `k6-mask363-order26185`, and `k7-mask478-order12940`. The six are distinct from the frozen development IDs and the cycle7 certificate `(mask, order_index)` list, but all six are already certified by the fixed-catalog control. The union has **zero new certificates over that catalog**; neither generated arm adds one. The two remaining names are `k6-mask378-order33207` and `k7-mask367-order13766`. Their status is **NO_CERTIFICATE from the tested finite profile pools**, never infinity or an infeasibility theorem. For k6 the returned feasible base is `6611/96 > 67` in every arm. For k7 it is `958/13 > 73` for catalog and `956/13 > 73` for the other four. These returned mixtures do not certify a pool optimum.

For the six certificates, the audit independently repriced all 38 fixed-catalog direct profiles and every accepted candidate word with `resources`, replayed the visible unit words, verified support membership, recomputed exact rational weights and intercept/slope inequalities, and checked 216 nonunit literal expansions across 72 support appearances. Each certified mixture has base strictly below `31 + 6k` and every slope at most six. The resulting claim is an upper bound for all positive block lengths for these six selected unit families under the direct-word triangle stretching argument recorded in [the criterion](../direct-mixture-criterion.md). Finite literal replays are cross-checks, not a substitute for that lemma. This does not prove the general LRX conjecture or settle either unresolved family.

The confirmation set is consumed. Its outcomes must not be used as proposer context or to select another candidate for the same holdout.
