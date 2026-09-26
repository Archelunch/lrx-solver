---
name: lrx-claims
description: Add a Session entry to research/claims.md and a matching top section to HANDOFF.md for an LRX result, with the required status words, attribution and conditionality. Use after any computation, certificate, negative or campaign worth keeping.
---

# lrx-claims

`research/claims.md` is the claims register: a summary table, then one
`## Session N: <title> (<date>)` entry per iteration, appended at the end.
`HANDOFF.md` has the newest iteration first, directly under the intro lines.
Both are English. Existing entries are history: add a later note instead of
rewriting them (Session 13's addendum is the model).

## Status words

Use exactly one per statement:

| word | meaning |
|---|---|
| computed | complete exact computation here (table, enumeration, exact LP) |
| replicated | someone else's result, re-checked here independently |
| certified (conditional) | evaluator and independent audit agree; conditional on the group's lemmas at general m |
| conjecture | believed for all m or all r, checked only finitely |
| observation | a finite pattern, no claim beyond the data |
| negative (exact) | proved impossible by a complete exact method; name the method and its completeness assumption |
| negative (search) | not found by the methods tried; proves nothing |

Resource limits are INCOMPLETE. Never write infinity, "impossible" or
"no word exists" for a search that stopped early.

## Attribution

Lemma 1, formulas (4)-(6), criteria (7)/(8), tree certificates and the full
m = 8 package are the research group's. The recurrences, the 6k-2 family and
the lifting candidate come from the unpublished manuscript. Name the source
each time; claim no priority. Every certificate at m != 8 carries:

> Conditional on the research group's Lemma 1 (with refinement) and criteria
> (7)/(8) applied at general m; proved by the group for m = 8 only.

## Session entry template

```markdown
## Session N: <one-line result> (YYYY-MM-DD)

Note `autoresearch/<dir>/<NOTE>.md`; data `<json>`; re-check `<script>`
(<who> re-ran it: <exact output summary>).

- <status word>: <statement>, with numbers, m range and tables (sha256).
- <status word>: ...
- Not done or not certified: <list with gaps>.

<Conditionality line.> <Scope: which families or graphs.> The general
conjecture remains open.
```

## HANDOFF section template

```markdown
## Latest iteration: <title> (YYYY-MM-DD)

<What was done, offline or live, spend.> <Main result with numbers.>
<Limits.> Next: <concrete next steps>. Claims Session N.
```

## Checklist

- Every path named in the entry exists; every number matches the stored JSON
  or console output.
- Spend comes from the ledgers, not estimates.
- A re-check command exists and refuses to overwrite its data file.
- Superseded statements get an addendum pointing to the new Session.
- The README "Current state" section is updated only for headline changes.
