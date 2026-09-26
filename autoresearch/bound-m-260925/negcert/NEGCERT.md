# Portable negative certificate: m = 9, zeros in gaps {0,4}, root leaf

Date 2026-09-26. Offline. There were no provider calls, no LLM-generated code was executed, and nothing was committed.
No BFS table was read or built on disk. Lemma 1, its bookkeeping and criteria (7)/(8) are the research group's
(m=8 manuscript). The main conjecture stays open.

This note answers the reviewers' request (review 2900, `downloads/lrx-solver-review-2900/REVIEW.md`, item 3): "a
compact verifiable lower-bound certificate or a portable exhaustive oracle with proven completeness". What was
achieved is the second option (route B of the task). It is a stdlib checker that rebuilds everything it uses in
memory, verifies the heuristic it relies on, and proves completeness in its docstring. It is not a compact dual table
(route A). The certificate JSON holds only parameters, witnesses and the claimed value. The proof is a 16-second
recomputation.

## 1. Statement

- **Family.** Labels 9..1, one zero in gap 0 and one in gap 4.
  - The unit base is v = (0,9,8,7,6,0,5,4,3,2,1), the same as `lrx_m.base_vector(labels, 1|1<<4)`.
  - T = T_9(11) = 52 and s = m-2 = 7.
- **Claim (verified).** Every word over {L,R,X} that sorts v and is accepted by the Lemma 1 bookkeeping has
  B(w) + 3 beta_0(w) >= 75, and 75 is attained. "Accepted" means the word never swaps two zeros, which is the domain
  of `lrx_m.Profile`.
- **Consequence.** A root-leaf mixture needs Bbar < T+1 = 53 and betabar_0 <= 7. That forces
  Bbar + 3 betabar_0 < 74, while the functional is linear, so every mixture has at least 75. No root-leaf certificate
  exists for this family. The Session 23 two-leaf tree remains the certificate.
- **Two optimal words.** Both re-priced by the checker and by `lrx_m.Profile`.

| word | length | B | beta | B + 3 beta_0 |
|---|---|---|---|---|
| `RXLLLLXLLXLXRRXRXRXLXLXLXRXRXRXRXLXLXLXLXLLLXLXLXRRXLX` (Session 23 witness) | 54 | 54 | (7,7) | 75 |
| `XLXLXRRXLXRXRRRXRXRXRRXLXLXLXLXLXRRXRXLXLXRXRXRX` (new, from this checker) | 48 | 48 | (9,3) | 75 |

## 2. Files (all new, under `autoresearch/bound-m-260925/negcert/`)

| file | role | sha256 |
|---|---|---|
| `negcert_check.py` | the checker: stdlib only, no repository imports, reads only the JSON it is given | `402eb81b…` |
| `negcert-m9-04.json` | the certificate: m, labels, mask, base, T, s, lam = 3, claim_min = 75, abstraction partition, witnesses | `680a1e5f…` |
| `validate_small.py` | a validation harness that deliberately imports `integrations/lrx_m.py` and brute-forces m = 3..6 | `d9760bc6…` |
| `NEGCERT.md` | this note | |

**Certificate format.** The fields are the family (`m`, `labels`, `mask`), the expected `base`, `T` and `s`, the
weight `lam`, and `claim_min`. The `abstractions` field is a list of label partitions, one per pattern table. The
`witnesses` field lists each word with its B and beta. The checker recomputes the base vector and T, builds and
verifies each pattern table, runs the exact search, and fails unless the exact minimum equals `claim_min`. It also
fails unless every witness re-prices to its stated (B, beta) and to `claim_min`, and unless `claim_min >= T+1+3s`.

## 3. Completeness argument (full text in the checker's docstring)

- **Definitions.** `profile_cost` is a letter-by-letter transcription of `lrx_m.Profile` for a unit state.
  - Segments are the runs of rotations between X letters, with d = #L - #R.
  - cz is the net crossing count of zero 0: an L on it gives +1, and an R landing on it gives -1.
  - A ZL swap gives +1 on the closing segment and one count in A_0. An LZ swap gives one count in A_0 and starts the
    next segment at cz = -1.
  - B = q + sum |d| and beta_0 = 2 A_0 + sum |cz|.
- **Lemma R (reduction).** Deleting an adjacent LR, RL or XX never increases F = B + 3 beta_0, and the result still
  sorts and stays accepted.
  - LR and RL cancel inside one segment.
  - For XX, the empty middle segment has cz = 0. Merging the two outer segments costs |a+b| <= |a|+|b| on both d and
    cz, and q and A_0 drop.
  - So the minimum over all accepted words equals the minimum over reduced words.
- **Lemma C (exact segment accounting).** In a reduced word each segment is L^a or R^a, so |d| = a. Its cz starts at
  0 or -1, moves monotonically, and closes with e in {0,1}.
  - A six-case analysis gives |cz| exactly as a per-crossing charge plus a closing charge.
  - This uses seven contexts: S, X0, X1, L0, L1, R0, R1.
  - So F is a sum of nonnegative edge costs on the finite graph of (vector, context) nodes, and min F is a shortest
    path there.
  - The other zeros have weight 0 and are encoded alike. This is exact, not a relaxation.
- **Lemma A (abstraction).** Mapping labels to class codes commutes with every step, because steps read only zero-ness
  and the position of zero 0. It also maps roots to roots.
  - The pattern table h is the exact cost-to-go in the abstract graph, built by backward Dijkstra.
  - It is not trusted as built. `verify()` checks h(u,c) <= w + h(t,c') on every abstract node and letter, and
    h(root,c) <= final(c).
  - Consistency lifts to concrete nodes, so h is an admissible and consistent heuristic.
- **Theorem.** A* with a consistent heuristic is Dijkstra on the reduced costs. The first terminal it pops is the
  exact minimum over reduced words, and by Lemmas R and C over all accepted sorting words.
  - If the search ran out of resources, the checker would raise INCOMPLETE and would never report a bound.
- **Unlike the Session 23 oracle** (`checks/reversal_midband_search/mb.py`), this checker does not use the Lemma 1
  lift bound as a heuristic. It uses no (9,3)..(9,6) table and no file on disk.

## 4. How to run, runtime, observed output

From `autoresearch/bound-m-260925/negcert/` with Python 3.12.8 on the lab Mac:

```
$ time python3 negcert_check.py negcert-m9-04.json
statement: m=9 base=[0, 9, 8, 7, 6, 0, 5, 4, 3, 2, 1]  min over accepted sorting words of B + 3*beta_0 >= 75
pattern table [[9, 8], [7, 6], [5, 4], [3, 2, 1]]: 831600 abstract vectors, 4989600 nodes, 9918720 edges, consistent; max h 71; bound at start 67 (13.7 s)
A*: exact minimum 75 after 444460 expansions (2.7 s); optimal word XLXLXRRXLXRXRRRXRXRXRRXLXLXLXLXLXRRXRXLXLXRXRXRX
  re-priced by the transcription: len 48, B=48, beta=[9, 3], F=75
witness RXLLLLXLLXLXRRXRXRXLXLXLXRXRXRXRXLXLXLXLXLLLXLXLXRRXLX: B=54 beta=[7, 7] F=75 ok
witness XLXLXRRXLXRXRRRXRXRXRRXLXLXLXLXLXRRXRXLXLXRXRXRX: B=48 beta=[9, 3] F=75 ok
root mixture needs Bbar < T+1 = 53 and betabar_0 <= s = 7, so Bbar + 3 betabar_0 < 74; every word, hence every mixture, has >= 75: NO ROOT-LEAF CERTIFICATE
total 16.4 s
VERIFIED
real 16.44 s (15.98 s user)
```

The pattern table alone bounds the start at 67. The concrete A* closes the remaining gap of 8 exactly.

**Cross-check with a second abstraction.** With the partition {9,8,7},{6,5},{4,3},{2,1}, the table bounds the start
at 65. A* then finds the same exact minimum 75 after 527,909 expansions, with the same optimal word, in 16.2 s.

**Negative tests.**
- With `claim_min` set to 76, the checker prints `exact minimum 75 != claimed 76` plus two witness mismatches and ends
  with `FAILED`.
- Raising any single table entry by 1 was rejected by `verify()` in all 18 trials on an m = 6 table.

## 5. Validation against brute force

`python3 negcert_check.py --selftest` takes 38 s and uses no repository code:

- On all 16,630 reduced prefixes up to length 11 from three states, the compressed model equals the transcription.
- On 1,879 random sorting words, reduction never increased F, and the model equals the transcription.
- In 22 exact cases at m = 5, 6, the table-guided A* equals a Dijkstra with uncompressed raw cz and no table. The
  masks were {0,2}, {0,3}, {0,4}, {0,1,4}, {1,3}, {0,5}, {0,2,5} and {2,5}, with lam 1 and 3. Each optimal word
  re-prices to the same value.

`python3 autoresearch/bound-m-260925/negcert/validate_small.py` runs from the repository root in 365 s. It prices
with the repository's own `lrx_m.Profile`:

- **Part 1 (m = 5, 6).** It enumerates every reduced word whose prefixes satisfy len + d(state) <= F*, using exact BFS
  distances built in memory. This covers every reduced sorting word with F <= F*, since F >= length.
  - All 15 cases agree.
  - The largest was m = 6 {0,3} with lam = 3: 125,985,849 prefixes and 8,829,046 sorting words, minimum 37 = checker.

| m | mask | lam | checker | brute force |
|---|---|---|---|---|
| 5 | {0,2} | 1 / 3 | 19 / 27 | 19 / 27 |
| 5 | {0,3} | 1 / 3 | 20 / 26 | 20 / 26 |
| 5 | {0,4} | 1 / 3 | 19 / 23 | 19 / 23 |
| 5 | {0,1,4} | 3 | 28 | 28 |
| 5 | {1,3} | 3 | 20 | 20 |
| 6 | {0,2} | 1 / 3 | 25 / 36 | 25 / 36 |
| 6 | {0,3} | 1 / 3 | 28 / 37 | 28 / 37 |
| 6 | {0,4} | 3 | 34 | 34 |
| 6 | {0,5} | 3 | 31 | 31 |
| 6 | {2,5} | 3 | 22 | 22 |

- **Part 2 (m = 3, 4).** It enumerates every word, non-reduced included, up to length 16 at m = 3 and 15 at m = 4.
  - It checked up to 822,579 sorting words per case.
  - In all 6 cases the brute-force minimum equals the checker, which exercises Lemma R. One case has checker 16 with
    a length-16 word, above Lmax 15. The brute-force minimum there is 16, reached by a shorter non-reduced word.

## 6. What remains assumed, and limits

- **Assumed.** Only that `profile_cost` (equivalently `lrx_m.Profile`) is the group's Lemma 1 bookkeeping. The
  consequence for root leaves also uses the form of criteria (7)/(8) as `lrx_m.mixture_criterion` and
  `leaf_criterion` state them. Lemmas R and C and the A* theorem are elementary, and the checker tests them
  mechanically as well.
- **Scope.** The domain is the Profile domain: words that swap two zeros are rejected there and are not covered. Picks
  are the unit picks (one zero per block).
  - The claim is about this family, this origin and this functional only.
  - It says nothing about other leaves or origins, for example (1,2) and (2,2), which hit the node cap in
    Session 23. It also says nothing about m = 10 {0,5}.
- **Checked by the author only.** The checker was run and validated by its author. It has not yet been re-run by the
  reviewers.
- **CPU.** About 25 minutes in total. That includes an 11-minute exploratory forward search in a coarse abstraction
  used to choose the approach, plus the 6-minute validation.
