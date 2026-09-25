# k5-mask302-order15713: package certificate compatibility test

Date 2026-09-24. Purpose: check whether the external m=8 package certifies the
repo's hardest open development family, and whether our evaluator agrees.
This is the research group's certificate replayed here, not our discovery.

## Family

Name decoded from code (`autoresearch/official-integration-260924/prepare.py`,
`integrations/mixture_policy.py`, `integrations/projected_mixtures.py`):
mask 302 has bits 1,2,3,5,8 (bit j = gap before label j+1, bit 8 = trailing
gap); order index 15713 in `permutations(1..8)` is labels (4,1,7,8,5,6,3,2).
Unit-block vector: (4,0,1,0,7,0,8,5,0,6,3,2,0). k=5, threshold 31+6k = 61.

## Search history

1. A literal record with (mask 302, order 15713) does not exist in the
   five-gap bounded search, repairs, audit, or control files, nor as a
   six-gap superset. That first negative report was incomplete.
2. The actual route is Lemma 4 downward projection. The replay-generated
   coverage arrays (`directly_covered`, `union_covered`, `projected_covered`,
   `witness_record`, shape (40320, 512), indexed [order, mask]) show the family
   uncovered in `dependency_eight_projection.npz` and covered in
   `dependency_seven_projection.npz` with witness record 37688 of
   `literature/multiset_seven_gap_complement_certificates_20260924.json`:
   mask 446 (superset of 302), order 15713, same labels; four-term mixture,
   sources 33964/34239/33413/34915, weights 3/44, 5/11, 9/44, 3/11.

## Replays

| Replay | Code | Weighted base | Slopes | Criterion (7) |
|---|---|---|---|---|
| `replay_projection.py` | package library functions, read-only | 121/2 | 6, 63/11, 6, 6, 6 | holds |
| `replay_projection_independent.py` | stdlib only, own Lemma 1/3/4 | 121/2 | 6, 63/11, 6, 6, 6 | holds |
| `evaluator_check.py` | repo `integrations.projected_mixtures` | 121/2 | 6, 63/11, 6, 6, 6 | margin 1/2 |

The independent replay deletes the two extra zero atoms per Lemma 4, transfers
to the exact target state per Lemma 3 (swaps emitted equal inversions), lifts
per Lemma 1 macros, and executes literally at z = 0, e_j, 2e_j, and all ten
pairs e_i+e_j; every run sorts to (1..8,0^5) and lengths fit the affine form
exactly. 121/2 < 61 and all slopes <= 6, so the family is certified for all
positive block lengths, including the unit block a=1 that our pool missed.

## Comparison with repo state

Our 123-profile pool optimum was 1223/20 = 61.15 (3/20 above threshold).
The projected four-word mixture reaches 60.5, a genuinely different column set.
Repo claims for this family should cite the package certificate, attributed.

## Limitations

Only this one witness record was checked. The seven-gap bundle as a whole and
the coverage array generation were not re-audited here; that is the job of
`../checker/`. Nothing under `package/` was modified. Files: `family.json`,
`certificate-extract.json`, `replay-result.json` (with corrected conclusion),
`replay-projection-result.json`, `replay_projection_independent.py`,
`evaluator_check.py`.
