# Session 04: bounded EvoX comparison

Authorized 2026-09-23: Grok-4.7, at most $50 new spend; no remote writes.
Baseline checkout: public 4015c74. Historical logged spend $56.0159 is excluded
from this new session budget. The locked verifier remains unchanged.

Hypothesis: strategy evolution with proof-facing feedback can escape the
controller plateau more efficiently than fixed sequential or GEPA selection.
This tests the local JSON-policy EvoX adaptation, not official code-evolving EvoX.

Pilot: at most $2.50, two proposals and any triggered reflection/repair.
Main comparison planned: three engines, two seeds, 24 proposals per run,
$6 per run including reflection and repairs, identical model/seed/prompt and
batch size. Six run caps total $36; $11.50 remains uncommitted. Stop early on
infrastructure failure, verifier mismatch, or exhaustion; unused budget is not
a requirement to spend. Full runs are contingent on pilot health.

Primary outcome: all checked states solved, then worst train word/T. Secondary:
original score, invalids, duplicates, LLM dollars, evaluator CPU/wall, strategy
windows. Average-score-only improvement is not proof progress. Compare cost
curves at common budgets; unequal realized proposals are reported explicitly.
Two seeds are exploratory, not a statistically decisive engine ranking.

No feedback from final held-out tests. Existing held-out graphs are historical
regression cases, not all untouched. Freeze finalists before any additional
confirmation. Search code, configs, prompts and new tests only; never execute
generated code, change evaluator/data, or re-lock the trusted core.

Validation before paid work: 290 unit tests passed; compileall exit 0;
smoke passed=true; trusted ok=true. Evidence: verification-initial.log.

Run artifacts live in this fresh session directory. Preserve previous runs.

Pre-comparison scheduling revision (pilot still pending): batch=4 for all arms,
synchronous rounds, max wall 5400 s per run. Sequential means four sibling
refinements from the current best per round. EvoX can change strategies only
between complete rounds, avoiding attribution of old-policy calls to new policy.
