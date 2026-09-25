# LRX Lab: current handoff

General conjecture and full m=8 remain open. README and repository summaries stay English.

## Latest iteration: bound-m campaign, transfer to unseen m=11 (2026-09-25)

Four arms on the proof-shaped bound task, then one-shot holdout with all 165
m=11 families: EvoX 129 and GEPA 125 certified with worst gap 4 vs the best
hand control 98 (gap 7); AdaEvolve and sequential overfit (invalid outputs
at m=10,11). Audit 0 disagreements, $3.45. Details in
`autoresearch/bound-m-260925/finalists/REPORT.md`, `BEST-GEPA-CONSTRUCTION.md`,
claims Session 15. Next: fix set-order nondeterminism in the worker
(PYTHONHASHSEED), three seeds per arm, extend holdout to m=12, and hand the
identity-rotation conjecture with its construction to a human for proof.

## Latest iteration: loop v3, bounded-construction and Lean tracks built and live-checked (2026-09-25)

Ultracode workflow (35 agents, Opus/Sonnet) built three tracks as new files:
`integrations/sort_loop3*.py` (seeds, 30-instance GEPA Pareto, SkyDiscover
pareto_objectives + cascade, rich packets with optimal words, reflection on a
second model/ledger, 200 iterations, 3-seed runner), `integrations/bound_*.py`
(proof-shaped objective: certify(family) scored by exact Lemma 1 lift costs and
LP; worst gap to T over frozen family sets at m=9,10, holdout m=11) and
`integrations/lean_*.py` + `autoresearch/lean-loop-260925/lrxlean` (Lean 4.34
project, locked statements L1-L3, evaluator forbidding sorry/axioms/unsafe).
Adversarial review fixed 14 issues with regression tests; 571 tests pass.
Reduced live checks: bound sequential 20 iterations certified 164/303 vs seed
151 ($0.46); Lean sequential closed helper milestones only ($0.08); sort v3
GEPA needed two fixes (manifest path, reflection truncation fallback) before a
clean run. Reports: `autoresearch/LOOP-V3-REPORT-260925.md`,
`LIVE-CHECKS-260925.md`. Commits `fa678e5` and later. Next: full campaigns
(3 seeds per arm) on sort v3 and bound-m within the approved caps; Lean needs
a stronger proposer or a smaller first target.

## Latest iteration: sort-m9 v2 campaign, engines beat controls on holdout (2026-09-25)

Task `sort_word(v)` for m=9 with exact BFS scoring, 0.2 s CPU per state
(search cannot pass), worst-r uniformity term, cyclic-sweep seed. Holdout 2100
states incl. (9,6) and (10,3), once, audit 0 disagreements: naive 157, sweep
control 1846, sequential control 1918 (collapsed to 136/300 on unseen r=6),
EvoX 2053, AdaEvolve 2059, GEPA 2080. $4.58. Descriptive, one seed per arm.
GEPA's best is a heuristic portfolio on the seed construction, no length bound
(`autoresearch/sort-m9-260925/REPORT.md`, `BEST-GEPA-CONSTRUCTION.md`,
`GUARD-NOTE.md`). New exact tables: (9,6) radius 79 < T=80 (first strict gap
at m>=8), (10,3) radius 71 = T. Correlation rerun with fixed plumbing
(hash bca29cd3) running after it. Next: seed SkyDiscover's random_seed,
three seeds per arm, reward bounded constructions over portfolios.

## Latest iteration: trace audit, plumbing fixes, exact m=9 tables (2026-09-25)

A trace audit (`autoresearch/TRACE-AUDIT-260925.md`) found eight plumbing
defects that compromised the correlation campaign (fraction scored by float,
shared cap drained before EvoX, over-strict output parsing, repeated prompts,
GEPA minibatch over one example, stale best-so-far, truncation, misleading
status label). All fixed with 26 regression tests (452 tests OK); the
"engines failed" statement for that campaign is withdrawn pending a rerun.
Exact BFS tables now cover (9,4), (9,5), (8,5), (8,6): radii equal T_m(n).
The group's outer-layer class at m=9 is 94-96 % of all states for r<=5, so
their necessary condition barely restricts at small m; exact pointwise lifting
constants K = 14..20 recorded (`autoresearch/outer-layer-260925/REPORT.md`,
claims Session 13). Next candidate engine task: a uniform sorting program for
m=9 scored by slack against exact distances (train r<=5, holdout r=6 and
(10,3)); then an optional $5 rerun of the correlation campaign with fixed
plumbing. Lift broker output limit for the next run is in
`autoresearch/lift-m9-260924/broker-config.next.json` (8192). Nothing
committed since 4aa3c62.

## Latest iteration: correlation certificate, reproduction and campaign (2026-09-25)

Target: a universal coefficient formula for the group's Theorem 3 certificate
proving C <= 4K + 2H (their numeric certificates stop at m = 16). Done offline:
independent reproduction for m = 4..16, exact epsilon = 0 certificates for
m = 4..9, LP optimum exactly 0 at every m tested, and two negative structural
results (no degree <= 3 polynomial-plus-threshold formula beyond m = 8; no
label-local support, the gap width grows with m). Live campaign of all four
arms on `coefficients(m)`: 2/9 development (the worked examples only), 0/8
holdout, $3.58, kill rule met; independent audit 0 disagreements. Conjecture
recorded: the triple LP relaxation is exact for every m. See
`autoresearch/corr-cert-260924/REPORT-CAMPAIGN.md`, `REPORT.md`, `STRUCTURE.md`.
Remaining approved caps: lift $145.59, corr $21.42. Nothing committed or pushed.

## Latest iteration: live lift campaign, m=8 -> m=9 (2026-09-24)

Plumbing built and used: m-parametric exact evaluator (`integrations/lrx_m.py`,
`lift_task.py`, `lift_evaluator.py`), Gemini/xAI budget broker with local
reasoning abort and durable receipts (`integrations/research_budget.py`),
frozen lift sets, native GEPA/AdaEvolve/EvoX adapters (`integrations/lift_backends.py`),
finalize with one-shot holdout and independent audit (`integrations/lift_finalize.py`,
`lift_audit.py`). All four arms ran live on gemini-3.8-flash: development
336/337/337/334 vs naive 285, holdout 190 for every arm vs naive 158, 84 new
audited m=9 family certificates, 0 audit disagreements, $4.41 spent of $150.
No engine ranking; no lemma. See `autoresearch/lift-m9-260924/REPORT.md` and
`finalists/REPORT.md`. Next: reward new word constructions rather than
re-ranking, raise the output limit to 8k or use diff proposals for GEPA, fix
the stale best-so-far packet line, then a second campaign with repeated seeds.
Remaining cap: $145.59 of the approved $150 (ledgers under `autoresearch/lift-m9-260924/`).
Nothing committed or pushed.

## Latest iteration: independent replication of the external full m=8 package (2026-09-24)

The research group's package `lrx_m8_complete_verification` claims
E_(n-8)(n) <= 6n-18 for all n >= 9 with zero uncovered families. Both its own
replay (30 stages PASS, 1010 s) and an independent stdlib checker written from
the theorem text (every k=4..9 file in full, k>=4 union rebuilt with 0
uncovered, all low-block exception mixtures and trees) pass here. The k<=3
single-word search is replicated in full for k=1 and by seeded samples for
k=2,3 with 0 mismatches; full k=2,3 enumeration is not. The
previously open development family `k5-mask302-order15713` is certified in the
package by projection (base 121/2 < 61) and reproduced by our evaluator. The
m=8 search target is therefore closed by attribution; the optimizer target
moves to a frozen m=9 development set. Cap approved for that pilot: $8 / 20
contacts; no call was made and transport is still unfixed. See
`autoresearch/verify-m8-260924/REPORT.md`, `checker-report.md`, and
`research/claims.md` (Session 10). No commit or push was made.

## Next session pointer (2026-09-24)

The [short restart handoff](.handoffs/codex-s04-budgeted-evox-20260924T1331Z.md) and [proof-oriented optimizer plan](autoresearch/next-optimizer-session.md) specify a bounded native GEPA/AdaEvolve/EvoX pilot, matched controls, exact certificate gates, holdout exclusions, and budget reconciliation. No new experiment or paid call was run while preparing them. Preserve the existing evidence below.

## Latest iteration: focused k5 protocol and confirmation (2026-09-24)

The [initial protocol report](autoresearch/loop-260924-protocol/REPORT.md) is a historical snapshot after two timed-out Grok requests. The [continuation](autoresearch/loop-260924-protocol/CONTINUATION.md) records the final outcome. Frozen all-cuts remained 15/16 on development; the remaining unit-block k5 case was not certified. Independent Sol-authored construction reduced its exact feasible base to 1223/20, still 3/20 above the threshold, and establishes a conditional bound for every positive block-length vector with the first retained zero block of length at least 2. It does not prove the whole k5 family or the general conjecture.

A focused streamed Grok response completed after 533.977 seconds but exceeded the broker reservation, so live GEPA accepted no proposal. The exact source was recovered from the private receipt, evaluated under strict Seatbelt, and accepted in a separate zero-provider offline native GEPA replay. One-shot 16-case structural confirmation was then consumed: fixed catalog 12/16, deterministic all-cuts 13/16, recovered source 14/16. An independent exact audit verifies one extra named family, `k6-mask221-order731`, beyond catalog plus all-cuts, with base 1255/19 < 67 and all slopes at most 6. This is novelty against the frozen controls, not a literature-priority claim. Confirmation results are excluded from future prompts and archive retrieval.

Across this protocol, five generation requests plus one model-catalog GET used six of the 24-contact ceiling. Conservative broker accounting charged $0.9204712 of the $5 session cap, leaving $4.0795288 there and $16.6923578 of the previously recorded $50 allocation. No further provider calls are planned. The final 375-test guarded suite passed without skips in 14.152 seconds; compile, CLI smoke, trusted-lock, and authored-source diff checks passed. The [results](autoresearch/loop-260924-protocol/results.tsv), [handoff JSON](autoresearch/loop-260924-protocol/handoff.json), and confirmation audit give exact sources and receipts. Preserve the raw local receipts and development archive snapshot, but do not put consumed confirmation into model context.

## Latest completed work: official program search (2026-09-24)

The bounded official GEPA, SkyDiscover AdaEvolve, and EvoX live portfolio is
closed. On the frozen 16 development families the fixed direct catalog
certifies 12/16, the original executable seed 14/16, and an independent
post-hoc all-cuts control 15/16. The control adds the named
`k6-mask315-order31970` certificate for all positive block lengths by an
exact direct-word mixture; `k5-mask302-order15713` remains uncertified.
Every paid arm's best stayed at the 14/16 seed. Valid AdaEvolve and EvoX
programs tied it; invalid outputs, a failed strategy diff, and upstream
timeouts supplied development feedback, not a negative theorem.

The coordinator froze four finalist source hashes before local one-shot
confirmation. The catalog-only control and all four finalists certified the
same 6/8, zero addition over catalog; 40 candidate executions succeeded in
Seatbelt. The independent exact audit repriced 38 catalog profiles, checked
72 support appearances and 216 nonunit literal expansions. Confirmation is
consumed and must not enter future model prompts. See the [final report](autoresearch/loop-260924-live/report.md),
[confirmation report](autoresearch/loop-260924-live/confirmation-prep/confirmation-report.md),
and [frozen finalists](autoresearch/loop-260924-live/finalists/manifest.json).

Four durable broker ledgers account for 18 upstream attempts and $1.902142
conservatively against the run's 24-attempt/$8 cap. Three timeouts are charged
at full reservation, with provider billing unknown. The recorded remainder
of the original $50 allocation is $17.612829 on this conservative basis.
All model processes from that closed run are stopped. The final
guarded suite passed 353 tests in 12.587 seconds with no skips, plus compile,
CLI smoke and clean trusted lock. Next research should focus on exact
dual-guided k5 word/profile generation with strict output limits, trusted
replay/LP and a **new** untouched structural confirmation set. No general
proof or optimizer ranking follows from this session.

## Official-framework integration smoke (2026-09-24)

This work is separate from session09's local JSON planner labels. The frozen
pilot inputs under `autoresearch/official-integration-260924/frozen/` contain
16 development and 8 confirmation m8 families with 4–7 zero blocks. The
manifest hashes the source archive, old structural sets, cycle7's 8193-case
certificate list, and all new files. The sets have no pair overlap with those
exclusions. A direct catalog baseline has 4–7 profiles per case.

`integrations/research_budget.py` provides a single durable request and
estimated-spend ledger for official framework calls; `integrations/research_archive.py`
stores queryable development source, score, diffs, and raw word/block traces.
Focused broker/archive tests pass offline. GEPA 0.1.4, SkyDiscover AdaEvolve,
and SkyDiscover EvoX 0.2.0 have each completed a native offline framework
smoke against the trusted evaluator service. All selected the same seed on
development (14/16 family certificates, two above the fixed direct baseline);
the three runs do not rank methods. An AdaEvolve mock request confirmed that
selected archive source diff and raw word/block trace reached the proposer;
an EvoX generated strategy passed upstream validity and executed, with no
score improvement. All three final native manifests record a clean trusted
lock and frozen input hash. No paid calls or confirmation were made. See
`autoresearch/official-integration-260924/report.md` for manifests, counts,
checks, and limits. Final guarded suite: 351 tests in 11.599 seconds, OK,
no skips (`autoresearch/official-integration-260924/final-tests.log`);
compile, CLI smoke, trusted hash, and authored-source diff checks pass. Raw
upstream EvoX `labels.yaml` whitespace is retained as evidence. Preserve old
run files and keep confirmation out of
proposer contexts.

## Latest completed work: session09

Mixture word-policy adapter now uses all four local planners (offline tested).
Paid Grok pilot:12 proposals each EvoX/sequential, one EvoX reflection. Expanded
512-source catalog closed14 of48 prior development misses; EvoX adds4/34,
sequential2/34 (contained in4). Fresh confirmation:catalog22/30, both23/30,
adding the same family. Five LLM additions,41 distinct named certificates overall,
all positive block lengths through reviewed comparison/stretching lemmas.
Global coverage totals not recomputed; no engine ranking. EvoX rewrite did not
improve best. 331 tests, compile, smoke, trusted hashes and certificate audits pass.

Artifacts: `autoresearch/loop-260924-optimizer/report.md`, `handoff.json`,
`audit-results.json`, campaign run directories and `confirmation-results.json`.
Next proposer context: `context-next.json`, development evidence only.

## Next iteration

Extract the successful development word structures; measure offline random
policies and repeated LLM seeds. Consider more terminal phases in the bounded
constructor. Use fresh confirmation; never send consumed confirmation to models.
GEPA can preserve complementary policies; AdaEvolve needs distinct construction
classes. Aim for reusable proof structure and eventually general m.

## Budget and constraints

Current allocation $50; recorded spend before the latest iteration was
$30.485029, remaining $19.514971. The latest four broker ledgers account for
$1.902142 conservatively, leaving $17.612829 before the focused k5 protocol.
Its two timed-out generation requests add $0.4010996 conservatively, leaving
$17.2117294. Actual provider billing for all five timeout reservations is
unknown.
Session09 cost $0.336410, provider-reported, not invoice-reconciled. Legacy spend
guard is separate; never silently reset it. Exact payload approved by user.
Generated program execution and pinned official framework dependencies were
authorized for the separate isolated pilot (scope:
`autoresearch/official-integration-260924/authorization.md`); the trusted
core remains locked.
The focused k5 protocol's exact payload was approved; its two generation
attempts timed out, and no further call is planned in that iteration.
Main controller remains1.5625. Source manuscript global totals remain attributed.
Preserve old untracked runs. No push performed.
