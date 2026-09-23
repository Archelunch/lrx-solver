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

## Supplied nine-gap theorem and distributed verification data

A separate unpublished Russian manuscript, "LRX coverage: all orders of eight
labels with nine zero blocks", dated 2026-09-24, was supplied by the user as
`lrx_multiset_nine_gap_m8.pdf`. The PDF itself is not included. Its original
Russian theorem text and embedded verification archive are retained under
`autoresearch/loop-260923-2107/incoming/`; hashes are in `source-manifest.json`.
Source text retains its original language; repository summaries are in English.

Our independent data-only auditor checked 40,320 orders, 4,670 reference words,
152,937 rational mixture rows, and 42,030 literal stretch cases. Together with
the manuscript's comparison and stretching lemmas, these support the stated
all-positive-length nine-gap m=8 theorem. This does not prove full m=8 or the
general conjecture. No supplied archive code was imported or executed.

The manuscript's projection and union coverage counts are attributed, not
fully re-audited here. The union also relies on earlier reverse-order and
<=3-block results; the large <=3-block proof data are absent from this archive.
The supplied materials retain their source attribution; no new authorship or
license for them is inferred from this repository's code license.

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
