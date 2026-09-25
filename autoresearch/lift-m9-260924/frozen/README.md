# Frozen m=8 -> m=9 lift instance sets

Built by `autoresearch/lift-m9-260924/build_frozen.py` +
`split_and_enumerate.py`, seed 20260924, stdlib only. Reads
`autoresearch/verify-m8-260924/package/` read-only and never modifies it.

## Construction

1. `build_frozen.py` loads the full m=8 package once via
   `autoresearch/verify-m8-260924/checker/union.py`'s `load_all()` (our
   independent checker, not package code) and samples 300 parent
   `(labels, mask)` families, stratified over k=4..9 and over certificate
   route, replicating `union.do_order`'s exact route-priority chain so the
   recorded route matches what `checker/results/union.json` reports.
2. Each parent's certificate rows are rebuilt as literal words on the
   parent's own m=8 unit base: Lemma 4 deletion (`lrxm8.project`) for
   projected families, then Lemma 3 comparison transfer
   (`integrations/lift_task.comparison_word`). `base`/`slopes` are
   recomputed from the literal word by `integrations/lrx_m.Profile`
   (via `lift_task.plain_row`), never copied from the package.
3. The 300 parents are split 200 development / 100 holdout, disjoint on
   `(labels, mask)`, keeping each (k, route) stratum split roughly 2:1.
4. Every instance (insertion position 0..8, applicable splits) is
   enumerated with `integrations/lift_task.build_instances`, the same
   function the evaluator (`integrations/lift_evaluator.py`) uses to
   recompute and validate instances at run time.

## Route coverage

300 parents (200 dev / 100 holdout) use `direct_mixture` or
`projection_from_N`. `integrations/lift_task.check_instance` and
`integrations/lift_evaluator.py` both read `parent.certificate.rows` as a
flat list unconditionally; a tree/leaf certificate's per-box conditional
weights cannot be flattened into one mixture without breaking criterion
(8). lift-eval clarified, however, that the child-side scoring never uses
parent weights at all -- it always solves its own exact LP over whatever
words the candidate program returns, so parent weights are hints only.
That makes tree parents safe to include as flattened, weight-less hints.

15 more parents were added on that basis (10 dev / 5 holdout: 7
`direct_tree`, 8 `reverse_tree_transfer`), for `certificate.kind: "tree"`
with `weights_placeholder: true` and every row `weight: "0"`. Only
unit-origin (all block lengths 1) leaf rows are emitted, since only those
are literal words that sort the parent's own unit base directly;
non-unit-origin leaf rows were used here to verify the real leaf criterion
(8) with the package's real weights, but are not emitted (the evaluator
needs literal unit-base words, not stretched-origin ones). 24 other
tree-route candidates were tried and discarded (materialization/cut search
failed) before reaching 15 that fully verify; see `add_tree_stratum.py`.

## Files

- `development.json`, `holdout.json`: `{"schema": "lrx-lift-instances-v1",
  "set": "development"|"holdout", "instances": [...]}`, each instance is
  exactly `integrations/lift_task.build_instance`'s output (parent with
  materialized certificate, insert, child).
- `parents_raw.json`: all 315 sampled+materialized parent families (300
  mixture-route + 15 tree-route) before the dev/holdout split (includes
  `route`, `order_index` for provenance).
- `development.v1.json`, `holdout.v1.json`, `manifest.v1.json`,
  `parents_raw.v1.json`: the pre-tree-stratum freeze (300 parents, 200/100
  split), kept for the record per team-lead's re-freeze instruction.
- `manifest.json`: seed, per-(k, route) counts, instance counts, SHA-256
  of each file above.
- `sanity_check_result.json`: output of `sanity_check.py` (20 random
  instances, seed 999): child unit_base validity, parent row
  base/slopes recomputation, criterion (7), and an independent recompute
  via `integrations.lift_task.check_instance`. All 20 passed.

## Holdout discipline

`holdout.json` must never enter proposer (GEPA/AdaEvolve/EvoX) context
during search. It is evaluated once, after the finalist gadget is frozen,
per TASK.md's "Sets" section. Its SHA-256 is recorded in `manifest.json`
now, before any live optimizer call, so a later substitution would be
detectable.
