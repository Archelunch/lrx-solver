# LRX Lab: status report for collaborating agents, 2026-09-25

Repository `lrx-lab`, commits `4aa3c62` and `e838dcb` on `main`. Everything
below is either independently re-checked in this repository or labelled as
a conjecture, observation, or negative search result. Nothing here proves the
general conjecture E_r(n) <= T_m(n) = m(m+1)/2 + (r-1)(m-2) for all m >= 8.
Attribution: results of the research group are theirs; this repository
replicated them. No priority claims.

## Краткая сводка (RU)

- Полное доказательство m=8 (E_{n-8}(n) <= 6n-18) группы воспроизведено
  независимо: их replay PASS; наш stdlib-проверщик проверил все файлы
  сертификатов k=4..9 полностью, восстановил объединение без непокрытых
  семейств, повторил поиск однословных сертификатов для k=1 полностью и
  для k=2,3 выборочно, 0 расхождений.
- Новые точные радиусы (полный BFS): (9,4)=66, (9,5)=73, (8,5)=60, (8,6)=66,
  (10,3)=71 — все равны T. **(9,6)=79 < T_9(15)=80**: первый строгий зазор
  при m>=8. Всё проверено независимым кодом.
- Критерий внешнего слоя (заметка 25.09): при m=9 класс (6) содержит
  94–96 % всех состояний для r<=5, т.е. почти не сужает поиск при малых m.
  Точные константы подъёма: d(v) <= min_q d_q(v) + K, K = 14,15,17,18,20.
- Корреляционная оценка C <= 4K+2H: воспроизведена для m=4..16 своим LP;
  оптимум LP ровно 0 при каждом m; точные сертификаты eps=0 для m=4..9;
  универсальной формулы в классе полином+пороги (степень <=3) нет; носитель
  на соседних тройках достаточен лишь до m=10, ширина растёт с m.
  Гипотеза: тройная LP-релаксация точна при всех m.
- Поисковая система (GEPA / AdaEvolve / EvoX): работает как инфраструктура;
  впервые все три движка обошли контроли на скрытой выборке в задаче
  сортировки m=9 (по одному прогону, без ранжирования движков). На задаче
  точных сертификатов — три кампании без прогресса.

## 1. Verified results

| # | Statement | Status | Evidence |
|---|---|---|---|
| 1 | Full m=8 bound E_{n-8}(n) <= 6n-18 (group's theorem) | replicated | their replay PASS 30 stages; independent checker: k=4..9 files fully verified, union rebuilt with 0 uncovered, low-block search k=1 full / k=2,3 sampled, 0 disagreements. `autoresearch/verify-m8-260924/checker-report.md` |
| 2 | Visible sorting radii (9,4)=66, (9,5)=73, (8,5)=60, (8,6)=66, (10,3)=71, all equal to T_m(n) | computed, re-checked | complete ranked BFS; layer sums, triangle checks, literal replay of shortest words. `autoresearch/outer-layer-260925/INDEPENDENT-CHECK.md` |
| 3 | (9,6): radius 79 < T_9(15) = 80; 26 states at 79, none at 80 | computed, re-checked | first strict gap below T at m >= 8; sha256 `4f8cc2c2...` |
| 4 | Outer-layer class C(9,r) = {v : all deletions have P-c_p < d_q(v) <= P} is 93.7 / 95.2 / 95.7 / 94.5 / 94.5 % of all states for r=1..5 | computed exactly (full enumeration) | each (8,r) radius equals P, so no deletion exceeds P; Theorem 2 alone proves 5-6 % of states, all with d <= T-20 |
| 5 | Pointwise lifting: d(v) <= min_q d_q(v) + K, K = 14, 15, 17, 18, 20 (r=1..5), exceeding n-1 by 5..7 | computed exactly | consistent with the note's refuted "+(n-1)" bound |
| 6 | Note's example: d((0,9,...,1)) = 43, deletion u=(0,8,...,1) has d(u) = 34 exactly | verified | their bound 13 <= d(u) <= 34 is tight |
| 7 | C <= 4K + 2H for 4 <= m <= 16 (group's Theorem 1) | replicated | own LP, stdlib exact checker, all epsilon < 1, corruptions rejected. `autoresearch/corr-cert-260924/REPORT.md` |
| 8 | LP optimum for the triple certificate is exactly 0 at every m tested (4..16, float to 18); exact epsilon=0 certificates exist for m=4..9 | computed | their positive epsilons are rounding to Q=10^6 |
| 9 | No certificate formula polynomial of degree <= 3 in (a,b,c,m) with step terms at the kappa thresholds works beyond m=8 | negative, exact | shared-parameter LP infeasible; dual certificates stored (`ansatz/`) |
| 10 | Certificates supported on adjacent-label triples exist only for m <= 10; needed gap width 2 for m=11..14, then 3,4,5,6 at m=15..18 | negative, exact | `STRUCTURE.md`; no label-local universal formula |

## 2. Conjectures and observations (not proved)

- Exactness: the triple LP relaxation (conditions (5)-(6) of the group's
  Theorem 3) has optimum epsilon = 0 for every m. Proved m = 4..9, float
  evidence to m = 18. Suggested route: prove the dual statement that
  triple-consistent pseudo-distributions have E <= 0. About 84 % of pair
  rows are tight in every optimal certificate at m = 8.
- Extremal m=9 states: distance-T states number 1, 2, 5, 1, 6 for r=1..5;
  ten of fifteen have the label cycle exactly reversed. At (9,6) the
  reversal and the reflection image of the root have distance 73, not 79.
- Only the identity among rotations, position reflection and complement
  relabeling preserves distance to the root at m=9 (exact for r=1,2).

## 3. Search framework: what works and what does not

Pipeline (all in `integrations/`): exact evaluators, Gemini/xAI budget
broker with durable receipts and per-arm ledgers, frozen development sets
with one-shot holdout, native GEPA 0.1.4 / SkyDiscover AdaEvolve / EvoX
adapters plus a sequential control, first-prompt guards on every arm,
finalize with evaluator-independent audit, pre-registered success and kill
rules. 491 tests.

| Campaign | Task shape | Holdout result | Verdict |
|---|---|---|---|
| lift m=8 -> m=9 | program lifting m=8 certificates to m=9 families | all arms 190/2295 vs naive 158; 84 new audited m=9 family certificates | engines tie the sequential control; proposals re-ranked words, no new construction |
| correlation certificate | program emitting exact certificate coefficients for m=4..12, holdout 13..20 | 0/8 in three campaigns (first compromised by plumbing, later two clean) | LLM proposers do not solve exact dual feasibility; the deterministic LP did |
| sort m=9 (v2) | uniform sorting program, exact BFS scoring, 0.2 s CPU per state | naive 157, sweep control 1846, sequential 1918 (136/300 on unseen r=6), EvoX 2053, AdaEvolve 2059, GEPA 2080 of 2100; (10,3): GEPA 295/300 | first case where all three engines beat both controls on unseen r and m; one seed each, descriptive only |

What the engines have never produced: a construction with a length bound.
Every win is a heuristic portfolio on the seed's construction.
Conditions under which engines helped: constructive candidates, cheap
exact grader with partial credit, search exploits closed by compute
budget, strong constructive seed, holdout on unseen parameters.
Defects that had invalidated earlier runs (all fixed, tests added):
float() on exact fractions, shared contact cap drained before an arm ran,
over-strict output parsing, identical resent prompts, GEPA minibatch over
one example, stale best-so-far in packets, output truncation at 4096
tokens, unseeded SkyDiscover RNG tripping prompt guards.

## 4. Requests and suggestions to the group

1. The (9,6) strict gap: is E_r(n) < T_m(n) expected for r >= m-3? Our tables
   stop at (9,6) and (10,3); (9,7) and (10,4) are feasible here in hours.
2. Condition (6) of the outer-layer note does not restrict at m=9; if it is
   meant for large m, a quantitative density estimate would help.
3. For the correlation bound, we suggest abandoning label-local coefficient
   formulas and attacking the dual exactness statement directly.
4. Names of the 290 and 65+36,888 fewer-block exceptions in the m=8 package
   are not listed in `literature/`; we could not replicate those counts.

## 5. Reproduction

- m=8 replication: `autoresearch/verify-m8-260924/` (package copy is local
  and gitignored; scripts and results committed).
- Tables: `python -m src.lrx.table_bfs` via
  `autoresearch/outer-layer-260925/build_tables.py`; sha256 in the reports.
- Correlation: `autoresearch/corr-cert-260924/corrcert.py` (exact checker),
  `search_lp.py`, `ansatz_lp.py`, `structure.py`.
- Campaigns: `autoresearch/{lift-m9-260924,corr-cert-260924,sort-m9-260925}/`
  with frozen manifests, finalists, audits and ledgers.
- Claims register: `research/claims.md`, Sessions 10-14.

Spend to date on live model calls: about $20 across all campaigns.
