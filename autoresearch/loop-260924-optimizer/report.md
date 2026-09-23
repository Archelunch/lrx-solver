# Session 09: LLM optimizers search for mixture proof certificates

The general conjecture and full m=8 case remain open. This iteration adds
41 distinct named m=8 family certificates relative to session08's named set,
covering every positive block length through the supplied manuscript's reviewed
comparison/stretching lemmas. Five require new LLM-policy-generated words beyond
this iteration's fixed catalog baseline. Global coverage totals are not recomputed.

## Results

| Method | Difficult development families | Fresh confirmation families |
|---|---:|---:|
| Expanded 512-source catalog | 14/48 | 22/30 |
| Sequential finalist, added to fixed baseline | 2/34 remaining | 23/30 total |
| EvoX finalist, added to fixed baseline | 4/34 remaining | 23/30 total |

The two sequential development wins are contained in EvoX's four. Both arms add
the same confirmation family. Thus the unique count is 14+4+23=41, including
4+1=5 LLM additions relative to the 512-source baseline. All selected cases are
disjoint from session08's certificate cases. Confirmation membership uses the
source-reported residual inventory; global baseline exclusions and union counts
were not independently reconstructed here.

The initial seed policy certifies none of the 34 remaining development cases.
Each arm made 12 valid proposals from that seed. EvoX made one additional strategy
reflection (13 requests total); sequential made 12 requests. EvoX's best appeared
before its strategy rewrite, which produced no further improvement. One seed,
unequal reflection overhead, and tied confirmation provide no robust engine
ranking or causal evidence for the strategy rewrite.

Provider-reported cost: EvoX $0.181528, sequential $0.154882, total **$0.336410**.
Wall times: 155.0s and 145.2s, overlapping runs. Input/output token counts were
68,543/11,631 and 56,096/10,827 respectively. These are API usage, not the
orchestrator's own token usage, which was not measured. Remaining allocation:
$19.514971 of the original $50. Billing is not independently reconciled.

## What the optimizer actually searches

`integrations/mixture_policy.py` interprets a bounded JSON policy. For each family,
it chooses linear cuts and scores adjacent inverted pairs using five integer
weights: rotation distance, zeros crossed, zero involvement in a swap, position,
and rank difference. It chooses left/right/shortest rotations, swaps the selected
inversion, and finally returns to canonical phase. Every swap reduces inversions,
so generation terminates. Each policy emits at most 32 complete words per family.
No model-generated code is executed.

Every generated word is replayed and checked against the comparison premises.
Its base cost and block coefficients enter the same LP as the frozen catalog
profiles. Exact rational reconstruction requires weights summing to one, weighted
base <31+6k and every block coefficient <=6. The reviewed lemmas and integrality
then give d(v)<=6n-18 for all positive lengths in that named family. Expanded
sample replays additionally test the implementation; they do not establish the
infinite-length statement on their own.

`integrations/mixture_campaign.py` uses the existing engine planners. All four
(sequential, GEPA, AdaEvolve, EvoX) pass offline adapter tests; only sequential
and EvoX were paid arms. Models receive bounded development failure feedback,
profiles, and a frozen evidence context with hashes. Existing campaign machinery
handles proposals, reflections, deduplication, budget enforcement and logging.
The orchestrator intervened only for setup, authorization, audit and reporting.

## Verification and preserved evidence

- 331 tests passed; compileall, smoke and trusted-core hash checks passed.
- Independent repeated marked-zero projection checks for catalog support words.
- Expanded support-component replays: catalog development 433, confirmation
  baseline 577, sequential development 71, EvoX development 123, sequential
  confirmation 617, EvoX confirmation 613. These overlap across arms and are
  not a count of distinct words.
- `audit-results.json` records exact certificate reconstruction for each category.
- `baseline-results.json`, both run directories and `confirmation-results.json`
  retain policies, weights, words, profiles, prompts, failures and usage.
- The first offline test incorrectly expected one particular seed case to certify;
  the assertion was corrected to check validity and forbidden confirmation
  feedback. No evaluator or acceptance criterion was weakened.
- API launch was initially rejected by automatic review, then explicitly approved
  by the user. The rejected launch made no calls. See `authorization.md`.
- No dependency additions, trusted-core changes, or push. The historical legacy
  spend guard is separate and was not rerun or reset for this allocation.

## Interpretation and next iteration

Keep the adapter and certificates: the LLM-generated policies supply useful new
cost profiles, including one confirmed outside development. Keep the negative
result too: EvoX's rewrite did not improve its best, and confirmation does not
favor either engine.

Next use development evidence to simplify the four successful new constructions
and identify which slopes they improve. Then run a matched offline random-policy
control and a few repeated LLM seeds before attributing gains to optimizer
selection. GEPA can preserve complementary per-family policies; AdaEvolve can
allocate among different construction classes once those classes exist. Current
DSL fixes canonical physical phase and uses monotone adjacent comparisons; its
misses say nothing about other sorting words or the conjecture. A useful expansion
would allow several terminal phases, with verified phase-aware coefficients.

The proof target is a reusable structural construction, eventually for general
m; counting more m=8 certificates is an intermediate step. Do not feed the now
consumed confirmation cases back into future proposer context.
