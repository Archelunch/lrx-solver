# Protocol iteration: offline implementation kept; live launch blocked

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

The proposed Grok payload and $5/24-request cap are in `PAYLOAD-REVIEW.md`.
It explicitly includes the newly derived all-cuts code, frozen dual,
development context, and evolving development candidate/feedback excerpts.
The root attempted the exact prepared `launch-live-gepa.sh`; automatic
approval review rejected it **before the process started**:

> “This would transmit private seed, dual, development context, and evolving
> code/feedback to api.x.ai; transcript does not explicitly authorize this
> newly expanded payload, despite prior narrower Grok approvals.”

No broker ledger or live run directory was created, and no model request was
made. The live phase is blocked pending explicit approval of this payload;
there is no workaround launch. The engineering integration is kept, with no
new mathematical gain. Zero live Grok requests and zero new paid cost are
attributed to this session.
The earlier recorded $50 allocation remainder is $17.612829 on conservative
ledger accounting; the proposed $5/24 ceiling is not yet spent.

The root's final guarded suite passed **366 tests in 14.437 seconds**, no
skips ([receipt](final-tests.log)). `compileall` for `src`, `tests`, and
`integrations`, CLI smoke, trusted-lock status, and authored-source diff
checks also passed. These verify the implementation and offline acceptance,
not a new mathematical certificate.
The root's later focused evaluator and receipt checks passed 13/13 in 2.291
seconds under Seatbelt.

For a focused source/evidence commit, include `prepare.py`, `seed-archive.py`,
`launch-live-gepa.sh` (prepared only), `results.tsv`, `handoff.json`,
`PAYLOAD-REVIEW.md`, `REPORT.md`, `session.json`, `development-context.txt`,
`final-tests.log`, the eight named files in `frozen/`, and the initial
`development-archive.sqlite`; include the two offline
smoke scripts, native smoke `manifest.json` and `offline-smoke-report.json`,
and synthetic `fixture-report.json`. The other `offline-gepa-native-01/` and
`offline-gepa-graded/` files are generated runtime outputs, staged duplicates,
mock ledger receipts, and large evaluator logs. They are local audit artifacts
but are not needed in a compact implementation commit. Keep the frozen
confirmation files out of model prompts even though their hashes are recorded.
