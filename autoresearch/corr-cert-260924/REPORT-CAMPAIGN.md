# Campaign report: universal coefficients for the correlation certificate

Dates 2026-09-24/25. Goal (PROTOCOL.md): a program coefficients(m) producing
exact Theorem 3 certificates for every m, evolved by GEPA / AdaEvolve /
EvoX with sequential and deterministic controls. Model gemini-3.8-flash,
8192 output tokens after a first attempt at 4096 truncated 12 of 15 calls.

## Outcome against the pre-registered levels

| Level | Criterion | Result |
|---|---|---|
| 1 System works | engine passes m = 4..12, controls do not | **No.** Best of every arm: 2/9 (m = 4, 5, the worked examples in the prompt). Naive seed 0/9. |
| 2 Useful | same program passes holdout m = 13..20 | **No.** 0/8 for every arm. |
| 3 Proved | symbolic proof | Not reached. |

Kill rule (no program passing m >= 10) triggered for every arm. The
ledger hit its 147-contact ceiling as AdaEvolve ended, so EvoX made no
call. Spend $3.25 on the 8k ledger plus $0.33 on the aborted 4k attempt.

| Arm | Calls | Valid | Truncated | Dev passes | Holdout | USD |
|---|---:|---:|---:|---:|---:|---:|
| GEPA | 31 | 30 | 1 | 2/9 | 0/8 | 0.66 |
| sequential | 60 | 1 | 14 | 2/9 | 0/8 | 1.07 |
| AdaEvolve | 56 | 21 | 25 | 2/9 | 0/8 | 1.52 |
| EvoX | 0 | 0 | 0 | 0/9 | 0/8 | 0 |
| naive seed | 0 | – | – | 0/9 | 0/8 | 0 |

Independent audit of every claimed pass: 0 disagreements. Proposals
reduced violation mass (GEPA 234k to 8.7k) but never crossed feasibility
at m = 6.

## What was useful (all offline, deterministic, in REPORT.md and STRUCTURE.md)

1. Independent reproduction of the group's Theorem 1 (C <= 4K + 2H) for
   m = 4..16 with own LP and a stdlib exact checker.
2. New facts: the LP optimum is exactly 0 at every m tested (their positive
   epsilons are rounding); exact epsilon = 0 certificates exist for
   m = 4..9; max E = 0 is attained only at the reversal orders.
3. Negative structural results: no polynomial-in-(a,b,c,m) formula with
   threshold steps (degree <= 3) works beyond m = 8; certificates supported
   on adjacent-label triples exist only up to m = 10, and the needed gap
   width grows about m - 12 beyond m = 15. A universal formula, if it
   exists, must be global, not label-local. This is new information for
   the group's stated open question.
4. Conjecture, labelled as such: the triple LP relaxation is exact
   (optimum 0) for every m. Proved m = 4..9, float evidence to m = 18.
   Suggested proof route: the dual statement that triple-consistent
   pseudo-distributions have E <= 0.

## Why the engines failed here

The target requires exact feasibility of thousands of coupled integer
inequalities; an LLM writing formulas cannot search that space, and the
packet (worst three violations) does not carry enough gradient. The
deterministic LP with a shared-parameter ansatz was the right tool and it
answered the question negatively in 75 minutes. Engines are suited to
constructing objects a cheap evaluator can grade with a smooth signal,
not to solving exact dual feasibility.

## Files

corrcert.py, validate_identities.py, search_lp.py, ansatz_lp.py,
structure.py, kscan.py, tightface.py, certs*/, ansatz/, REPORT.md,
STRUCTURE.md, STRUCTURE_tables.md, TASK.md, frozen/, live-*/, finalists/
(manifest, holdout-results, audit, REPORT.md), broker ledgers and receipts,
approval material. Nothing committed.
