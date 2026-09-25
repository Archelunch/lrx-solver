# verify-m8-260924: independent replication of the external m=8 package

Started 2026-09-24. Source: `downloads/recent/lrx_m8_complete_verification`
(group package, claims E_{n-8}(n) <= 6n-18 for all n >= 9, zero uncovered
families among 20 603 520). Copied to `package/` (gitignored, 834 MB);
`m8_manifest.json` SHA-256: 147 entries, 0 mismatch, 0 missing.

Goals agreed with the user (2026-09-24):
1. Layer A: run the package's own `scripts/replay_multiset_m8_package.py`
   unchanged, nice'd, in background. Output `replay-full.json`,
   `replay-console.log`, logs in `package/m8_replay_logs/`.
2. Layer B: independent stdlib checker written from the theorem text
   (`checker/`), not from package scripts. Full 4-block complement, seeded
   samples of stages 5-9, union table rebuilt from certificates.
3. k5-mask302-order15713 compatibility test (`k5-mask302/`).
4. Claims stay attributed: repo claims flip only after 1-2 pass.
Deferred to a later iteration: transport fix, m=9 frozen development set,
GEPA pilot ($8 / 20 contacts cap approved, no call made yet).

No provider calls, no new dependencies, no commits in this run.
Lemma-14 counterexample note in downloads is a separate thread, out of scope.
