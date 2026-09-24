# Official framework integration, 2026-09-24

The official GEPA 0.1.4 and SkyDiscover AdaEvolve/EvoX 0.2.0
(`0d932b690670a7e544388ad362e9876c8bd256a0`) paths now run Python
`propose_words` candidates through a trusted evaluator service and a macOS
Seatbelt sandbox. The verifier core and its lock are unchanged. This is an
integration smoke, not a new optimizer benchmark or a claim that the LRX
conjecture is proved. The user-authorized generated-code exception and its
limits are recorded in `authorization.md`.

Generated words are priced as direct profiles by counting rotations and
zero-block crossings. A triangle bound controls expansion to arbitrary
positive block lengths; exact rational mixture acceptance requires weighted
base below `31+6k` and every block slope at most 6. Imported baseline words
are reconstructed as direct profiles before scoring. Literal replays check
selected finite expansions. The generated-word route does not need a
comparison-cut premise.

The frozen manifest `frozen/manifest.json` records 16 development and 8
confirmation m=8 residual families, split evenly across 4–7 retained zero
blocks. None of the new `(mask, order_index)` pairs overlaps the prior
structural samples or the 8,193 pairs in the cycle 7 certificate file. The
same direct 48-source catalog pool supplies baseline profiles; candidate code
cannot alter those profiles or the evaluator. The development case SHA256 is
`855ba92453c21b038f93210745d61b60ebe0d2a00ef911b8eecc8cc5f0237dc9`.

## Native offline smoke evidence

| Engine | Manifest | Official iterations | Verifier requests / successful case runs / failures | Best development score |
|---|---|---:|---:|---:|
| GEPA | `gepa-smoke-03/manifest.json` | 1 | 23 / 38 / 0 | 2014.0 |
| AdaEvolve | `ada-archive-smoke-01/manifest.json` | 1 | 3 / 48 / 0 | 2014.0 |
| EvoX | `evox-smoke-05/manifest.json` | 3 | 5 / 80 / 0 | 2014.0 |

All three selected the seeded candidate: 14 of 16 families certified, two
above the fixed direct baseline, with no execution or format failures. These
are the same finite development cases and do not rank the engines. Every
listed manifest records the clean trusted status and frozen input manifest
SHA256 `8231facd236a6f6cccf8f3a4a08537bab848d2e73e81c296345812659ac69179`.
The EvoX path generated a search-strategy source at
`evox-smoke-05/output/sky/search/iteration_1/code.py`; its metadata records
`metrics.validity = 1`, and `evox-smoke-05/console.log` records
`MOCK_STRATEGY_SAMPLE_USED`, confirming the evolved strategy ran. Its score
did not improve the seeded candidate.

The model responder was local and deterministic. **Paid API calls: 0; paid
spend: $0.** A future paid pilot must use the single durable broker ledger
and stay within its shared request and estimated-dollar limits. The broker
reserves for output and reasoning, counts errors and reflections, and halts
after uncertain usage. Provider billing can exceed a requested reasoning
limit, so its dollar figure is an estimate, not an invoice guarantee.

The development archive is SQLite and stores candidate source, parent diff,
score, feedback, raw word/block traces, provenance, and claim status. The
official runner appends verifier results and stages a bounded read-only
selection into the next run's prompt. This route was exercised by
`ada-archive-smoke-01/manifest.json`: archive row 1 was selected, context
SHA256 `b12656b7f051677cc2b718266280e48353f209be050627f9c4f9a578b71d13a8`,
and the mock upstream proposer log recorded both
`archive_raw_trace_seen: true` and `archive_source_diff_seen: true`. Its
three verifier requests produced 48 successful candidate case runs and three
new archive rows in `development-archive.sqlite`. This is selected pre-run
context, not autonomous file navigation. Confirmation rows are rejected by
the archive and confirmation files are not staged for the optimizer. No
confirmation was run in this integration smoke.

## Verification and limits

The final guarded command `LRX_TEST_SANDBOX=1 python -m unittest discover -s
tests -p 'test_*.py' -v` ran **351 tests in 11.599 seconds, OK, no skips**
(`final-tests.log`). It was launched with filesystem approval so the nested
Seatbelt checks could run. `python -m compileall -q src tests integrations`,
`python -m src.lrx.cli smoke` (`passed: true`, `visible_states: 12`),
the authored source/document diff check, and `trusted_status()` (`ok: true`,
no changed or missing locked files) passed. Raw upstream EvoX `labels.yaml`
artifacts retain their generated whitespace and were not rewritten. The
focused broker/archive suite ran 8 tests OK.

The frozen sample does not establish coverage of all 4–7-block families, any
8-block completion, or the general m=8 sorting radius. Each accepted
all-positive-length family certificate relies on the direct expansion bound
and exact mixture argument above. No paid method comparison, fresh
confirmation, or independent mathematical proof was performed here.
