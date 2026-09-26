---
name: lrx-bound-campaign
description: Run, resume or finalize an LRX bound-task campaign (certify(family), bound-eval-3) with the official engines GEPA, AdaEvolve, EvoX and the sequential control - prerequisites, first-prompt capture, approval hash, launch, spend, kill check, finalize, audit, and what to record. Live calls need explicit human authorization.
---

# lrx-bound-campaign

Reference campaign: `autoresearch/bound-m-c3-260926/` (spec `TASK-c3.md`,
prep report `REPORT-prep.md`). Driver `integrations/bound_c3.py`, finalize
`integrations/bound_c3_finalize.py`. Commands below use its default
campaign directory.

## Hard stops

- No live call without explicit human authorization for this campaign, cap
  and model. `payload-approved.sha256` is written by a human only.
- Never open or print the holdout file before finalize.
- Never execute candidate code outside the Seatbelt sandbox.
- Never edit trusted-core files, ledgers or existing run directories.

## 1. Prerequisites

- `.env` holds `GEMINI_API_KEY` (and `XAI_API_KEY` for older runs). Check the
  names only; never print values.
- `.venv-official/bin/python` exists (built from `integrations/requirements-official.txt`).
- `python tools/orchestrator.py trusted` prints `"ok": true`.
- The three verification commands from the README pass.
- Model id and prices in `broker-config-c3.json` were re-checked against a
  live listing by the human who approves.

## 2. First prompts and approval hash (offline)

```sh
bash autoresearch/bound-m-c3-260926/run-captures-c3.sh     # loopback mock, fresh paths, refuses existing
python -m integrations.bound_c3 approval-hash --write-material autoresearch/bound-m-c3-260926/approval-material.json
```

Read `first-prompts/*.md`. Grep them for validation and holdout family ids;
there must be none. Give the human the printed hash and the material. The
current c3 hash starts `ebac59b3`. Any config, seed or prompt change gives a
new hash and needs a new approval.

## 3. Launch (after approval only)

```sh
python -m integrations.bound_c3 check-approval             # refuses without a matching payload-approved.sha256
set -a; . ./.env; set +a
bash autoresearch/bound-m-c3-260926/run-campaign-c3.sh
```

Order: seed 1 of every arm, then the kill check, then seeds 2 and 3. One run:
`bash autoresearch/bound-m-c3-260926/run-one-c3.sh <arm> <seed>`. The runner
stops on a `HALT` file, a refused start, `FIRST_PROMPT_MISMATCH`, exit 3 from
the kill check, or two runs ending `INCOMPLETE` or `BROKER_STOPPED`.

## 4. Spend and broker

```sh
python -m integrations.bound_c3 campaign-spend             # contacts, charged_usd, pool, max_usd
```

Each (arm, seed) has its own ledger
`broker-ledger-bound-c3.<arm>-s<seed>.json`; its cap is the campaign
`max_usd` minus the other ledgers. The broker retries 502/503/504 and 429
with Retry-After in the same slot. A halted ledger is resumed only with an
audit note:

```sh
python -m integrations.research_budget --resume --ledger PATH --note "why"
```

A rerun of an (arm, seed) needs fresh run and ledger paths; the driver
refuses existing ones.

## 5. Kill rule

```sh
python -m integrations.bound_c3 kill-check --seed 1        # exit 3 = stop the campaign
```

It scores each arm's accepted candidates among the first 15 proposals on
validation; the campaign stops if none beats the seed (157/165).

## 6. Finalize and audit (once, human-run)

```sh
python -m integrations.bound_c3_finalize finalize --run-dir autoresearch/bound-m-c3-260926
```

It selects finalists on validation only, checks determinism, evaluates the
holdout exactly once, audits every CERTIFIED claim with `bound3_audit`, and
writes `finalists/REPORT.md`. Success needs both pre-registered conditions
in `TASK-c3.md`, averaged over the three seeds.

## 7. Record

- Claims: a new Session in `research/claims.md` with per-arm means and SDs,
  seed and control rows, target-family counts, audit disagreements, calls
  and USD from the ledgers, and the conditionality line (see lrx-claims).
- HANDOFF: a new top section with the result, spend and next step.
- Report failures and kills as they happened. One seed per arm is
  descriptive, never an engine ranking.
