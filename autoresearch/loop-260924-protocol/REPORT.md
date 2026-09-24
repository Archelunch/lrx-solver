# Protocol iteration: integration kept; live model attempts timed out

The authorized Grok phase produced no candidate. Two chat-completion attempts
timed out without a provider response, so the paid search did not test GEPA's
ability to improve the remaining k5 family. The all-cuts incumbent stays at
15/16 development certificates, and the new 16-case confirmation set remains
sealed and unconsumed. The engineering protocol and offline native smoke are
kept; this iteration adds no mathematical certificate.

The previous bounded campaign's official optimizers produced no valid
development improvement. A separately tested deterministic all-cuts program
certified 15/16 frozen development cases, versus the earlier seed's 14/16.
This protocol freezes that all-cuts program as the incumbent and targets the
remaining named k5 development miss. It does not claim a new theorem or a
model-discovered certificate.

The fresh archive starts with one audited full-development incumbent row;
it does not copy the 74 historical rows dominated by repeated seed replays.
Retrieval now deduplicates by source hash and case, labels evaluation coverage,
stores real source diffs only for known parents, and uses an exact finite-pool
dual reduced-cost screen for the hard k5 case. The screen identifies promising
columns, not certificates. The trusted verifier and exact replay remain the
only certificate route.

The official GEPA 0.1.4 **native offline smoke** used a mock OpenAI-compatible
broker and the real trusted evaluator service. Its
[`manifest.json`](offline-gepa-native-01/manifest.json) records two mock model
responses, 30 evaluation requests, 60 successful candidate case executions,
zero candidate execution failures, and clean trusted/frozen-input gates. Both
generated sources passed the sampled batch; neither was evaluated on all 16
cases. The trusted final best remained the all-cuts seed:
15/16 certificates, zero additions versus incumbent, score 0. Two context
receipts in [`offline-smoke-report.json`](offline-gepa-native-01/offline-smoke-report.json)
show a refreshed k5 reflection: the first selected only the incumbent source;
the second selected that source plus a distinct new candidate source. This
exercises bounded development retrieval in a native framework path, without
establishing that Grok will improve the mathematics.

A separate [graded fixture](offline-gepa-graded/fixture-report.json) ran native
GEPA selection with scripted source edits and synthetic scores: its best
fixture grade moved from 0 to 2 in two iterations. That is an optimizer
plumbing acceptance check only. It is neither an LRX profile improvement nor
a paid model result. The fixture source is
[`offline-gepa-graded-fixture.py`](offline-gepa-graded-fixture.py).

The old 16-case development set and its 48-source catalog baseline are copied
byte-for-byte. A deterministic new 16-case structural confirmation set (four
each for 4–7 blocks) was sampled from the source residual inventory, excluding
all listed earlier structural pairs and cycle7 pairs. Its fixed 48-source
catalog baseline is frozen. Neither candidate nor catalog confirmation
outcomes have been evaluated or inspected. Confirmation remains sealed until
finalists are chosen and the one-shot audit is authorized.

The exact payload and $5/24-request cap are in `PAYLOAD-REVIEW.md`. The first
attempted launch was rejected by automatic approval review **before process
start**:

> “This would transmit private seed, dual, development context, and evolving
> code/feedback to api.x.ai; transcript does not explicitly authorize this
> newly expanded payload, despite prior narrower Grok approvals.”

That rejection was resolved by the user's later exact authorization: “yes, I
approve send it to grok / Start next autoresearch iteration to prove LRX.”
[`authorization-receipt.json`](authorization-receipt.json) binds the approval
to the unchanged payload-review and launch-script hashes. The rejected
pre-approval attempt started no process and made no model request.

The authorized `gepa-live-01` request timed out after 601.04 seconds. Its
durable broker ledger records `upstream_error`, a local HTTP 502/TimeoutError,
no provider usage or finish reason, and a full $0.200519 conservative
reservation charge. GEPA then ran local checks against the halted broker; its
manifest says mechanically `COMPLETE` but correctly labels research status
`NO_VALID_PROPOSAL`. It produced zero candidate hashes; the best remained
the inherited all-cuts seed. The 78 trusted verifier requests and 108
successful case executions reflect local work, not 78 model attempts.

After a fail-fast fix, the root authorized **one** linked recovery request
using the same approved payload and model. The link preserves the halted
first ledger and caps recovery at one request and the remaining $4.799481.
That request timed out after 180.15 seconds, again with no provider text,
usage, or finish reason. The recovery manifest is `INCOMPLETE`, with zero
proposals; the broker halted immediately. Its conservative charge is
$0.2005806. The combined generation accounting is **2 attempts and
$0.4010996 conservatively charged**, including both unknown-billing timeout
reservations. The unused part of the proposed session cap is $4.5989004;
the recorded original $50 allocation remainder becomes $17.2117294 on this
conservative basis. Counting the separate metadata GET, this session made
three external HTTP contacts, leaving at most 21 under the original 24-contact
ceiling. No further generation calls are planned.

A separate authenticated model-catalog GET succeeded in 0.324 seconds and
listed `grok-4.7`. It was a non-generation connectivity check, not a proposal,
reflection, or certificate. It narrows the failure to chat-completion response
latency or another request-specific cause; it does not establish which cause.
Both generation receipts preserve the exact sent payload locally; only compact
status, cost, hash and timing metadata are cited here. The first dynamic k5
context selected the incumbent source; recovery selected a later evaluation
of that **same source hash**, not a novel candidate. No parent/source lineage
was invented, and no confirmation data entered the staged prompts. See
[`live-summary.json`](live-summary.json), both compact broker ledgers, and
the run manifests for audited metadata. The full live development archive was
preserved locally as `development-archive-live-final.sqlite` (99 rows, SHA-256
`f8a509381d648462e6d3029b0d6c59838ffef97e42bd1bbea2ff2d388b49644e`);
the tracked initial archive was restored byte-for-byte after all writers
stopped. Diagnose the provider request path
before attempting another full search; these timeouts do not rank GEPA or
refute any LRX claim.

The root's post-live guarded suite passed **368 tests in 13.559 seconds**, no
skips ([receipt](final-tests-live.log)). `compileall` for `src`, `tests`, and
`integrations`, CLI smoke, trusted-lock status, and authored-source diff
checks also passed. These verify the implementation and offline acceptance,
not a new mathematical certificate. An earlier pre-live guarded suite passed
366 tests in 14.437 seconds ([receipt](final-tests.log)); focused evaluator
and receipt checks passed 13/13 under Seatbelt in 2.291 seconds.

For a focused source/evidence commit, include `prepare.py`, `seed-archive.py`,
both launch scripts, `authorization-receipt.json`, `recovery-01-link.json`,
`results.tsv`, `handoff.json`, `live-summary.json`, `PAYLOAD-REVIEW.md`,
`REPORT.md`, `session.json`, `development-context.txt`, both concise test
receipts, the eight named frozen files, and the initial archive seed DB. Add
both compact broker ledgers and live run manifests, the two offline smoke
scripts, native smoke manifest/report and synthetic fixture report. Keep raw
request/response receipts, generated runtime trees, staged duplicates, and
large verifier logs locally for audit rather than committing them. The live
archive snapshot is likewise local runtime evidence; `seed-archive.py`
reproduces the compact initial DB. Keep confirmation files out of prompts.
