# LRX autoresearch program (Claude orchestrator = meta-optimiser)

## Mission

Make progress toward a proof of the **LRX sorting-radius conjecture**
(open; see `research/problem.md`):

    E_r(n) <= T_m(n) = C(n,2) - (r-1)(r+4)/2   for m = n - r >= 8.

You do not write the proof and you do not touch the checker. You improve and
run the **search system** (engines, proposers, prompts, feedback, campaign
designs) that looks for machine-checkable proof ingredients, and you run the
exact finite checks that decide which proof routes are alive.

## Proof routes and what counts as progress

| Route | Artefact | Checked by | Milestone |
|---|---|---|---|
| A. Constructive | rules controller (explicit sorting procedure) | replayed words, `eval`, `ratio` | best sound lead has ratio <= 1.0 (within T on every m>=8 train graph), then held-out, then a human proof of that procedure |
| B. Recursion via lifting | finite facts about A_P(v) = min_j H_P(v\j, j) | `python -m src.lrx.cli lift M R` (exact, numpy) | lemma candidates that hold on every computed graph, stated precisely in `research/claims.md` |
| C. Potential | closed-form phi with local descent | `eval`, `certify M R` | zero local-descent failures on sanity + `certify` on (8,2) |

Current state: the "Results so far" section of `README.md`, the open items in
`ROADMAP.md`, and the latest `autoresearch/session-*-report.md`.

## Metric, Guard, Scope

| field | value |
|---|---|
| Verify | `python tools/orchestrator.py ratio` (route A progress; lower is better; 1.0 = within T) |
| Guard | `python tools/orchestrator.py trusted && python tools/orchestrator.py spend && python -m unittest discover -s tests -p 'test_*.py' -q` |
| Scope (editable) | `campaigns/**`, `candidates/leads/**`, `prompts/**`, `autoresearch/**`, `research/claims.md` (append findings only), search code: `src/lrx/evolve.py`, `src/lrx/proposers.py`, `src/lrx/prompt.py`, `src/lrx/feedback.py`, `src/lrx/trace.py`, `src/lrx/report.py`, `integrations/**`, new `tests/test_search_*.py` |
| Locked (never edit) | the TRUSTED list in `tools/orchestrator.py` (checker, DSL interpreter, tables, spend ledger, CLI, existing tests, AGENTS.md); `datasets/`; `runs/` (read only) |

Route B/C experiments usually do not move Verify. Keep them only if they add
a finding (logged in `autoresearch/results.tsv` and `research/claims.md`);
their configs/notes are the kept change.

## One iteration = one experiment

1. **Review cheaply.** `python tools/orchestrator.py status`,
   `python -m src.lrx.cli leaderboard`, last rows of `autoresearch/results.tsv`,
   `git log --oneline -10`. Do not read whole `events.jsonl` files; use
   `python -m src.lrx.cli trace RUN --timeline` / `--tree` / `--show ID`.
2. **Choose one hypothesis** about the search system or a route, e.g.
   "strong-model refinement of the lead", "edit-only mutation mode beats
   rewrites", "feedback with move traces raises the valid rate", "lift check at
   (12,9,3)".
3. **Make one change**: a new campaign config `campaigns/sNN-*.json`, a prompt or
   insights edit, or a search-code change (with a `tests/test_search_*.py` test).
4. **Run it**: `python -m src.lrx.cli evolve campaigns/<cfg>.json --allow-network`
   then `python tools/orchestrator.py promote runs/<run>`; or
   `python -m src.lrx.cli lift M R --out runs/lifting-check-<stamp>/mMrR.json`.
5. Commit (`experiment: ...`), Verify, Guard, keep/discard per the skill.
6. Log one row in `autoresearch/results.tsv`: run, route, hypothesis, engine,
   model, proposals, USD, wall, Verify before/after, finding, decision.

## Search-architecture rules

- Compare engines/prompts only at equal proposals and USD; one seed is a hint.
- Prefer cheap models for mutation, the reasoning model (grok-4.7, ~9 min,
  ~$0.27/call) for refinement of sound leads and for reflection.
- A search-code change must keep all existing tests green and add a test.
- Never let held-out results reach a prompt, insights file, or feedback.
- Never execute model-generated code; candidates stay JSON.

## Budgets and stops

- `LRX_MAX_TOTAL_USD` (default 20) caps logged spend; each config caps its own.
- Stop and ask the human when: ratio <= 1.0 for any lead; a lift check fails
  (a counterexample to the lifting candidate) or `A_below_distance_violations`
  is non-zero (checker inconsistency); `trusted` or tests fail; spend would
  exceed the cap; two infrastructure failures in a row.

## Token discipline

Summaries over raw logs. One experiment per iteration. Do not re-derive facts
in this file or in `research/claims.md`. Do not paste large JSON into the
conversation; write it to `autoresearch/` and cite the path.

## Claims discipline

Finite checks are finite. A controller within T on probes is not a proof; a
lift check on a graph is a statement about that graph. Record findings with
exact scope and evidence path. The conjecture stays open until a human proof.
