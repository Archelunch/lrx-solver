# Claim register

| Claim | Status and evidence |
|---|---|
| General sorting-radius bound for m>=8 | Open; not proved by this project |
| Radius recursion E_r(n)<=E_(r-1)(n-1)+m-2 | Open |
| Slack-funded lifting bound A_P<=P+m-2 | Open |
| Exact F recurrence | Theorem 1 in supplied manuscript; implementation independently checked on finite domains |
| H absolute-budget reformulation | Derived from the same first-transition decomposition; checked against independent budget BFS |
| F/H/oracle agreement | Exhaustive n=4..7, m=2..n-2, all marked states, F excess 0..4; H budgets 0..diameter(smaller)+4 |
| Reconstructed DP words | Independently replayed at the largest tested H budget for every finite marked-state value in those graphs |
| Family word length6k-2, projection5k-3 | Replayed for k=2..30, m=8k-1, both zero markings |
| Family exact distance6k-2 | Theorem 2 in supplied manuscript; independently certified only for k=2,3,4 at m=8k-1 using disjoint complete balls and explicit words |
| Infinite-family detour barrier2k-2 | Theorem 2 in supplied manuscript, not independently proved here |
| Source's large audits / 48,384,000 states | Reported by manuscript, not reproduced here; source tools unavailable |
| Visible sorting radii E_r(n) | Reproduced by complete ranked BFS (`table_bfs.py`, every layer sum = n!/r!): (m,r)=(4,2)12, (5,2)19, (6,2)25, (5,3)21, (4,4)17, (7,2)33, (7,3)38, (6,4)33, (8,2)42, (8,3)48, (9,2)52, (8,4)54, (9,3)59. All m>=8 values equal T_m(n). Tables cross-checked against `reference_bfs` on every state for n<=7, and against cayleypy 0.2.0 coset BFS: identical layer sizes for all 13 registry graphs (`tools/cayleypy_crosscheck.py`) |
| Radius formula (m-2)n-(m^2-3m-4)/2 for m>=8 | Matches the five m>=8 tables above (n<=12); finite evidence only |
| v2 candidate scores | Probe-based finite evidence. "feasible" means no failure on probes, not a certificate. `certify` checks one whole graph only |
| Potential bound d(v) <= phi_ba656(v), all m, r >= 1 | Short argument below (model-written, checked by the orchestrator, not peer-reviewed); exhaustive `certify` agrees on every table run. Implies E_r(n) <= (floor(n/2)+1)(C(m-1,2)+(m-1)r) + floor(n/2), which is cubic and weaker than E_r(n) <= C(n,2) from the manuscript. Says nothing about T |
| Pure LRX lower bound D_n >= C(n,2) (Antiufeev, arXiv:2601.08715v3) | External claim, not checked here. An external audit (cayleypy_experiments handoff, 2026-09-23) reports its values correct (BFS n <= 12) but its optimality step unproven. Not used by any claim above; statements that rely on it (`misc/LRX_multiset_progress.md` §1 "D_n = N", Prop. 4.3) are conditional beyond BFS range |

The small exhaustive DP cases are **outside m>=8** and test machinery only.
Word replay establishes upper bounds, not shortest-path optimality.
No universal result follows from a finite pattern or a model's explanation.

## Known obstruction

For `k>=2, m>=8k-1, r=2`, the supplied manuscript gives

    v=(1,...,k,0,k+1,...,m-k+1,0,m-k+2,...,m)
    W=L^(k-1) X (RX)^(k-1) R^k X (LX)^(k-2) L^3.

Its proof excludes any universal constant excess-projection allowance.
It does **not** refute the main conjecture. The lab currently tests the
minimal permitted m for each k, and does not claim coverage of all larger m.

The earlier progress notes contain empirical extrapolations and inconsistent
counts. They are motivation, not an authority for universal claims.

## Leads (finite evidence only)

| Lead | Evidence |
|---|---|
| `candidates/leads/1ea0a8de58e2fa16.json` rules controller "circular block insertion" (proposed by grok-4.7) | Every probe state sorted and replayed on all 17 registry graphs (sanity exhaustive; others sampled); max word 84 vs T=42 at (8,2), 299 vs 178 at (16,4). Upper bounds on those probed states only; not a bound on E_r(n). |

Scoring note (2026-09-22): sanity probes are shuffled; a rules/beam fail-fast
stop estimates the failure rate from the checked prefix (`fail_rate_estimated`).
Feasibility is unchanged: any failure still fails the graph.

## Route B: slack-funded lifting A_P(v) <= P + m - 2 (manuscript §6 candidate)

Exact, exhaustive, finite. Engine `src/lrx/lifting_fast.py` (numpy), equal to
the pure-Python DP on every state of six small graphs at three budgets each.
Evidence: `evidence/lifting-check-260922-230343/`.

| (n,m,r) | P=E_{r-1}(n-1) | budget P+m-2 | A_P <= budget | states with A_P > d |
|---|---|---|---|---|
| (10,8,2) | 36 | 42 | holds on all 1,814,400 | 0 |
| (11,9,2) | 45 | 52 | holds on all 19,958,400 | 0 |
| (12,8,4) | 48 | 54 | holds on all 19,958,400 (max = 54) | 59 |
| (11,8,3) | 42 | 48 | **fails on exactly 1 of 6,652,800** | 5 |
| (12,9,3) | 52 | 59 | **fails on exactly 1 of 79,833,600**: v=(2,1,0,0,0,9,8,7,6,5,4,3), d=59=T, A_P=61 (overrun 2) | 1 |

**Counterexample to the lifting statement at (11,8,3)** (not to recursion (1),
not to the conjecture): v = (2,1,0,0,0,7,8,6,5,4,3), d(v) = 47, A_P(v) = 49 > 48.
- Lower side: two independent exhaustive DPs (numpy engine; pure-Python tuple
  DP `tools/verify_lift_independent.py`, output `m8r3-independent.json`) give
  H_42 = 49 for each of the three zero deletions.
- Upper side: replayed lift word of length 49 with projection 41; replayed
  geodesic of length 47 whose projection is 43 for every deleted zero
  (`m8r3-counterexample-certificates.json`).
- With projection cap 43, A(v) = d(v) for every state of (11,8,3).
So the manuscript's candidate needs at least one extra projection letter at
r = 3; whether a bounded extra suffices in general is open.

(12,9,3) is a single-engine result (numpy engine; the pure-Python check does
not scale to 240M marked states). Its failing vector has the same shape as at
(11,8,3) and the overrun grows from 1 to 2: a candidate infinite obstruction
for r = 3, analogous to the manuscript's 6k-2 family at r = 2. Open: describe
the family, prove its overrun, and find which modified lifting budget survives.
At (12,8,4) with projection cap 49, A = d on all but 5 states and max A = 54.

## Route B update, session 02 (2026-09-23)

Finite; details and evidence paths in `autoresearch/r3-family.md` and
`autoresearch/lift-thresholds.md` (runs under `evidence/lifting-check-260922-234448/`).

- **(12,9,3) failure is now two-engine.** An independent forward search
  (`autoresearch/lift_forward.py`, no shared DP code) gives H_52 = 61, 61, 62
  for the three deletions of v = (2,1,0,0,0,9,8,7,6,5,4,3), witnesses replayed;
  the exhaustive sweep lists it as the only over-budget vector at q = P.
- **Correction to the paragraph above:** the failing vectors do not share one
  shape and the overrun does not grow. Exactly one vector fails on each of
  (10,7,3), (11,8,3), (12,9,3): F1_7 = (2,1,0,0,0,7,...,3) overrun 4,
  F2_8 = (2,1,0,0,0,7,8,6,...,3) overrun 1, F1_9 overrun 2. At (13,10,3),
  F1_10 has A_P = 71 = T (tight) and F2_10 has A_P = 68; a targeted exhaustive
  check of the 529 vectors with a zero whose deletion lies at distance >= P-2
  in (12,10,2) finds none over budget (that neighbourhood contains the unique
  failing vector on m = 7, 8, 9). The other ~1.04e9 states of (13,10,3) are
  unchecked.
- u_m = (2,1,0,0,m,...,3) is an antipode of (m+2,m,2) for m = 4..10, and
  d(F1_m) = T_m(m+3) for m = 5..9.
- E_2(12) = 63 = T_10(12): full BFS of (12,10,2) by `table_bfs.build_table`
  (239,500,800 states, complete).
- Projection cap P+1 brings every vector within P+m-2 on every computed graph
  (r = 2..6, n <= 12) whose radius is at most the budget, including (11,8,3),
  (12,9,3), (12,8,4); A = d everywhere needs up to P+3 ((11,7,4)). Candidate
  replacement lemma (open): A_{P+1}(v) <= P+m-2 for m >= 8.
- **(13,9,4), targeted, q = P:** no over-budget vector among the 2945 vectors
  with a zero whose deletion lies at distance >= P-2 = 57 in (12,9,3)
  (P = E_3(12) = 59, budget 66 = T_9(13)). 62 of them have a deletion with
  H_P > 66 (up to 74); each also has a deletion within budget (exact A_P from
  60 to 66, two tight at 66; all 248 witnesses replayed). Evidence:
  `targeted-m9r4-k2.json` (`autoresearch/lift_targeted.py`, 38 min). The rest
  of (13,9,4) is unchecked.

## Route B update, session 03 (2026-09-23)

Finite; details in `autoresearch/r3-family.md` (runs under
`evidence/lifting-check-260923-0838/`).

- **(13,10,3), targeted k = 3, q = P:** no over-budget vector among the 1998
  vectors with a zero whose deletion lies at distance >= P-3 = 60 in (12,10,2)
  (P = 63, budget 71). Four have a deletion with H_P > 71; each has another
  deletion within budget: A_P = 71 (tight, (0,0,10,9,...,1,0)), 68, 68, 66.
  (3,1,0,0,10,9,0,8,7,6,5,4,2) with A_P = 68 is new at k = 3. All 2431 pairs
  COMPLETE, 12 witnesses replayed. Evidence: `targeted-m10r3-k3.json`
  (23 min). The rest of (13,10,3) is unchecked.
- **(13,9,4), targeted k = 3, q = P:** no over-budget vector among the 11258
  vectors with a zero whose deletion lies at distance >= P-3 = 56 in (12,9,3)
  (P = 59, budget 66). 83 have a deletion with H_P > 66 (up to 74; 21 of them
  new at k = 3); each has another deletion within budget, exact A_P from 60 to
  66. Six are tight at 66; four of these are new and every deletion of those
  four lies at distance 56 (slack 3), for example (8,7,9,6,5,4,3,2,1,0,0,0,0).
  So tight vectors reach the edge of the covered band, and a wider band
  (k >= 4) may contain vectors over budget. All 15288 pairs COMPLETE, 332
  witnesses replayed. Evidence: `targeted-m9r4-k3.json` (91 min). The rest of
  (13,9,4) is unchecked.

## Route C: sound potentials (session 03, 2026-09-23)

A potential phi certifies d(v) <= phi(v) on a graph when phi >= 0, phi(root) = 0 and every
non-root state has a neighbour with phi at most phi - 1. Candidates are grok-4.7 proposals;
`python -m src.lrx.cli certify FILE m r` checks every state of one complete table.

- `candidates/probes/a5bd55171a2e922c.json` (round 2): phi = n * (S - m(m^2-1)/6) + k with the
  weighted position sum S. Exhaustive certify holds on m4r2, m5r2, m4r4, m5r3, m6r2, m6r4, m7r2,
  m7r3, m8r2 (max 1123 vs T 42), m8r3 (1544 vs 48) and m8r4 (2021 vs 54, 19,958,400 states).
  Evidence: `evidence/potential-certify-260923-1059/`.
- `candidates/probes/ba656bf2c7e03787.json` (round 3): phi = rot_dist if csorted, else
  (floor(n/2)+1) * e + k. Exhaustive certify holds on m4r2 (max 38 vs T 12), m5r2, m4r4, m5r3,
  m6r2, m6r4, m7r2, m7r3 (200 vs 38), m8r2 (212 vs 42), m8r3 (254 vs 48) and m8r4 (346 vs 54,
  19,958,400 states). Evidence: `evidence/potential-certify-ba656-260923-1311/`.
  Argument (all m, r >= 1). Read positions as offsets o(p) = (p - pos1) mod n. Let I be the
  inversions of the token sequence read clockwise from token 1 and
  excess = sum of token offsets - m(m-1)/2 >= 0 (offsets are distinct, token 1 has offset 0).
  e = I + excess is 0 exactly when the tokens occupy offsets 0..m-1 in order, i.e. csorted.
  L and R change no offset, so e is invariant. Call position q improving when position q+1 holds
  a token t > 1 and position q holds a zero or a token u > t. X at an improving position 0 never
  moves token 1, and since offsets of positions 0 and 1 are consecutive it either swaps u and t
  (I drops by 1, excess unchanged) or moves t one offset down past a zero (excess drops by 1,
  I unchanged): e drops by exactly 1. If no position is improving, every token t > 1 has a
  smaller token directly counterclockwise, so the tokens form one clockwise run 1, 2, ..., m and
  the vector is csorted. With k = shorter circular distance to the nearest improving position,
  a rotation lowers k by 1, and X changes phi by -(floor(n/2)+1) + k' <= -1; if X makes the
  vector csorted, rot_dist <= floor(n/2) < phi. Hence phi descends and d(v) <= phi(v).
  Maximum: e <= C(m-1,2) + (m-1)r, so phi <= (floor(n/2)+1)(C(m-1,2)+(m-1)r) + floor(n/2)
  (m8r3: bound 257, measured max 254). This is O(n m^2); it does not approach T = O(mn).
- `candidates/probes/6ff08052bb698f26.json` (round 4; orchestrator generalisation of grok-4.7's
  5d536a0608217df6 = 4e + k + 2u, whose own argument needs n <= 11): phi = rot_dist if csorted,
  else a * e + k + c * u with u = 1 + number of improving positions, c = floor(n/4), a = c + 2.
  Train: 0 failures on all 11 graphs, value_max 158/186/196 on m8r2/m8r3/m9r2 (3.875x T).
  Exhaustive certify holds on m4r2 (33 vs 12), m5r2, m4r4, m5r3, m6r2, m6r4, m7r2 and m7r3
  (148 vs 38), m8r2 (158 vs 42), m8r3 (186 vs 48) and m8r4 (272 vs 54, n = 12, 19,958,400
  states). The constant version 5d536a0608217df6 **fails** on m8r4: 227 states have no descending
  neighbour, as its n <= 11 condition predicts. Evidence: `evidence/potential-certify-6ff08-260923-1415/`.
  Argument, extending the one above. L and R leave e and u unchanged and lower k by 1. X at an
  improving position 0 lowers e by 1 and only changes the adjacencies (n-1,0), (0,1), (1,2).
  Position 0 stops being improving, so a position that becomes improving is n-1 or 1, at
  distance 1. If the new k' >= 2, no position at distance <= 1 is improving, so u drops by at
  least 1 and phi changes by at most -a + floor(n/2) - c. If k' <= 1, u rises by at most 1 and
  phi changes by at most -a + 1 + c. Both are <= -1 when a >= c + 2 and a + c >= floor(n/2) + 1,
  which c = floor(n/4), a = c + 2 satisfy for every n. If X makes the vector csorted,
  rot_dist <= floor(n/2) <= a + 2c - 1 <= phi - 1 because u >= 2 before the X. So d(v) <= phi(v)
  for all m, r >= 1. Maximum: phi <= (floor(n/4)+2)(C(m-1,2)+(m-1)r) + floor(n/2) + floor(n/4) m,
  still O(n m^2), about half of ba656's bound for large n; it does not approach T.

## 2026-09-23 session 05: erasure identity and bounded lifting checks

An elementary auxiliary lemma, with a move-by-move proof in
`autoresearch/loop-260923-2004/proof-note.md`: for m>=2, r>=1 and any LRX word W
of length ell, label and transport the zeros. Let S count X swaps of two
zeros, and let I_z count rotations carrying zero z across the boundary plus
X swaps of z with a positive token. The uncancelled projection length after
deleting z is exactly `ell-S-I_z`. Thus the minimum over marked deletions is
`ell-S-max_z I_z`. This identifies the erasures a fixed sorting word needs to
certify a lifting budget; it does not establish existence of short sorting
words for every vector. It is an elementary proof, not a formalization or a
claim of novelty in the literature.

A second elementary bound: from full depth t and smaller state w, every
sorting continuation needs at least d(w) full moves, since each projects to
at most one smaller move. Pruning when `t+d(w)>B` is therefore safe for the
bounded question H_q<=B. Exhaustion after this pruning certifies only H_q>B,
not infinity. Implemented only in the search-side forward tool.

Finite result: all **27 distinct vectors** formed by inserting a zero at any
position into any of the **3 antipodes of (m=8,r=4)** have independently replayed
sorting words of length <=60 and, for at least one marked zero, projection
length <=54. Thus **A_54(v)<=60** for this explicitly enumerated family in
(m=8,r=5). The search used q=55, but trusted replay of every marked deletion
of each resulting word establishes the stronger q=54 statement. Word lengths
range from 54 to 60; these are upper-bound witnesses, not exact A values.
Evidence: `autoresearch/loop-260923-2004/m8r5-frozen.json` and
`autoresearch/loop-260923-2004/m8r5-checks.jsonl`.

A frozen 24-vector subset of zero insertions into (8,8) antipodes was tested
at (8,9), q=79, B=84. **All 24 were INCOMPLETE** at 100000 stored states per
marked deletion (checked between BFS layers; the count can overshoot).
They establish neither the proposed lifting claim nor its negation.
Evidence: `autoresearch/loop-260923-2004/target-summary.json` and associated
frozen cases/checkpoint records. The main sorting-radius conjecture remains open.

## 2026-09-23 session 06: constructive fixed-word routing

Auxiliary constructive results, with explicit proofs in
`autoresearch/loop-260923-2036/proof-note.md`:

- For a fixed smaller sorting word V, with no projection-identity letters,
  an optimal lift can use shortest zero-projection repairs of length <=2
  between its letters and at its ends. A dynamic program on n marked positions
  per letter computes its exact minimum lift in O(n(|V|+1)) operations.
  Infeasibility applies only to that word, never all words with the same cap.
- For V using only L and X, let k=#L and j its initial mark. The explicit
  repair procedure in `integrations/word_lift.py` has overhead at most
  `2 floor((k+n-1-j)/(n-2))` whenever its final mark is in the terminal set
  after the prescribed final repair. The proof charges each repair's advance
  of at least n-2 positions against the k left rotations and starting offset.
  The bound is attained by the infinite family j=n-1, V=L^(n-2)X with u the
  inverse image of the smaller root. The endpoint and short-word existence
  conditions remain essential; this does not establish the conjecture.

Finite constructive certificates from six frozen letter-priority geodesic
policies and the exact fixed-word router:

- For all 27 distinct zero insertions into the 3 (8,4) antipodes,
  **A_54(v)<=58**, improving the previous length-60 witnesses. Search 0.171s.
- For all **346 distinct zero insertions into the 39 (8,8) antipodes**,
  **A_77(v)<=83** at (8,9). Search 9.331s. This includes all 24 previously
  resource-incomplete vectors; those 24 alone took 0.560s. Table loading is
  excluded from these search timings. This is a finite family among
  980179200 visible (8,9) states, not a full-graph result.

Each certificate was checked by trusted marked and visible replay. Evidence:
`autoresearch/loop-260923-2036/m8r5-geodesics-certificates.json` and
`autoresearch/loop-260923-2036/m8r9-all-geodesics-certificates.json`.
Full policy outcomes are also preserved, compressed for the 346-case batch.
The method searches a restricted family; a portfolio miss is not a lower bound.

The six geodesic policies still miss the known old-cap (8,3)/(9,3) obstructions,
with best full lengths 49/61. Adding one distance-level projected step repairs
(9,3): projection 53, full length 59. The fixed-priority one-defect portfolio
misses (8,3), but the already-known exact length-47 witness has projection 43
with one uphill step from smaller distance 36 to 37. Thus allowing that step
is not sufficient without suitable subsequent geodesic choices. This is a
construction limitation, not a counterexample to the replacement lifting claim.

All successful hard-family geodesic words here use both L and R; the L/X-only
amortized lemma does not explain them. The universal short-word construction,
mixed-direction repair bound, and general r=2 base remain unresolved.

## Session 07: engine-driven lifting portfolios (finite only)

The fixed-word router now evaluates reusable constrained construction policies
proposed by the existing engines. On 28 frozen development vectors with
q=T(m,r-1)+1 and B=T(m,r), the six-geodesic baseline certifies 20; 12 sequential
proposals produce a 22-case portfolio, and 12 EvoX proposals produce a 24-case
portfolio. Baseline and both frozen finalists certify all 120 fresh random
confirmation vectors, which do not distinguish the policies. No universal
claim or engine ranking follows. The (8,3) obstruction remains a portfolio miss.

For v=(8,7,9,6,5,4,3,2,1,0,0,0,0) at (9,4), both finalists give a trusted
certificate **A_58(v)<=66** by deleting zero j=9. The smaller distance is 56;
RLX priority with an uphill R at projected index 5 gives a 58-letter projection
and 8 invisible repair moves. The six-geodesic baseline's best saved word has
projection 56 and 12 repairs, total 68. This comparison concerns those words,
not all geodesics. EvoX's finalist also certifies the three frozen L/R/X
neighbours. See `autoresearch/loop-260923-2107/evox-run/evals/7e7c102248da0306.json`
and `autoresearch/loop-260923-2107/sequential-run/evals/556ab94746a63a8f.json`.

Removing all detours from the frozen EvoX policy raises development misses
from 4 to 9 (sequential: 6 to 8). These are finite portfolio ablations, not a
necessity theorem. The report, context provenance, full certificates, ablations
and separated confirmation are under `autoresearch/loop-260923-2107/`.

## Supplied nine-gap m=8 theorem: independently checked certificate premises

After session 07 the user supplied `lrx_multiset_nine_gap_m8.pdf`, claiming
for every permutation a of 1..8 and positive ell_0,..,ell_8 that
v=(0^ell_0,a_1,0^ell_1,...,a_8,0^ell_8) satisfies d(v)<=6n-18.
The manuscript's comparison/stretching lemmas reduce all positive lengths to
finite exact rational mixture inequalities. Our separately written data-only
auditor reproduced all 40,320 orders, 4,670 reference words, 152,937 mixture
rows, 42,030 literal stretch checks, and 40,320 comparison-word replays.
Maximum weighted base is 32299/380<85; all weighted slopes are <=6.
The checked source archive and audit are in
`autoresearch/loop-260923-2107/incoming/`; see `paper-review.md` for details.
This supports the manuscript's computer-assisted nine-gap theorem, not a proof
of full m=8 or arbitrary m. No archive code was executed or imported.

Projection coverage 12,680,558 and union coverage 16,107,991 remain attributed
to the supplied manuscript: we did not rerun all projected inequalities, and
the union additionally relies on previous results including <=3-block data
not included in the archive. The reported 4,495,529 remaining families with
4–8 blocks are therefore a research target, not a freshly verified complement.
The next search priority is new rational mixtures after projection. The
single-fixed-macro obstruction has the manuscript's explicit scope and does
not invalidate adaptive constructions or the conjecture.

## Session 08: 76 projected-mixture family certificates

A bounded deterministic search produced exact rational certificates for
**76 distinct m=8 families with 4–8 retained zero blocks**, each covering all
positive lengths through the supplied manuscript's comparison/stretching
lemmas. Of a frozen structural sample, 52/100 development and 24/50 separate
confirmation families were certified. The old inherited weights fail the
projected base-price test on all selected cases, and scalar checks exclude
them from the supplied reverse-order transfer domains. These are additional
certificates relative to those checked methods on named cases, not a freshly
reconstructed global coverage count or a claim of historical novelty.

60 certificates use reweighted inherited word supports; 16 more use existing
words from a fixed 128-word catalog pool. All accepted weights and inequalities
are exact. A separate repeated marked-zero projection audit agreed on 226
unique projected words and replayed 1,811 expanded support-component words.
The infinite-length conclusion uses the exact affine coefficients and the
lemmas, not extrapolation from those replay samples. Evidence:
`autoresearch/loop-260923-2154/train-v2-results.json`,
`confirmation-v2-results.json`, and `certificate-audit.json` in that directory.

Example: for all positive a,b,c,d,
v=(4,0^a,8,3,0^b,6,0^c,1,5,0^d,7,2) satisfies d(v)<=6n-18.
The four weights (1/3,1/5,1/15,2/5) give weighted base 797/15<55 and
slopes (6,6,5,6). The report supplies the averaging/integrality argument and
catalog references. The inherited weighted base 2757/49 fails the <55 test.

A failed initial sampler used the wrong byte order and was stopped by the
baseline guard; its artifacts are preserved and excluded. The corrected
inventory was checked against the supplied data table. Global union counts
remain partly attributed. The 74 search misses prove no infeasibility, and
full m=8 and the general conjecture remain open. No API calls were used.

## Session 09: optimizer-generated words contribute five family certificates

A frozen 512-source catalog closes 14 of session08's 48 remaining development
families. On the other 34, JSON policies optimized by Grok certify four (EvoX)
and two (sequential, contained in the four). Fresh structural confirmation gives
22/30 for the catalog and 23/30 for both finalists, adding the same one family.
Thus five distinct certificates require policy-generated words beyond this
catalog baseline, and 41 named family certificates are recorded overall.
All cover arbitrary positive block lengths through the reviewed manuscript
lemmas and exact rational inequalities. Word expansion audits passed.
Evidence: `autoresearch/loop-260924-optimizer/report.md`, both run directories,
`confirmation-results.json`, and `audit-results.json`.

One seed per arm does not establish engine ranking. EvoX's sole strategy rewrite
brought no improvement. Misses do not prove infeasibility. General m and full m=8
remain open; global coverage counts were not reconstructed. API cost $0.336410;
331 tests and trusted-core hashes pass. No controller lead was changed.
