# Roadmap and open problems

The conjecture is open. Everything below is either a mathematical question the
finite evidence suggests, or an engineering task that would make the search or
the checks stronger. Evidence for each item is in `research/claims.md` and
`autoresearch/`.

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
6. **Engine comparisons at equal budget and several seeds.** So far one seed
   per arm: sequential refinement won most rounds, GEPA with a focus graph won
   once, AdaEvolve's exploration did not pay at 12 proposals.

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
14. **Official integrations.** The official GEPA runner
    (`integrations/run_gepa_official.py`) has run only with a fake LM;
    SkyDiscover is not integrated.
