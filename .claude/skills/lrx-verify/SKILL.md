---
name: lrx-verify
description: Verify an LRX claim with the exact tools in this repo - a sorting word for one state, an exact distance from a table, or a words/tree certificate for a family (a, S). Use before reporting any bound, certificate or distance.
---

# lrx-verify

Run from the repository root with `PYTHONPATH=.`. No provider calls. Never
import or run a candidate program outside the evaluator sandbox.

## Inputs

- **Word claim**: a state v (tuple of labels 1..m and zeros) and a word over L, R, X.
- **Distance claim**: v plus a complete table for its (m, r).
- **Family certificate**: labels (permutation of 1..m), gap mask, and an output
  `{"words": [...]}` or `{"tree": NODE}` (schema in `integrations/bound3_task.py`).
- **Program claim**: a candidate source defining `certify(family)`.

## Commands

Word replay (upper bound for that one state):

```python
from integrations import lrx_m as C
assert C.is_root(C.run_naive(v, word))   # d(v) <= len(word)
```

Exact distance (see lrx-table for building tables):

```python
from src.lrx.table_bfs import DistanceTable
DistanceTable('datasets/generated', m, r).distance(v)
```

Family certificate, evaluator then independent audit:

```python
from integrations.bound_task import make_family
from integrations.bound3_evaluator import score_output
from integrations.bound3_audit import audit_claim
fam = make_family(labels, mask)
row = score_output(fam, output)
if row['status'] == 'CERTIFIED':
    print(audit_claim(fam, row['output'], row['certificate']))   # must be (True, 'ok')
```

Program on a frozen development set (sandboxed, fresh output path):

```sh
python -m integrations.bound3_evaluator --program P.py \
  --families autoresearch/bound-m-260925/frozen/development.json --output /tmp/lrx-eval-NEW.json
python -m integrations.bound3_audit --families autoresearch/bound-m-260925/frozen/development.json \
  --results /tmp/lrx-eval-NEW.json
```

Stored reversal-orbit rows (fast, no tables):

```sh
PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_k2.py        # "problems: none"
PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_midband.py   # "problems: none"
```

Known-good smoke: word_C for m = 11 gives `CERTIFIED`, gap 0, audit
`(True, 'ok')`; see section 1 of `docs/AGENT-GUIDE.md`.

## Reading the result

- **CERTIFIED** with audit `(True, 'ok')`: a certificate. Anything else from
  the audit is a disagreement; report it and do not claim the family.
- **BOUNDARY**: criterion met with equality. Not a certificate.
- **NO_CERTIFICATE**: these words miss by `gap`. The family is not refuted.
- **INVALID_OUTPUT**: a word does not sort or the schema is broken.
- **INCOMPLETE**: a resource limit. Never a negative, never infinity.

## Report line

Every certificate report at m != 8 must include:

> Conditional on the research group's Lemma 1 (with refinement) and criteria
> (7)/(8) applied at general m; proved by the group for m = 8 only.

A replayed word is an upper bound for one state. A table distance holds for
that (m, r) only. The general conjecture remains open.
