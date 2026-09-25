# Independent checker for the LRX m=8 package: report

Date: 2026-09-24. Checker: `autoresearch/verify-m8-260924/checker/`.
Python standard library only. Exact integers and `fractions.Fraction`.
The package scripts were not imported, copied or read. Nothing under `package/` was modified.

## What the checker implements (from LRX_MULTISET_M8_COMPLETE_THEOREM_RU.md, sections 2-6)

- `lrxm8.py`
  - Word executor. A cursor version is cross-checked against the naive definition in the tests.
  - `Profile`: atomic run with distinguished zeros, Lemma 1 macros, and formula (4)-(5).
    It checks that the word sorts, that no two zeros are swapped, and the same-sign condition per rotation gap.
    Refinements use `origin` and `picks`, formula (6).
  - `Reference.transfer`: Lemma 3 and formula (11). It checks the cut is not crossed, #X = inv(Q), A_j = sigma_j(Q), and P ⪯ Q via the prefix counts H.
    It then compare-executes on P, requires a sorted result with swaps = inv(P), and recomputes (11).
  - `project`: Lemma 4 letter deletion.
  - `mixture_criterion` implements (7) and `leaf_criterion` implements (8), both with Fractions.
    `tree_leaves` splits boxes as u_j<=t and u_j>=t+1 from the root box [1,inf)^k.
- **Literal checks.** Every affine cost is also checked by executing the lifted word on stretched inputs.
  The stretch vectors are z = 0, e_j and 2e_j for every j, and e_i+e_{i+1} for i<3.
  Each run must end sorted with length equal to B+beta.z.
  For comparison rows, the lifted Q word is compare-executed on stretched P.
  That run rechecks P_z ⪯ Q_z, swaps = inv(P_z), and length equal to (11) at z.

## Results

### Stage files, full runs, 6 processes, nice 10

| stage | families | passed | failed | mixture rows | tree leaves / rows | claim mismatches | wall s |
|---|---:|---:|---:|---:|---:|---:|---:|
| four: complement plus 14 repair trees | 262513 | 262513 | 0 | 675106 | 34 / 83 | 0 | 235.6 |
| five: complement plus 4 trees | 337965 | 337965 | 0 | 1006798 | 8 / 27 | 0 | 285.6 |
| six: complement plus 2 trees | 228966 | 228966 | 0 | 760672 | 5 / 18 | 0 | 188.1 |
| seven: complement plus 1 reverse-tree fallback | 74614 | 74614 | 0 | 274056 | 3 / 12 | n/a | 70.3 |
| eight: complement | 10278 | 10278 | 0 | 41908 | - | n/a | 15.8 |
| nine: all orders | 40320 | 40320 | 0 | 152937 | - | n/a | 53.3 |
| reverse trees, direct | 4088 | 4088 | 0 | - | 4227 / 11356 | 0 | 5.1 |

- The seeded samples (seed 20260924, 2000 families each) for five through nine also pass with 0 failures. The chosen indices are recorded in `results/<stage>_sample.json`.
- The four-block counts match the theorem text exactly: 262499 mixtures, 14 trees, 675106 mixture rows, and 83 rows in 34 leaves.
- "Claim mismatches" compares recomputed mixture base and slopes, and tree-row base_cost and beta, against the stored values. The seven, eight and nine files store no such values.
- No same-sign violation occurred in any reference or tree word. Literal letters executed in the four-block run: 287920266 for lift checks and 477368284 for transfer checks.
- Counters named `reference_words` exceed the catalog size because each worker rebuilds its own cache.

### Coverage union for k>=4 (`union.py`, full, 40320 orders x 382 masks)

`union.py` reads no coverage table, npz file or projection table from the package.
For each (a,S) it takes the first of these that verifies:

1. A direct mixture record, checked by transfer and (7).
2. A direct tree, checked by (8).
3. A projection of any direct mixture record (a,M) with M strictly containing S. Each reference word is projected, the child reference is rebuilt and fully re-verified by Lemma 3, and (7) is checked with the child budget.
4. A whole-tree comparison transfer of one of the 8 reverse trees with mask S. Every weighted row in every leaf must transfer with some valid cut, then (8) is checked.

| k | families found | expected | uncovered | direct | proj. from 9 | from 8 | from 7 | from 6 | from 5 | reverse transfer |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 5080320 | 5080320 | 0 | 262499+14 trees | 2650704 | 82559 | 283720 | 796227 | 980978 | 23619 |
| 5 | 5080320 | 5080320 | 0 | 337961+4 | 3424724 | 115017 | 411857 | 778101 | - | 12656 |
| 6 | 3386880 | 3386880 | 0 | 228964+2 | 2739391 | 105814 | 310153 | - | - | 2556 |
| 7 | 1451520 | 1451520 | 0 | 74613+1 | 1321595 | 55311 | - | - | - | 0 |
| 8 | 362880 | 362880 | 0 | 10278 | 352602 | - | - | - | - | 0 |
| 9 | 40320 | 40320 | 0 | 40320 | - | - | - | - | - | 0 |

- No direct record failed, there were no errors, and 0 rows needed an alternative cut.
- The k=8 projection count 352602 equals the package's nine-projection table. The other split counts differ from the package because the order of attempts differs.
- Literal stretched execution ran on the deterministic 1/97 subset of decisions: 158785 families and 1179157504 letters.
- The run took 2081 s wall and 9752 s user CPU. Peak parent RSS was 1.37 GB.

### Low blocks (k<=3)

- **One block.** All 338 exception mixtures pass (7), with literal lifts. The set of their 338 states equals the `exceptions` list in `multiset_single_zero_resource_m8_20260919.json`.
- **Two blocks.** All 37323 trees in the full-cycle batch plus refinement rounds 1-8 pass, with 37323 distinct bases and 106618 rows. The seeded 2000-case sample also passes.
- **Three blocks.** All 639357 certified trees pass in 8 slices, 90.6 s total. That is 639357 distinct bases: 638889 from the native batch, with the rest from follow1, follow2 and the last-family file. The 468 refined cases and a seeded 2000 sample were also run separately, and all pass.

### Negative controls (`results/negative_controls.txt`)

The original eight-block record was accepted. Five corruptions were each rejected:

- a changed weight;
- a cut crossed by a swap;
- the single worst row with weight 1, which fails (7);
- a truncated reference word;
- reversed labels, which fail P ⪯ Q.

### Repository checks

The repository test suite ran 380 tests OK with 1 skipped. The skip is outside the new file, and the 5 new tests run in about 1 ms.
`compileall` passed, and `cli smoke` passed.

## Limitations: what was NOT independently replicated

1. **The k<=3 single-word certificates were not replicated.** These are 362542, 1776787 and 5976490 unit bases.
   They come from the resource search, which stores no words. Completeness of the exception lists rests on that search too, apart from the one-block list cross-check against the package's own resource file.
   Not checked either: the claims that 290 two-zero and 65+36888 three-zero exceptions with fewer linear blocks are covered by smaller cases.
   A k<=3 union table was therefore not rebuilt.
2. **Validity for all lengths rests on the lemmas as written.** These are Lemma 1, formulas (4)-(5), Lemma 3 with preservation of ⪯ under stretching, and Lemma 2.
   I read and re-derived these arguments and did not formalise them. Literal execution covers only the sampled z.
   Soundness does not depend on the same-sign condition: without it, B and beta from (5) are still upper bounds.
3. **Coverage in `union.py` was re-derived, not audited against the package's split.** It shows existence, not their exact assignment. The per-family literal stretch checks there are a 1/97 subset. The unit-base transfer and criteria were checked for every family counted.
4. **Not examined:** the Lean files, the n>=130 large-n theorem, the C++ programs, `projection_*` binaries, npz tables and package audit JSON.
   The large-n theorem is not needed, because the unbounded (7) and (8) were checked.
5. **Not checked:** the partition claim of section 2, that every vector is exactly one (a,S,u). The union enumerates all 8! x 511 pairs, which is that partition.
6. This is a computational re-check of finite certificates plus hand-checked lemmas. It is not a formal proof of the theorem.

## Files

- `checker/lrxm8.py`, `checker/check_stage.py` (`python check_stage.py STAGE [--sample N --seed S | --slice i/n] [--workers W]`), `checker/union.py`
- `checker/results/*.json` (per stage), `four_full.log`, `union.log`, `low3_full.log`, `negative_controls.txt`
- `tests/test_search_m8checker.py`

## Low-block search replication (section 7 single-word class)

The files are `checker/lowsearch.py` and the driver `checker/low_search.py`. Results are in `checker/results/low_search_*.json`. Everything is stdlib and was written from the theorem text only.

**The class searched.**
- Words are freely reduced: no LR, RL or XX.
- No word swaps two zeros.
- |W| <= 30+6k.
- Every zero j keeps the running resource hat-beta_j <= 6 after every letter.
- Resource increments use the section 7 table, keyed by letter and previous letter.

**How the search works.**
- It is a forward depth-first search per base. It prunes on g+1+dist(child) <= 30+6k, where dist is the exact unconstrained LRX distance from a stdlib BFS over all vectors.
- It also prunes by dominance on (vector, previous letter) using (length, resource vector).
- A search that exhausts certifies only "no word in this class". It does not certify infeasibility of the base.

**Independent re-check.** Each found word is re-checked with `lrxm8.Profile(each_zero=True)`, the Lemma 1 / (4)-(5) implementation. The word must sort, |W| <= 30+6k must hold, and every beta_j must be <= 6.
In every found case the end resource equals Profile beta exactly. That is 362542 + 4891 + 4478 words, with 0 disagreements.
No search hit the node budget.

| k | bases searched | words found | no word in class | matches the package | mismatches | wall s |
|---|---:|---:|---:|---|---:|---:|
| 1, all bases | 362880 | 362542 | 338 | exception set equals the 338 listed, exactly | 0 | 1246 (2 procs) |
| 2, seeded sample | 5000 | 4891 | 109 | all 109 are two-block bases listed in the tree file; all 974 adjacent-zero bases got words | 0 | 235 (2 procs) |
| 2, listed exceptions | 400 | 0 | 400 | seeded sample of the 37323 tree bases, all confirmed | 0 | 393 (2 procs) |
| 2, first_missing | 20 | 0 | 20 | 3 have adjacent zeros; the 17 two-block ones are in the tree file | 0 | 41 |
| 3, seeded sample | 5000 | 4478 | 522 | 491 three-block, all listed; 31 two-block, which cannot be compared (see below) | 0 | 1410 (4 procs) |
| 3, listed exceptions | 160 | 0 | 160 | seeded sample of the 639357 tree bases, all confirmed | 0 | 301 (4 procs) |

- All samples use seed 20260924.
- The expected exception counts in the samples are about 103.7 for k=2 and 480.5 for three-block k=3. The observed counts are 109 and 491.
- 31 two-block k=3 bases had no word. That is consistent with the claimed 36888 two-block exceptions, whose expected sample count is 27.7, but it could not be matched against a list.

**Arithmetic checks.** 37613 - 290 = 37323 and 676310 - 65 - 36888 = 639357. The trees verified earlier are 37323 distinct two-block bases and 639357 distinct three-block bases.

**Not replicated here:**
1. **Full k=2 and k=3 enumeration.** Of the 1814400 and 6652800 bases, only seeded samples of 5000 each were searched.
   A found word takes about 40 ms (k=2) and 0.3 s (k=3). An exhaustive absence proof takes 1-4 s (k=2) and 5-50 s (k=3) in pure Python. So full runs would take many CPU-hours.
2. **Most listed exceptions were not confirmed.** Only 400 of 37323 and 160 of 639357 were confirmed to have no class word.
3. **The adjacent-zero and fewer-block exception lists were not checked.** These are the 290 k=2 bases, and the 65 one-block and 36888 two-block k=3 bases.
   The literature files do not list them. They appear only as counts in the text, and as a replay byte array whose ranking would require the package scripts.
   So neither those counts nor the reduction of those bases to smaller cases was independently checked.
   In the samples, no adjacent-zero k=2 base lacked a word, and 31 two-block k=3 bases lacked one.
4. **The table itself was not re-derived.** Its correctness is supported only empirically, by exact agreement of resource and beta on every found word.
   The theorem proves that the final resource equals beta and that increments are non-negative. Pruning at 6 is valid only under those claims.
