# Sources

## Mathematical sources (not distributed with this repository)

1. **Manuscript.** "Добавление нуля: точная редукция и неограниченный
   перерасход проекции" ("Adding a zero: exact reduction and unbounded
   projection overrun"), unpublished, in Russian, dated 2026-09-21. File
   `lrx_multiset_marked_zero_reduction.tex`, SHA-256 in `source-manifest.json`.
   The code calls it "the manuscript". Its Theorem 1 (exact F recurrence),
   Theorem 2 (the 6k-2 family and its detour barrier) and section 6 (the
   lifting candidate A_P <= P+m-2) are the results this lab tests.
2. **Progress notes.** "LRX with repeated entries: the conjecture, corrected,
   reparametrised, and reduced to the pure Cayley graph", unpublished working
   notes dated 2026-09-18. Source of the empirical radius formula
   `(m-2)n - (m^2-3m-4)/2` and of the radius values used as test targets.

Neither document is included here, and no authorship or license is inferred
for them. Every result they contain is attributed to them in
`research/claims.md` and is not independently certified unless that file says
so.

The original audit tools named in the manuscript were not available:
`multiset_marked_zero_geodesic.cpp`, `audit_multiset_marked_zero.py`,
`audit_multiset_marked_zero_barrier.py`,
`multiset_marked_zero_lift_final_20260920.json`. This repository is an
independent Python implementation, not a port of them.

## Published work

- V. Antiufeev, arXiv:2601.08715 (pure LRX lower bound D_n >= C(n,2)).
  External claim, not checked here; see `research/claims.md`.

## Frameworks (researched; not vendored)

- cayleypy: https://github.com/cayleypy/cayleypy (independent BFS cross-check,
  `tools/cayleypy_crosscheck.py`)
- GEPA: https://gepa-ai.github.io/gepa/ (reflective Pareto search;
  `src/lrx/evolve.py` has a compact local re-implementation,
  `integrations/` wires the official package)
- AdaEvolve / SkyDiscover: https://skydiscover-ai.github.io/blog.html,
  https://arxiv.org/html/2602.20133v1
- autoresearch loop: https://github.com/uditgoenka/autoresearch
- xAI Grok API: https://docs.x.ai/developers/grok-4-7

No native SkyDiscover integration or framework performance result is claimed.
