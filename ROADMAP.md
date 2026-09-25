# Roadmap and open problems

The conjecture is open. Everything below is either a mathematical question the
finite evidence suggests, or an engineering task that would make the search or
the checks stronger. Evidence for each item is in `research/claims.md` and
`autoresearch/`.

## Immediate priority: general m after the external m=8 closure

Update 2026-09-24: the research group's package claims the full m=8 bound
E_(n-8)(n) <= 6n-18 for all n >= 9, and this repo replicated it (their replay
PASS; independent checker on every k=4..9 file and a rebuilt k>=4 union with
0 uncovered; k<=3 single-word certificates not replicated). See
`research/claims.md` Session 10. Items 1-5 below are historical m=8 targets
and are superseded. The first live m=9 lift campaign ran on 2026-09-24 (`autoresearch/lift-m9-260924/`):
all three engines plus a sequential control tie at 190/2295 holdout certificates
against 158 for the fixed gadget, 84 new audited m=9 families, no lemma.
Next campaign: reward new word constructions (not re-ranking), 8k output or
diff proposals, repeated seeds for a comparison, and search for a gadget that
is uniform in m. Keep the general conjecture open.

The supplied nine-gap m=8 theorem has independently checked certificate
premises for all 40,320 label orders and arbitrary positive block lengths.
The general conjecture remains open.

1. Extend the selected-case projection baseline toward a full auditable
   inventory. Session 08 certified 76 named families with 4–8 blocks, checking
   their exclusion from inherited mixtures and supplied reverse transfer.
   Global union totals remain partly attributed.
2. Expand the existing-catalog search beyond the 128-word pool used in session
   08. The deterministic mixture optimizer and exact acceptance checks work;
   keep weights summing to one, weighted base <31+6k, and slopes <=6.
   Search failure is not infeasibility. Use fresh structural confirmation
   for the next method comparison.
3. The data-only mixture adapter now works with all four planners. Session09
   ran EvoX and sequential: four versus two development additions and the same
   one confirmation addition. Next compare offline random policies and repeated
   seeds; retain complementary profiles for GEPA and distinct construction
   classes for AdaEvolve. No robust engine ranking follows from this pilot.
4. Seek new words only after measuring the limits of the existing catalog.
   Reward newly certified infinite families, preserve an untouched structural
   confirmation set, and extract mathematical reasons for successful mixtures.
5. On the official executable-program branch, the frozen all-cuts control
   certifies 15/16 development families. The remaining unit-block k5 family
   is still open; a Sol-authored dual-guided column lowered the feasible base
   to 1223/20 but did not cross the strict threshold 61. Its conditional
   construction works when the first retained zero block has length at least
   2. A broker-rejected complete Grok response, independently evaluated and
   accepted in an offline native GEPA replay, added one named family beyond
   catalog plus all-cuts on the consumed one-shot confirmation (14/16 versus
   13/16). See the [continuation](autoresearch/loop-260924-protocol/CONTINUATION.md).
   Next seek an exact unit-block k5 mixture or a different proof mechanism;
   freeze a new holdout before any further model search, and never treat a
   failed finite search as infeasibility.

This supersedes the pre-PDF proposal to immediately expand routing-priority
search. See [the bounded next-iteration protocol](autoresearch/next-iteration.md)
and [the source review](autoresearch/loop-260923-2107/paper-review.md).

## Mathematics (needs a human proof or review)

1. **Review the potential arguments.** The descent proofs for
   `candidates/probes/ba656bf2c7e03787.json` and
   `candidates/probes/6ff08052bb698f26.json` (Route C in
   `research/claims.md`) are short and were checked by the orchestrator only.
   They give cubic bounds, far above T_m(n), but they are the first
   certificates of this kind here.
2. **Replacement lifting lemma.** For m >= 8, r >= 3: A_{P+1}(v) <= P + m - 2
   for every visible v. It holds on every exhaustively computed graph where the
   budget is at least the radius, and would carry the radius recursion
   E_r(n) <= E_{r-1}(n-1) + m - 2 just as the refuted q = P version would.
3. **The r = 3 obstruction family.** Exactly one vector fails A_P <= P+m-2 on
   each of (10,7,3), (11,8,3), (12,9,3), with alternating shapes and overruns
   4, 1, 2 (`autoresearch/r3-family.md`). Describe the family and decide
   whether the overrun stays bounded. Side targets: d(u_m) = C(m+2,2) - 3 for
   u_m = (2,1,0,0,m,...,3), and d(F1_m) = T_m(m+3).

## Search (Routes A and C)

4. **Rules controllers.** The best lead,
   `candidates/leads/49ab346cb44b2f1b.json`, is at 1.5625 x T on the m >= 8
   train probes and has plateaued at (8,3) (75 vs T = 48). Next idea: build a
   two-sided controller (two complementary arcs) on small graphs first, then
   refine it.
5. **Tighter potentials.** Add a third amortisation level (a count of blocks
   or runs), or find a smaller invariant e. The 80-node DSL limit is binding;
   raising it is a trusted-core change that needs human review.
6. **Engine comparisons at matched budgets and several seeds.** Session 04
   ran two seeds per main arm; its training gains did not separate finalists
   on fresh confirmation. Session 07 ran one 12-proposal lifting arm each for
   sequential and EvoX: 22/28 versus 24/28 development coverage, both 120/120
   on random confirmation. EvoX's strategy rewrites brought no new best.
   No robust ranking follows. Use harder structural confirmation and report
   proposal count, reflection count, actual cost and evaluation work separately.

## Exact checks (Route B)

7. **(13,9,4) at k = 4** around the four band-edge tight vectors found at
   k = 3. Most states of (13,10,3) and (13,9,4) are still unchecked.
8. **n = 13 tables** (3.1 billion states for r = 2) need a larger machine or
   an external engine (cayleypy on a GPU box).
9. **Original audits.** The manuscript's C++ tools and its 48,384,000-state
    audits are unavailable and have not been reproduced.

## Engineering

10. **Installable package.** Data paths (`datasets/`, `runs/`,
    `candidates/`) are resolved relative to the source tree, so run from a
    checkout or an editable install (`pip install -e .`). Making them
    configurable would allow a normal wheel install.
11. **CLI help.** `python -m src.lrx.cli --help` lists only the v1 commands;
    the v2 commands dispatch through `src/lrx/commands.py`.
12. **Retire the legacy `experiment` command** and `provider_adapter.py` once
    nothing depends on them; `evolve` supersedes both.
13. **Windows.** Parallel table builds use the `fork` start method.
14. **Official program-search pilot.** The older JSON GEPA shim
    (`integrations/run_gepa_official.py`) was tested only with a fake LM.
    A separate official GEPA/SkyDiscover program-search integration has
    completed offline smokes; its frozen 4–7-block inputs, shared broker, and development
    archive are described in `integrations/official-research.md`. Native
    offline iterations of GEPA, AdaEvolve, and EvoX have run with isolated
    candidate evaluation. Bounded archive context retrieval reached an
    AdaEvolve proposer in an offline smoke. An evolved EvoX strategy also
    executed inside its worker boundary. A later bounded paid live iteration
    used all three official engines and a shared capped broker. The paid arms
    produced no development gain over the 14/16 seed, while a separate
    deterministic all-cuts control reached 15/16. Catalog and all frozen
    finalists tied at 6/8 on sealed confirmation. See the [live report](autoresearch/loop-260924-live/report.md)
    for exact accounting, failure modes, and source attribution. No engine
    ranking or general theorem follows. The subsequent k5 protocol's
    [continuation](autoresearch/loop-260924-protocol/CONTINUATION.md) has a
    conditional Sol-authored k5 bound and one independently audited named
    holdout certificate from a broker-rejected Grok response. An offline
    native replay accepted that source; the live native run did not.
