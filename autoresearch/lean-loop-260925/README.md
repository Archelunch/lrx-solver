# Track 3: Lean in the loop (implementation, 2026-09-25)

Design: `SPEC-track3.md`. Install: `INSTALL-LOG.md`. Lemma 1 and Lemma 4 are the research
group's results; the statements here formalise them and say nothing about the open conjecture.
No provider call has been made. No `payload-approved.sha256` exists, so every `run-*.sh` refuses to start.

## Layout

| Path | Role |
|---|---|
| `lrxlean/` | locked lake project (core only): `LrxLean/Defs.lean` model + `LRX.Stmt.{L1,L2,L3,M1..M7,M9}`, `LrxLean/Conformance.lean` (473 `rfl` examples generated from `src/lrx/state.py` by `gen_conformance.py`), `Audit.lean` (trusted `lrxaudit`) |
| `lean.lock.json` | sha256 of sources, `Defs.olean`, `lrxaudit`; checked before every evaluation. Written by the implementer, pending human review and re-lock |
| `seed.lean` | control (a): every target and milestone stated with `sorry` (score 0) |
| `reference/control-L1.lean` | human-written reference proof of L1 (pipeline control). Not on any sandbox read path, never in prompts |
| `adversarial/exploits.lean` | wrong type, user axiom, shadowed `Stmt`, redefined `exec`, `native_decide`, forged footer line, lemma spam |
| `controls/` | `seed-stub.json`, `reference-L1.json`, `sweep.json` (control (b), LLM-free tactic sweep) |
| `broker-config.json`, `campaign-config.json` | fresh ledger prefix `broker-ledger-lean`, max_usd 18, 108 contacts, per-arm sub-caps 35/35/35 |
| `first-prompt-{gepa,sequential,adaevolve}.{md,sha256}` | offline captures through `mock_api.py` |
| `approval-material.json` | everything a live arm sends or spends; its hash is the approval hash |
| `smoke-*` | mock-HTTP engine smokes (zero provider calls) |

## Code (search side; recommend adding the evaluator files to TRUSTED after review)

`integrations/lean_task.py` (contract, bans, blocks, scoring, lock), `lean_worker.py` (Seatbelt
runner: no network, no `process*`, exec of listed binaries only, rlimits, RSS watchdog, killpg),
`lean_evaluator.py` (stages A/B/C, packets, CLI), `lean_backends.py` (verifier service, GEPA,
AdaEvolve, sequential control, approval, live wrapper; EvoX excluded), `lean_control_sweep.py`,
`lean_finalize.py`. Tests: `tests/test_search_lean_task.py`.

## Commands

```
python -m integrations.lean_evaluator eval FILE [--response] [--full]
python -m integrations.lean_evaluator verify-lock
python -m integrations.lean_control_sweep --output controls/<fresh>.json
python -m integrations.lean_backends approval-hash --write-material approval-material.json
python -m integrations.lean_finalize --output finalists/<fresh>.json
```

## Fix pass (2026-09-25, lean-loop findings)

Helper credit A now counts only theorems reachable from a *closed* root whose type uses a
`LrxLean.Defs` constant (`Audit.lean`; `lrxaudit` rebuilt, `lean.lock.json` re-written by the
implementer, still pending human re-lock). The footer covers every declared id in any layout, and
footer-line errors add no penalty or pruning. Word bans skip comments (fail-closed comment lexer);
`#` and ``` stay banned everywhere. The cache key binds the evaluator source hash and the sandbox
flag. Unsandboxed runs and stage C "no verdict" results are never cached. The SYSTEM prompt lists every banned word.
Fresh evidence: `smoke-{sequential,gepa,adaevolve}-fix*`, `controls/sweep-fix.json`,
`smoke-finalize-fix.json`. The previous first prompts and approval material are in `superseded-prefix-260925/`.
