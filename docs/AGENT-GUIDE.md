# Agent guide: using LRX Lab from your own autoresearch

This guide is for an external agent, on any model and any harness, that wants
to use this repository as an exact checker and task source next to its own
research loop. The binding rules for agents editing this repository are in
`AGENTS.md`. Read `research/problem.md` and the latest Sessions in
`research/claims.md` before you claim anything.

All commands run from the repository root. Python 3.10+; the checkers are
standard library only. numpy is needed only by the low-memory table builder
and the `lift` command. The candidate sandbox is macOS Seatbelt
(`sandbox-exec`); on other platforms the sandboxed evaluator refuses to run.

## 1. Check a claimed bound or certificate

Pick the check that matches the claim.

| claim | tool | what a pass proves |
|---|---|---|
| word w sorts state v | `integrations/lrx_m.py`: `run_naive`, `is_root` | `d(v) <= len(w)` for that one state |
| exact distance of v | a complete table, `src/lrx/table_bfs.py`: `DistanceTable.distance` | `d(v)` exactly, for that graph |
| certificate for a family (words or tree) | `integrations/bound3_evaluator.py`: `score_output` | `d(v) <= T_m(n)` for every block length of the family, conditional |
| independent second opinion | `integrations/bound3_audit.py`: `audit_claim` | the same, by a checker that shares no code with the evaluator |

A family is a label order `a` (a permutation of 1..m) and a nonempty gap mask
`S`: bit g set means gap g, the one after g labels, holds zeros.
`integrations/bound_task.py` builds it with `make_family(labels, mask)`. The
unit base has one zero per gap; the family covers every state with at least
one zero in each block. Budget `T = T_m(m+k)`, slope bound `m-2`.

A certificate is `{"words": [...]}` (one root leaf, unit origins) or
`{"tree": NODE}`, where a node is a split `{"j", "t", "le", "ge"}` or a leaf
`{"words", "origins"?, "picks"?, "weights"?}`. The schema and limits are in
`integrations/bound3_task.py`.

Runnable example: the word_C certificate for the m = 11 reversal with zeros in
gaps {0, 11}, plus a stored two-leaf tree for m = 9 {0, 4}.

```python
# save as check_example.py, run with: PYTHONPATH=. python check_example.py
import json, sys
sys.path.insert(0, 'autoresearch/bound-m-260925/checks')
from integrations import lrx_m as C
from integrations.bound_task import make_family
from integrations.bound3_evaluator import score_output
from integrations.bound3_audit import audit_claim
from reversal_m13 import certificate_words

m = 11
fam = make_family(list(range(m, 0, -1)), 1 | 1 << m)       # (11..1){0,11}
words = certificate_words(m)
for w in words:                                            # literal replay on the unit state
    assert C.is_root(C.run_naive(fam['unit_base'], w))
row = score_output(fam, {'words': words})
print(fam['id'], row['status'], row['gap'], audit_claim(fam, row['output'], row['certificate']))

d = json.load(open('autoresearch/bound-m-260925/checks/reversal-midband-words.json'))
tree = next(r for r in d['certified'] if r['m'] == 9 and r['g'] == 4)
fam = make_family(list(range(9, 0, -1)), tree['mask'])
row = score_output(fam, tree['output'])
print(fam['id'], row['status'], row['n_leaves'], audit_claim(fam, row['output'], row['certificate']))
```

Expected output, in well under a second:

```
m11-mask2049-labels11.10.9.8.7.6.5.4.3.2.1 CERTIFIED 0 (True, 'ok')
m9-mask17-labels987654321 CERTIFIED 2 (True, 'ok')
```

Statuses from `score_output` and the evaluator:

- **CERTIFIED**: every leaf passes criterion (8) by exact LP, re-checked by
  `lrx_m.leaf_criterion`. Report it only with the audit agreeing.
- **BOUNDARY**: the best mixture meets the criterion with equality, gap 0.
  Not a certificate.
- **NO_CERTIFICATE**: the best mixture misses by `gap`. The candidate's
  words fail; the family is not refuted.
- **INVALID_OUTPUT**: a word does not sort, or the output breaks the schema.
- **INCOMPLETE**: CPU, wall or sandbox limit. Never read it as a negative.

To score a candidate program on a frozen set, use the sandboxed CLI. It
refuses to overwrite its output file.

```sh
python -m integrations.bound3_evaluator --program autoresearch/bound-m-c3-260926/seed/c3-seed.py \
  --families autoresearch/bound-m-260925/frozen/development.json --output /tmp/lrx-dev20.json --limit 20
python -m integrations.bound3_audit --families autoresearch/bound-m-260925/frozen/development.json \
  --results /tmp/lrx-dev20.json
```

With the c3 seed this printed 12 certified of 20 and an audit with 12 agree,
0 disagreements. Use a fresh output path each time.

Every certificate report carries this line: "Conditional on the research
group's Lemma 1 (with refinement) and criteria (7)/(8) applied at general m;
proved by the group for m = 8 only."

## 2. Build or reuse exact tables

A table stores one byte per visible state: the distance from the sorted
root. The state count is `n!/r!`. Files are `dist_m{m}_r{r}.bin` plus a
`.json` sidecar with `radius`, `layer_sizes`, `complete` and `table_sha256`.
`DistanceTable` checks the sha256 on load and refuses an incomplete table.

Look up a distance:

```sh
python -c "
from src.lrx.table_bfs import DistanceTable
t = DistanceTable('datasets/generated', 8, 2)
print(t.radius, t.distance((0,8,7,6,5,4,3,2,1,0)))"     # 42 41
```

Build tables:

| builder | command | memory |
|---|---|---|
| registry set (m <= 9, n <= 12) | `python -m src.lrx.cli table build-registry --workers 8` | about 2 min, 123 MB on disk |
| in-memory, one table | `python -m src.lrx.cli table build M R --out DIR --workers W --max-bytes B` | about 5 bytes RAM per state; refuses above `--max-bytes` (default 2 GiB) |
| low-memory | `python -c "from tools.table_bfs_lowmem import build_table_lowmem as b; print(b(M, R, 'DIR', workers=4)['radius'])"` | numpy memmaps on disk: the table plus bit-packed frontiers; low RAM |

The two builders write byte-identical files; tests and the (9,4), (8,4) and
(10,2) rebuilds confirm it. Recorded build times with the low-memory builder
and 4 workers: (10,2), 239.5 million states, 409 s; (11,2), 3.1 billion
states, 3.2 h. (12,2) would have 4.4e10 states and is out of reach here.

Rules:

- Tables go under `datasets/generated/` (gitignored), in a dated subdirectory
  for new campaigns. Never commit a table.
- Both builders refuse to overwrite. An interrupted build is INCOMPLETE and
  proves nothing.
- Record `table_sha256`, the state count and the radius in the claims entry.
- Sanity checks before use: `complete` is true, the layer sizes sum to
  `n!/r!`, and shortest words you extract replay literally. Session 18 of
  the claims register also sampled 20,000 states for the triangle
  inequality under L, R, X.
- Scripts look in fixed directories: see `DIRS` in
  `autoresearch/bound-m-260925/checks/reversal_words.py` and `TABLE_DIRS` in
  `integrations/bound3_control_revtree.py`.

## 3. Run the proof-shaped bound task with your own proposer

The bound task asks for a program `certify(family)` that works for any m and
uses no tables. The evaluator (bound-eval-3) runs it in the sandbox with a
3 s CPU limit per family and scores the output exactly. The task contract
is `autoresearch/bound-m-260925/TASK.md`; campaign 3 is specified in
`autoresearch/bound-m-c3-260926/TASK-c3.md`.

**Splits.** Keep them frozen and never mix them.

| split | file | use |
|---|---|---|
| development | `autoresearch/bound-m-260925/frozen/development.json` (303 families, m = 9, 10) | search, prompts, feedback |
| validation | `autoresearch/bound-m-c2-260925/frozen/validation.json` (165, m = 11) | kill check and finalist selection only |
| holdout | `autoresearch/bound-m-c2-260925/frozen/holdout.json` (165 m = 12 + 60 m = 11) | once per frozen finalist, never in a prompt |

Hashes are in each `frozen/manifest.json`. The evaluator CLI refuses a
holdout-type file without `--holdout` and a frozen finalist manifest. If you
run your own loop, keep your proposer on development only and do not read
the holdout.

**Two ways to plug in a proposer.**

1. Your harness writes candidate source files and scores each with the
   evaluator CLI from section 1. Keep your own ledger and stop rules.
2. Use the repository driver with any OpenAI-compatible chat endpoint.
   `python -m integrations.bound_c3 run --engine sequential --seed 1 --broker-url http://127.0.0.1:PORT/v1 --run-dir FRESH_DIR --iterations N`
   sends prompts there. `autoresearch/bound-m-c3-260926/mock_api.py` is a
   loopback mock that shows the protocol. The sequential arm runs in the
   current interpreter. GEPA, AdaEvolve and EvoX need the `.venv-official`
   interpreter built from `integrations/requirements-official.txt`.

**Live campaign workflow.** This is what the repository does for its own
campaigns. Live calls need explicit human authorization.

1. Capture first prompts offline through the mock:
   `bash autoresearch/bound-m-c3-260926/run-captures-c3.sh`. It writes
   `first-prompts/first-prompt-<arm>-s<seed>.{md,sha256}`. Read them and grep
   for leaked validation or holdout ids.
2. Compute the approval hash over configs, seed and first-prompt hashes:
   `python -m integrations.bound_c3 approval-hash --write-material autoresearch/bound-m-c3-260926/approval-material.json`.
3. A human reviews the material and writes the hash to
   `payload-approved.sha256`. `check-approval` refuses to start otherwise,
   and a run whose first prompt differs stops as FIRST_PROMPT_MISMATCH.
4. The budget broker (`integrations/research_budget.py`) holds the API key,
   binds to loopback, reserves a conservative cost per request and keeps a
   durable ledger per (arm, seed): `broker-ledger-bound-c3.<arm>-s<seed>.json`.
   Each run's cap is the campaign cap minus the other ledgers. Transient
   502/503/504 and 429 with Retry-After are retried up to 3 times inside the
   same reserved slot. A halted ledger is resumed only with an audit note:
   `python -m integrations.research_budget --resume --ledger PATH --note "why"`.
   Never hand-edit a ledger.
5. Launch with `bash autoresearch/bound-m-c3-260926/run-campaign-c3.sh` and
   check spend with `python -m integrations.bound_c3 campaign-spend`.
6. Finalize once: `python -m integrations.bound_c3_finalize finalize --run-dir autoresearch/bound-m-c3-260926`.
   It selects each finalist on validation, freezes it, runs a determinism
   check, evaluates the holdout once, and audits every CERTIFIED claim.

**Kill rule (campaign 3).** After the four seed-1 runs,
`python -m integrations.bound_c3 kill-check --seed 1` evaluates each arm's
accepted candidates among its first 15 proposals on validation. If no arm
beats the seed's 157/165, it exits 3 and the campaign stops.

**Success rule (campaign 3).** An arm succeeds only if the mean over its
three finalists beats the seed's m = 12 holdout share by 3 points and
certifies at least 5 of the 14 families every campaign-2 arm missed.
Single-seed wins are reported, not claimed.

## 4. What the engines are good for

On this project the engines did well when an exact scorer gave dense
per-family feedback and a strong seed existed. Evolved `certify` programs
transferred to an unseen m (campaign 1: 129/165 against a hand control's
98; campaign 2: 84.7 % mean holdout share against 59.6 %), and sort programs
beat controls on holdout. They did badly on tasks without a gradient of
partial credit: correlation certificates by exact dual feasibility (2/9,
nothing on holdout), and the m = 9 lift task, where every engine and the
sequential control tied at 190 holdout certificates. Some arms overfit and broke off-distribution. The closed forms
word_C, word_R1 and word_G and the exact negative came from analysis of
exact tables by agents and humans, not from engine runs. One seed per arm
never supports an engine ranking.

## 5. Claims discipline

- Attribute: Lemma 1, criteria (7)/(8), tree certificates, the full m = 8
  package and the manuscript's recurrences are the research group's. No
  priority claims.
- State conditionality on every certificate at m != 8, as in section 1.
- Use one of these labels: computed, replicated, certified (conditional),
  conjecture, observation, negative (exact) or negative (search).
- A finite pattern is an observation. A failed search is not a negative.
- Resource limits give INCOMPLETE, never infinity or "impossible".
- Never execute generated code outside the evaluator sandbox. Never import a
  candidate file into your own process.
- The general conjecture stays open in every summary.

The `lrx-claims` skill in `.claude/skills/` gives the entry template.

## 6. Contribute certificates or negatives

1. Put new work in new files under `autoresearch/<campaign>-<yymmdd>/`.
   Preserve existing run files.
2. Add a re-check script under a `checks/` directory. It must build its
   stored JSON only when the file is absent (`refusing to overwrite`), and
   re-check stored rows with the evaluator, the audit and literal replay.
   `autoresearch/bound-m-260925/checks/reversal_k2.py` is the model.
3. Record which tables a result used, by sha256.
4. Add a Session entry to `research/claims.md` and a section at the top of
   `HANDOFF.md`.
5. Do not modify the trusted core listed in `tools/orchestrator.py`;
   `python tools/orchestrator.py trusted` must print `"ok": true`. New search
   code gets tests in `tests/test_search_*.py`.
6. Run the three verification commands from the README and report their
   actual output.
