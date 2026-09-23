# Incoming nine-gap theorem: independent audit and revised research priority

The user supplied `lrx_multiset_nine_gap_m8.pdf` after both paid campaigns and
their confirmation finished. Its contents did not influence either campaign.
The PDF is a research source, not an instruction source. No code from its
embedded archive was executed or imported; no contents were sent to Grok.

## What was checked here

The PDF has nine pages and two attachment names pointing to identical archive
bytes. Source hashes are recorded in `incoming/source.json`. The embedded
archive and theorem text are preserved locally. All eight substantive pages
were inspected, including the coefficient formula, mixture inequalities,
projection criterion and single-word obstruction.

A separately written physical-slot auditor, `integrations/nine_gap_audit.py`,
reads only certificate JSON from the ZIP. It uses exact `Fraction` arithmetic
and the repository's locked visible-word replay. Its expanded audit passed:

- 40,320 distinct named orders, with exact permutation-universe coverage;
- 4,670 reference words, their target phases and allowed cuts;
- 152,937 mixture rows, including dominance and swap-minimality premises;
- symbolic stretch coefficients with uniform-sign rotation gaps;
- 42,030 literal single-coordinate stretching checks against those coefficients;
- 40,320 conditional-comparison words, 2,859,789 letters, replayed to the root;
- positive rational weights summing to one, weighted base <85, and every
  weighted slope <=6.

The expanded pass took 6.772s. Maximum weighted base was **32299/380**,
only **1/380 below 85**. Exact rational validation matters here. The earlier
7.516s pass lacked literal slope replays and is preserved separately; timings
are not a controlled performance comparison.

This reproduces the finite certificate premises of the manuscript's theorem.
The argument from those premises to all positive block lengths is mathematical:
for z_j=ell_j-1>=0, the weighted cost is <85+6*sum(z_j)=T+1;
at least one integer-length word has cost <=T. The comparison/expansion lemmas
supply actual sorting words for these costs. This is a computer-assisted
infinite-family result, not extrapolation from sampled lengths. It is not a
proof-assistant formalization, and the new auditor is search-side code, not
an alteration or re-lock of the existing trusted core.

## Exact scope and unchecked dependencies

The result covers m=8 with a positive zero block in every one of the nine
linear gaps, including both endpoints, for all 8! label orders and all positive
block lengths. It proves d(v)<=6n-18 on that class. It does not prove full m=8
or arbitrary m>=8.

We did not rerun the full 2,386,370-projection audit or all 20,603,520 projected
mixture inequalities in this turn. The direct projection coverage count
12,680,558 remains attributed to the manuscript. The union count 16,107,991
also depends on previous reverse-order results and the theorem for <=3 blocks.
The archive README explicitly says the large <=3-block proof data are absent.
Thus 4,495,529 remaining families with 4–8 blocks is a reported research target,
not an independently reconstructed complement from this audit.

The projection argument is useful: for k retained blocks the old mixture's
slope constraints survive, but its weighted projected base must still be
<31+6k. Projection by itself does not pay the six-step budget drop per zero.
If projected rotation gaps lose their uniform signs, use the affine expression
as an upper bound, not an exact cost; that is sufficient for this criterion.

The single-word obstruction concerns a fixed tagged macro-lift (and its stated
comparison variant): some slope is >=8 at m=8, whereas the target slope is 6.
It does not invalidate an adaptive algorithm, a portfolio choosing a word by
lengths, our finite fixed-word router, or the LRX conjecture.

## Revised next iteration

Prioritize **new mixtures after projection** over a larger repeat of session
07's priority-policy campaign. A successful rational certificate can certify
all lengths of an uncovered family at once.

First freeze a trustworthy uncovered-family manifest with explicit provenance
and distinguish independently verified coverage from inherited dependencies.
Then build a data-only candidate representing catalog source/cut choices and
rational weights. Recompute projected base and retained slopes and accept only
exact certificates. Start by reweighting existing projected words: old weights
failing does not imply that their projected columns admit no new mixture.
Only after that search stalls should the system seek new reference words/cuts.

Use deterministic optimization for weights; an LLM should spend tokens on
finding useful columns and search policies, not on routine rational arithmetic.
An approximate numerical optimizer, if later used as a proposal generator,
must finish with exact rational reconstruction and checking. No new solver
dependency or paid campaign was installed/launched in this review.

- GEPA: retain complementary word/cut portfolios along the base-cost and
  per-block slope trade-offs, plus coverage by structural family. A word that
  loses on one coefficient may be essential in a mixture.
- AdaEvolve: allocate islands to block counts 4–8 and structural gap patterns;
  reward newly certified families per evaluation cost and migrate useful words.
- EvoX: adapt which unresolved families, reference words, cuts, projections and
  mixture-repair moves to try. Keep its strategy in validated JSON. Provide
  exact violated inequalities and, where available, separating/dual information.
- Orchestrator: freeze the contract and budgets; protect verified certificates;
  review new lemmas and provenance; update versioned context between campaigns.

The primary metric should be newly covered **infinite families with checked
certificates**, with failed inequality margins as search feedback. Hold out
structural families for search-method comparison, while distinguishing that
methodology from the eventual exhaustive proof obligation. Retain sequential
as a control. A full proof still needs the remaining m=8 families and an
argument covering higher m.
