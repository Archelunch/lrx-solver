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
| Full m=8 bound E_(n-8)(n) <= 6n-18, n>=9 (external group package, 2026-09-24) | External computer-assisted claim. Replicated here on 2026-09-24: package replay PASS (30 stages, 1010 s); independent stdlib checker verifies every k=4..9 certificate file in full, rebuilds the k>=4 union with 0 uncovered, and verifies all low-block exception mixtures and trees. Low-block single-word search replicated in full for k=1 and by seeded samples for k=2,3 with 0 mismatches (see `autoresearch/verify-m8-260924/checker-report.md`). Lemmas hand-checked, not formalised. Attributed to the group; no priority claim |
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

## Session 10: independent replication of the external full m=8 package

On 2026-09-24 the research group supplied `lrx_m8_complete_verification`
(834 MB, 147 manifest entries, all SHA-256 verified), claiming
E_(n-8)(n) <= 6n-18 for every n >= 9 with all 20,603,520 (a,S) families
covered. This is the group's theorem, not ours. Two replications ran here,
recorded under `autoresearch/verify-m8-260924/`:

1. **Their pipeline, our machine.** `scripts/replay_multiset_m8_package.py`
   unchanged: 30 stages PASS in 1009.6 s, completion audit reports 0 remaining
   families and rejects 5 negative controls (`replay-full.json`).
2. **Our checker, written from the theorem text.** Stdlib and exact Fractions,
   no package script imported (`checker/`). Every k=4..9 certificate file
   verified in full by Lemma 3 transfer, formula (11), and criteria (7)/(8),
   with literal stretched execution at z = 0, e_j, 2e_j and adjacent pairs:
   four 262,513 / five 337,965 / six 228,966 / seven 74,614 / eight 10,278 /
   nine 40,320 families, 0 failures, 0 stored-claim mismatches. The k>=4
   union was rebuilt over all 8! x 382 masks without any package coverage
   table: 0 uncovered, per-k counts equal to the package table. All 338
   one-block exception mixtures, 37,323 two-block trees and 639,357
   three-block trees pass. Five corrupted records were rejected.

The repo's hardest development family `k5-mask302-order15713` (unit block
a=1, our pool optimum 1223/20) is certified in the package by Lemma 4
projection from seven-gap record 37688 (mask 446): weights 3/44, 5/11, 9/44,
3/11, weighted base 121/2 < 61, slopes (6, 63/11, 6, 6, 6). Reproduced by a
stdlib replay and by `integrations/projected_mixtures.py`
(`autoresearch/verify-m8-260924/k5-mask302/REPORT.md`).

Low-block single-word certificates were partly replicated by an independent
bounded search from the section 7 resource table: k=1 in full (362,542 words,
the 338 exceptions match exactly); k=2 and k=3 by seeded samples of 5,000
bases plus listed exceptions, 0 mismatches. Not independently replicated: the
full k=2 and k=3 enumerations (1.81M and 6.65M bases), the unlisted
fewer-block exception counts (290, 65+36,888), the Lean files, the
C++ programs, and the n>=130 theorem (unneeded, since the unbounded criteria
were checked). Lemmas 1-4 were read and re-derived, not formalised. The
general conjecture for arbitrary m remains open. No optimizer was involved
and no provider call was made; optimizer contribution this session is zero.

## Session 11: live three-engine campaign on the m=8 -> m=9 lift task

After the m=8 replication, the search target moved to a label-insertion
gadget: a program lifting certified m=8 family certificates to m=9 children
(budget T_9(n) = 7n-25; unit-base criterion weighted base < 39+7k, slopes
<= 7). Frozen sets: 210 development parents / 4588 instances, 105 holdout
parents / 2295 instances. Model gemini-3.8-flash through the budget broker,
after a grok-4.7 attempt hit the 480 s wall with no answer.

Exact finite results, all independently audited with 0 disagreements
(`autoresearch/lift-m9-260924/finalists/`): the naive fixed gadget certifies
285 development and 158 holdout m=9 families; GEPA 336 / 190, sequential
refinement control 334 (337 intermediate) / 190, AdaEvolve 337 / 190, EvoX
337 / 190. The union adds **84 audited m=9 family certificates** (52
development, 32 holdout) beyond the control, each an exact bound for all
positive block lengths of that family. Cost $4.41 of the $150 cap over 264
calls.

Operational success: all three native engines ran live end to end with
mechanism traces. Mathematical: finite certificates only; no label-insertion
lemma and no progress on the general conjecture. Comparative: not
established; one seed per arm, all arms tie the sequential control on
holdout. Proposals mostly re-ranked the same constructed words; the
constructor itself rarely changed. Misses prove nothing.

## Session 12: correlation certificate C <= 4K + 2H, reproduction and ansatz search

The group's note (2026-09-24) proves C <= 4K + 2H for 4 <= m <= 16 via a
general certificate criterion (their Theorem 3) plus numeric LP certificates,
and states that a universal coefficient formula is missing. Their coefficient
files were not available. Here (`autoresearch/corr-cert-260924/`):

- Definitions and Lemma 2 identities re-derived and validated by full
  enumeration for m = 4..8 and seeded samples for m = 9, 10; no failures.
  Max E = C - 4K - 2H is 0, attained only at the reversal orders p_i = -i.
- Certificates regenerated independently by LP (system scipy, search side
  only) and re-checked by a stdlib exact checker for every m = 4..16; all
  epsilon < 1, corruptions rejected. New facts: the LP optimum is exactly 0
  at every m tested (positive epsilons are rounding), and exact epsilon = 0
  certificates exist for m = 4..7 with Q = 1, 1, 2, 596. This reproduces
  their Theorem 1 for m <= 16 with independent code and is not a priority claim.
- Negative result: coefficient formulas polynomial of degree <= 3 in
  (a, b, c, m) with step terms at the kappa thresholds (and q times steps)
  fit m = 4..8 but fail exactly at m = 9; no such family reaches m = 12.
  The obstruction concentrates on triples with a unit gap and on wrap rows
  q + t > m (dual certificates stored). So a universal formula, if it
  exists, is not of that polynomial-plus-threshold form.
The general conjecture is untouched. Misses prove nothing beyond the stated
ansatz classes.

Addendum (2026-09-25): the structure hunt (`STRUCTURE.md`) shows certificates
supported on adjacent-label triples exist only for m <= 10, and the needed
gap width grows with m (2 for m = 11..14, then 3, 4, 5, 6 at m = 15..18), so
no label-local universal formula exists. Exact epsilon = 0 certificates are
now verified for m = 4..9. Conjecture (not proved): the triple LP relaxation
is exact, optimum 0, for every m; proved m <= 9, float evidence to m = 18.
A live campaign of GEPA / AdaEvolve / EvoX / sequential on the program
`coefficients(m)` produced no certificate beyond the two worked examples
(m = 4, 5) on development and none on holdout m = 13..20; $3.58 spent
(`autoresearch/corr-cert-260924/REPORT-CAMPAIGN.md`). Engines do not solve
exact dual feasibility; the deterministic LP did.
Correction (2026-09-25): a trace audit (`autoresearch/TRACE-AUDIT-260925.md`)
found plumbing defects that invalidate the engine comparison in the
correlation campaign (fraction-to-float scoring bug, exhausted shared cap,
over-strict output parsing, repeated prompts, stale packet line). The
deterministic mathematical results stand; the "engines failed" statement is
withdrawn pending a rerun with fixed plumbing.

## Session 13: exact m=9 tables and the outer-layer class (2026-09-25)

New exact radii by complete ranked BFS (`src/lrx/table_bfs.py`, tables under
`datasets/generated/outer-layer-260925/`, sha256 recorded):
(9,4) radius 66 on 259,459,200 states; (9,5) radius 73 on 726,485,760 states;
(8,5) 60; (8,6) 66. All equal T_m(n). Together with the locked tables, the
conjecture is verified at m=9 for r<=5 and at m=8 for r<=6.

Against the group's note of 2026-09-25 (deletion criterion, Theorems 1-2,
condition (6)): the class of m=9 states whose every single-label deletion lies
in the outer layer P-c_p < d_q <= P contains 93.7 / 95.2 / 95.7 / 94.5 / 94.5 %
of all states for r=1..5 (full enumeration, no sampling), because each (8,r)
radius equals P. Theorem 2 alone proves the remaining 5-6 %, whose distances
stay 20-29 below T. Every class member is within budget (class maximum equals
the radius). Exact pointwise lifting constants: d(v) <= min_q d_q(v) + K with
K = 14, 15, 17, 18, 20 for r=1..5, exceeding n-1 by 5..7. Distance-T states
number 1, 2, 5, 1, 6; ten of fifteen have the label cycle exactly reversed.
The note's example is confirmed: d(u)=34 (their upper bound is tight), d(v)=43.
Cross-checks (independent BFS, rank checks, literal replay of extremal words):
0 failures. Finite results for m=9, r<=5; patterns are observations.

Addendum (2026-09-25, tables for the sort task): two further complete ranked
BFS tables, built with the unmodified `table_bfs.build_table` and verified by
an independent checker (sha256, layer sums, triangle consistency, literal
replay of shortest words; `autoresearch/outer-layer-260925/INDEPENDENT-CHECK.md`):
(10,3): 1,037,836,800 states, radius 71 = T_10(13), 4 states at the radius,
sha256 6deed7ea4ad9ea199a12877fe8c50485207f39d35814b9ff591d2a4fa505285f.
(9,6): 1,816,214,400 states, radius **79 < T_9(15) = 80**, 26 states at 79,
no state at 80, sha256 4f8cc2c236511a5f0fe3f7462c8a32180050132edca41ec567d4c892ddcee6dd.
This is the first computed case with m >= 8 where the visible sorting radius
is strictly below T_m(n); the earlier statement "all m>=8 values equal
T_m(n)" in the table above holds for the graphs listed there, not universally.
The reversal (0^6,9,...,1) and the reflection image (2,1,0^6,9,...,3) have
distance 73 at (9,6), not extremal. Tables live in `datasets/generated/`
(gitignored); hashes above identify them.

## Session 14: uniform sorting program for m=9, live campaign (2026-09-25)

Task: evolve `sort_word(v)` for m=9 with exact scoring against complete BFS
tables, 0.2 s CPU per state so state-space search cannot pass. Development
1500 states (r=1..5), holdout 2100 states including (9,6) and (10,3),
evaluated once; independent audit 0 disagreements
(`autoresearch/sort-m9-260925/REPORT.md`). Holdout within-budget counts:
naive 157, cyclic-sweep control 1846, sequential control 1918 (collapsed to
136/300 on the unseen r=6), EvoX 2053, AdaEvolve 2059, GEPA 2080 of 2100;
GEPA 290/300 on (9,6) and 295/300 on (10,3). Each within-budget word is an
exact certificate for its one state. No program meets T on all sampled
states; GEPA's best is a heuristic portfolio on the seed's construction with
no length bound. One seed per arm: descriptive, not an engine ranking. The
general conjecture is untouched.
Correlation rerun with fixed plumbing (2026-09-25, v3): still no certificate
beyond the worked examples m=4,5 in any arm; three campaigns now agree. The
negative is specific to LLM proposers on exact dual feasibility; the
mathematics from the deterministic LP work stands
(`autoresearch/corr-cert-260924/REPORT-CAMPAIGN.md`).

## Session 15: bounded-construction campaign, evolved certifiers transfer to m=11 (2026-09-25)

Task (`autoresearch/bound-m-260925/TASK.md`): a program certify(family) emits
words for the unit base of an m-label family (a,S); the evaluator recomputes
exact Lemma 1 lift costs, solves an exact LP, and certifies the family for all
positive block lengths iff weighted base < T_m(unit)+1 and all slopes <= m-2
(the group's criterion (7) with m as a parameter). Development: 303 families
at m=9,10; holdout evaluated once: 468 families including all 165 at m=11
(never seen by any engine). Model gemini-3.8-flash, 168 calls, $3.45.

Holdout certified (m=9/10/11 of 153/150/165) and worst gap at m=11:
EvoX 108/119/**129**, gap 4; GEPA 91/105/**125**, gap 4; sweep+LP control
76/84/98, gap 7; AdaEvolve 127/111/100 and sequential 124/114/109 with
invalid outputs at m=10,11 (bound broken off-distribution). Independent
audit (`integrations/bound_audit.py`, lrxm8 checker with M=m): 0
disagreements. Each certified family is a machine-checked theorem
d(v) <= T_m(n) for every block-length vector of that family, conditional on
the group's Lemma 1 and criterion (7).

New: two evolved, m-parametric constructions (no m-specific data) certify
125-129 of 165 unseen m=11 families with sound worst-case gap 4, against 98
for the best hand-written control. The constructions are bubble sorts on the
universal cover with new cursor routings and per-zero complementary word
selection (`BEST-GEPA-CONSTRUCTION.md`). Conjecture only: identity-rotation
families are certified at every m. No family class is proved for all m; the
general conjecture remains open. One seed per arm; no engine ranking.
Determinism caveat: the GEPA and EvoX finalists truncate a word union in
set order; audited certificates are unaffected, reproducibility is not yet.

## Session 16: bound-m campaign 2, three seeds, transfer to unseen m=12 (2026-09-25/26)

Campaign `autoresearch/bound-m-c2-260925/`: development m=9,10 (303 families),
validation = campaign-1 m=11 holdout (165, used only to pick each arm's
finalist), holdout evaluated once = 165 fresh m=12 families plus 60 fresh
m=11 families, all never seen by any engine. Seed program = campaign-1 EvoX
finalist. Four arms x three seeds, 30 iterations each, gemini-3.8-flash,
360 calls, about $7. Per-family word pool (development only) reported as a
secondary metric; selection standalone.

Holdout certified share, mean over seeds (SD): AdaEvolve 84.7 % (4.4),
EvoX 83.1 % (0.8), GEPA 80.3 % (0.5), sequential 76.4 % (6.9); seed 80.0 %;
sweep+LP control 59.6 %. Best single finalist: AdaEvolve seed 2 certifies
148 of 165 m=12 families and 54 of 60 fresh m=11 families; the control
certifies 95 and 39. Independent audit 0 disagreements; every finalist
deterministic under PYTHONHASHSEED=0; no m-specific literals. Each
certified family is a machine-checked bound d(v) <= T_12(n) for all block
lengths of that family, conditional on the group's Lemma 1 and criterion
(7) at general m. GEPA returned the seed unchanged in two of three seeds.
This is the first multi-seed result where evolved constructions beat both
the seed and the hand control on an m none of them saw. No family class is
proved for all m; the general conjecture remains open.

## Session 17: tree certificates (bound-eval-3), construction note, broker retry (2026-09-26)

Evaluator `integrations/bound3_*.py` (new files; `bound_evaluator.py` and
TRUSTED untouched) accepts a tree of box splits with leaves of words and
decides the group's criterion (8) per leaf by exact LP, re-checked by
`lrx_m.leaf_criterion`, plus a literal lift at sampled block lengths. Limits:
depth <= 6, <= 32 leaves, <= 32 words per leaf. A plain word list scores
byte-identically to bound-eval-2 (20 development families, every status,
gap and score equal). Audit `bound3_audit.py` reuses `lrxm8` through an exact
affine change of the m=8 criterion; it agrees with the evaluator on 411/411
stored campaign-2 rows and 24/24 new tree certificates.

Tree control (`bound3_control_revtree.py`, words taken from exact tables, so
not m-uniform): the m=9 reversal (9..1){0,4} is CERTIFIED with three leaves
(u0 in [1,2], [3,4], >= 5), where every campaign-2 arm had gap 15/7 or 9/5;
the m=8 analogue reproduces the group's 3-leaf tree; the m=10 tight family
{0,10} is CERTIFIED; the m=10 reversal {0,4} is not (gap 47/20: certified up
to u0 = 4, but u0 >= 5 needs origins above 2 and no (10, r>=4) table exists). Of the 43 development families AdaEvolve-s2 misses, the
tree control certifies 19 (16 at m=9, 3 at m=10; 8 rev_rot, 7 tight, 2 refl,
1 high_inv, 1 uniform). Nothing at m=11: no (11,r) table yet, so the limit is
word supply, not the certificate shape. Conditional on Lemma 1 with
refinement.

Construction note `bound-m-c2-260925/BEST-C2-CONSTRUCTION.md` (read-only):
AdaEvolve-s2 keeps the seed's routings and Lemma 1 price and adds lift
variants at every k (second window for even n, reversed tie-break in the
sum-0 normalization), rotated cursor start, two sweep modes, and a
hull/Frank-Wolfe word selection. It certifies 19 m=12 families the seed
misses and loses none; EvoX-s3 (variants only for k <= 4) gets 5 of those.
All arms miss the same 14 m=12 families, worst the plain reversal with two
zeros at gap 5. Observations only: identity rotations 23/23 and the easy
class 45/45 across m=9..12 in every arm.

Broker: bounded in-slot retry for 502/503/504 and 429 with Retry-After (3
tries, backoff 2/4/8 s, never after a partial stream), receipts record each
try; 4 mock tests. Suite 604 tests OK. No provider calls this session.
The (11,2) exact table (low-memory builder) is at layer 52 of about 75.

## Session 18: exact (11,2) table, reversal with two outer zeros has distance 74 (2026-09-26)

Complete ranked BFS of (m,r)=(11,2), n=13, 3,113,510,400 states, by the
low-memory builder (`tools/table_bfs_lowmem.py`, 4 workers, 3.2 h, table
sha256 `1c3f4915f4bea4e856d2eaed66f1c58caa4c7f43d896ae25e63475bc83192325`,
`datasets/generated/m11-260925/`, gitignored). Checks: layer sizes equal the
byte histogram, no unreached state, triangle inequality on 20,000 random
states under L, R, X, and literal replay of the extracted words.

Radius 75 = T_11(13). Exactly two states at 75: (0,0,11,10,...,1) and its
rotation (2,1,0,0,11,...,3); eight states at 74. The reversal with two outer
zeros, (0,11,10,...,1,0) (family 11..1 {0,11}, mask 2049), has exact
distance 74 = T-1; a shortest word is stored in
`autoresearch/bound-m-260925/checks/m11-r2-reversal-words.json`. So the
base-bound gap 4 recorded for that family in REVERSAL-OBSTACLE.md was a
limit of the word generators, not an obstruction: a unit-corner word of
length T-1 exists. The rotations of that state have distances
74,73,72,71,71,71,72,73,74,74,75,74,75. Family 5.4.3.2.1.11..6 {5,10} has
unit distance 64. The conjecture E_2(13) <= T_11(13) holds with equality.

## Session 19: reversal with two outer zeros, shortest words at m=8..11 and certificates to m=12 (2026-09-26)

Note `autoresearch/bound-m-260925/REVERSAL-WORDS.md`, script and words in
`checks/`. Exact (10,2) table built (409 s, low-memory builder, sha256
equal to an in-memory rebuild). Tables (8,2), (9,2), (10,2), (11,2) all
checked (histogram, no unreached, 20,000-sample triangle and predecessor).

Computed: the unit state (0,m,...,1,0) has distance exactly T_m(m+2) - 1 for
m = 4..11 (41, 51, 62, 74 at m = 8..11); numbers of shortest words 108,
132, 1104, 1296; every shortest word has floor((m+1)^2/4) - 1 swaps. The
radius of (m,2) equals T_m for m = 8..11 and is attained by exactly two
states, (0,0,m,...,1) and (2,1,0,0,m,...,3). Three stdlib generators of
words as pure functions of m: word_E(m) reproduces a shortest word at
m = 8..11 and sorts the state with T-1 letters for every m = 8..200 by
literal replay (upper bound only); word_A(m) (length T-1+floor((m-10)^2/2),
slopes (9,8) for all m) and word_B(m) (length T-1+floor((m-8)^2/2), slopes
(7,6); the W_m word of REVERSAL-OBSTACLE.md).

Certified, conditional on the group's Lemma 1 and criterion (7) at general
m, evaluator bound-eval-3 and the independent lrxm8-based audit agreeing
(orchestrator re-ran both): family (m..1){0,m} for all block lengths at
m = 9 (word_B), m = 10 (word_A and word_B with weights 1/2, 1/2), m = 11
(word_A alone, 74 letters, slopes (9,8)), m = 12 (word_A and word_E with
weights 6/7, 1/7). Not certified at m = 13..16 (gap 6/5 at m = 13, growing):
word_A's base overshoots T by about (m-10)^2/2 while every shortest word
has slope about 3m/2 > m-2, so no shortest word or mixture of shortest
words certifies at m >= 10. At m = 11 the stored lexicographically least
shortest word has slopes (15,14) and does not certify; word_A does.

Conjectures only: d((0,m,...,1,0)) = T_m(m+2) - 1 for all m; the (m,2)
radius equals T_m with exactly two extremal states for all m >= 8. What a
proof for this family needs from m = 13 on: an m-uniform word (or mixture)
with base <= T and slopes <= m-2 at once, which none of the three
generators provides.

## Session 20: m-uniform certificate for the reversal with two outer zeros, m = 9..40 (2026-09-26)

Note `autoresearch/bound-m-260925/REVERSAL-M13.md`, generator and words in
`checks/reversal_m13.py`, `checks/reversal-m13-words.json`. The "two-core"
word word_C(m, a), a pure stdlib function of (m, a): core 1 grows a zigzag
around the zero block carrying a labels across it (a label carried through
the zeros inside a sweep costs exactly 2 per zero, so the Lemma 1 slopes
are (2a+1, 2a)); core 2 is an in-place zigzag on the other m-a labels; a
final R walk ends the word. Closed forms verified by replay for m = 9..200
(worker) and m = 9..120 (orchestrator): length - T = 2(a-(m-2)/2)^2 - 1 -
(m mod 2)/2 for every a except a = 2 floor(m/2).

Certificate of the family (m..1){0,m} for all block lengths, root leaf,
unit origins, no tree: odd m, one word with a = (m-3)/2, length T-1, slopes
(m-2, m-3); even m, weights 1/2, 1/2 on a = (m-2)/2 (length T-1, slopes
(m-1, m-2)) and a = (m-4)/2 (length T+1, slopes (m-3, m-4)), averaging to
base T and slopes (m-2, m-3). CERTIFIED by bound-eval-3 and the independent
lrxm8-based audit at every m = 9..40 (worker 32 rows; orchestrator re-ran
all 32 with replay to the root), and by lrx_m.mixture_criterion. The LP
over the whole family a = 0..m at m = 9..20 selects exactly this support.
At m = 9..11 the T-1 words are members of the enumerated shortest sets.
Why the earlier generators failed: word_E carries zeros through labels at
cost 3 per crossing (slope about 3m/2); word_A lets only 4 labels cross
(base overshoot (m-10)^2/2).

This is the first m-uniform, closed-form certificate family in this
repository. Scope and conditionality: one family only; conditional on the
group's Lemma 1 and criterion (7) at general m; evaluator and audit ran to
m = 40, replay only beyond. Conjecture: the certificate holds for all
m >= 9 (a hand proof needs only the two closed forms above).

## Session 21: reversal orbit, 111 certified families and a second closed form (2026-09-26)

Note `autoresearch/bound-m-260925/REVERSAL-ORBIT.md`; words, trees and
search scripts in `checks/reversal_orbit.py`, `checks/reversal-orbit-words.json`,
`checks/reversal_orbit_search/`. Generic insertion-core generator
core_word(state, t, cores, fin) (two cores grown by partial carries, zeros
tied), full enumeration, Pareto front on (base, slopes), then the exact
leaf LP at the root or in a memoized tree search (depth <= 3, thresholds
<= 5, refined origins). The orchestrator re-ran every stored row through
bound-eval-3, the independent audit and literal replay: 111/111 agree.

- Second closed form: word_R1(m) = core_word(state, (m-3)//4, [(0, m//2,
  'l'), (m//2+1, None, 'r' if m%4==1 else 'l')], 'R') certifies the
  reversal with zeros in gaps {1,m} (the mask-4098 type, gap 3 in every
  campaign-2 arm) with one word of length T-2 (T when m = 2 mod 4) and
  slopes <= m-2; CERTIFIED and audited at m = 9..40 (orchestrator re-ran
  all 32), replay and criterion (7) to m = 200 (worker).
- Reversal with zeros in gaps {0,4}: CERTIFIED at m = 10..16 (two-leaf
  trees at m = 10, 11; root leaf at m = 12..16); not at m = 9.
- All two-zero masks of the reversal: m = 9 42/45, m = 10 53/55 certified.
  Misses: m = 9 {0,4}, {0,5}, {5,9}; m = 10 {0,5}, {0,6}. The m = 11..16
  survey was not run.
- Of the 14 m = 12 families every campaign-2 arm missed: 10 CERTIFIED
  (masks 4097, 4098, 2064, 4113, 1060 by a two-leaf tree, 1089, 4370,
  5252, 165, 4592); 130 (near_rev) and 7300 not certified; 6309 and 3534
  not completed (CPU). Of the m = 11 misses: 145 CERTIFIED; 1056 and 2456
  not; 3685 not completed.
- Every miss binds on the base, not the slopes: slopes <= m-2 are feasible
  at the root and the minimum base excess over T is 7/3, 4, 1 (m = 9),
  17/4, 4 (m = 10), 74/15 (mask 130), about 5.41 (7300), 2 (1056), 9/2
  (2456). The trees tried did not close them.
- Hand-proof sketch (REVERSAL-ORBIT.md section 4, labelled a sketch) of
  the word_C closed forms: len = (a^2+3a-1) + ((r-1)^2+r-2) + W0 +
  floor(a/2) with r = m-a and W0 = r/2+1 (r even), (r+3)/2 (a, r odd),
  (r+1)/2 (a even, r odd), giving len - T = 2(a-(m-2)/2)^2 - 1 - (m mod 2)/2
  for 1 <= a <= m-2; slopes (2a+1, 2a) from 2 per zero per carried label
  with cursor-crossing terms cancelling inside sweeps (exception a = 1, m
  even: (4,3)). Numerically checked m = 5..60.

Per-m rows other than word_C and word_R1 are search outputs, not formulas.
Conditional on the group's Lemma 1 and criteria (7)/(8) at general m.

## Session 22: k=2 reversal masks, closed form word_G for the outer band (2026-09-26)

Note `autoresearch/bound-m-260925/REVERSAL-K2.md`; words in
`checks/reversal-k2-words.json`, re-check script `checks/reversal_k2.py`
(evaluator, audit and replay on every row; orchestrator re-ran it: 390
word_G rows and 150 stored rows, no problems), searches in
`checks/reversal_k2_search/`.

- Closed form word_G(m, g), one two-core word with cut, seeds, sweep count
  and sides fixed by m mod 4 and by min(g, m-g), certifies the reversal
  (m..1) with zeros in gaps {0, g} whenever g <= floor(m/4) or m-g <=
  floor(m/4): 390 certificates at m = 9..40 (evaluator + audit + replay),
  1210 more at m = 41..80 by replay and criterion (7). Length between T-11
  and T, slopes <= m-2. The rules were read off the data, not derived.
- Middle band floor(m/4) < g < m - floor(m/4): no closed form; at
  m = 9..13 a root LP over the whole two-core pool fails where min(g, m-g)
  >= about m/2 - 2, always with slopes feasible and the base binding (the
  cheap words put nearly all slope on the gap-0 zero).
- Survey at the root, all k=2 masks: m = 11 59/66, m = 12 72/78, m = 13
  18/25 (only masks with a zero in gap 0 or 13 run). Every miss has one
  zero in gap 0 or gap m and the other near m/2; every mask with both
  zeros in gaps 1..m-1 certified at m = 11, 12.
- Misses: m = 9 {5,9} newly CERTIFIED by a 5-leaf tree. Still not found
  (trees to depth 4, thresholds 6, up to 11 origins): m = 9 {0,4} (base
  excess 9/4), {0,5} (4); m = 10 {0,5} (17/4), {0,6} (4); m = 12 mask 130
  (74/15); m = 11 mask 1056 (2). Not run: three-core words, rotated-cut
  sweeps, higher-k masks 7300, 2456, 6309, 3534, 3685, trees on the survey
  misses, m = 14.

Since the table-fed tree control (Session 17) certifies m = 9 {0,4} from
BFS words with origins (3,1) and (5,1), that miss is a word-generation
limit; the next step is to mine the (9,2), (10,2), (11,2) tables for the
structure of shortest refined-origin words in the middle band.

## Session 23: middle band mined from exact tables; first exact negative for a root leaf (2026-09-26)

Note `autoresearch/bound-m-260925/REVERSAL-MIDBAND.md`; data
`checks/reversal-midband-words.json`; re-check `checks/reversal_midband.py`
(orchestrator re-ran with `--tables`: 14 certificates CERTIFIED, audit ok,
replay ok, word_S re-derived letter by letter, exact negative reproduced,
no problems); searches in `checks/reversal_midband_search/`.

- Exact negative (computed; the first for a root leaf): for m = 9, zeros
  in gaps {0,4}, every sorting word of the unit base has B + 3 beta_0 >= 75
  (exact A* over all reduced words with Lemma 1 bookkeeping, heuristic from
  the stretched-zero tables (9,3)..(9,6), matched against brute force on 25
  small cases at m = 5, 6; 8760 nodes), while a certifying root mixture
  needs < 74. The exact optimum of the criterion (8) left side over all
  words is 2; witness word B = 54, slopes (7,7). No root-leaf certificate
  exists for that family; the tree with leaves u0 = 1 and u0 >= 2 (origin
  (2,1), exact optimum 4/5) certifies it. Table distances alone never
  refute a leaf (every distance is <= T(u)); the refutation needs the
  base-slope trade-off. Caveat: exactness rests on the oracle's
  completeness over reduced words.
- New m = 9 certificates: {0,5} at the root (length T-1, slopes (7,4)),
  {0,4} by the two-leaf tree, {0,3} and {0,6} at the root; so every k=2
  mask of the m = 9 reversal is now certified (with Sessions 21, 22).
- Exact data: unit distances of all band masks at m = 9, 10, 11 lie 7..11
  below T; every shortest word loads beta_0 = 9..16 on the gap-0 zero and
  nearly nothing on the other; along u1 the distance does not grow, along
  u0 it grows by 10 per zero at m = 9 {0,4} against 7 allowed; the state
  (0^4, 9..6, 0, 5..1) is at distance exactly T.
- Structure: certifying middle-band words split the crossings between
  the two zeros, i.e. two independent one-zero reversals on disjoint
  blocks; the two-core pool always loaded the gap-0 zero. Generator
  word_S(m, g, b, ds, schedule, fin) (schedules rr(lr)*, chosen per
  (m, g), so not a closed form) certifies at the root: m = 9 {0,5},{0,6};
  10 {0,6},{0,7}; 11 {0,7},{0,8}; 12 {0,7},{0,8}; 13 {0,8},{0,9}; nothing
  at m = 14..16 (gaps 1/10, 1, 2) because it walks the zero at 3 per
  crossing (beta_0 = 3b-2); the carry-across variant at 2 per crossing, as
  in word_C, was not written.
- Not certified: m = 10 {0,5} (leaves u0 in [1,2] and u0 >= 5 pass, u0 =
  3, 4 fail with every word tried; no (10,4) table); m = 11 {0,5}, {0,6}
  (m = 11 {0,4} is listed as a miss in REVERSAL-MIDBAND.md, whose search
  was root-only; it is CERTIFIED by the two-leaf tree of Session 21, mask
  17, audit ok, re-run 2026-09-26); m = 12 {0,5},{0,6}; m = 13 {0,5},{0,6},{0,7}; the whole band at
  m = 14..16. Base binds in every miss. Exact root and (2,1) optima at
  m = 10 unknown (1.5M-node cap); m = 9 origins (1,2), (2,2) hit the cap;
  picks first-atom only.

## Session 24: external independent review of the findings package (2026-09-26)

Two reviewers of the research group (AutoMathLab, review request 2900;
files in `downloads/lrx-solver-review-2900/`, kept untracked: REVIEW.md,
independent_check.py, receipts) checked `lrx-findings-260926.zip` (sha256
`04be4d4a...`) and the repository at `defc5c6`, with their own stdlib
executor and checker, no repository modules, no BFS tables, no API.

Confirmed by them: 393/393 words replay to (1..m,0,0) (the 390 word_G
unit-block words at m = 9..40 and the three m = 11 words of lengths 74, 75,
75); 665 stored rows, 852 word executions and 675 exact leaf inequalities
re-derived from segments with their own Lemma 1 bookkeeping; coverage of
unique k=2 reversal masks 45/45 at m = 9 and 74/78 at m = 12; the
campaign-2 finalist table (148/165 vs control 95/165).

Not confirmed by them, correctly: shortestness of words (needs tables);
the exact radii of (10,2), (11,2), (9,6) and the two-extremal-state count
(tables not shipped); the single-leaf negative for m = 9 {0,4} (the
shipped check only re-runs a witness; a refutation needs a portable
exhaustive oracle with proven completeness or a compact lower-bound
certificate); the campaigns themselves.

Their corrections, accepted: (1) for even m, word_C is a mixture of two
words (T-1 with slopes (m-1, m-2) and T+1 with (m-3, m-4), weights 1/2),
not one word of length T-1 with the required slopes; the summary must say
so. (2) The engine gain must be stated against the strong seed (129/165 at
m = 12), so AdaEvolve-s2 adds 19 families, not 53. (3) FINDINGS.md pinned
`defc5c6` and VERIFY.md `6e56ddf`; one commit must be pinned. (4) The zip
is not self-contained: the check scripts import `integrations/*.py`, and
`mb.py` hard-codes an absolute path. (5) Every certificate for all block
lengths and general m stays conditional on Lemma 1 and criteria (7)/(8);
finite checks of the formulas do not replace a proof.

Their suggested next step, adopted: close the inductive invariants of
word_C for both parities and bind the general-m Lemma 1 / (7)/(8)
separately; keep the architecture "optimizer proposes, data-only checker
verifies"; measure engine gains against the strong seed at equal budget
with several repetitions and a frozen new holdout.

## Session 25: proof of the word_C length and slope formulas (2026-09-26)

`autoresearch/bound-m-260925/WORDC-PROOF.md` (about 5,900 words) proves,
for all m >= 3 and 1 <= a <= m-2, that word_C(m, a) sorts (0,m,...,1,0) to
(1..m,0,0), has length T_m(m+2) + 2(a-(m-2)/2)^2 - 1 - (m mod 2)/2 with
B = length (every segment unidirectional), and Lemma 1 slopes (2a+1, 2a)
except a = 1 with m even, where they are (4,3). Structure: sweep lemma
(two inductions, mod n), Lemma A (core 1, cyclic wrap explicit), Lemma B
(core 2, both parities of r and a, the values of start and right), Lemma C
(the walks W0 and Wf in five written-out cases), Lemma D (letter count),
Lemma E (segment enumeration and the cz accounting: the only surviving
terms are the first X and, in the a = 1, m even tie, W0). Corollary for
m >= 9: odd m, a = (m-3)/2 gives (T-1, (m-2, m-3)); even m, a = (m-2)/2 and
(m-4)/2 give (T-1, (m-1, m-2)) and (T+1, (m-3, m-4)), so the 1/2-1/2
mixture has Bbar = T and betabar = (m-2, m-3).

Mechanical check `checks/wordc_proof_check.py` (orchestrator re-ran):
every intermediate claim of Lemmas A-E and the theorem against the actual
execution, m = 9..40, 720 pairs, 0 mismatches; corollary failures 0; two
deliberate mutations caught (45 and 12 mismatches). Written by an Opus
worker; not yet reviewed by a human mathematician. Section 8 lists what is
not covered: Lemma 1 itself, criterion (7), that the mixture certifies
(Lemma 1 + criterion (7) applied to these numbers), a = m-1, m, and
minimality. So the certificate of (m..1){0,m} for all m >= 9 is now
conditional only on the group's Lemma 1 and criterion (7) at general m.

## Session 26: middle band at m >= 14, word_M closed form on the band ends (2026-09-26)

Note `autoresearch/bound-m-260925/REVERSAL-CARRY.md`; words in
`checks/reversal-carry-words.json`; re-check `checks/reversal_carry.py`
(orchestrator re-ran: 59 stored rows CERTIFIED, audit ok, replay ok, 160
closed-form rows scored by evaluator + audit at m <= 40, 207 by replay +
criterion (7) at m = 41..60, no problems); searches in
`checks/reversal_carry_search/`.

- The literal carry-across variant does not reach 2 per crossing: traces
  show a zero crossed from one side only costs 3 in slope whether the zero
  walks or the labels are carried, since the cursor must cross it again.
  What reaches 2 per crossing is a word_C-style zero core at the gap-0
  zero carrying labels from both sides; the gap-g zero is then crossed from
  one side at 3. New generator word_K (two cores, one cut per core, side
  lo or hi); closed form word_M(m, g, side) with parameters by m mod 4.
- word_M certifies (m..1){0,g} at the root on contiguous runs at both ends
  of the middle band at every m = 14..60: 1/7 of the band at m = 14, 6/11
  at m = 24, 12/29 at m = 60; along each run B-T and beta_g rise by 3 per
  step in g. Rule read off data, not proved. At m = 14..24 the 59
  certificates are 44 word_M rows plus 13 word_K root mixtures; m = 14..16
  had none before.
- Newly certified open leaves: m = 11 {0,4} (root; also certified by the
  Session 21 tree) and m = 13 {0,5} (root). Still not found: m = 10 {0,5}
  (best leaf value 2 at u0 = 3, exactly 1 at u0 = 4), m = 11 {0,5}, {0,6},
  m = 12 {0,5}, {0,6}, m = 13 {0,6}, {0,7}.
- The middle of the band is not certified; the base binds with slopes
  feasible everywhere. Minimum base excess at g = m/2: 16, 16, 30, 46, 64,
  84 at even m = 14..24. Boundary cases with gap 0 and base excess 1:
  m = 16 {0,10}, 19 {0,8}, 23 {0,14}, 24 {0,10}. Trees at m = 14 {0,8},
  {0,9} not found (binding strip u1 = 1, u0 >= 3, leaf values 3..4); no
  trees at m = 15..24. The 3-per-crossing claim is a model backed by
  traces, not an impossibility proof.

## Session 27: Lemma 1, (4)-(6), criteria (7) and (8) at general m (2026-09-26)

`autoresearch/LEMMA1-GENERAL-M-260926.md` (about 4,600 words) audits the
group's manuscript `lrx_multiset_m8_complete.tex` step by step and writes
general-m proofs. Verdicts: Lemma 1 m-independent as written (the only 8
is the root, notational; the manuscript proof is a sketch, the note gives
a full macro-by-macro induction valid for m >= 2); (4)/(5) m-independent
(triangle inequality gives F_W(z) <= B + sum beta_j z_j for every word;
same-sign is needed only for equality); refinement (6) and Lemma 2
m-independent (integer budget only); criterion (7) m-independent with a
one-line averaging argument the manuscript omits even at m = 8, using only
that T_m is an integer and T_m(m+r) - T_m(m+r') = (m-2)(r-r'); criterion
(8) m-independent after replacing 6 by m-2, proof written. Every real use
of m = 8 is in the finite part (8!(2^9-1) families, resource search,
tables, four-block data). `lrx_m.py` matches the general-m statements;
its m=8 defaults are stricter at m' > 8, so conservative.

Table checks (`autoresearch/checks-lemma1/lemma1_tables_check.py`,
orchestrator re-ran, PASS): 380 (family, word) pairs (300 at m = 9, 60
at m = 10, 80 refined bases) over tables (9,1)..(9,6), (10,2), (10,3),
3,806 exact points, 0 violations of d <= F <= affine bound; criterion (7)
at m = 9 on 146 root-certified families, 1,637 block-length vectors, 0
violations of d(v(u)) <= T_9(n); manuscript section 8 example reproduced.
Caveat: d <= F follows from "the lift sorts", so the tables cross-check
executor, pricing and tables rather than prove the lemma.

LEMMA14 note: refutes lemma (14) of the separate connected-proof
manuscript (pi = [0,2,4,1,5,3], 41 > 36); the m=8 manuscript says that
lemma is not used. Not audited yet: Lemmas 3, 4 and formula (11)
(transfer, projection); certificates using them at m >= 9 stay conditional.

Consequence, stated with care: combining Session 25 (word_C formulas,
proved) with this session (Lemma 1, (5), (7) at general m, proved), the
chain "for every m >= 9 and all u0, u1 >= 1, d((0^u0, m, ..., 1, 0^u1)) <=
T_m(m + u0 + u1)" is now a complete written proof with no conditional
step, for the odd-m single word and the even-m 1/2-1/2 mixture. Both
proofs were written by models and mechanically checked; neither has been
reviewed by a human mathematician. Until that review, the repository
records it as "proof written, unreviewed", not as a theorem.

## Session 28: proof of word_R1; exact closed-form hypotheses for word_G (2026-09-26)

`autoresearch/bound-m-260925/WORDR1-PROOF.md` (about 8,000 words, same
structure as WORDC-PROOF.md) proves for all m >= 9 that word_R1(m) sorts
the unit base of (m..1){1,m} with B = length and, for m = 4u + rho: rho = 0:
length T-2, slopes (m-4, m-2); rho = 1: T-2, (m-5, m-3); rho = 2: T,
(m-6, m-4); rho = 3: T-2, (m-5, m-3); m = 9, 10 are instances, not
exceptions. Key lemma P: core_word never makes a partial carry here
(every step is a full carry or empty), so the word_C sweep lemmas apply
verbatim; every cz term is 0. With Session 27, (m..1){1,m} for all
m >= 9 has a complete written proof chain (model-written, unreviewed).
Mechanical check `checks/wordr1_proof_check.py` (orchestrator re-ran):
m = 9..60, 0 mismatches over Lemmas P, A-E, theorem, corollary; worker
also m = 9..200, 0; three mutations caught.

word_G is not proved. Section 11 states what a proof needs (a
partial-carry version of the sweep lemma: 1,509 of 1,600 words have a
partial core-1 carry) and `checks/wordg_formula_check.py` tests exact
closed-form hypotheses in (m, g) at m = 9..80 (1,600 rows, orchestrator
re-ran): all 28 rule-row hypotheses hold with 0 exceptions; C2 (2 <= g <=
j-2: length - T = 2-g, slopes (m-2, m-2-g-2[m even])), C4 (1 <= r <=
j-2: 1-r, (m-2, m-3-r)), C6 (B = length), C7 (B <= T, slopes <= m-2) hold
with 0 exceptions; the deliberately coarse C1, C3, C5 fail (35, 54, 107).
Out of sample at m = 81..120 (2,010 rows) the 26 nonempty hypotheses hold
with 0 exceptions.

## Session 29: portable negative certificate for m = 9 {0,4} (2026-09-26)

`autoresearch/bound-m-260925/negcert/`: `negcert_check.py` (stdlib only,
imports nothing from the repository, reads no tables), the certificate
`negcert-m9-04.json`, `validate_small.py`, `NEGCERT.md`. Route B of the
brief: an exhaustive oracle with a written completeness argument (in the
checker's docstring: dropping LR, RL and XX never raises the cost; a
7-context segment accounting is exact for Lemma 1's B and beta), an
in-memory abstraction table whose consistency is verified on every node,
then A*; no Lemma 1 lift bound used.

Result: the exact minimum of B + 3 beta_0 over all accepted sorting words
of (0,9,8,7,6,0,5,4,3,2,1) is 75; a root mixture needs Bbar + 3 betabar_0
< 74 (Bbar < 53, betabar_0 <= 7), so NO ROOT-LEAF CERTIFICATE exists for
(9..1){0,4}; the tree of Session 23 remains the certificate. A second
optimal word (B = 48, slopes (9,3)) was found besides the (54, (7,7))
witness. Orchestrator re-ran the checker from an isolated copy with
`python -I`: VERIFIED in 15.6 s; `validate_small.py` agrees with brute
force priced by `lrx_m.Profile` in all 21 cases at m = 3..6 (all-words
check of the reduction step): VALIDATED. A second abstraction gives 75; a
false claim of 76 fails. Assumed only: Profile is the group's Lemma 1
bookkeeping; words swapping two zeros are excluded as Profile excludes
them. This answers the reviewers' request (Session 24) for a portable
oracle with proven completeness.

## Session 30: Lemma 3, formula (11), Lemma 4, section 7 at general m (2026-09-26)

`autoresearch/LEMMA34-GENERAL-M-260926.md` continues Session 27. Sections
5 and 6 of the manuscript contain no 8, 6, 30, 31 or 8!. Lemma 3 with (9),
(10): m-free, proof written out (adding that comparators never swap two
zeros and that the end state is exactly the root). Formula (11): m-free;
the manuscript's stretching paragraph is a sketch, the note fills three
steps (A_j = sigma_j(Q) from #X = inv(Q); lifting never crosses the cut;
stretching preserves (9)); (11) is exact for same-signed words, an upper
bound otherwise. Lemma 4: m-free, manuscript proof complete; the
commutation claim proved after normalising rotation runs. Section 7
resource formula beta_j = 3A_j + B_j - 2F_j and increment table: m-free,
thresholds 30+6k and 6 become T_m(m+k) and m-2; the enumerations are m=8
data. Table checks (`autoresearch/checks-lemma1/lemma34_tables_check.py`,
orchestrator re-ran, PASS): transfer 540 instances, 4,555 stretched
points, 90,923 comparator steps, 0 violations; projected reference then
transfer 60 instances, 724 points, 0; projection 472 instances, 3,766
child points, 0; resource formula 320 words, 980 zero atoms, 0; negative
control: all 540 inputs violating (9) fail to sort.

Correction to Session 27: no m >= 9 certificate in this repository uses
Lemma 3, Lemma 4 or (11) (the lift task builds literal m=8 parent words
that Profile re-prices; bound campaigns, trees and the reversal
certificates are literal words priced by Profile and decided by (7)/(8)),
so the sentence "certificates using them at m >= 9 stay conditional"
refers to an empty set. The m = 8 uses (Sessions 8, 9, 10) now have
complete written proofs, marked proof written, unreviewed. Step most
worth a human reader's attention: note section 4.3 items 2-3.

## Session 31: k=3 reversal class, word_W closed form (2026-09-26)

Note `autoresearch/bound-m-260925/REVERSAL-K3.md`; words
`checks/reversal-k3-words.json`; re-check `checks/reversal_k3.py`
(orchestrator re-ran: 455 stored certified rows and 50 misses, word_W 122
rows by evaluator + audit + replay at m <= 24 and 728 by replay +
criterion (7) at m = 25..40, no problems); searches in
`checks/reversal_k3_search/`. First survey of the reversal m..1 with three
zero blocks, all C(m+1,3) masks up to rotation.

| m | masks | certified | root | trees |
|---|---|---|---|---|
| 9 | 120 | 112 | 106 | 6 |
| 10 | 165 | 148 | 147 | 1 |
| 11 | 220 | 195 | 193 | 2 |

The 50 misses all bind on the base (slope excess 0 at the root; minimum
base excess 1 to 11/2, seven exactly 1); every miss has a zero in gap 0 or
gap m; every mask with all three zeros in gaps 1..m-1 certifies at the
root (the k=2 pattern again). Closed form word_W(m, g1, g2) for masks
{0, g1, g2}: two-core word, cut (m-3)//4 + dt, core 1 on the gap-0 zero
with m//2 + dk sweeps, core 2 at the complement middle, parameters
(dt, dk, d1, d2) by m mod 4: (0,1,l,r), (0,0,r,l), (1,0,l,l), (-1,1,r,r);
band (j = m//4, r2 = m - g2): m = 0 mod 4: 2 <= g1 <= j-1, r2 <= j-1;
1: 3 <= g1 <= j-1, r2 <= j-1; 2: 2 <= g1 <= j-1, r2 <= j; 3: 3 <= g1 <= j,
r2 <= j-1. Rule read off data, unproved. Not done: the m = 12 survey
(only 3 word_W rows), refined-origin trees on the m = 10, 11 misses,
three-core pools (a 3-mask diagnostic certified nothing).

## Session 32: interior masks of the reversal, k = 2, 3, 4 (2026-09-26)

Note `autoresearch/bound-m-260925/REVERSAL-INTERIOR.md`; words
`checks/reversal-interior-words.json`; re-check `checks/reversal_interior.py`
(orchestrator re-ran: 837 certified rows, 14 misses, no problems);
searches in `checks/reversal_interior_search/`. Root leaf over the
two-core pool, unit origins, no trees. Interior mask: all zeros in gaps
1..m-1.

- k = 2: 28/28, 36/36, 45/45, 55/55, 66/66 at m = 9..13 (m = 13 new).
- k = 3: 56/56, 84/84, 120/120, 165/165 at m = 9..12 (m = 12 new).
- k = 4: 64/70 at m = 9, 118/126 at m = 10 (new). The 14 misses are wide
  masks (first zero in gap 1 or 2, last in gap >= m-2); five bind on the
  slopes, the first slope-bound misses seen at any k (m = 9 {1,2,5,7}
  excess 1/6, {1,3,6,8} 1/2, {2,4,7,8} 1/6; m = 10 {1,3,6,9} 49/538,
  {1,4,7,9} 53/626); nine bind on the base (m = 9 {1,2,6,8} excess 1).
- Not run: k = 4 at m = 11, k = 3 at m = 13.
- No closed form: many interior masks have no certifying single word
  (k = 2: 37 of 105 at m = 16; k = 3: 93 of 165 at m = 12); no parameter
  tuple in word_G coordinates covers more than about 30 % of masks at any
  m, and the best tuple changes with m.
- Conjectures (evidence, not proof): I1, every interior mask at k = 2 or 3
  has a root certificate (cheap words merge one zero into its neighbour
  at 3 per label crossed, base slack -3 to -21 lets the LP balance
  slopes); I2, at k >= 4 evenly spread masks have no root certificate in
  this pool (cheap support words have slope sums at or above k(m-2)).
