# First-prompt guard note: AdaEvolve mode-guidance block (2026-09-25)

**Cause.** AdaEvolve chooses exploration, exploitation or balanced parent selection with
`rand = self.rng.random()` (SkyDiscover 0.2.0, adaevolve/database.py). `base_database` seeds
that RNG with `random.Random(config.random_seed)`, and our sky config (`lift_backends._sky_config`)
sets no `random_seed`, so the draw comes from OS entropy. The user message's
"PARENT SELECTION CONTEXT" paragraph is therefore EXPLORATION, OPTIMIZATION or empty (balanced)
at random. Two offline captures happened to agree, which was not evidence of determinism.

**Consequence.** Live `live-v2-adaevolve-260925-135343` sent first solution prompt `799905f2...`
against the approved `fb0b7a84...`. The system message, program and packet were byte-identical;
only that paragraph differed (OPTIMIZATION live, EXPLORATION captured). The post-run guard
marked the arm FIRST_PROMPT_MISMATCH and exited 1, so `_finish` never ran and there is no
`verified_best_result`. `sort_finalize` now admits such an arm only after computing the diff
itself: every changed line must be a SkyDiscover mode-label line or blank, and the messages
must be identical once the labels are removed. It stores the unified diff and both hashes under
`admitted_with_prompt_mismatch` in `finalists/manifest.json`, and it uses the best record in
the arm's `verified/evaluations`, re-executed. Any other difference keeps the arm excluded.

**Fix for future campaigns.** Set `random_seed` in `_sky_config`. That function lives in
`integrations/lift_backends.py`, which plumbing-fix owns and the approval hash covers, so the
change needs a new approval hash. With a fixed seed, capture the AdaEvolve and EvoX first
prompts again and confirm they are reproducible over several captures before approving.
