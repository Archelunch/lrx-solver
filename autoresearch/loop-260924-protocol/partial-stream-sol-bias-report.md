# Bounded interpretation of an interrupted proposer stream

The saved external stream ended before producing a complete program or word. It suggested biasing selection-sort rotations around costly zero blocks and asserted an unverified profile with base 55 and slopes `[8, 8, 7, 3, 3]`. The two sources below are Sol-completed interpretations of that idea, **not** completed Grok proposals or evidence for the asserted profile. Both target only frozen development case `k5-mask302-order15713`; the trusted evaluator retains the fixed catalog and all-cuts incumbent for every case.

| Interpretation | Source SHA-256 | Accepted words on k5 | Minimum new reduced cost | Exact feasible base after | New certificates vs incumbent |
| --- | --- | ---: | ---: | ---: | ---: |
| Cuts 4 and 10 | `2087a451036ffae9cae686a415a520cd93f4380a4bd8d9d37361d6ffbf525850` | 1 | `55/28` | `24149/392` | 0 |
| All 13 cuts, two tie directions | `38db120c55f99dcf05808d15362856d27ef19711ac27321b5f8f7b8685bc026d` | 20 | `55/28` | `24149/392` | 0 |

Sources: [first interpretation](partial-stream-sol-rotation-bias.py), [second interpretation](partial-stream-sol-rotation-bias-allcuts.py). Strict Seatbelt development evaluations: [first JSON](partial-stream-sol-bias-eval-01/2087a451036ffae9-evaluation.json), [second JSON](partial-stream-sol-bias-eval-02/38db120c55f99dcf-evaluation.json).

Both ran on all 16 frozen development cases without an execution or format failure. Each scored 0 under the incumbent-relative metric: the 15 certified cases are inherited, while the remaining k5 case kept base `24149/392`, above the strict threshold 61 by `237/392`. The lowest reduced cost is positive, so these accepted profiles do not improve the incumbent LP under the verified old-pool dual. This is a statement about these finite generated pools, not infeasibility.

The independent saved-output auditor checked source hashes, 423 fixed direct profiles, accepted direct profiles (1 and 20 respectively), exact primal and dual diagnostics, 48 certificate support profiles, and 144 nonunit literal replays per evaluation. No confirmation case or model API was accessed. Audit command, with the corresponding source and JSON arguments:

```sh
python autoresearch/loop-260924-protocol/audit-development.py --program SOURCE --evaluation EVALUATION_JSON
```
