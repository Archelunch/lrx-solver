# Architecture findings from the bounded experiment

Status: comparison and confirmation complete; see [report.md](report.md).
Further proposals below are hypotheses, not established engine advantages.

```mermaid
flowchart LR
    C[Campaign contract and budget] --> S[Strategy selection]
    S --> P[Grok proposer]
    P --> V[JSON validation]
    V --> E[Deterministic evaluator]
    E --> A[Candidate archive and costs]
    A --> S
    A --> R[Occasional strategy reflection]
    R --> S
    A --> F[Freeze finalists]
    F --> H[Fresh-state confirmation]
```

## Separate search control from evidence

Keep the deterministic evaluator and replay boundary. Use one campaign contract
(candidate kinds, objective, resource caps, data split) for both proposer and
reflector. During the comparison the reflector saw all candidate shapes and could recommend
a kind that the candidate validator rejects. The post-comparison fix makes the
allowed kinds explicit in both messages and restricts reflection shapes. A strategy is not entitled to change the task it is measured on.

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
Selection from the global best or Pareto front can leave those families without
further refinement, even while their records remain in the archive. Test
a small family archive with a fixed refinement allowance, charging that allowance
to the same total budget. Keep this separate from the current engine comparison.

Before increasing meta-optimization depth, measure the corrected allowed-kind
contract in a future paid comparison. Do not infer that official SkyDiscover EvoX is ineffective from this
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

## Avoid treating temporary reservations as failed science

Both EvoX runs stopped with budget-denied slots in the last concurrent batch,
although final settled spend remained below $5 of the $6 cap. The ledger was
correct to reject overcommitted requests. A search-side scheduler could defer
those slots until earlier calls settle, then retry only if funds remain. Such
slots must be distinguished from generated invalid candidates in comparisons.
Do not relax the ledger or treat missing usage as zero to increase throughput.

## Reduce the outer autoresearch cost

Use the general coding agent at phase boundaries: define the experiment, repair
infrastructure failures, inspect completed evidence, and decide the next search
space. Let a deterministic campaign runner handle proposal dispatch, budget
reservations, validation, scoring, archival and final reports between those
boundaries. Strategy reflection is already a bounded model call inside the loop.

This session's dollar accounting covers Grok calls only. It excludes the outer
Codex conversation and local compute. Therefore the measured API spend is not an
end-to-end cost comparison against a general autoresearch agent. Eliminating
repeated outer-agent supervision is a plausible architectural saving, separate
from claiming that one evolutionary engine is better than another.
