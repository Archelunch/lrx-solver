# Offline all-cuts control — development only

This was one bounded, deterministic check after the live-arm prompts had
started. It is a separate post-hoc control for this session, not part of any
official engine's causal result or a precommitted baseline. No API call or
confirmation case was used.

`allcuts_seed.py` changes the self-contained seed's four selected cuts to
every cut, with both tie directions. It returns at most 2n words per case
(n≤15 here), under the evaluator's 32-word cap. Source SHA-256:
`3fcc0f0d23ced3f0202454d3f44c419819e0fa3e8621a82a75bae2b2ab9df884`.
The strict Seatbelt development evaluation is
`offline-allcuts/3fcc0f0d23ced3f0-evaluation.json`.

| Pool | Certified development families |
|---|---:|
| Fixed direct catalog | 12/16 |
| Four-cut seed plus catalog | 14/16 |
| All-cuts control plus catalog | 15/16 |

The added family relative to the seed is `k6-mask315-order31970`, labels
`(7,3,4,5,1,6,2,8)`, mask 315. Cut 11 with prefer-right produces a complete
70-letter word with direct slopes `(6,7,10,7,4,5)`. At weight 7/68 alongside
four already available words, its exact mixture has weighted base 1136/17,
strictly below 67 by 3/17, and slopes `(199/34,6,6,99/17,6,6)`.
Against the old finite-pool exact optimum 1817/27, this lowers weighted base
by 217/459. Its reduced cost under the old dual is -124/27, so it passes the
previous necessary improvement filter. The bound covers all positive lengths
for this named family through the direct-word mixture criterion; this is not a
result for all m=8 states.

`k5-mask302-order15713` remains without a certificate. The all-cuts pool's
weighted base is still 24149/392, exceeding its strict threshold 61 by
237/392. Its best newly generated reduced cost under the old exact dual is
positive 55/28, so those words cannot improve that pool optimum. This says
nothing about other words or mathematical infeasibility.

An independent development-only audit of the evaluation rechecked source
hash, direct resources and replay for all support words, exact Fraction
mixture inequalities, and 144 nonunit literal expansions across 48 support
components. The named families are disjoint from the 8,193 cycle-7
certificate pairs. Full historical novelty was not established.
