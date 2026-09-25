# Budget ledger notes for `lift-m9-260924`

User-approved 2026-09-24 (`TASK.md`): total cap **$150.00** for this run.
This is a fresh ledger path and a fresh cap; it does not reset, merge with,
or replace the legacy `$5` session guard or the `$50` allocation guard from
`autoresearch/loop-260924-protocol/`, both of which remain in force for any
further use of those older ledger paths.

## Prior allocations cited (not reset by this ledger)

- The `$50` allocation: conservative remainder **$16.6923578**, as recorded
  in `autoresearch/loop-260924-protocol/CONTINUATION.md` and
  `autoresearch/next-optimizer-session.md`.
- The `$5` session: conservative spend **$0.9204712 of $5**, as recorded in
  `autoresearch/loop-260924-protocol/CONTINUATION.md` ("Aggregate
  conservative generation accounting ... 4 attempts / $0.6055236" plus the
  stream-focused attempt's $0.3149476 charge = $0.9204712 total).

Neither figure changes here. This run's $150 cap is additional, tracked in
its own ledger at `autoresearch/lift-m9-260924/broker-ledger.json` (created
on first `serve`, not present yet — no live call has been made).

## This run's parameters

See `broker-config.json` for the full machine-readable record. Summary:

| Field | Value |
| --- | ---: |
| Cap | $150.00 |
| Model | grok-4.7 |
| Reasoning cap (enforced locally, not provider-guaranteed) | ~8,000 tokens |
| `reasoning_effort` (ENFORCED provider parameter) | `low` |
| `max_completion_tokens` | 4,096 |
| Input / output rate | $2.2 / $6.6 per million tokens |
| Conservative reservation per request | $0.3460864 |
| Contact ceiling (raw `floor(150 / 0.3460864)`) | 433 |
| Contact ceiling (capped at 400 per authorization) | **400** |

The reservation formula and its inputs (`max_prompt_bytes` = 120,000,
`reasoning_cap_tokens` = 8,000, `max_tokens` = 4,096) are recorded in
`broker-config.json`. It reuses the worst-case-bytes-as-tokens convention
already used by `integrations/research_budget.py`'s `DurableBudget.reserve`,
so it is consistent with (not looser than) every prior ledger in
`autoresearch/loop-260924-protocol/`.

## Why 400, not 433

The team lead's authorization caps the contact ceiling at 400 regardless of
what the reservation arithmetic would otherwise allow; 433 is recorded above
only to show the unrounded computation was checked before capping.

## Status

No live provider call has been made for this run. `broker-ledger.json` does
not exist until `python -m integrations.research_budget serve ...` is run
against this config; `python -m integrations.research_budget --dry-run --run
lift-m9-260924` prints the exact payload that would be sent, for approval,
without creating a ledger or making a network call.
