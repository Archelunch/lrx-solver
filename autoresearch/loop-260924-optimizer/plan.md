# Session 09: optimizer-driven mixture word construction

Goal: progress toward the LRX radius conjecture through exact certificates for
all positive block lengths at m=8, while automating proposal/reflection work.

Frozen development: the 48 failures from session08 development. Expand its
128-source pool to a nested 512-source pool; 14 certify. Optimize on the 34
remaining cases against that fixed baseline. Baseline certificates and failures
are preserved. This sample is deliberately difficult and not representative.

Fresh confirmation: 30 structural families, six per block count 4..8, sampled
before baseline evaluation and disjoint from both previous datasets. Do not
expose results until both arms finish; never feed outcomes into a proposer.

Two arms: sequential and EvoX, same seed policy, 12 proposals, at most $2 each,
30 minutes each; EvoX may additionally reflect every three proposals. Report
reflection overhead and spend separately; this is a one-seed pilot, not ranking
proof. All four local planners are covered by offline adapter tests.

Policy: bounded JSON weights choose adjacent inversions and rotation routes,
with up to32 complete sorting words. No model-generated code is executed.
Every word descends in inversions relative to a fixed linear cut and canonical
phase. Add its verified cost profile to the fixed catalog support and optimize
rational mixtures. Exact reconstructed inequalities decide acceptance. Misses
are not lower bounds or proof of infeasibility. Model feedback contains up to
four development failures with coefficient profiles and base deficits.

The orchestrator handles setup, audit and final interpretation. Existing campaign
machinery runs model proposals, EvoX reflections, deduplication, evaluation,
feedback, logs and provider budget enforcement without per-proposal intervention.
The context is frozen within this comparison; accepted development conclusions
can enter the next context revision with evidence hashes.

API scope is in payload-scope.json. Automatic review rejected the initial launch
pending explicit approval of this exact unpublished payload to api.x.ai. No API
call occurred in that rejected attempt. No new dependencies or core modifications.
