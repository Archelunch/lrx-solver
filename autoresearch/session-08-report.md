# Session 08: exact projected mixtures without API calls

The bounded local phase certified 76 distinct m=8 families for all positive
zero-block lengths using the reviewed comparison/stretching lemmas. General
LRX and full m=8 remain open; no global coverage total was recomputed.

- 52/100 frozen development families and 24/50 confirmation families certified.
- 60 certificates use reweighted inherited supports; 16 add existing words
  from a seeded 128-word pool. No new reference words or model calls.
- A development ablation finds 38 certificates with old coefficient bounds,
  versus 39 with freshly computed projected coefficients on inherited support.
- Independent repeated marked-zero projection agreed on 226 words; 1,811
  expanded support-component words replayed successfully.
- The initial sampler's little-endian decoding bug was caught by the baseline
  guard. That attempt is preserved and excluded; version-2 results are final.
- 327 tests, compileall, smoke and trusted hashes pass. Remaining API budget:
  $19.851381. Numerical optimization proposes; exact arithmetic accepts.
- Next: broaden the existing catalog on unresolved development families and
  freeze fresh confirmation. A paid engine pilot is not yet necessary.

Full evidence and mathematical example:
`autoresearch/loop-260923-2154/report.md`.
