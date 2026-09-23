# Session 02 report

> Loop logs, campaign configs of the session and `runs/` directories are local
> and not published. Published evidence lives in `evidence/`.

Autoresearch loop `autoresearch/loop-260922-2338/`, 2026-09-22 23:38 to
2026-09-23 01:25 (about 1 h 50 min wall). Queue from
`autoresearch/session-02.md`: B1, B2, A1, A2, A3, C1, all run. Six iterations
of six. Nothing pushed.

## Outcome

| | before | after |
|---|---|---|
| Verify, `python tools/orchestrator.py ratio` | 2.0625 (lead 1ea0a8de58e2fa16) | **1.8333** (lead 4189a604963f7a9e) |
| Best train score, `python tools/orchestrator.py score` | -154.7414 | -116.1072 |
| Logged spend, `python tools/orchestrator.py spend` | $0.2723 | $4.8156 (session $4.54; guard $20) |
| Guard: `trusted`, `spend`, unit suite | pass | pass (270 tests) |

The stop-and-ask trigger fired once: B1 confirmed the (12,9,3) counterexample
with a second engine. The human chose to run the full queue. No lead reached
ratio <= 1.0.

## Experiments

| iter | item | route | model | USD | wall | Verify after | decision | commit |
|---|---|---|---|---|---|---|---|---|
| 1 | B1 r=3 failing family | B | - | 0 | ~20 min CPU | 2.0625 | keep (finding) | 49f3f9a |
| 2 | B2 projection thresholds | B | - | 0 | ~17 min CPU | 2.0625 | keep (finding) | ed9ef5e |
| 3 | A1 edit mode vs free rewrites, 3 arms x 40 | A | grok-4.20 | 0.871 | 313 s (arms in parallel) | 2.0625 | keep configs; promoted f0c3486445fb14ac (score only) | d68b084 |
| 4 | A3 controller word vs optimal word in feedback, 40 | A | grok-4.20 | 0.286 | 199 s | 2.0625 | discard | a125a84 |
| 5 | C1 potential probe, 3 of 4 requests made | C | grok-4.7 | 1.136 | 1100 s | 2.0625 | discard | 4b84397 |
| 6 | A2 refine the lead, 7 of 8 requests made | A | grok-4.7 | 2.250 | 2060 s | **1.8333** | keep; promoted 4189a604963f7a9e | f849509 |

Per-run rows with hypotheses: `autoresearch/results.tsv`. Loop log and evals:
`autoresearch/loop-260922-2338/`. Infrastructure commits, each tested before
any live use: de925ae (Route B tools), b1269c0 (edit mode, `explore_max`),
5cc79c0 (`feedback_words`).

## Route B findings

All statements are finite and hold on the listed graphs only. Details and
evidence paths: `autoresearch/r3-family.md`, `autoresearch/lift-thresholds.md`,
and the session-02 section of `research/claims.md`.

1. **The (12,9,3) failure of A_P(v) <= P + m - 2 is a two-engine result.**
   The new forward search (`autoresearch/lift_forward.py`, no code shared with
   the trusted engines) gives A_52(v) = 61 > 59 = T for
   v = (2,1,0,0,0,9,8,7,6,5,4,3), with replayed witness words.
2. **One failing vector per fully computed r = 3 graph with m = 7, 8, 9, and
   the overrun does not grow.** The shape alternates: F1_7 (+4), F2_8 (+1),
   F1_9 (+2). This corrects the earlier "same shape, overrun 1 -> 2" reading
   in `research/claims.md` and in the session handoff.
3. **No F-shape failure at m = 10.** On (13,10,3), F1_10 is tight (A_P = 71 = T)
   and F2_10 has A_P = 68. A targeted exhaustive check found no over-budget
   vector among the 529 vectors that have a zero whose deletion lies at
   distance >= P - 2 in (12,10,2). The other ~1.04e9 states are unchecked.
4. **One extra projection letter suffices on every computed graph.** On the
   16 of 24 exhaustively computed graphs where the budget is at least E_r(n),
   the cap q = P + 1 brings every vector within P + m - 2. This includes the three
   graphs in the conjecture domain with r >= 3: (11,8,3), (12,9,3), (12,8,4).
5. **No failure near the far layers of (13,9,4) either.** With P = E_3(12) = 59
   and budget 66 = T_9(13), the targeted k = 2 check covered the 2945 vectors
   that have a zero whose deletion lies at distance >= 57 in (12,9,3). None is
   over budget. 62 of them have a deletion with H_P > 66 (up to 74), and each
   also has a deletion within budget: exact A_P from 60 to 66, two tight at
   66, all 248 witnesses replayed (38 min, 1.6 GB peak,
   `evidence/lifting-check-260922-234448/targeted-m9r4-k2.json`). Since
   H_{P+1} <= H_P, the replacement lemma below also holds on these vectors.
   The rest of (13,9,4) is unchecked.

Proof targets for the human, none proved:

- Replacement lemma: for r >= 3 and m >= 8, A_{P+1}(v) <= P + m - 2 for every
  visible v. It would carry recursion (1) exactly as the refuted q = P version
  would.
- d(u_m) = C(m+2,2) - 3 for u_m = (2,1,0,0,m,...,3) (true for m = 4..10), and
  d(F1_m) = T_m(m+3) (true for m = 5..9).

## Route A findings

- **The stronger model is what moved Verify.** grok-4.7 made 7 proposals for
  $2.25, and 6 beat their parent. The lineage went from lead 1ea0a8de58e2fa16
  (score -154.74) to 68d1e8c489f14f2c (-134.09) to 4189a604963f7a9e (-116.11).
  The m >= 8 train maxima dropped from 84 / 99 / 104 to 71 / 88 / 93 on
  m8r2 / m8r3 / m9r2, with no failures. grok-4.20 made 160 proposals for $1.16
  across A1 and A3 and found one score-only improvement.
- **The new lead** (12 rules, "block insertion, early-X finish") keeps the
  circular block insertion. It adds two shortcuts: seek token 2 directly
  instead of homing token 1, and finish an XL walk with a single X when the
  predecessor is at position 1. The model claims neither change ever makes a
  word longer; that claim was not checked state by state. Held-out graphs,
  reported for the human and not used for any decision: no failures, value/T
  from 1.59 (m16r4) to 1.75 (m9r3).
- **Edit-only proposals (A1) did not help.** Neither edit arm improved on the
  lead. The sequential edit arm returned 20 duplicates in 40, and its best
  candidate was the lead itself. `refine_mode` stays `exploit` by default.
- **Word feedback (A3) hurt proposal quality.** 16 of 40 replies used the
  uphill trace, but sound non-duplicate proposals fell from 20 to 6 against
  the A1 control. `feedback_words` stays off by default.
- All Route A comparisons are one run with one seed each: hints, not verdicts.

## Route C findings

- **C1 did not reach the first milestone.** The first milestone is zero
  local-descent failures on the sanity graphs. grok-4.7 proposed 3 potentials
  (the budget pre-check refused the fourth). The best by score,
  93546e543768c29f, still has 2742 non-descending states on the five sanity
  graphs, against 4863 for the naive seed. Each reply argued descent for some
  move cases only.

## Limitations

- Spend is the client's estimate from xAI-reported token costs
  (`billing_verified: false`). grok-4.7 cost per call ranged from $0.11 to
  $0.53, and time per call from 4 to 21 minutes. Two calls ran past the
  60k reasoning-token budget (81k and 86k tokens).
- The budget pre-check reserves the worst case per request (about $0.42 for
  grok-4.7 at 63k output plus reasoning tokens). Both grok-4.7 runs therefore
  made one request fewer than configured.
- The session handoff said the (12,9,3) failure has the same shape as
  (11,8,3). With the owner's approval it now carries the correction.

## Next queue (proposed)

1. **A2 again from 4189a604963f7a9e.** grok-4.7, sequential exploit,
   8 proposals, `max_spend_usd` 3.6 so that the pre-check allows all 8.
   About $2.5 to $3.2 and 35 to 45 min, based on this session.
2. **A2 with medium reasoning effort, 4 proposals** from the same lead, to test
   whether more reasoning buys shorter words per dollar.
3. **Route B.** Run k = 3 targeted checks on (13,10,3) and (13,9,4) to widen
   coverage around the smaller graph's far layers (the k = 2 runs took 9 and
   38 min). Hand the replacement lemma and the r3-family targets to the
   human.
4. **Route C.** Pause paid rounds. First make potential feedback list, for a
   few non-descending states, every neighbour's value (search-side change,
   mock-tested).
5. Retire the grok-4.20 refinement arms: A1 and A3 show a plateau at that
   model.
