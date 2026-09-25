# Audit of downloads/audit_multiset_antipodal_peak90.py

## 1. What it verifies
For `m >= 90, n >= 2m-2`, asserts `len(word) <= target(m,n)` (the claimed
`E_{n-m}(n) <= T_m(n)` bound), via three layers per sampled state: (a) a
symbolic/rational algebra chain (loads, cycle counts, cut multiplicities,
four rational weights `1/2,2/3,3/4,1`, moments, a "geometric"/"relaxed"
sandwich, boundary/threshold scalar identities up to `m=10000` and formal
`10^5..10^30`) all done with exact `Fraction` arithmetic; (b) geometric
identities relating direct/antipodal ("opposite") anchor descriptions,
transport distances, and approach sums; (c) for a subset of states, literal
construction and replay of an actual LRX word (`literal_replay`) checked
against the exact target permutation. It is a finite-case validator over
enumerated/sampled states plus a symbolic scalar-identity check for large
`m`, not itself a proof for all `m,n`.

## 2. Inputs / self-containment
Not self-contained. It imports four modules that do not exist anywhere in
this repo or in `downloads/`: `multiset_antipodal_peak_bound.py`,
`audit_multiset_direct_anchor.py`, `audit_multiset_mixed_moments.py`, and
`audit_multiset_sparse_cover` — the last exists under
`downloads/recent/lrx_m8_complete_verification/scripts/` and
`autoresearch/verify-m8-260924/package/scripts/`, but only that one; the
other three, plus `audit_multiset_peak_load219.py`,
`audit_multiset_discrete_geometry.py`, `audit_multiset_rank_classes.py`,
`audit_multiset_rank_triples.py`,
`audit_multiset_reserve_geometry_and_sharp_rotation.py`, and
`multiset_named_rotation_transfer.py` (listed at the end for sha256
hashing) are absent entirely. No Lean files or literature JSON are read.

## 3. Run attempt
Copied to scratch, ran `python3 audit_multiset_antipodal_peak90.py --output
./result.json`. Exact failure:
```
Traceback (most recent call last):
  ...
    from audit_multiset_sparse_cover import all_states,literal_replay
ModuleNotFoundError: No module named 'audit_multiset_sparse_cover'
```
Did not fabricate any missing module; script cannot execute as-is even with
the one partially-matching helper file found in the repo, since the other
three core modules it needs first (`multiset_antipodal_peak_bound`, etc.)
are also missing and would fail next.

## 4. Independent spot-check (stdlib only)
Implemented cycle decomposition, `lambda_C(j)` as the standard linear-cut
crossing count per nontrivial cycle, `Lambda = sum_C max_j lambda_C(j)`,
`Delta = sum|pi(i)-i|`, and checked `Delta <= m*Lambda - Lambda^2/2`.
Exhaustive over all permutations for `m=4..8` (51,224 total) plus 5,000
seeded random permutations at `m=12`: **zero failures**. This supports the
inequality under this natural cut-load definition but does not confirm the
script's own internal definitions (`opposite_description`/`price`/etc.),
which were unreachable since the module defining them is missing.

## Bottom line
Script is well-structured and exact-arithmetic throughout, but not
runnable here: 4 of ~15 dependency modules are missing from the repo, so
the theorem's own machinery could not be exercised. The one bound we could
isolate and brute-force independently held with no counterexamples in the
tested range.
