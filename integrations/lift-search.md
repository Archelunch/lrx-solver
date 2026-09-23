# Engine-driven lifting search

`lift_campaign.py` adapts the existing `Campaign` planners to the data-only
construction policies in `lift_policy.py`. It supports sequential, GEPA,
AdaEvolve and EvoX; these remain the repository's compact adaptations, not
runs of the official packages. All use the same policy interpreter and exact
fixed-word router. The only shared engine change is an overridable feedback hook.

Run a frozen campaign with:

```sh
python -m integrations.lift_campaign CONFIG.json --allow-network
```

Live calls require authorization. See `autoresearch/loop-260923-2107/` for a
complete matched experiment: context, train/confirmation split, seed, configs,
manifest and payload scope. Each run uses a fresh directory. A config wrapper
contains `campaign` (standard engine config), `context_file`, `train_file`,
`max_words`, and `run_dir`. `kinds` must be `["lift_policy"]`, `select` must be
`"score"`, and `final_heldout_top` must be zero. Confirmation is a separate
one-shot operation after every compared arm finishes.

The candidate chooses zero ordering, move-priority schedules and optional
single non-descending projected moves. Exact smaller BFS distances constrain
construction; the router optimizes invisible repairs for each resulting word.
Every successful full word is independently replayed by the trusted validator.
Schema checks reject executable code and explicit state lookup fields.

A failed policy only misses within this restricted portfolio and generation
cap. It establishes no lower bound, no infinity, and no counterexample to the
conjecture. A successful policy establishes finite upper bounds for its saved
vectors. Generalizing it still requires an existence/cost argument and the
base case. In particular, exact distance queries are an oracle for discovery.

Research context has two distinct sources:

1. A frozen, hash-verified evidence packet with status and scope on each claim.
   It includes development evidence only. Updating it is an explicit versioned
   research decision, not something a model reflection can do automatically.
2. Campaign-generated context: selected parents, deterministic feedback,
   histories, inspirations, focus, and tactics. The inherited engine selects
   these. EvoX reflections may change its validated JSON strategy; all generated
   prose remains a hypothesis. Prompts and strategy decisions are retained.

Context hashing proves provenance, not mathematical truth or absence of
mislabeling. The orchestrator still reviews source roles and claim scope.
`PolicyEvaluator(..., role="confirmation")` refuses feedback extraction; do not
copy its results into future proposal packets. If confirmation becomes a
future development set deliberately, replace it with fresh confirmation data
and disclose that change.

Per-arm provider ledgers cap both proposals and reflections. Report actual
costs as well as proposal counts: equal ceilings are not equal actual spend.
Preserve failed attempts, stopped calls and incomplete campaigns. A small
single-seed comparison is a mechanism test, not an engine ranking.
