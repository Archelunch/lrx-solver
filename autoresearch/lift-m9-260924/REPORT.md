# Campaign report: m=8 -> m=9 label-insertion lift, live, 2026-09-24

Orchestrator: Claude Fable 5.1. Workers: Opus (evaluator, engine wiring,
finalize), Sonnet (transport, frozen sets). Model: gemini-3.8-flash via the
budget broker, reasoning_effort low, 4096 output tokens, 480 s wall.
User approvals: payload hashes 3ead0205 (Gemini) and 93186c26 (fresh ledger),
cap $150, contact ceiling 400 (user later approved 800; not needed).

## Question

Can GEPA, AdaEvolve and EvoX evolve a program `lift(instance)` that turns a
certified m=8 family certificate into an m=9 certificate for the child family
after inserting label 9? Score: exact m=9 family certificates (weighted base
< 39+7k, all slopes <= 7, all positive block lengths). Contract: TASK.md.

## Sets

Frozen before any live call: 210 development parents / 4588 lift instances,
105 holdout parents / 2295 instances, disjoint, hashes in frozen/manifest.json.
Holdout evaluated once after finalist freeze, never shown to any model.

## Results

| Program | Development (4588) | Holdout (2295) | Model calls | USD |
|---|---:|---:|---:|---:|
| naive seed (fixed control) | 285 | 158 | 0 | 0 |
| Gemini one-shot probe | 317 | not evaluated | 1 | 0.012 |
| GEPA best | 336 | 190 | 78 | 1.73 |
| sequential refinement (control) finalist | 334 (best intermediate 337) | 190 | 60 | 0.77 |
| AdaEvolve best | 337 | 190 | 60 | 1.03 |
| EvoX best | 337 | 190 | 67 | 0.86 |

Independent audit (`integrations/lift_audit.py`, m=8 checker lineage with
M=9, no evaluator import): every claimed development and holdout certificate
replays; 0 disagreements. Union of finalists certifies 84 audited m=9 child
families that the naive control does not (52 development, 32 holdout). Every
holdout addition is certified by all four arms.

Ledger: 264 Gemini calls, $4.167 on broker-ledger-gemini.json; plus $0.218
for the cancelled grok-4.7 attempt on broker-ledger.json and $0.023 on the
two probe ledgers. Total $4.41 of the $150 cap.

## Success levels

- Operational: yes. All three native engines ran end to end live: GEPA
  accepted 14 candidates over 77 reflections with lineage; AdaEvolve ran 50
  iterations on 2 islands with UCB visits [23, 22] and a migration
  opportunity; EvoX generated strategy artifacts and 4 new bests; sequential
  accepted 5 steps. Every arm beat the fixed control on holdout.
- Mathematical: finite only. 84 new audited m=9 family certificates, each an
  exact bound for all positive block lengths. No uniform label-insertion
  lemma was found; the general conjecture remains open.
- Comparative: not established. One seed per arm, one model, one budget.
  All four arms, including the sequential control, reach 190 on holdout.
  No engine ranking follows.

## Findings that matter for the next campaign

1. Proposals overwhelmingly re-rank the same candidate words; exact score
   ties dominated GEPA iterations 5-60. The word constructor itself rarely
   changed. Reward new constructions explicitly.
2. Gains plateaued at 336-337 development within the first accepted
   proposal of each arm. The remaining 4251 instances need a different
   mechanism, not more re-ranking.
3. 4096-token output limit truncated 25-28 responses per whole-source arm,
   concentrated on the best, longest programs. Raise to 8k or switch GEPA to
   diff proposals.
4. gemini-3.8-flash: 6-10 s per call, ~$0.016 per call, no reasoning
   overrun. grok-4.7 with reasoning_effort low streamed ~18 tokens/s and hit
   the 480 s wall with no answer. grok-4.3 worked (10 s) but its one-shot
   program was weaker (286).
5. GEPA's packet best-so-far line was stale; sequential's was not.

## Files

frozen/, probe/, controls/, live-*/ (manifests, consoles, verified sources),
finalists/ (manifest, holdout-results, audit, REPORT.md), broker ledgers and
receipts, first-prompt.md, approval-material.json, payload-approved.sha256,
transport-notes.md, budget-ledger-notes.md. Nothing committed.
