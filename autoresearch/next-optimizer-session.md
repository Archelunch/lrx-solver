# Next session (written 2026-09-26 evening)

Read HANDOFF.md top section, research/claims.md Sessions 24-36, and
autoresearch/SESSION-REPORT-260926.md first.

Ordered next steps:
1. Human review of the four flagged proof steps (LEMMA1-GENERAL-M 4.1,
   LEMMA34-GENERAL-M 4.3 items 2-3, WORDC-PROOF Lemma E, WORDR1-PROOF
   Lemma P). Until then every "proved" line stays "proof written,
   unreviewed". Send lrx-findings-260926-v4.zip to the group.
2. Campaign 3 seeds 2-3: get "approve <hash>" for the current
   `python -m integrations.bound_c3 approval-hash --campaign-dir
   autoresearch/bound-m-c3-260926` (ca4ee0f0... at hand-off), then
   `bash autoresearch/bound-m-c3-260926/run-one-c3.sh <arm> <seed>` for
   seeds 2, 3 (8 runs, about $8), then
   `python -m integrations.bound_c3_finalize finalize --run-dir
   autoresearch/bound-m-c3-260926`. Run with the machine otherwise idle
   (Session 35 caveat: oracle load caused evaluation timeouts). Record in
   claims as Session 37 with the seed-relative gain.
3. Middle band m = 13, 14 with the C oracle on a bigger machine (needs
   about 12-16 GB for the abstraction tables), or extend lrxtree_wide
   with a coarser abstraction. Target: the odd-centre conjecture (root
   impossible for {0,(m-1)/2}) at m = 13, and tree closures.
4. Prove word_G from the 28 hypotheses in WORDR1-PROOF.md section 11
   (needs a partial-carry sweep lemma). Then word_M, word_W.
5. Generalise: a lower-bound lemma on label crossings of a cut zero (2
   per crossing for carries, 3 for walks) would turn the refutations into
   theorems for whole bands.
6. Engines: only launch on a task where the seed is strong and the
   holdout is unseen m; measure against the seed, not the naive control.

Rules unchanged: never push or call a provider without explicit human
approval; first prompt and hash shown before launch; holdout one-shot;
claims wording (computed / replicated / certified conditional / proof
written unreviewed / conjecture / negative).
