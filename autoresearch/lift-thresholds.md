# B2: projection thresholds for the lifting statement (finite)

Question (session-02 queue B2): for each computed graph, how far above
P = E_{r-1}(n-1) must the projection cap q go before (a) every vector has a lift
within the fixed budget P + m - 2, and (b) every vector has a lift of length
d(v)? Is the needed excess bounded (0 for r = 2, 1 for r = 3, ...)?

Evidence: `evidence/lifting-check-260922-234448/sweep-m{M}r{R}.json`,
made by `python autoresearch/lift_sweep.py M R --family --listing 40`, which
evaluates A_q(v) = min_j H_q(v\j, j) for every visible v after each layer q of
the trusted layer DP (step-for-step copy of `src/lrx/lifting_fast.h_layers`;
`tests/test_search_lift_tools.py` checks every layer against `h_layers` and
the q = P row against `lifting_fast.check_graph`). Default window
q = P-3 .. P+5 with early stop once A_q = d everywhere. All 24 runs COMPLETE,
`A_below_d = 0` on every row (no checker inconsistency).

Columns: `q_budget` = smallest q in the window with A_q(v) <= P+m-2 for all v
(none if E_r(n) > P+m-2, then no cap can work); `q_exact` = smallest q with
A_q(v) = d(v) for all v. Both are reported as offsets from P.

| r | m | n | P | P+m-2 | E_r(n) | T_m(n) | over-budget at q=P | q_budget - P | q_exact - P |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 4 | 6 | 10 | 12 | 12 | 12 | 0 | 0 | 0 |
| 2 | 5 | 7 | 15 | 18 | 19 | 18 | 1 | none (E > budget) | 0 |
| 2 | 6 | 8 | 21 | 25 | 25 | 25 | 0 | 0 | 0 |
| 2 | 7 | 9 | 28 | 33 | 33 | 33 | 0 | 0 | 0 |
| 2 | 8 | 10 | 36 | 42 | 42 | 42 | 0 | 0 | 0 |
| 2 | 9 | 11 | 45 | 52 | 52 | 52 | 0 | 0 | 0 |
| 3 | 4 | 7 | 12 | 14 | 15 | 14 | 2 | none (E > budget) | +1 |
| 3 | 5 | 8 | 19 | 22 | 21 | 21 | 0 | 0 | 0 |
| 3 | 6 | 9 | 25 | 29 | 29 | 29 | 0 | 0 | +2 |
| 3 | 7 | 10 | 33 | 38 | 38 | 38 | 1 | +1 | +1 |
| 3 | 8 | 11 | 42 | 48 | 48 | 48 | 1 | +1 | +1 |
| 3 | 9 | 12 | 52 | 59 | 59 | 59 | 1 | +1 | +1 |
| 4 | 4 | 8 | 15 | 17 | 17 | 16 | 0 | 0 | 0 |
| 4 | 5 | 9 | 21 | 24 | 25 | 24 | 6 | none (E > budget) | +1 |
| 4 | 6 | 10 | 29 | 33 | 33 | 33 | 1 | +1 | +1 |
| 4 | 7 | 11 | 38 | 43 | 43 | 43 | 3 | +1 | +3 |
| 4 | 8 | 12 | 48 | 54 | 54 | 54 | 0 | 0 | +2 |
| 5 | 4 | 9 | 17 | 19 | 20 | 18 | 9 | none (E > budget) | 0 |
| 5 | 5 | 10 | 25 | 28 | 29 | 27 | 3 | none (E > budget) | 0 |
| 5 | 6 | 11 | 33 | 37 | 38 | 37 | 3 | none (E > budget) | +1 |
| 5 | 7 | 12 | 43 | 48 | 49 | 48 | 9 | none (E > budget) | +1 |
| 6 | 4 | 10 | 20 | 22 | 23 | 20 | 4 | none (E > budget) | -1 |
| 6 | 5 | 11 | 29 | 32 | 32 | 30 | 0 | -1 | -1 |
| 6 | 6 | 12 | 38 | 42 | 42 | 41 | 0 | -2 | 0 |

No vector anywhere lacks an admissible lift at q = P (`no_admissible_lift = 0`
in every q = P row).

## Findings (finite; each holds on the listed graphs only)

1. **r = 2:** q = P suffices for both questions on every computed graph
   m = 4..9 (except (7,5,2), where E_2(7) = 19 exceeds the budget 18, a small-m
   exception to the conjecture itself). At q = P, A = d on every vector.
2. **Budget excess never exceeds 1.** On every computed graph where the budget
   P+m-2 is at least E_r(n), q = P+1 brings every vector within budget
   (r = 3: m = 7, 8, 9 need +1; r = 4: m = 6, 7 need +1; all others need 0
   or less).
   This includes the three graphs in the conjecture domain m >= 8 with r >= 3:
   (11,8,3) +1, (12,9,3) +1, (12,8,4) 0.
3. **Exactness excess is small but not constant:** q_exact - P ranges over
   -1..+3 ((11,7,4) needs +3, (12,8,4) +2, (9,6,3) +2).
4. Whenever the budget P+m-2 equals T_m(n) (every row with m >= 6 and r <= 4),
   `A_q(v) <= P+m-2` for all v implies E_r(n) <= T_m(n) on that graph; the cap
   q is only a device for the recursion, so the capped statement with q = P+1
   is as useful for recursion (1) as the refuted one with q = P.

## Replacement lemma candidate for the human (not proved)

    For r >= 3 and m >= 8 (n = m + r), with P = E_{r-1}(n-1):
    A_{P+1}(v) <= P + m - 2 for every visible v.

Evidence: holds on (11,8,3), (12,9,3), (12,8,4) (exhaustive, this file), and
also on (10,7,3), (10,6,4), (11,7,4) outside the conjecture domain. Partial
evidence at n = 13: the targeted k = 2 checks find even the q = P version
true on every covered vector of (13,10,3) (529 vectors) and (13,9,4)
(2945 vectors), and H_{P+1} <= H_P (`targeted-m10r3-k2.json`,
`targeted-m9r4-k2.json`; see `autoresearch/r3-family.md` and
`research/claims.md`). Session 03 widened both to k = 3 (deletions at
distance >= P-3): still no vector over budget at q = P on (13,10,3) (1998
covered vectors) or (13,9,4) (11258 covered vectors), but (13,9,4) has four
new tight vectors (A_P = 66) whose deletions all lie at distance P-3, the edge
of the band (`evidence/lifting-check-260923-0838/targeted-m{10r3,9r4}-k3.json`). The
refuted q = P version fails on (11,8,3) and (12,9,3) at one vector each (see
`autoresearch/r3-family.md`). Open: whether +1 stays enough for larger m and r;
r >= 5 graphs computed here are all outside the domain (E_r(n) > budget).
