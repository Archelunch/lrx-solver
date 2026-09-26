# LRX Lab

Exact computation and LLM-guided program search for an open problem about
sorting with three moves.

Arrange the tokens `1, 2, ..., m` and `r` indistinguishable zeros on a circle
of `n = m + r` cells. Three moves are allowed:

- **L**: rotate everything one cell left
- **R**: rotate everything one cell right
- **X**: swap the first two cells

How many moves does the worst arrangement need to reach the sorted one,
`(1, 2, ..., m, 0, ..., 0)`? That number is the **sorting radius** `E_r(n)`.
It is the eccentricity of the sorted state in a Schreier graph of the LRX
Cayley graph, not the graph's diameter.

## The conjecture (open)

For `m >= 8` and `r >= 2`:

```
E_r(n) <= T_m(n) = m(m+1)/2 + (r-1)(m-2)
```

This repository does **not** prove it. It provides:

1. **Exact ground truth.** Complete BFS distance tables, an exact dynamic
   program for the manuscript's lifting approach, and an m-parametric exact
   checker for the research group's certificate criteria.
2. **Verifier-first search.** LLM engines (GEPA, AdaEvolve, EvoX, and a
   sequential control) propose programs or JSON policies. Deterministic
   checkers replay words and solve exact LPs. No LLM judges anything.
3. **A claims register.** `research/claims.md` separates computed, replicated,
   conditionally certified, conjectured and negative statements, session by
   session, with attribution.

## Current state (2026-09-26)

The general conjecture is open. Details and evidence for every line are in
`research/claims.md`; the latest summary is `HANDOFF.md`.

**Exact radii.** Complete ranked BFS, sha256 in each table's metadata.

| m | r | states | radius | T_m(n) |
|---|---|---|---|---|
| 8 | 1..6 | up to 121,080,960 | 36, 42, 48, 54, 60, 66 | equal |
| 9 | 1..5 | up to 726,485,760 | 45, 52, 59, 66, 73 | equal |
| 9 | 6 | 1,816,214,400 | **79** | 80 |
| 10 | 2, 3 | 239,500,800 / 1,037,836,800 | 63, 71 | equal |
| 11 | 2 | 3,113,510,400 | 75 | equal |

(9,6) is the first computed case with m >= 8 where the radius is strictly
below `T_m(n)`: 26 states at 79, none at 80. At (m,2) for m = 8..11 the radius
is attained by exactly two states, and the reversal with two outer zeros
`(0, m, ..., 1, 0)` has distance exactly `T - 1`.

**m = 8.** The research group's package claims the full bound
`E_(n-8)(n) <= 6n - 18` for all n >= 9. This repository replicated it
independently (their replay PASS; our stdlib checker on every k = 4..9
certificate file and a rebuilt k >= 4 union with 0 uncovered). This is the
group's theorem. See claims Session 10.

**Certificates at general m.** A certificate for a family (label order,
nonempty gaps) proves `d(v) <= T_m(n)` for every block-length vector of that
family. It is **conditional** on the group's Lemma 1 and criteria (7)/(8),
which the group proved for m = 8 and which this repository applies with m as a
parameter. Three closed-form word families certify parts of the reversal orbit:

- **word_C** certifies the reversal with zeros in gaps {0, m} at every
  m = 9..40 by evaluator and independent audit, and by replay to m = 200
  (Session 20).
- **word_R1** certifies the reversal with zeros in gaps {1, m} at m = 9..40,
  with replay and criterion (7) to m = 200 (Session 21).
- **word_G** certifies the reversal with zeros in gaps {0, g} for the outer
  band `min(g, m-g) <= floor(m/4)`, audited at m = 9..40 and checked by replay
  and criterion (7) at m = 41..80. Its rules were read off data (Session 22).

Every two-zero mask of the m = 9 reversal is now certified (Sessions 21-23).
Several middle-band masks at m >= 10 remain uncertified, and the whole
band at m = 14..16 (Session 23).

**First exact negative for a root leaf.** For m = 9 with zeros in gaps
{0, 4}, no single-leaf (root) certificate exists: the exact optimum of the
criterion (8) left side over all words is 2, against the required value
below 1. A two-leaf tree certifies the family. The exactness rests on the
completeness of the A* oracle over reduced words (Session 23).

**Search campaigns on the bound task.** Engines evolve `certify(family)`;
the evaluator decides each family by exact LP.

| campaign | holdout | result | spend |
|---|---|---|---|
| bound-m 1 | all 165 m = 11 families, unseen | EvoX 129, GEPA 125, hand control 98 | $3.45 |
| bound-m 2 | 165 m = 12 + 60 fresh m = 11, 3 seeds | mean share AdaEvolve 84.7 %, EvoX 83.1 %, GEPA 80.3 %, sequential 76.4 %, seed 80.0 %, control 59.6 % | about $7 |
| bound-m 3 | prepared, not launched | seed alone: 283/303 development, 157/165 validation | $15 cap |

Independent audits found 0 disagreements. Campaign 3 has a pre-registered
success and kill rule and awaits human approval of its payload hash
(`autoresearch/bound-m-c3-260926/REPORT-prep.md`). Earlier campaigns (lift
m = 9, sort m = 9, correlation certificate, official program search) are
summarised in `HANDOFF.md` and the claims register. No campaign establishes
an engine ranking or a proof for all m.

## Verify

Python 3.10+. The runtime is the standard library; numpy is an optional
extra used by the `lift` command and the low-memory table builder. Run from
the repository root:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q src tests
python -m src.lrx.cli smoke
```

On 2026-09-26 the suite ran 617 tests with 4 skipped. The skipped tests
exercise the Seatbelt sandbox and run when `LRX_TEST_SANDBOX=1` is set.
Rebuild the registry tables (about 2 min, 123 MB) with:

```sh
python -m src.lrx.cli table build-registry --workers 8
python -m src.lrx.cli table verify
```

Re-check stored certificates without tables or provider calls:

```sh
PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_k2.py        # word_G and stored k=2 rows
PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_midband.py   # middle-band rows
```

Other entry points:

```sh
python -m src.lrx.cli bfs 4 2                          # sorting radius of a small graph
python -m src.lrx.cli family 4 --exact                 # a finite lower-bound certificate
python -m src.lrx.cli eval candidates/leads/49ab346cb44b2f1b.json
python -m src.lrx.cli evolve campaigns/offline-rules-gepa.json   # offline search, no API
python tools/orchestrator.py trusted                   # trusted-core hash check
```

The full v2 command reference is in [docs/usage.md](docs/usage.md).

## Repository layout

| path | contents |
|---|---|
| `src/lrx/` | state model, ranked BFS tables, exact DP, certificates, DSL, evaluator, search engines, CLI |
| `integrations/` | task definitions, exact evaluators, independent audits, finalize scripts, official-engine backends, budget broker (`research_budget.py`) |
| `integrations/lrx_m.py` | m-parametric exact checker: replay, Lemma 1 lift, criteria (7)/(8) |
| `integrations/bound3_*.py` | bound-eval-3: tree certificates, evaluator and audit |
| `tools/` | trusted-core orchestrator, low-memory BFS builder, cayleypy cross-check |
| `tests/` | unit tests; `test_search_*.py` cover search-side code |
| `autoresearch/<campaign>-<date>/` | one directory per campaign: task, frozen splits, configs, run logs, finalists, reports |
| `autoresearch/bound-m-260925/checks/` | reversal-orbit generators, stored words and re-check scripts |
| `research/claims.md` | the claims register, one Session entry per iteration |
| `datasets/` | graph registry and table hash lock |
| `datasets/generated/` | exact tables, gitignored, rebuilt locally |
| `candidates/`, `campaigns/`, `evidence/` | JSON candidates, campaign configs, cited check outputs |
| `references/` | sources and attribution |

Exact tables are large and never committed. Registry tables rebuild with
`table build-registry`. Larger tables sit in dated subdirectories of
`datasets/generated/` and are identified by the sha256 recorded in the claims
register. Rebuild them with `table build` or the low-memory builder; see
[docs/AGENT-GUIDE.md](docs/AGENT-GUIDE.md).

## Ground rules

- A replayed word proves an upper bound for that one state only.
- A failed or long heuristic search is never a lower bound.
- Resource limits produce INCOMPLETE, never infinity.
- A finite check is a statement about that graph only.
- Certificates at m != 8 are conditional on the group's Lemma 1 and
  criteria (7)/(8) at general m. Say so in every report.
- Holdout sets are evaluated once, after finalists are frozen, and never
  reach a prompt.
- Generated code runs only inside the evaluator sandbox (macOS Seatbelt).
  Never execute it anywhere else.
- Live API calls, new dependencies and remote writes need explicit human
  authorization. Credentials stay in environment variables.
- The trusted core listed in `tools/orchestrator.py` is hash-locked; only a
  human re-locks it.

## For agents

- [AGENTS.md](AGENTS.md): binding rules for coding agents in this repository.
- [docs/AGENT-GUIDE.md](docs/AGENT-GUIDE.md): how an external agent checks
  claims, builds tables, runs the bound task with its own proposer and
  contributes results.
- `.claude/skills/`: short operational skills `lrx-verify`, `lrx-table`,
  `lrx-bound-campaign` and `lrx-claims`.

## Sources

The exact recurrences, the 6k-2 obstruction family and the lifting candidate
come from an unpublished manuscript. The empirical radius formula comes from
unpublished progress notes. Lemma 1, criteria (7)/(8), tree certificates and
the full m = 8 package are the research group's. None of these is distributed
here. They are cited in
[references/source-manifest.md](references/source-manifest.md), and every
result taken from them is attributed in `research/claims.md`.

The supplied nine-gap theorem's verification archive and original Russian
text are preserved under `autoresearch/loop-260923-2107/incoming/`.
Repository summaries and the README are maintained in English; original
source material is retained in its original language.

## License

[MIT](LICENSE)
