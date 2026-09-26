# LRX Lab: status report for collaborating agents, 2026-09-26

Repository `lrx-lab`, latest commit `143dd4c` on `main`. This updates the
2026-09-25 report (`REPORT-FOR-AGENTS-260925.md`). Everything below is either
independently re-checked in this repository or labelled as a conjecture,
observation, or negative search result. Nothing here proves the general
conjecture E_r(n) <= T_m(n) = m(m+1)/2 + (r-1)(m-2) for all m >= 8.
Attribution: Lemma 1, criteria (7)/(8) and reversal trees are the research
group's (m=8 manuscript); this repository applies them with m as a
parameter and replicates or extends them. No priority claims.

## Краткая сводка (RU)

- Задача "сертификация ограничения" (программа certify(family), точная LP
  по критерию (7) группы с параметром m): эволюционные конструкции впервые
  переносятся на невиданные m=11 и m=12. Кампания 1: EvoX 129/165, GEPA
  125/165 на m=11 против 98 у ручного контроля (зазор 4 у обоих движков).
  Кампания 2 (3 семени на движок): среднее покрытие на holdout AdaEvolve
  84.7%, EvoX 83.1%, GEPA 80.3%, контроль 59.6%; лучший finalist AdaEvolve
  seed 2 сертифицирует 148/165 при m=12.
- Найденная конструкция (AdaEvolve-s2): та же рамка лифта-и-свипа, что у
  затравки EvoX, плюс второе окно для чётного n, обратный tie-break при
  нормализации суммы 0, две новые развёртки (bounce), старт курсора со
  сдвигом и геометрический отбор слов (выпуклые оболочки, лучи,
  Франк-Вульф). +19 семейств при m=12 без потерь.
- Древесные сертификаты (bound-eval-3, критерий (8) группы): контроль на
  готовых таблицах закрывает m=9-реверс {0,4} тремя листьями и 19 из 43
  семейств, которые пропускает AdaEvolve-s2, но ничего при m=11 (нет
  таблицы). Разница bound-eval-2/3 - 0 байт на общих строках.
- Точные таблицы (10,2) и (11,2) построены: радиус = T в обоих случаях,
  ровно два экстремальных состояния, реверс с двумя внешними нулями лежит
  на T-1. Ручные генераторы word_A/word_B/word_E сертифицируют семью
  (m..1){0,m} при m=9..12 и не справляются с m=13, где база и наклон
  требуют противоречивых свойств одновременно.
- Кампания 3 подготовлена (древесный драйвер, затравка с уточнённым
  началом координат, лимит $15), но не запущена - ждёт человека.
- Условность: каждый сертификат условен на лемме 1 группы и критерии (7)/
  (8) группы при общем m, что группой не подтверждено вне m=8. Общая
  гипотеза остаётся открытой.

## 1. Verified results

| # | Statement | Status | Evidence |
|---|---|---|---|
| 1 | Evolved certifiers transfer to unseen m=11: EvoX 129/165, GEPA 125/165, worst gap 4; best hand control 98/165, gap 7 | computed, audited | `autoresearch/bound-m-260925/finalists/REPORT.md`; 0 audit disagreements, $3.45 |
| 2 | Campaign 2, three seeds, unseen m=12 and fresh m=11: holdout mean AdaEvolve 84.7%, EvoX 83.1%, GEPA 80.3%, sequential 76.4%, sweep+LP control 59.6%; best single finalist AdaEvolve-s2 148/165 at m=12, 54/60 at fresh m=11 | computed, audited | `autoresearch/bound-m-c2-260925/finalists/REPORT.md`; 0 audit disagreements, about $7 |
| 3 | bound-eval-3 (tree contract, criterion (8) per leaf) byte-identical to bound-eval-2 on plain word lists; audit agrees on 411/411 stored campaign-2 rows and 24/24 new trees | verified | `integrations/bound3_*.py`, `tests/test_search_bound3.py`; independently confirmed here: control-a rescore of AdaEvolve-s2 under bound-eval-3 reproduces 260/303 dev and 151/165 validation exactly, `autoresearch/bound-eval3-260926/control-a-summary.json` |
| 4 | Table-fed tree control certifies the m=9 reversal {0,4} with three leaves (every campaign-2 arm had gap 15/7 or 9/5), the m=10 tight family {0,10}, and 19 of the 43 development families AdaEvolve-s2 misses; nothing at m=11 for lack of a table | computed, audited | `autoresearch/bound-eval3-260926/`, claims Session 17 |
| 5 | Exact (11,2) table (n=13, 3,113,510,400 states): radius 75 = T_11(13), exactly two extremal states, (0,0,11,...,1) and its rotation (2,1,0,0,11,...,3) | computed, re-checked | low-memory builder, 4 workers, 3.2 h; histogram, no unreached state, 20,000-sample triangle inequality, literal replay; `autoresearch/bound-m-260925/checks/m11-r2-reversal-words.json` |
| 6 | The reversal with two outer zeros (0,11,...,1,0) has exact distance 74 = T-1 at m=11 (family {0,11}, mask 2049); the earlier gap-4 verdict was a construction limit, not an obstruction | computed | shortest word stored and replayed; also true at m=8,9,10: distance = T_m(m+2)-1 exactly | `autoresearch/bound-m-260925/REVERSAL-WORDS.md` |
| 7 | Exact (10,2) table (n=12, 239,500,800 states): radius 63 = T; same two-extremal-state pattern | computed, re-checked | low-memory builder matches an independent in-memory rebuild byte for byte, sha256 3f9ad500... |
| 8 | For m=8..11, d((0,m,...,1,0)) = T_m(m+2)-1 exactly; every shortest word has floor((m+1)^2/4)-1 swaps; number of shortest words 108, 132, 1104, 1296 | computed | full DAG enumeration, replay-checked; `checks/reversal-words-m8-11.json` |
| 9 | Hand generators word_A, word_B, word_E (pure functions of m, stdlib only) certify family (m..1){0,m} for all block lengths, conditional on Lemma 1 and criterion (7): m=9 (word_B alone), m=10 (word_A+word_B, 1/2-1/2), m=11 (word_A alone, 74 letters, slopes (9,8)), m=12 (word_A+word_E, 6/7-1/7) | computed, audited | evaluator bound-eval-3 and the independent lrxm8-based audit agree; `autoresearch/bound-m-260925/REVERSAL-WORDS.md` |
| 10 | The same family is NOT certified at m=13..16 by any of the three generators or their mixtures; gap grows from 6/5 at m=13 | negative, exact (LP) | word_A's base overshoots T by about (m-10)^2/2 while every shortest word (E-shape) has slope about 3m/2 > m-2; no shortest word or mixture certifies for m>=13 |

## 2. Conjectures and observations (not proved)

- **Identity rotations (Conjecture A').** For m >= 9 and any cyclic rotation
  of 1..m with any mask, the lift-and-sweep pool contains a certifying
  mixture. Evidence: 23/23 in campaign 2's own records (4/4, 6/6, 8/8, 5/5
  at m=9..12), plus 11 more from campaign 1, for 34/34 total. Sample is
  small against 12 x (2^13-1) families at m=12.
- **Easy class (Conjecture E).** Same claim for the low-inversion "easy"
  class. AdaEvolve-s2 certifies 45/45 across m=9..12; weaker than A'
  because it is engine-dependent (the seed and control each miss one at
  m=9).
- d(u_m) = T_m(m+2)-1 for all m >= 4 (exact m=4..11; upper bound by replay
  of word_E to m=200; lower bound beyond m=11 unknown, (12,2) has 4.4e10
  states).
- The (m,2) radius equals T_m for all m >= 8, attained by exactly two
  states (exact m=8..11; upper bound by replay beyond).
- What would close family (m..1){0,m} from m=13: an m-uniform word or
  mixture with base <= T and Lemma-1 slopes <= m-2 simultaneously; none of
  E, A, B, or their mixtures provides this. Untested hybrid: E's balanced
  zigzags with A's bounded number of crossings of the zero block.
- The worst family missed by all four campaign-2 arms at m=12 is the plain
  reversal with two cyclically adjacent zeros (mask 4097/4098), stuck at
  gap 5 in every arm; this is the direct analogue of campaign 1's worst
  m=11 miss.

## 3. Search framework: what works and what does not

Same pipeline as the 2026-09-25 report (`integrations/`: exact evaluators,
Gemini/xAI budget broker with durable receipts, frozen development/holdout
splits, native GEPA/AdaEvolve/EvoX adapters plus a sequential control,
finalize with independent audit, pre-registered success/kill rules). New
this cycle: `bound3_*.py` tree-contract evaluator and audit, bounded
in-slot broker retry for 502/503/504/429 with Retry-After. Suite grew to a
reported 604-612 tests across sessions as new regression tests were added.

| Campaign | Task shape | Holdout result | Verdict |
|---|---|---|---|
| bound-m campaign 1 | certify(family): exact Lemma-1 lift + LP, dev m=9,10, holdout m=11 (all 165 unseen) | EvoX 129/165 gap 4, GEPA 125/165 gap 4, control 98/165 gap 7; AdaEvolve and sequential overfit (invalid outputs off-distribution) | first transfer to unseen m; both winning engines beat the hand control |
| bound-m campaign 2 | same task, 3 seeds/arm, seed = campaign-1 EvoX finalist, dev+validation m<=11, holdout m=12 + fresh m=11 | mean holdout% AdaEvolve 84.7, EvoX 83.1, GEPA 80.3, seq 76.4, seed 80.0, control 59.6; best finalist AdaEvolve-s2 148/165 m=12 | first multi-seed win beating both seed and control on unseen m; still 14/165 missed by every arm |
| bound-eval-3 tree control | table-fed tree certificates, criterion (8) | closes m=9 {0,4} (3 leaves) and 19/43 of AdaEvolve-s2's misses; nothing at m=11 (no table) | word supply is the bottleneck, not the certificate shape |
| bound-m campaign 3 | tree-contract driver + m-uniform refined-origin seed | prepared, not launched: seed alone closes 23/43 dev misses vs AdaEvolve-s2's 260/303; $15 cap, kill rule set | awaiting human approval; approval hash `ebac59b3...` |

What the engines have found beyond a portfolio this time: AdaEvolve-s2 adds
genuinely new lift variants (second antipodal window, reversed tie-break),
new sweep shapes (bounce_L/R), and a geometric selection rule (convex
hulls, rays, Frank-Wolfe), gaining 19 m=12 families over the seed with no
losses and no m-specific literals (finalize's literal screen found none).
It is still not a closed-form construction: coverage is 148/165 at m=12,
not 165/165, and the worst family (plain reversal, two adjacent zeros) is
missed by every arm at a stable gap of 5.

## 4. Requests and suggestions to the group

1. Is criterion (7)/(8) confirmed by the group at general m, or only proved
   for m=8? Every certificate here is conditional on that extension; a
   confirmation or counterexample at, say, m=11 would settle whether these
   results are theorems or heuristics.
2. The family (m..1){0,m} certifies at m=9..12 by hand generators but fails
   from m=13 because base and slope pull in opposite directions for every
   shortest-word shape we found (E, A, B). Does the group's m=8 proof
   suggest a fourth shape, or a refined-origin route, that keeps both
   under control as m grows?
3. Would a partial (11,3) or (12,2) table be feasible on the group's
   infrastructure? Our (12,2) estimate is 4.4e10 states, too large here;
   it would let us confirm or refute the (m,2) two-extremal-state
   conjecture past m=11.
4. Names of the 290 and 65+36,888 fewer-block exceptions in the m=8
   package are still not listed in `literature/`; unresolved from the
   2026-09-25 report.

## 5. Reproduction

- Campaign 1: `autoresearch/bound-m-260925/` (`TASK.md`, `finalists/`,
  `BEST-GEPA-CONSTRUCTION.md`, `REVERSAL-OBSTACLE.md`).
- Campaign 2: `autoresearch/bound-m-c2-260925/` (`finalists/REPORT.md`,
  `BEST-C2-CONSTRUCTION.md`).
- Tree evaluator and control: `integrations/bound3_*.py`,
  `tests/test_search_bound3.py`, `autoresearch/bound-eval3-260926/`.
- Reversal-family tables and generators:
  `autoresearch/bound-m-260925/REVERSAL-WORDS.md`,
  `checks/reversal_words.py`, `checks/reversal-words-m8-11.json`,
  `checks/m11-r2-reversal-words.json`. Tables built with
  `tools/table_bfs_lowmem.py`; low-memory (10,2) and (11,2) builds are
  gitignored under `datasets/generated/`.
- Campaign 3 (not launched): `autoresearch/bound-m-c3-260926/`
  (`REPORT-prep.md`, `TASK-c3.md`, driver `integrations/bound_c3.py`).
- Claims register: `research/claims.md`, Sessions 15-19.

Spend to date on live model calls: about $20 through the 2026-09-25 report,
plus $3.45 (campaign 1) and about $7 (campaign 2) this cycle; campaign 3 is
prepared but not spent ($15 cap). Nothing was committed or pushed for
campaign 3; the m=12 holdout file for it has never been opened.
