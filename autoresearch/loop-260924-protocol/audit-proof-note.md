# Proof scope for a development finalist

For a fixed m=8 label order and k retained zero blocks, the trusted evaluator accepts complete unit-block words and computes a direct profile `(B, beta_1, ..., beta_k)`. The [direct-word criterion](../loop-260924-live/direct-mixture-criterion.md) expands each word for arbitrary positive block lengths `ell_j` and bounds its lifted length by

`B + sum_j beta_j (ell_j - 1)`.

Suppose exact nonnegative rational weights on verified words sum to one, their weighted base is **strictly below** `31+6k`, and every weighted slope is at most `6`. The weighted mean of the lifted upper bounds is then strictly below

`31+6k + 6 sum_j(ell_j-1) = 31+6 sum_j ell_j = (6n-18)+1`, where `n=8+sum_j ell_j`.

At least one lifted word has length no greater than that mean. Its length is an integer, so it is at most `6n-18`. This proves the bound for **that fixed label order and gap mask for every positive length vector**. It does not prove all m=8 states or the general LRX conjecture.

The saved-evidence auditor checks the unit words, direct resources, exact weights, strict intercept and slope inequalities, and several nonunit literal expansions independently. The finite expansions are implementation cross-checks. The all-length step depends on the general direct-word macro and triangle argument, not extrapolation from those finite replays. New output has not received separate human review or formalization of that argument. A reduced-cost improvement or lower feasible LP intercept is search guidance until a complete exact mixture passes these checks. A missing certificate is not infeasibility.

If a finalist certifies the remaining development k5 case, record its exact word construction, support weights and complementary slope tradeoff. Call it a named-family certificate; claim a reusable cut or routing lemma only if the construction rule and its proof work beyond that one case.
