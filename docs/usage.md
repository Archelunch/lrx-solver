# Usage reference

All commands run from the repository root and print JSON.
`python -m src.lrx.cli --help` lists the v1 commands; the v2 commands
(`table`, `eval`, `certify`, `features`, `evolve`, `prompt`, `leaderboard`,
`llm-smoke`, `trace`, `report`, `lift`) each have their own `--help`.

Exit codes: 0 for a successful check or run, 1 for a failed certificate or a
finite lifting-bound failure, 2 for invalid input or an incomplete
resource-limited computation. A heuristic run completing is not a claim that it
solved every input.

## Exact tools (v1)

```sh
python -m src.lrx.cli info 8 2                       # state counts, T_m(n)
python -m src.lrx.cli bfs 4 2                        # visible sorting radius, bounded BFS
python -m src.lrx.cli projection 4 2                 # exhaustive min_j H_q(v\j, j) <= q+m-2
python -m src.lrx.cli projection 4 2 --q 10          # absolute projection cap, e.g. Q = T_m(n-1)
python -m src.lrx.cli family 3                       # replay the manuscript's 6k-2 family word
python -m src.lrx.cli family 4 --exact               # plus a finite lower-bound certificate
python -m src.lrx.cli verify 2 2 X --start 2,1,0,0 --mark 2
```

`family` defaults to word replay only. `--exact` also builds two complete
bounded balls whose radii sum to one less than the word length; disjointness
certifies the lower bound for that particular family member. It does not prove
the infinite family theorem.

`projection` separates "no admissible lift", finite budget violations and
incomplete computation. Worst finite witnesses are replayed independently. The
DP keeps `q+1` bounded layers; the default cap is 1,000,000 cells and q <= 100,
plus a work estimate cap. `projection 8 2 --q 36` intentionally returns
INCOMPLETE before attempting the large computation. For large graphs use `lift`.

## Ground truth tables

```sh
python -m src.lrx.cli table build-registry --workers 10   # ~90 s on 10 cores, 123 MB
python -m src.lrx.cli table verify                        # hashes vs datasets/tables.lock.json
python -m src.lrx.cli table build 8 2 --out DIR           # one table
```

Tables are ranked one-byte BFS distances from the canonical root, written to
`datasets/generated/` (git-ignored). `datasets/registry.json` assigns every
graph a role:

- **sanity** (m <= 6): exhaustive; any failure stops evaluation.
- **train**: feedback allowed.
- **heldout**: scored only at the end of a campaign, never shown to a proposer.

T_m(n) is applied only for m >= 8.

## Candidates

Candidates are JSON (`src/lrx/candidates.py`, expression DSL in
`src/lrx/dsl.py`), interpreted and never executed. Kinds:

| kind | meaning | checked by |
|---|---|---|
| `rules` | sorting controller that emits an explicit L/R/X word | word replay against the root |
| `potential` | phi with phi(root) = 0 and a descending neighbour everywhere else | local descent on probes, `certify` on whole tables |
| `bound` | per-state upper bound on d(v) | comparison with tables |
| `radius` | formula for E_r(n) | comparison with table radii |
| `beam` | beam-search heuristic | replayed words |

```sh
python -m src.lrx.cli eval candidates/baselines/rules_bubble.json             # train score
python -m src.lrx.cli eval candidates/baselines/rules_bubble.json --feedback  # what a proposer sees
python -m src.lrx.cli eval FILE --split heldout                               # human only
python -m src.lrx.cli certify candidates/probes/6ff08052bb698f26.json 8 3     # every state of one table
python -m src.lrx.cli features 8 2 --v 8,7,6,5,4,3,2,1,0,0
```

`candidates/baselines/` holds the reference candidates, `candidates/leads/` the
best rules controllers found, `candidates/probes/` potentials and other
interesting proposals.

## Campaigns

A campaign config (`campaigns/*.json`) chooses an engine, candidate kinds,
seeds, budgets and a proposer.

| engine | idea |
|---|---|
| `best_of_n` | independent proposals from the seeds |
| `sequential` | refine the current best with feedback |
| `gepa` | GEPA-style Pareto front over per-graph scores, reflective mutation, parallel proposals, merges |
| `adaevolve` | AdaEvolve-style islands, UCB island choice, adaptive exploration, migration, meta-guidance on stagnation |
| `evox` | a strategy text that the reflector rewrites after a window without gain |

These are compact local re-implementations of the published ideas, not the
official packages. `integrations/lrx_eval.py` exposes the same evaluator to the
official GEPA package (see `integrations/requirements-ext.txt`; install it in a
separate virtual environment, never in the verifier's).

```sh
python -m src.lrx.cli evolve campaigns/offline-rules-gepa.json      # free: random mutations
python -m src.lrx.cli prompt campaigns/grok-rules-adaevolve.json    # inspect the prompt
python -m src.lrx.cli llm-smoke campaigns/grok-smoke.json --allow-network   # ONE paid request
python -m src.lrx.cli evolve campaigns/grok-rules-adaevolve.json --allow-network
python -m src.lrx.cli leaderboard
```

Live providers read `XAI_API_KEY` from the environment or from a git-ignored
`.env`. Nothing is sent without `--allow-network`. The client streams, enforces
wall-clock and reasoning-token budgets itself, rejects redirects, caps response
size and never retries automatically. Spend is estimated from the rates in the
config, or taken from the provider-reported cost when present. The local ledger
does not enforce the provider's actual bill: set a provider-side limit too.

## Run directories and observability

Each campaign writes `runs/<name>-<stamp>-<hash>/`:

| path | contents |
|---|---|
| `config.json`, `summary.json`, `best.json`, `results.tsv` | configuration, outcome, best candidate |
| `events.jsonl` | `start`, one `candidate` per proposal (candidate, parents, island, mode, prompt, model reply, tokens, cost, timings, per-graph scores, feedback), one `batch` per round, `reflection`, `migration`, `heldout`, `end` |
| `prompts/system-<sha>.txt` | each distinct system prompt, stored once |
| `evals/<hash>.json` | full evaluator result per distinct candidate |
| `report.html` | self-contained HTML report, rewritten after every batch |

```sh
python -m src.lrx.cli trace RUN               # overview
python -m src.lrx.cli trace RUN --tree        # lineage
python -m src.lrx.cli trace RUN --timeline    # per batch: best, stall, timing, spend
python -m src.lrx.cli trace RUN --show 12     # one candidate: prompt, reply, evaluation
python -m src.lrx.cli trace RUN --follow      # live tail until the run ends
python -m src.lrx.cli report RUN [RUN ...]    # one run, or a comparison page
```

Existing run files are never overwritten.

## Exact lifting checks (Route B)

```sh
pip install numpy   # or: pip install -e '.[lift]'
python -m src.lrx.cli lift 8 3 --out runs/lifting-check-NEW/m8r3.json
```

`lift` computes H_q exactly for every marked state and A_q(v) for every visible
state (`src/lrx/lifting_fast.py`). It is cross-checked against the pure-Python
DP on small graphs. n = 12 fits on a laptop (5.8 GB peak at (12,9,3)).
Independent checks that share no DP code: `tools/verify_lift_independent.py`
and `autoresearch/lift_forward.py`. Band-limited checks for n = 13:
`autoresearch/lift_targeted.py`; threshold sweeps: `autoresearch/lift_sweep.py`.

## Autoresearch orchestrator (optional)

`autoresearch/PROGRAM.md` is the operating manual for an LLM coding agent that
runs campaigns, promotes leads and logs findings. `tools/run_orchestrator.sh`
launches it with the Claude CLI and the permission file
`autoresearch/orchestrator.settings.json`. `tools/orchestrator.py` provides the
metric (`ratio`), the spend guard (`spend`) and the trusted-core hash check
(`trusted`); `lock-trusted` is for a human after review. None of this is needed
to use the library.

## Legacy v1 experiment command

```sh
python -m src.lrx.cli experiment 3 2 --mode sequential --proposals 8 --seed 42
```

The `experiment` command and its three-integer policy predate v2. It keeps the
bounded solver, work caps (default 1,000,000 expansions, hard maximum
10,000,000) and the optional `provider_adapter.py` API proposer. Use `evolve`
campaigns for research runs.

## Safety and scale

There are `n!/r!` visible and `n!/(r-1)!` marked states: 1,814,400 and
3,628,800 at (m, r) = (8, 2). Missing distance-oracle entries, time or resource
refusal, and infinity have different meanings, and the code keeps them apart.
Do not remove safeguards to imitate the manuscript's optimized C++ results.
