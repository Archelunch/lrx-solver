# Closed live iteration handoff — confirmation audited

The next official LRX program-search iteration was prepared with a shared
budget and frozen development cases. Automatic approval review rejected the
first EvoX launch before the broker forwarded a request because prior Grok
permission did not specifically cover the prepared private payload. The user
then said, “Yes, I approve sending requests to grok. Do proper autoresearch”.
The official backend worker is authorized to resume under the same limits.
The earlier zero-call rejection remains in `payload-review.json`; use the
durable `broker-ledger.json` for current usage as runs proceed.

The frozen inputs and hashes are in `manifest.json`. Use only the 16 frozen
development cases and their direct baseline during search. The eight
confirmation cases are sealed; the coordinator must freeze finalist source
hashes before a one-shot confirmation evaluation. The 24-attempt/$8 estimated
cap covers EvoX strategy and reflection calls, GEPA reflections, AdaEvolve
proposals, retries, and failures. It is a broker reservation cap, not a
provider invoice guarantee.

`development-context.txt` contains reviewed development-only mathematical
targets. `development-archive.sqlite` contains one offline seed row with source,
score, and raw development traces. The compact prompt preview in
`payload-preview/archive_context.json` selects the two failed-family traces
and bounded source/diff excerpts; it was transmitted to EvoX only after the
user's explicit approval. The exact
finite-pool dual audit and conditional direct-mixture proof note are in
`development-dual-audit.json` and `direct-mixture-criterion.md`. Their results
do not establish infeasibility, all of m=8, or the general conjecture.

An independent all-cuts deterministic control was added after live prompts
began. `allcuts_seed.py` and `offline-allcuts/` show 15/16 development
certificates, adding `k6-mask315-order31970` over the frozen 14/16 seed.
This is post-hoc development evidence, not a precommitted baseline or an
optimizer gain; only k5 remains uncertified by this control. The frozen
research context remains intact; `development-context-v2.txt` adds this
control for future fresh arms only, not the already staged AdaEvolve run.

The first authorized EvoX segment attempted four upstream calls. Two were
small connectivity checks; one variation-operator call settled with usage but
no adopted rewrite was verified; the fourth
timed out and was charged at its full reservation because provider usage is
unknown. The broker then failed closed. EvoX's runner returned `COMPLETE`,
but its four configured iterations did not complete successfully: the trusted
best remained the seed at 14/16, with two evaluation requests and 32
successful case replays. The search strategy file is marked
`is_fallback: true`; it does not demonstrate a generated or adopted strategy.
The original ledger accounts for four attempts and
$0.3371082 conservatively. The coordinator authorized a new ledger with at
most 20 attempts and $7.6628918 remaining, preserving the aggregate cap of
24 attempts/$8. Sum both ledgers; do not represent the timeout reservation
as known provider billing.

The initial GEPA continuation then made one high-reasoning Grok request that
timed out after 600 seconds. The runner was mechanically `COMPLETE` but
produced no valid proposer output or improvement. Its 29 evaluator requests
yielded 44 successful case replays with zero case failures; the trusted best
was still the seed at 14/16. The second broker ledger halted and conservatively
charged $0.2575012, whose actual provider bill is unknown. The coordinator
authorized a third ledger capped at 19 requests and $7.4053906, the exact
remaining aggregate allowance. Sum all three ledgers. The low-reasoning
continuation changes conditions, reinforcing that this is not an engine
benchmark.

`gepa-low/manifest.json` completed three model calls with explicit low
reasoning. It had 35 evaluator requests, 46 successful case replays and four
case failures; its best remained the seed at 14/16, score 2014.0. The three
generated sources were invalid or mixed-output proposals, including one that
returned 56 words beyond the 32-word cap. The third ledger charged $0.3412772
for those three settled calls. The aggregate is now eight attempts and
$0.9358866 conservatively accounted; 16 attempts and $7.0641134 remain
within the original cap. The independent all-cuts k6 gain is separate.

`adaevolve-low/manifest.json` returned mechanically `COMPLETE` after two
settled model calls and one 600-second timeout. One generated source ran all
16 cases and tied the original seed at 14/16; another failed execution on all
16. The trusted best remained seed, with 4 evaluator requests, 48 successful
case replays and 16 failures. AdaEvolve's three attempts account for
$0.4665826 conservatively, including a full $0.2752486 timeout reservation
with unknown provider bill. The third ledger closed at 6 attempts/$0.8078598;
aggregate use across the first three ledgers is 11 attempts/$1.4024692.

The coordinator authorized one final `evox-low` arm: two iterations, 1200
seconds wall time, fourth ledger capped at 13 attempts/$6.5975308. The
first proposed staging sent the new all-cuts source and v3 context; automatic
review rejected that newly derived payload before any upstream request, so
the fourth ledger stayed at zero attempts/$0. The coordinator narrowed the
final attempt to the byte-identical original approved four-cut seed, original
research context and original archive preview. The all-cuts 15/16 result
remains offline control only; the live input baseline is again 14/16. If
automatic review rejects this narrower stage too, stop live calls. There
are no further arms afterward. Confirmation remains sealed.

The narrowed `evox-low-approved/` stage passed automatic review and completed
with manifest hashes matching the original approved seed/context/archive
preview. Its first generated source ran all 16 cases and tied the seed at
14/16; iteration two produced no valid diff. There was no adopted strategy
rewrite or gain. The fourth ledger settled seven requests at $0.4996728.
All model processes are stopped and no more live calls are planned.

Final aggregate across four ledgers: 18 upstream attempts, $1.902142
conservatively accounted against the $8/24 cap. Fifteen responses settled
with token usage ($1.1281468); three upstream timeouts were charged at their
full combined $0.7739952 reservation, actual provider charges unknown. The
recorded original $50 allocation balance is $17.612829 under that
conservative accounting. All paid-arm bests remained the original 14/16
seed. The only new development certificate is the independent all-cuts k6
control, giving session union 15/16; k5 remains uncertified. Do not rank
engines from these sequential, unequal contexts and settings.

The coordinator froze four finalists in `finalists/manifest.json`: original
seed, independent all-cuts control, valid AdaEvolve tie, and valid EvoX tie.
No confirmation case was used during search. One-shot local confirmation is
complete: catalog and all four finalists certified the same 6/8, with zero
addition over catalog and 40/40 Seatbelt executions successful. The
independent saved-output audit repriced 38 catalog profiles, checked 72
support appearances and 216 nonunit literal expansions; the coordinator
reran that auditor successfully. This confirmation set is consumed and must
not enter future model prompts. Do not run any more model calls.
The coordinator's final full suite passed 353 tests in 12.587 seconds with
no skips (`final-tests.log`); compileall passed and trusted lock status
remained clean. `report.md` has the complete provenance and limitations.
