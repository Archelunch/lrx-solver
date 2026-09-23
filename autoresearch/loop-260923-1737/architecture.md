# Architecture findings from the bounded experiment

Status: interim; the frozen comparison is still running. These are proposed
next steps, not claims that an untested optimizer will outperform another.

## Separate search control from evidence

Keep the deterministic evaluator and replay boundary. Use one campaign contract
(candidate kinds, objective, resource caps, data split) for both proposer and
reflector. Currently the reflector sees all candidate shapes and can recommend
a kind that the candidate validator rejects. The contract must be explicit in
both messages. A strategy is not entitled to change the task it is measured on.

The existing ratio-first selection makes the objective correspond to the
constructive route. Mean gap remains a tie-breaker. A raw bound expression T
must never be credited as a constructive proof: it is only a conjectural bound
validated on finite tables.

## Make the search space cheaper before adding an optimizer

A semantics-preserving position lookup rewrite shortens controllers and reduces
interpreter work. Store both original and normalized specs if this is integrated
into proposal handling, so model output and evaluated output remain auditable.
Measure valid rate and cost as well as evaluation time; the current benchmark
only establishes identical words on the checked small graph and identical train
metrics, not a campaign cost reduction.

Simple expression rewrites are a useful program-optimization target within the
JSON boundary. Searching arbitrary Python evaluator implementations would cross
the locked-core boundary and is outside this run. A future JSON strategy DSL can
expose real search choices without executing generated source.

## Give EvoX a useful decision horizon

Current strategy choices mainly change mutation modes, parents and prompt text.
New controller families often start much worse than the mature insertion seed.
A global best/front archive can discard those families before refinement. Test
a small family archive with a fixed refinement allowance, charging that allowance
to the same total budget. Keep this separate from the current engine comparison.

Before increasing meta-optimization depth, fix the allowed-kind contract and
measure it. Do not infer that official SkyDiscover EvoX is ineffective from this
compact JSON-policy adaptation. Do not infer it is superior from its flexibility
either; compare measured outcomes at matched cumulative cost.

## Spend on the expensive stage

Model generation and reasoning dominate evaluator runtime. Candidate batching,
shorter feedback, constrained edits, and a measured reasoning-token cap are more
likely to reduce dollar cost than a faster cache alone. These are hypotheses:
a smaller cap can raise truncations and repair costs, so use a paired bounded
pilot rather than changing every arm at once. Reflection calls should include
remaining dollars, validity failures, and improvement per dollar.

Synchronous rounds preserve policy attribution but wait for their slowest call.
An asynchronous version should tag every proposal with strategy version and
parent IDs, then attribute late results to their originating policy. Otherwise
meta-feedback mixes strategies and can mislead the optimizer.

## Ask finite questions that can stop early

For lifting feasibility A_Q(v) <= B, search until an independently replayed
witness meets B. Do not compute every deletion's exact optimum when one witness
settles the decision. Negative answers require complete bounded searches over
all deletions. Resource exhaustion is INCOMPLETE, never infinity or false.
Benchmarks in this session preserve this distinction and show savings mainly
on positive instances. They reproduce known cases, not a new lifting lemma.

## How this relates to the published method

The [EvoX paper](https://arxiv.org/html/2602.23413v1) evaluates open frameworks
at 100 iterations. Its strategy history associates performance with population
state, including score distribution, frontier structure and parent-selection
frequencies. Its signal-processing example has major changes around iterations
48, 70 and 96. Our 24-proposal runs with four-proposal windows are a smaller,
different experiment, and cannot settle the paper's longer-horizon claim.

The local adaptation exposes fixed JSON policy fields and a tactic string.
Giving its strategy evaluator richer population descriptors and preserving
family diversity are plausible improvements; they remain hypotheses here.
