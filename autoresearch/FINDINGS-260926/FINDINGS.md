# LRX Lab: findings for the research group, 2026-09-26

Repository `lrx-lab`, package committed at `8eaf639` on `main`. FINDINGS.md, VERIFY.md and MANIFEST.md refer to
that one commit. This package collects what the repository has computed and re-checked in Sessions 10 to 23 of
`research/claims.md`. Section (h) summarizes the external review of Session 24, and section (i) gives the proof status after it
(Sessions 25 to 30). Every number below is quoted from a note
in this folder, from `CLAIMS-SESSIONS-10-23.md`, from a re-run recorded in `VERIFY.md`, or from the review.

**Attribution.** Lemma 1 (with refinement), the cost formulas (4)-(6), criteria (7) and (8), the reverse trees, the
full m=8 theorem, the correlation certificate criterion and the outer-layer note are the research group's. This
repository applies the m=8 statements with m as a parameter, replicates the group's results, and extends the
computations. It makes no priority claim. **The general conjecture E_r(n) <= T_m(n) for all m >= 8 remains open.**

## Краткое содержание (RU)

- **Точные результаты (без условий).** Полные BFS-таблицы дают радиус = T_m(n) для всех вычисленных (m,r) с m >= 8,
  кроме (9,6): радиус 79 < T = 80 (26 состояний на 79, ни одного на 80). Для (m,2) при m = 8..11 радиус равен T и
  достигается ровно двумя состояниями. Реверс с двумя внешними нулями (0,m,...,1,0) лежит ровно на T-1 при m = 4..11.
  Число кратчайших слов: 108, 132, 1104, 1296 при m = 8..11. Радиусы, число экстремальных состояний и расстояния T-1
  ещё не подтверждены независимо вне репозитория (таблицы не приложены).
- **Репликации.** Полный пакет группы для m=8 воспроизведён двумя путями (их конвейер и наш независимый чекер).
  Оценка C <= 4K + 2H группы воспроизведена для m = 4..16; оптимум LP равен ровно 0 на всех проверенных m.
- **Первое точное отрицание.** Для m=9 с нулями в зазорах {0,4} сертификата с одним корневым листом не существует
  (точный A*-оракул: B + 3 beta_0 >= 75, тогда как нужно < 74). Дерево из двух листьев эту семью сертифицирует.
  Отрицание ещё не подтверждено независимо вне репозитория (полнота оракула независимо не проверена).
- **Условные результаты** (при лемме 1 и критериях (7)/(8) группы с общим m). Три замкнутые формулы (для word_C формулы длины и наклонов теперь доказаны в WORDC-PROOF.md, доказательство написано моделью и механически проверено при m = 9..40, человеком пока не проверено): word_C
  сертифицирует (m..1){0,m}, word_R1 сертифицирует (m..1){1,m}, word_G сертифицирует (m..1){0,g} во внешней полосе.
  Для нечётного m word_C — одно слово длины T-1 с наклонами (m-2, m-3). Для чётного m word_C — **смесь двух слов**
  с весами 1/2 и 1/2: слово длины T-1 с наклонами (m-1, m-2) и слово длины T+1 с наклонами (m-3, m-4); в среднем
  база T и наклоны (m-2, m-3). Это не одно слово длины T-1 с нужными наклонами: первое слово само по себе нарушает
  ограничение на первый наклон.
  Всё проверено оценщиком и независимым аудитом при m = 9..40 и воспроизведением слов до m = 200 (word_G до 80).
  Все маски k=2 реверса при m=9 сертифицированы. Средняя полоса floor(m/4) < g < m - floor(m/4) остаётся открытой;
  везде связывает база, а не наклоны.
- **Поисковый фреймворк.** Эволюционные конструкции переносятся на невиданные m=11 и m=12 (кампания 2: AdaEvolve
  84.7% против 59.6% у контроля и 80.0% у сильного seed). Лучший финалист AdaEvolve-s2 даёт 148/165 при m=12;
  сам seed даёт 129/165, так что прирост относительно seed — 19 семейств, а 53 — относительно ручного контроля
  (95/165). Это свидетельство полезности поиска, а не превосходства одного оптимизатора; это расширение покрытия,
  а не новое математическое понимание.
- **Внешний review (сессия 24).** Два рецензента группы независимо перепроверили пакет своим stdlib-чекером;
  четыре поправки приняты и внесены (раздел (h)).
- **Цепочки доказательств (сессии 25-30).** Для (m..1){0,m} и (m..1){1,m} при всех m >= 9 и всех длинах блоков
  теперь есть полные письменные цепочки: формулы word_C и word_R1 плюс лемма 1 и (7) при общем m. Доказательства
  написаны моделью, механически проверены на конечных m и человеком пока не проверены. word_G и word_M не доказаны
  (раздел (i)).
- **Отрицательный сертификат.** Для m=9 {0,4} есть переносимый stdlib-чекер без таблиц и без модулей репозитория
  с письменным доказательством полноты: точный минимум B + 3 beta_0 по всем словам равен 75, результат VERIFIED
  (около 16 с). Рецензенты его ещё не перезапускали.
- **Аудит леммы 1.** Пошаговый аудит рукописи группы не нашёл зависимости от m=8 в лемме 1, (4)-(6), лемме 2,
  (7), (8), лемме 3, (11) и лемме 4; все места с m=8 относятся к конечной части. Доказательства при общем m
  написаны, но не проверены человеком.
- **Просьбы к группе.** Подтвердить лемму 1 и (7)/(8) при общем m; подсказать четвёртую форму слова для средней
  полосы; оценить осуществимость таблицы (12,2); назвать исключения пакета m=8 (290 и 65+36,888).
- **Точная колонная генерация (сессия 33).** Точный оракул по всем словам сертифицирует корневой лист при m=10
  {0,5} и m=11 {0,6} (V < T+1) и точно опровергает его при m=11 {0,5} и (сессия 34) m=12 {0,5}, {0,6} (V = T+1);
  прежние оценки "избытка базы" по ограниченным пулам генераторов (сессии 23, 26) не были точными нижними границами.
- **Отрицания при m=12 и дерево для m=11 {0,5} (сессии 34-35).** Оба корня m=12 {0,5} и {0,6} опровергнуты точным
  C-оракулом (negcert/fast/); обе семьи m=12 остаются BOUNDARY с одним открытым листом на границе lhs=1. m=11 {0,5}
  сертифицирован целиком деревом из 4 листьев.

## Conventions

T_m(n) = m(m+1)/2 + (r-1)(m-2) with n = m + r. A family (a,S) fixes the cyclic label order a and the set S of gaps
that hold zero blocks. Its unit base has one zero per block. The notation (m..1){i,j} means the reversal
m, m-1, ..., 1 with one zero block in gap i and one in gap j. For a word, B is its Lemma 1 base and beta_j its slope
on zero block j. Criterion (7) on one root leaf asks for a mixture with weighted base below T(unit)+1 and every
weighted slope at most s = m-2. Criterion (8) is the per-leaf version for box trees with refined origins.

## (a) Exact unconditional results

These are complete finite computations. They use only the executor and BFS, not the group's lemmas.

**Radii.** Complete ranked BFS tables, every layer sum equal to n!/r!:

| m | r | n | states | radius | T_m(n) | radius - T |
|---|---|---|---|---|---|---|
| 8 | 1 | 9 | 362,880 | 36 | 36 | 0 |
| 8 | 2 | 10 | 1,814,400 | 42 | 42 | 0 |
| 8 | 3 | 11 | 6,652,800 | 48 | 48 | 0 |
| 8 | 4 | 12 | 19,958,400 | 54 | 54 | 0 |
| 8 | 5 | 13 | 51,891,840 | 60 | 60 | 0 |
| 8 | 6 | 14 | 121,080,960 | 66 | 66 | 0 |
| 9 | 1 | 10 | 3,628,800 | 45 | 45 | 0 |
| 9 | 2 | 11 | 19,958,400 | 52 | 52 | 0 |
| 9 | 3 | 12 | 79,833,600 | 59 | 59 | 0 |
| 9 | 4 | 13 | 259,459,200 | 66 | 66 | 0 |
| 9 | 5 | 14 | 726,485,760 | 73 | 73 | 0 |
| **9** | **6** | 15 | 1,816,214,400 | **79** | 80 | **-1** |
| 10 | 2 | 12 | 239,500,800 | 63 | 63 | 0 |
| 10 | 3 | 13 | 1,037,836,800 | 71 | 71 | 0 |
| 11 | 2 | 13 | 3,113,510,400 | 75 | 75 | 0 |

The r = 1 rows lie outside the conjecture, which needs r >= 2; they are listed because the tables exist. Below
m = 8 the registry radii are (4,2) 12, (5,2) 19, (6,2) 25, (5,3) 21, (4,4) 17, (7,2) 33, (7,3) 38 and (6,4) 33.
(5,2) and (4,4) exceed T by 1; neither is in the conjectured range.

**Status of the radii, including (9,6) below:** not yet independently confirmed outside this repository (tables not
shipped; oracle completeness not independently checked).

**The (9,6) strict gap.** The radius is 79 against T_9(15) = 80. There are 26 states at 79 and, by explicit scan,
none at 80. An independent checker confirmed the sha256, the layer sums, triangle consistency on 20,000 x 3 samples
and literal replay (`autoresearch/outer-layer-260925/INDEPENDENT-CHECK.md`). This is the first computed case with
m >= 8 where the radius is strictly below T. The reversal (0^6,9,...,1) and the reflection image (2,1,0^6,9,...,3)
are at 73.

**The (m,2) radius and its extremal states.** For m = 8, 9, 10, 11 the radius of (m,2) equals T and is attained by
exactly two states, (0,0,m,...,1) and its rotation (2,1,0,0,m,...,3). The numbers of states at radius-1 are 13, 7,
10 and 8. At m = 11 the distances of the 13 rotations of (0,11,...,1,0) are 74,73,72,71,71,71,72,73,74,74,75,74,75.
**Status of the two-extremal-state counts:** not yet independently confirmed outside this repository (tables not
shipped; oracle completeness not independently checked).

**Unit distances T-1 and shortest-word counts.** The state u_m = (0,m,...,1,0), the unit base of (m..1){0,m}, has
distance exactly T_m(m+2) - 1 for m = 4..11. All shortest words were enumerated on the geodesic DAG:

| m | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|
| d(u_m) = T-1 | 11 | 17 | 24 | 32 | 41 | 51 | 62 | 74 |
| shortest words | 3 | 4 | 14 | 18 | 108 | 132 | 1104 | 1296 |
| X per word | 5 | 8 | 11 | 15 | 19 | 24 | 29 | 35 |

Every shortest word at a given m has floor((m+1)^2/4) - 1 swaps, and every one is same-sign. The minimum Lemma 1
slope over shortest words is (7,6) at m = 8, 9 and (9,8) at m = 10, 11. At m = 11, 192 shortest words have slopes
within s = 9. The middle-band unit bases (m..1){0,g} at m = 9, 10, 11 lie 7 to 11 below T. **Status of the T-1
distances and shortest-word counts:** not yet independently confirmed outside this repository (tables not shipped); a
shipped word certifies an upper bound only.

**m=8 replication (Session 10).** The group's package `lrx_m8_complete_verification` was replicated twice. Their
pipeline on our machine passed 30 stages in 1009.6 s with 0 remaining families. Our stdlib checker, written from
the theorem text, verified every k=4..9 certificate file in full, 0 failures. Per k the family counts were:

| k | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|
| families verified | 262,513 | 337,965 | 228,966 | 74,614 | 10,278 | 40,320 |

It rebuilt the k>=4 union over all 8! x 382 masks with 0 uncovered. It passed all 338 one-block exception mixtures,
37,323 two-block trees and 639,357 three-block trees. Five corrupted records were rejected. Not replicated: the full
k=2 and k=3 low-block enumerations, the fewer-block exception counts, the Lean files and the C++ programs.

**Correlation bound replication (Session 12).** The group's C <= 4K + 2H for 4 <= m <= 16 was reproduced with
independent code. LP certificates were regenerated and re-checked by a stdlib exact checker at every m = 4..16, with
all epsilon < 1 and all corruptions rejected. The identities were validated by full enumeration at m = 4..8. Max E is
0, attained only at the reversal orders. **LP-exactness observation:** the LP optimum is 0 at every m tested, and the
positive epsilons are rounding. Exact epsilon = 0 certificates are verified for m = 4..9. Polynomial-plus-threshold
coefficient ansatzes of degree <= 3 fit m = 4..8 and fail exactly at m = 9. Certificates supported on adjacent-label
triples exist only for m <= 10, and the needed gap width grows to 6 at m = 18.

**Exact negative for m = 9, zeros in gaps {0,4} (Session 23).** No root-leaf certificate exists. Every sorting word
of the unit base has B + 3 beta_0 >= 75, while a certifying mixture (Bbar < 53, betabar_0 <= 7) would need < 74. The
exact optimum of the criterion (8) left side over all words at the root is 2, with dual lambda = (3,0). The witness
word has B = 54 and slopes (7,7):

    RXLLLLXLLXLXRRXRXRXLXLXLXRXRXRXRXLXLXLXLXLLLXLXLXRRXLX

The oracle is an A* search over all reduced sorting words with exact Lemma 1 bookkeeping. Its admissible heuristic
combines three bounds: the table distance; the lift bound B + z beta_j >= d(base with zero j stretched by z), from
tables (9,3) to (9,6); and a pending-segment bound. It expanded 8760 nodes. The tree with leaves u0 = 1 and u0 >= 2
at origin (2,1) certifies the family, with exact leaf optimum 4/5. **Caveat:** exactness rests on the oracle's
completeness over reduced words. The oracle is scratch code, validated against brute force on 25 small cases at
m = 5, 6 only. The negative is stated for Lemma 1's pricing. **Status of the single-leaf negative:** not yet
independently confirmed outside this repository (tables not shipped; oracle completeness not independently checked).
The shipped check without tables re-runs only the witness word, an upper bound on the minimum; the refutation needs
the lower bound over all words.

**Portable checker for this negative (Session 29).** The m=9 {0,4} negative now has a portable checker,
`negcert/negcert_check.py` with the certificate `negcert/negcert-m9-04.json` (`negcert/NEGCERT.md`). It uses the
stdlib only, imports nothing from the repository and reads no tables, so it does check the lower bound over all
words. Its docstring gives a written completeness argument. It shows that dropping LR, RL and XX never raises the
cost, and that a 7-context segment accounting is exact for Lemma 1's B and beta. It then builds an in-memory
abstraction table, verifies its consistency on every node, and runs A*; no Lemma 1 lift bound is used. It finds the
exact minimum of B + 3 beta_0 over all accepted sorting words of (0,9,8,7,6,0,5,4,3,2,1) to be 75, and prints
VERIFIED in about 16 s (`VERIFY.md` section 1). A second optimal word has B = 48 and slopes (9,3). `validate_small.py`
agrees with brute force priced by `lrx_m.Profile` in all 21 cases at m = 3..6. Assumed only: Profile is the group's
Lemma 1 bookkeeping, and words that swap two zeros are excluded, as Profile excludes them. The checker was run and
validated by its author and re-run by the orchestrator; the reviewers have not yet re-run it.

**Outer layer (Session 13).** Against the group's outer-layer note: at m=9, r = 1..5, the class of states whose every
single-label deletion lies in the outer layer holds 93.7 to 95.7 % of all states, by full enumeration. Every class
member is within budget. The exact pointwise lifting constants are K = 14, 15, 17, 18, 20.

## (b) Certified results, conditional on the group's Lemma 1 and criteria (7)/(8) at general m

A CERTIFIED family is a machine-checked bound d(v) <= T_m(n) for every block-length vector of that family,
**provided** Lemma 1 and criteria (7)/(8) hold with m as a parameter. The group has proved them for m = 8 only.
Each row below passed two checks:
- `bound3_evaluator.score_output`: Profile, no zero-zero swap, literal lifts at z = 0, e_j, 2e_j, e_1+e_2 and the box
  points, and the exact LP;
- the independent `bound3_audit.audit_claim`: the stdlib m=8 checker at M = m, with an affine map to m = 8.

Every leaf word was also replayed literally to the root.

### Three closed forms

**word_C(m, a), family (m..1){0,m}.** Evaluator and audit certify it at every m = 9..40, 32 of 32 rows.

- **Odd m:** one word, a = (m-3)/2, of length T - 1 and slopes (m-2, m-3).
- **Even m:** two words with weights 1/2 each, giving base T and slopes (m-2, m-3). They are a = (m-2)/2, of length
  T - 1 and slopes (m-1, m-2), and a = (m-4)/2, of length T + 1 and slopes (m-3, m-4).
- **For even m the certificate is this mixture of two words, not a single word of length T - 1 with the required
  slopes.** The T - 1 word alone has first slope m - 1 > s = m - 2 and fails criterion (7) by itself.
- **Closed forms,** by replay only for m = 9..200: len - T = 2(a - (m-2)/2)^2 - 1 - (m mod 2)/2 for 1 <= a <= m-2.
  The slopes are (2a+1, 2a), except a = 1 with m even, which gives (4,3). The length formula fails only at
  a = 2 floor(m/2).
- The LP over all a = 0..m at m = 9..20 selects exactly this support. At m = 9, 10, 11 the T-1 words are members of
  the enumerated shortest sets.

**word_R1(m), family (m..1){1,m}.** One word of weight 1. Evaluator and audit cover m = 9..40. Replay and criterion
(7) cover m = 9..200 with 0 failures.

| m | length - T | slopes |
|---|---|---|
| 9 | -2 | (4,6) |
| 10 | 0 | (4,6) |
| m >= 11, m = 0 mod 4 | -2 | (m-4, m-2) |
| m >= 11, m = 1 or 3 mod 4 | -2 | (m-5, m-3) |
| m >= 11, m = 2 mod 4 | 0 | (m-6, m-4) |

**word_G(m, g), family (m..1){0,g} in the outer band.** One word of weight 1. It is defined when g <= floor(m/4) or
m - g <= floor(m/4), by the rule table in the source below. When m = 3 mod 4 it also covers
m - g = floor(m/4) + 1.
- 390 certificates at m = 9..40 by evaluator, audit and replay.
- 1210 more at m = 41..80 by replay and criterion (7).
- Length - T lies in [-11, 0], and every slope is at most m - 2.

**The rules were read off data at m = 9..40, not derived.**

### Generator source, verbatim

Physical model of `integrations/lrx_m`: n = m + 2 cells on a cycle, cursor at cell 0, L moves it +1, R moves it -1,
X swaps cells c and c+1. `C` is `integrations.lrx_m`, and `C.base_vector(labels, mask)` builds the unit base.

From `checks/reversal_m13.py`:

```python
def word_C(m, a):
    """Two-core word for (0, m, ..., 1, 0).  Physical model: cells 0..n-1 on a cycle, cursor c (start 0),
    L: c+1, R: c-1, X swaps cells c, c+1.  A core is a cyclic arc of cells, grown by alternately carrying its
    right neighbour across the whole core to its left end ('r', letters X (RX)^len-1) and its left neighbour
    to its right end ('l', letters X (LX)^len-1), the cursor stepping one cell between sweeps.
      core 1 = the zero block (cells n-1, 0), grown by a labels, first 'r' (so ceil(a/2) large labels
               m, m-1, ... cross the zeros leftwards and floor(a/2) small labels 1, 2, ... rightwards);
      core 2 = the complementary arc of the r = m-a remaining labels, grown from one cell by r-1 sweeps,
               first 'r' if r is even else 'l', the start cell chosen so that core 2 ends exactly on that arc;
      then R steps until the cursor is on label 1."""
    n, r = m + 2, m - a
    cell = [0] + list(range(m, 0, -1)) + [0]
    st = {'c': 0, 'w': []}

    def step(ch):
        st['w'].append(ch)
        c = st['c']
        if ch == 'L':
            st['c'] = (c + 1) % n
        elif ch == 'R':
            st['c'] = (c - 1) % n
        else:
            j = (c + 1) % n
            cell[c], cell[j] = cell[j], cell[c]

    def goto(p, d=None):
        f, b = (p - st['c']) % n, (st['c'] - p) % n
        d = d or ('L' if f <= b else 'R')
        for _ in range(f if d == 'L' else b):
            step(d)

    def grow(lo, hi, side, sweeps):
        for _ in range(sweeps):
            ln = (hi - lo) % n + 1
            if side == 'r':
                goto(hi)
                step('X')
                for _ in range(ln - 1):
                    step('R')
                    step('X')
                hi = (hi + 1) % n
            else:
                goto((lo - 1) % n)
                step('X')
                for _ in range(ln - 1):
                    step('L')
                    step('X')
                lo = (lo - 1) % n
            side = 'l' if side == 'r' else 'r'

    q, p = (a + 1) // 2, a // 2                    # labels crossing the zeros leftwards / rightwards
    grow(n - 1, 0, 'r', a)
    if r > 1:
        first = 'r' if r % 2 == 0 else 'l'
        right = (r - 1 + (first == 'r')) // 2      # 'r' sweeps of core 2 extend its right end
        start = n - 2 - p - right                  # core 2 then covers cells 1+q .. n-2-p exactly
        grow(start, start, first, r - 1)
    goto(cell.index(1), 'R')
    return ''.join(st['w'])


def certificate_words(m):
    """Odd m: one word, a = (m-3)/2.  Even m: a = (m-2)/2 and a = (m-4)/2 (the LP weights them 1/2, 1/2)."""
    return [word_C(m, (m - 3) // 2)] if m % 2 else [word_C(m, (m - 2) // 2), word_C(m, (m - 4) // 2)]
```

From `checks/reversal_orbit.py`:

```python
def core_word(state, t, cores, fin):
    """Insertion-core word. Physical model of lrx_m: cells 0..n-1 on a cycle, cursor c = 0, L: c+1, R: c-1,
    X swaps cells c, c+1. Target order: cut t, i.e. labels t+1..m, zeros (tied), labels 1..t.
    A core is a cyclic arc grown from one seed cell; sides alternate starting with `side`. Growing on the right
    inserts cell hi+1 into the sorted core by carrying it leftwards (X (RX)^(s-1)) past the s core elements of
    larger rank; growing on the left inserts cell lo-1 rightwards (X (LX)^(s-1)). Zeros never swap with zeros.
    cores: [(seed, sweeps or None = until the cycle is sorted, side)]. Then a walk to label 1 ('R' or 'L').
    Returns the word, or None if the cycle is not cyclically sorted after the cores. word_C(m, a) grows its cores
    the same way but always carries across the whole core; it is not claimed to be a special case of this."""
    n = len(state)
    m = sum(1 for x in state if x)
    order = list(range(t + 1, m + 1)) + [0] + list(range(1, t + 1))
    rk = {x: i for i, x in enumerate(order)}
    cell, w, c = list(state), [], 0

    def goto(p):
        nonlocal c
        f, b = (p - c) % n, (c - p) % n
        w.append('L' * f if f <= b else 'R' * b)
        c = p

    def srt():
        i = cell.index(1)
        return [cell[(i + x) % n] for x in range(m)] == list(range(1, m + 1))

    for seed, sweeps, side in cores:
        lo = hi = seed
        ln, cnt = 1, 0
        while ln < n and (not srt() if sweeps is None else cnt < sweeps):
            if side == 'r':
                j = (hi + 1) % n
                s = 0
                while s < ln and rk[cell[(hi - s) % n]] > rk[cell[j]]:
                    s += 1
                if s:
                    goto(hi)
                    w.append('X' + 'RX' * (s - 1))
                    v = cell[j]
                    for i in range(s):
                        cell[(j - i) % n] = cell[(j - i - 1) % n]
                    cell[(j - s) % n] = v
                    c = (j - s) % n
                hi = j
            else:
                j = (lo - 1) % n
                s = 0
                while s < ln and rk[cell[(lo + s) % n]] < rk[cell[j]]:
                    s += 1
                if s:
                    goto(j)
                    w.append('X' + 'LX' * (s - 1))
                    v = cell[j]
                    for i in range(s):
                        cell[(j + i) % n] = cell[(j + i + 1) % n]
                    cell[(j + s) % n] = v
                    c = (j + s - 1) % n
                lo = j
            ln += 1
            cnt += 1
            side = 'l' if side == 'r' else 'r'
    if not srt():
        return None
    p = cell.index(1)
    w.append('L' * ((p - c) % n) if fin == 'L' else 'R' * ((c - p) % n))
    return ''.join(w)


def word_R1(m):
    """Family (m..1){1,m}: state (m, 0, m-1, ..., 1, 0). One word: cut (m-3)//4; core 1 from cell 0, m//2 sweeps,
    first 'l'; core 2 from cell m//2+1 until sorted, first 'r' iff m = 1 mod 4; final R walk."""
    st = C.base_vector(list(range(m, 0, -1)), 2 | 1 << m)
    return core_word(st, (m - 3) // 4, [(0, m // 2, 'l'), (m // 2 + 1, None, 'r' if m % 4 == 1 else 'l')], 'R')
```

From `checks/reversal_k2.py`. word_G is `core_word` with rule parameters. The file's `RULES_TEXT`, a string copy of
`RULES`, is omitted here.

```python
RULES = {
    0: [('g', lambda g, j: g == 1, (-1, 1, -1, 'r', -1, 'r')),
        ('g', lambda g, j: 2 <= g <= j - 1, (0, 0, -1, 'r', -1, 'r')),
        ('g', lambda g, j: g == j and j >= 4, (-2, 2, -2, 'l', 0, 'l')),
        ('r', lambda r, j: 1 <= r <= j - 2, (-1, 0, -1, 'r', -1, 'r')),
        ('r', lambda r, j: r == j - 1, (0, 0, -1, 'l', -1, 'r')),
        ('r', lambda r, j: r == j, (1, -1, -1, 'l', -1, 'r'))],
    1: [('g', lambda g, j: g == 1, (0, 1, 0, 'l', -1, 'r')),
        ('g', lambda g, j: 2 <= g <= j - 1, (1, 0, 0, 'l', -1, 'r')),
        ('g', lambda g, j: g == j, (-1, 1, -1, 'r', 0, 'l')),
        ('r', lambda r, j: 0 <= r <= j - 1, (0, 0, 0, 'l', -1, 'r')),
        ('r', lambda r, j: r == j, (1, -1, 0, 'r', -1, 'r'))],
    2: [('g', lambda g, j: g == 1 or g == j, (0, 1, -1, 'l', 0, 'l')),
        ('g', lambda g, j: 2 <= g <= j - 1, (1, 0, -1, 'r', 0, 'l')),
        ('r', lambda r, j: 1 <= r <= j - 1, (0, 0, -1, 'r', 0, 'l')),
        ('r', lambda r, j: r == j, (1, -1, -1, 'r', 0, 'l'))],
    3: [('g', lambda g, j: g == 1, (0, 1, 0, 'l', 0, 'l')),
        ('g', lambda g, j: 2 <= g <= j - 1, (1, 0, 0, 'l', 0, 'l')),
        ('g', lambda g, j: g == j, (-2, 1, 0, 'r', 0, 'r')),
        ('r', lambda r, j: 0 <= r <= j, (0, 0, 0, 'l', 0, 'l')),
        ('r', lambda r, j: r == j + 1 and j >= 3, (1, -2, -1, 'r', -1, 'r'))],
}


def params_G(m, g):
    j, r = m // 4, m - g
    for var, cond, p in RULES[m % 4]:
        if cond(g if var == 'g' else r, j):
            return p
    return None


def word_G(m, g):
    """Single two-core word for (m..1){0,g}, i.e. state (0, m, ..., m-g+1, 0, m-g, ..., 1); None outside the rules."""
    p = params_G(m, g)
    if p is None:
        return None
    dt, s1, dk, d1, ds2, d2 = p
    n = m + 2
    t, k1 = (m - 3) // 4 + dt, m // 2 + dk
    nr = (k1 + 1) // 2 if d1 == 'r' else k1 // 2  # right-growth steps of core 1
    mid = s1 + nr + 1 + (n - k1 - 1) // 2          # middle of the complement arc
    st = C.base_vector(list(range(m, 0, -1)), 1 | 1 << g)
    return core_word(st, t, [(s1 % n, k1, d1), ((mid + ds2) % n, None, d2)], 'R')
```

From `checks/reversal_midband.py`. word_S is parametric but **not a closed form**. Its side schedule is chosen per
(m, g) from the family rr(lr)* / rrr(lr)* with an rl tail. The winning parameters are stored in
`reversal-midband-words.json` under `word_S_params`.

```python
def sched_word(state, t, cores, fin, pre=''):
    """Insertion cores with explicit side schedules (core_word of reversal_orbit.py grows sides alternately; here
    each core has a string of sides). Physical model of lrx_m: cells 0..n-1, cursor c = 0, L: c+1, R: c-1,
    X swaps cells c, c+1. Target order from cut t: labels t+1..m, zeros (tied), labels 1..t. `pre` is executed
    literally first. A right step inserts cell hi+1 by carrying it left (X (RX)^(s-1)) past the s core elements
    of larger rank; a left step inserts cell lo-1 by carrying it right (X (LX)^(s-1)). Then a walk to label 1."""
    n = len(state)
    m = sum(1 for x in state if x)
    order = list(range(t + 1, m + 1)) + [0] + list(range(1, t + 1))
    rk = {x: i for i, x in enumerate(order)}
    cell, w, c = list(state), [], 0
    for ch in pre:
        if ch == 'L':
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
        else:
            j = (c + 1) % n
            cell[c], cell[j] = cell[j], cell[c]
        w.append(ch)

    def goto(p):
        nonlocal c
        f, b = (p - c) % n, (c - p) % n
        w.append('L' * f if f <= b else 'R' * b)
        c = p

    for seed, sides in cores:
        lo = hi = seed
        ln = 1
        for side in sides:
            if side == 'r':
                j = (hi + 1) % n
                s = 0
                while s < ln and rk[cell[(hi - s) % n]] > rk[cell[j]]:
                    s += 1
                if s:
                    goto(hi)
                    w.append('X' + 'RX' * (s - 1))
                    v = cell[j]
                    for i in range(s):
                        cell[(j - i) % n] = cell[(j - i - 1) % n]
                    cell[(j - s) % n] = v
                    c = (j - s) % n
                hi = j
            else:
                j = (lo - 1) % n
                s = 0
                while s < ln and rk[cell[(lo + s) % n]] < rk[cell[j]]:
                    s += 1
                if s:
                    goto(j)
                    w.append('X' + 'LX' * (s - 1))
                    v = cell[j]
                    for i in range(s):
                        cell[(j + i) % n] = cell[(j + i + 1) % n]
                    cell[(j + s) % n] = v
                    c = (j + s - 1) % n
                lo = j
            ln += 1
    i = cell.index(1)
    if [cell[(i + x) % n] for x in range(m)] != list(range(1, m + 1)):
        return None
    w.append('L' * ((i - c) % n) if fin == 'L' else 'R' * ((c - i) % n))
    return ''.join(w)


def word_S(m, g, b, ds, sc1, fin='L'):
    """(m..1){0,g}, unit base. Split: the b smallest labels form block 2 (with the gap-0 zero), labels m..b+1 form
    block 1 (with the gap-g zero, which a = m-g-b labels cross). Prefix RX (label 1 crosses the gap-0 zero), block-1
    core seeded at cell 1+ds with side schedule sc1 (length g+a), block-2 core seeded at cell n-b growing right b
    times, cut t = b, final walk fin."""
    st = C.base_vector(list(range(m, 0, -1)), 1 | 1 << g)
    a = m - g - b
    if a < 0 or len(sc1) != g + a:
        return None
    return sched_word(st, b, [(1 + ds, sc1), (m + 2 - b, 'r' * b)], fin, 'RX')
```

### Certified coverage of the k = 2 reversal orbit

Combined from Sessions 21, 22 and 23. Counts are over all C(m+1,2) two-zero masks of the reversal m..1.

| m | masks | certified | not certified | how the count is built |
|---|---|---|---|---|
| 9 | 45 | **45** | none | 42 (Session 21), plus {5,9} by a 5-leaf tree (Session 22), plus {0,4} by a 2-leaf tree and {0,5} at the root (Session 23) |
| 10 | 55 | **54** | {0,5} | 53 (Session 21), plus {0,6} by word_S (Session 23) |
| 11 | 66 | **61** | {0,5}, {0,6}, {5,11}, {6,11}, {7,11} | 59 from the root survey (Session 22), plus {0,4} by a 2-leaf tree (Session 21), plus {0,7} by word_S (Session 23) |
| 12 | 78 | **74** | {0,5}, {0,6}, {6,12}, {7,12} | 72 from the root survey (Session 22), plus {0,7} and {0,8} by word_S (Session 23) |
| 13 | 25 outer of 91 | **19** of 25 | {0,5}, {0,6}, {0,7}, {6,13}, {7,13}, {8,13} | 18 at the root (Session 22), plus {0,8} by word_S; the 66 interior masks were not run |
| 14..16 | not surveyed | {0,m}, {1,m}, {0,4} and the word_G band | the whole middle band | word_S root gaps start at 1/10 (m = 14, {0,9}) |
| 17..40 | not surveyed | {0,m}, {1,m} and the word_G band | middle band not attempted | closed forms only |

**Note on m = 11 {0,4}.** Session 23 and `REVERSAL-MIDBAND.md` list it as not certified, meaning not by word_S. The
two-leaf tree of `REVERSAL-ORBIT.md` certifies it. Its leaf u0 = 1 uses (1, 66, (12,0)), and its leaf u0 >= 2 at
origin (2,1) has lhs 2/5. Today's re-run of `reversal_orbit.py` reproduces that row.

At m = 9..12, every mask with both zeros in gaps 1..m-1 is certified at the root. Every miss has one zero in gap 0 or
gap m and the other near m/2.

**The 14 m = 12 families every campaign-2 arm missed** (Session 21, `REVERSAL-ORBIT.md` section 1c):

| family (mask) | k | status |
|---|---|---|
| 12..1 {0,12} (4097) | 2 | CERTIFIED, word_C pair |
| 12..1 {1,12} (4098) | 2 | CERTIFIED, word_R1(12), (1, 86, (8,10)) |
| near_rev 11..3.1.2.12 {4,11} (2064) | 2 | CERTIFIED, root |
| near_rev 1.12.10.11.9..2 {1,7} (130) | 2 | not found; root base excess 74/15 |
| 4.3.2.1.12..5 {0,4,12} (4113) | 3 | CERTIFIED, root |
| 2.1.12..3 {2,5,10} (1060) | 3 | CERTIFIED, two-leaf tree |
| near_rev 1.12..7.5.6.4.3.2 {0,6,10} (1089) | 3 | CERTIFIED, root |
| 3.2.1.12..4 {1,4,8,12} (4370) | 4 | CERTIFIED, root |
| 10..1.12.11 {2,7,10,12} (5252) | 4 | CERTIFIED, root |
| near_rev 12..4.2.3.1 {0,2,5,7} (165) | 4 | CERTIFIED, root |
| 12..1 mask 7300 | 5 | not found; root base excess 37838/6993, about 5.41 |
| refl 12..1 {4,5,6,7,8,12} (4592) | 6 | CERTIFIED, root |
| refl 2.1.12..3 mask 6309 | 6 | not completed (CPU) |
| 2.1.12..3 mask 3534 | 8 | not completed (CPU) |

Ten of the 14 are certified. Among the m = 11 misses, mask 145 is certified. Masks 1056 (excess 2) and 2456 (excess
9/2) were not found, and 3685 was not completed.

### What remains open, and what binds

- **The middle band** floor(m/4) < g < m - floor(m/4) has no closed form. In every miss the slopes are feasible at
  the root (t = 0), and **the base binds**.
- **Why the pools fail.** Cheap two-core words put nearly all the slope on the gap-0 zero. Carrying a zero costs 3
  per crossing, while carrying a label past a zero costs 2. Shortest band words have beta_0 = 9..16 and beta_1 about 0.
- **Where word_S stops.** Certifying band words split the crossings between the two zeros, and word_S does this. But
  it walks the gap-0 zero at 3 per crossing, so beta_0 = 3b - 2, and it stops working after m = 13.
- **m = 10 {0,5}.** The leaves u0 in [1,2] and u0 >= 5 pass. The leaves u0 = 3 and 4 fail with every word tried, and
  no (10,4) table exists for refined origins.
- **Exact optima at m = 10.** The exact root and (2,1) optima are unknown, because the pricing hit the 1.5M-node cap.
- **Higher k.** The misses 130, 7300, 1056 and 2456 also bind on the base.

**Correction (Session 33, `MIDBAND-LOWERBOUND.md` section 4).** The "root base excess" figures reported above from
Session 23 (e.g. 74/15 at mask 130, 37838/6993 at mask 7300, the excess-2 and excess-9/2 misses at m = 11) and the
"minimum base excess 16, 16, 30, 46, 64, 84 at g = m/2, m = 14..24" of `REVERSAL-CARRY.md` (Session 26) are seed-LP
values over the stored generator pools (word_S, word_K, word_M, word_C, shortest words), **not exact lower bounds**
on the root LP. The exact exhaustive oracle of `MIDBAND-LOWERBOUND.md` finds that the true root excess V - T is
often much smaller, or zero: at m = 10 {0,5} the pool gave 9/5 but V - T is exactly 1/2 (certifiable); at m = 11
{0,6} the pool gave 4/3 but V - T is exactly -1 (certifiable); the optimal words carry both zeros near slope s, a
shape none of the stored generators produces. Read every restricted-pool "excess" figure in this file and in
`REVERSAL-CARRY.md` as an upper bound on the true root LP excess only, not as evidence that the base binds.

## (c) word_C's closed forms: proof in WORDC-PROOF.md, with the earlier sketch as an outline

A full proof of the closed forms now exists in `WORDC-PROOF.md`. Its theorem covers every m >= 3 and 1 <= a <= m-2:
word_C(m, a) sorts the unit base, its length is T + 2(a - (m-2)/2)^2 - 1 - (m mod 2)/2, its base equals its length,
and its slopes are (2a+1, 2a), except (4,3) for a = 1 with m even. The corollary for m >= 9 gives the certificate
words of section (b): one word for odd m, and the two-word mixture with weights 1/2 for even m. Every intermediate
claim was mechanically checked by `checks/wordc_proof_check.py` against the literal execution of word_C at
m = 9..40 (720 pairs (m, a), 0 mismatches; `VERIFY.md` section 1). The proof was written by a model and has not yet
been reviewed by a human mathematician. It does not cover Lemma 1 and criterion (7) themselves, which remain the
group's statements applied with m as a parameter. The sketch below, copied from `REVERSAL-ORBIT.md` section 4 with
light edits, is kept as an outline of that proof.

**Assumptions.** The executor is `lrx_m`, as above. word_C is exactly the code in section (b), including the tie
rule of `goto`, which goes L when both directions are equally long. Lemma 1 is taken as `lrx_m.Profile` implements
the group's statement:
- Split the word at its X letters into segments. The base is B = #X + sum over segments of |L - R|.
- The slope of zero j is beta_j = 2 A_j + sum over segments of |cz_j|. Here A_j counts the X that swap a label with
  zero j.
- cz_j is the segment's net signed count of cursor passes over zero j. An L leaving j's cell counts +1, and an R
  arriving on it counts -1.
- An X with zero j at the cursor adds +1 to the current segment. An X with zero j at c+1 starts the next segment at -1.

The sketch counts letters and those terms. It does not re-derive Lemma 1.

**Setup.** Cells 0 and n-1 hold zero 0 (gap 0) and zero 1 (gap m), and cell j holds label m+1-j. Let q = ceil(a/2),
p = floor(a/2) and r = m - a. Assume 1 <= a <= m-2, so r >= 2.

**(i) Length.**

1. A sweep over a core of length l is X (RX)^(l-1) or X (LX)^(l-1). That is 2l - 1 letters and l swaps.
2. An 'r' sweep ends on the core's left end lo, and an 'l' sweep on hi - 1. The next sweep, of the other side, starts
   one cell away. So every sweep after the first in a core costs a 1-letter walk.
3. Core 1 starts as the zero block (length 2) and makes a sweeps; the first needs no walk. Sweep i has core length
   i+1, so core 1 costs sum_{i=1..a} (2i+1) + (a-1) = a^2 + 3a - 1.
4. Core 2 makes r-1 sweeps of lengths 1..r-1, costing (r-1)^2 + (r-2) plus the entry walk W0.
5. After core 1 the cursor is at n-1-p (a odd) or at q-1 (a even). Core 2 ends exactly on cells q+1..n-2-p. The
   shorter cyclic entry walk is W0 = r/2 + 1 (r even), (r+3)/2 (a and r odd), or (r+1)/2 (a even, r odd). It is
   strictly shorter than n/2 unless a = 1 and m is even, where the two directions tie.
6. The last sweep of core 2 is always 'r', so the cursor ends on q+1. Core 1 has turned (p..1, 0, 0, m..m-q+1) into
   (m-q+1..m, 0, 0, 1..p). So label 1 is on cell q - p + 1, and the final R walk has Wf = p letters.
7. Total: len = (a^2 + 3a - 1) + ((r-1)^2 + r - 2) + W0 + floor(a/2). Substituting the three cases of W0 and
   T = m(m+1)/2 + m - 2 gives len - T = 2(a - (m-2)/2)^2 - 1 - (m mod 2)/2. The case a = m-1 has r = 1 and no
   core 2. That is why the formula fails at a = 2 floor(m/2) for odd m.
8. Every segment is a walk in one direction, so B = len.

**(ii) Slopes (2a+1, 2a).**

1. Each of the a carried labels crosses the whole of core 1, which contains the zero block, so A_0 = A_1 = a. Core 2
   and the walks never swap a zero. So the 2A_j term is 2a.
2. Inside an 'r' sweep, when the carried label reaches zero j, the preceding R arrived on j's cell (-1). The X then
   has j at the cursor (+1), so the net is 0.
3. Inside an 'l' sweep, the X with j at c+1 opens the next segment at -1. The following L leaves j's cell (+1), so the
   net is 0.
4. A term survives only where a zero is the first element touched, with no preceding R in the segment. That happens
   once, at the first X of the word, where the cursor already stands on zero 0. So |cz_0| = 1.
5. At the end of an 'l' sweep whose last swap is with a zero, the -1 is cancelled by the one-step L walk out of that
   zero's cell.
6. W0, core 2 and Wf stay inside the labels between the cores and pass no zero.
7. Hence beta_0 = 2a + 1 and beta_1 = 2a.
8. For a = 1 with m even, W0 = n/2 ties, and `goto` goes L across both zeros. That adds 1 to each term and gives
   (4,3). The certificate uses a >= 3.

**Still to check before this is a proof:**
- an induction that the core cells hold the reversed arc and the cursor ends where stated, including the cyclic wrap
  of core 1 across cell 0;
- the parity bookkeeping of `start` and `right` in core 2;
- that W0 and Wf pass no zero for every m and a;
- the small cases a = 1, 2, written out;
- Lemma 1 and criterion (7) themselves.

The numeric check confirms both closed forms at m = 5..60.

## (d) Search-framework results: coverage amplification, not insight

The engines, GEPA, AdaEvolve and EvoX with a sequential control, evolved a program `certify(family)`. It emits words
for a family's unit base. The evaluator prices them with Lemma 1 and solves an exact LP for criterion (7). The model
was gemini-3.8-flash throughout.

| campaign | development | holdout (evaluated once) | result |
|---|---|---|---|
| 1 (Session 15) | 303 families, m = 9, 10 | 468 families, including all 165 at m = 11 | At m=11: EvoX 129/165 and GEPA 125/165, worst gap 4; sweep+LP control 98/165, gap 7. AdaEvolve 100 and sequential 109, with invalid outputs off-distribution. 168 calls, $3.45 |
| 2 (Session 16) | m = 9, 10; validation on the campaign-1 m=11 holdout | 165 fresh m=12 and 60 fresh m=11 families | Mean holdout over 3 seeds: AdaEvolve 84.7 % (SD 4.4), EvoX 83.1 % (0.8), GEPA 80.3 % (0.5), sequential 76.4 % (6.9); seed 80.0 %; control 59.6 %. Best finalist AdaEvolve-s2: 148/165 at m=12, 54/60 at m=11. 360 calls, about $7 |

**Strong-seed baseline.** The campaign-2 seed is the campaign-1 EvoX finalist. By itself it scores 129/165 at m = 12
(80.0 % of the holdout). AdaEvolve-s2's 148/165 is therefore a gain of 19 families over the seed. The comparison
148 vs 95 is against the hand-written sweep+LP control, a gain of 53. With m = 11 included, the reviewers' reconciliation
gives 202/225 for AdaEvolve-s2, 180/225 for the seed and 134/225 for the control. As the external reviewers put it,
this is evidence that the search is useful, not that one optimizer is superior: three seeds per method, selection of
the best run and different timeouts do not support a ranking of the methods.

The independent audit found 0 disagreements in both campaigns. All campaign-2 finalists are deterministic under
PYTHONHASHSEED=0 and contain no m-specific literals. GEPA returned the seed unchanged in two of three seeds.

**The construction the engines found** (`BEST-C2-CONSTRUCTION.md`). AdaEvolve-s2 keeps the seed's frame: a lift, a
sweep on the universal cover, and the exact Lemma 1 price. It adds five things:
- a second antipodal window for even n;
- a reversed tie-break in the sum-0 normalization;
- bounce sweeps;
- a cursor pre-rotated to the target cut;
- a geometric word selection by lower convex hulls, rays and softmax Frank-Wolfe.

It certifies 19 m=12 families the seed misses and loses none. How that gain splits between the pool and the
selection was not measured.

**Plain reading.** The engines turned a hand-written portfolio into a larger one that transfers to unseen m. They
did not produce a closed form, a lemma, or an explanation. Every arm missed the same 14 m=12 families, all in or next
to the reversal orbit, and the plain reversal {0,12} stayed at gap 5 in every arm. Hand constructions (section b)
later closed ten of them, not the engines. On the correlation task, three campaigns produced no certificate beyond
the worked examples m = 4, 5; the deterministic LP did the mathematics.

**Spend.** About $20 on model calls through the 2026-09-25 report, plus $3.45 and about $7 for the two bound
campaigns. A third campaign, using the tree contract with a $15 cap, is prepared and not launched.

## (e) Conjectures (each unproved)

1. **Conjecture (unit distance).** d((0,m,...,1,0)) = T_m(m+2) - 1 for all m >= 4. Exact for m = 4..11. The upper
   bound holds to m = 200 by replay of word_E.
2. **Conjecture ((m,2) radius).** The (m,2) radius is T_m for all m >= 8, attained by exactly two states. Exact for
   m = 8..11.
3. **Conjecture (swap count).** Every shortest word for u_m has floor((m+1)^2/4) - 1 swaps. Exact for m = 4..11.
4. **word_C (no longer a conjecture about the formulas).** The length and slope formulas are proved in
   WORDC-PROOF.md for all m >= 3 and 1 <= a <= m-2 (model-written, mechanically checked at m = 9..40, not yet
   reviewed by a human mathematician). That word_C's mixture certifies (m..1){0,m} for all m >= 9 therefore
   depends only on Lemma 1 and criterion (7) at general m.
5. **word_R1 (no longer a conjecture about the formulas).** Proved in WORDR1-PROOF.md for all m >= 9
   (model-written, mechanically checked at m = 9..200, not yet reviewed by a human mathematician); the
   certificate of (m..1){1,m} for all m >= 9 depends only on Lemma 1 and criterion (7) at general m.
6. **Conjecture (word_G).** word_G certifies (m..1){0,g} for all m >= 9, wherever its rule is defined.
7. **Conjecture (interior masks).** Every two-zero mask of the reversal with both zeros in gaps 1..m-1 has a root
   certificate among two-core words. Checked at m = 9..12.
8. **Conjecture ({0,4}).** For m >= 14, one word with slopes (12,0) or (14,2) certifies (m..1){0,4}. Seen at m = 14
   and 16.
9. **Conjecture (middle band).** With unit origins, the band min(g, m-g) >= about m/2 - 2 has no root certificate in
   any insertion-core pool. Refined origins or a new word shape are needed.
10. **Conjecture A' (identity rotations).** For m >= 9 the lift-and-sweep pool certifies every identity rotation
    with any mask. 34 of 34 across both campaigns.
11. **Conjecture E (easy class).** The same holds for the low-inversion class. AdaEvolve-s2 certifies 45 of 45 at
    m = 9..12.
12. **Conjecture (triple LP exact).** For every m >= 4 the correlation LP (5)-(6) has optimum epsilon = 0. Proved
    exactly for m = 4..9; float evidence to m = 18.
13. **Conjecture (even centre certifiable from m = 10), REFUTED (Session 34).** `MIDBAND-LOWERBOUND.md` conjecture 2
    claimed every root leaf in the band is certifiable for even m >= 10. `MIDBAND-M12-14.md` finds m = 12 {0,6}
    has exact root LP value V = T+1 = 89: NO ROOT-LEAF CERTIFICATE, by the C oracle (`negcert-m12-06.json`).
14. **Conjecture (no base barrier away from the odd centre), REFUTED (Session 34).** `MIDBAND-LOWERBOUND.md`
    conjecture 3 claimed V - T <= 1/2 for m >= 10, g != (m-1)/2. Both m = 12 {0,5} and {0,6} have V - T = 1
    exactly, by the C oracle (`negcert-m12-05.json`, `negcert-m12-06.json`).

## (f) Requests to the group

1. **Review of the written general-m proofs.** Every certificate in section (b) was stated as conditional on Lemma 1
   and criteria (7)/(8) at general m. The step-by-step audit of the group's manuscript (`LEMMA1-GENERAL-M-260926.md`,
   `LEMMA34-GENERAL-M-260926.md`) found no dependence on m = 8 in Lemma 1, (4)-(6), Lemma 2, (7), (8), Lemma 3, (11)
   or Lemma 4; every real use of m = 8 is in the finite part. The general-m proofs are written there, but by a model.
   We ask the group to review them, and the word proofs of section (i), starting with the steps the auditors flagged:
   - `LEMMA1-GENERAL-M-260926.md` section 4.1, the macro-by-macro induction for Lemma 1;
   - `LEMMA34-GENERAL-M-260926.md` section 4.3 items 2-3: the cut is not crossed after lifting, and the insertion
     form of stretched ranks;
   - `WORDC-PROOF.md` Lemma E, the segment enumeration and the cz accounting;
   - `WORDR1-PROOF.md` Lemma P: core_word never makes a partial carry for word_R1.
2. **A fourth word shape for the middle band.** The E, A, B and two-core shapes fail there because they load the
   gap-0 zero. The split-merge shape word_S works to m = 13, but it walks the gap-0 zero at 3 per crossing. A block-2
   core that carries the small labels across that zero at 2 per crossing, as word_C does, has not been written. Does
   the group's depth-7 m=8 tree for 8..1 {0,4} suggest a shape, or a refined-origin route, that scales?
3. **(12,2) table feasibility.** The estimate is 4.4e10 states, too large here. A complete or partial table would
   test conjectures 1 and 2 beyond m = 11.
4. **The m=8 exception names.** The 290 two-zero and 65 + 36,888 three-zero fewer-block exceptions appear only as
   counts. A list would close the last unreplicated part of the m=8 package.

## (g) Verifying everything offline

`VERIFY.md` has the full recipe. The package is self-contained for its nine re-checks, including the mechanical
checks of the word_C and word_R1 proofs and the portable negative certificate. From the package root, `sh run_checks.sh` (or `python run_checks.py`) runs them with the
byte-identical copies in `vendor/` only, without the repository, tables or numpy, and prints the expected last lines. Inside the repository, run these from the
repository root with Python 3.12:

```
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q src tests
python -m src.lrx.cli smoke

PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_k2.py
PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_midband.py            # no tables
PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_midband.py --tables   # needs (9,2)..(9,6)
```

`reversal_m13.py` and `reversal_orbit.py` rebuild their JSON and refuse to overwrite it. Run them on a copy of
`checks/` without the two JSON files, then compare the new JSON with the stored one. `VERIFY.md` gives the commands.
Expected last lines:

| script | expected last line |
|---|---|
| reversal_m13.py | `wrote .../reversal-m13-words.json 2.0 s`, preceded by `closed forms m=9..200 failures: []` |
| reversal_orbit.py | `wrote .../reversal-orbit-words.json 2.3 s`, preceded by `R1 failures m=9..200: []` |
| reversal_k2.py | `re-checked 390 word_G rows and 150 stored rows in 2.3 s; problems: none` |
| reversal_midband.py | `problems: none` |

Tables are gitignored under `datasets/generated/`. Rebuild the large ones with the low-memory builder:

```
python -c "from tools.table_bfs_lowmem import build_table_lowmem as b; b(10, 2, 'datasets/generated/m10-r2-260926', workers=4)"
python -c "from tools.table_bfs_lowmem import build_table_lowmem as b; b(11, 2, 'datasets/generated/m11-260925', workers=4)"
```

With 4 workers, the (10,2) build took 409 s and the (11,2) build 3.2 h. The sha256 values from their metadata are:

    (10,2) 3f9ad500d390e7e264a26f9bcbdba13c2bd90ca500352e8d4cd4d9ae6ea4563b
    (11,2) 1c3f4915f4bea4e856d2eaed66f1c58caa4c7f43d896ae25e63475bc83192325

## (h) External review (Session 24)

Two reviewers of the research group (AutoMathLab, review request 2900) checked the previous version of this package
(`lrx-findings-260926.zip`, sha256 `04be4d4a8302765b5136c0cbd269ec0e0c91cce6994bee0051873bd008735491`) and the
repository at `defc5c6`. They used their own stdlib executor and checker, no repository modules, no BFS tables and no
API calls. Their report is theirs; the summary below is this repository's reading of it (`research/claims.md`,
Session 24).

**Confirmed by them:**
- 393 of 393 words replay literally to (1..m,0,0): the 390 word_G unit-block words at m = 9..40 and the three m = 11
  words of lengths 74, 75 and 75;
- 665 stored rows, 852 word executions and 675 exact leaf inequalities, re-derived from segments with their own
  Lemma 1 bookkeeping (counts of records with repeats, not of unique families);
- coverage of unique k = 2 reversal masks, 45/45 at m = 9 and 74/78 at m = 12;
- the campaign-2 finalist table, 148/165 against control 95/165, as a reconciliation of the report, not a re-run.

**Not confirmed by them:** shortestness of words; the exact radii of (10,2), (11,2) and (9,6) and the
two-extremal-state count (tables not shipped); the single-leaf negative for m = 9 {0,4}, which needs a portable
exhaustive oracle with proven completeness or a compact lower-bound certificate; the campaigns themselves.

**Accepted corrections, applied in this version:**
1. For even m, word_C is a mixture of two words, T - 1 with slopes (m-1, m-2) and T + 1 with slopes (m-3, m-4),
   weights 1/2 each, not one word of length T - 1 with the required slopes. Summary and section (b) now say so.
2. The engine gain is stated against the strong seed (129/165 at m = 12): AdaEvolve-s2 adds 19 families, and 53 is
   the gain over the hand control. Section (d) now says so.
3. One commit is pinned: FINDINGS.md had `defc5c6` and VERIFY.md `6e56ddf`. All three documents now name
   `8eaf639`.
4. The package was not self-contained: the check scripts imported `integrations/*.py` from the repository, and
   `mb.py` hard-coded an absolute path. `vendor/` now holds the import closure, `run_checks.sh` and `run_checks.py`
   run the re-checks from the package alone, and the table root of `mb.py` is a parameter.

The reviewers also stressed, and this package keeps saying, that every certificate for all block lengths and general
m stays conditional on Lemma 1 and criteria (7)/(8), and that finite checks of the formulas do not replace a proof.
Their suggested next steps are adopted: close the inductive invariants of word_C for both parities, bind the general-m
Lemma 1 and (7)/(8) separately, keep "optimizer proposes, data-only checker verifies", and measure engine gains
against the strong seed at equal budget with several repetitions and a new frozen holdout.

## (i) Proof status after the review

Sessions 25 to 30 answer the reviewers' request to close the inductive invariants of word_C and to bind Lemma 1
and (7)/(8) at general m separately. All proofs below were written by models and checked mechanically on finite
ranges. **None has been reviewed by a human mathematician.** Finite checks validate finite cases only. The general
conjecture E_r(n) <= T_m(n) for all m >= 8 remains open.

| statement | proof file | mechanical check | status |
|---|---|---|---|
| word_C(m, a) sorts the unit base of (m..1){0,m}; length T + 2(a - (m-2)/2)^2 - 1 - (m mod 2)/2 = B; slopes (2a+1, 2a), (4,3) for a = 1 with m even; all m >= 3, 1 <= a <= m-2 (Session 25) | `WORDC-PROOF.md` | `checks/wordc_proof_check.py`: m = 9..40, 720 pairs, 0 mismatches, corollary failures 0 | proof written, unreviewed |
| word_R1(m) sorts the unit base of (m..1){1,m} with B = length; for m = 4u + rho: rho = 0 gives T-2, (m-4, m-2); rho = 1 gives T-2, (m-5, m-3); rho = 2 gives T, (m-6, m-4); rho = 3 gives T-2, (m-5, m-3); all m >= 9 (Session 28) | `WORDR1-PROOF.md` | `checks/wordr1_proof_check.py`: m = 9..60, 0 mismatches over Lemmas P, A-E, theorem, corollary (the author also ran m = 9..200, 0) | proof written, unreviewed |
| Lemma 1, (4), (5), refinement (6), Lemma 2, criteria (7) and (8) at general m (Session 27) | `LEMMA1-GENERAL-M-260926.md` | `checks-lemma1/lemma1_tables_check.py` (needs tables): 380 (family, word) pairs, 3,806 exact points, 0 violations; (7) at m = 9 on 146 families and 1,637 block-length vectors, 0 violations | proof written, unreviewed |
| Lemma 3 with (9), (10), formula (11), Lemma 4, section 7 resource formula at general m (Session 30) | `LEMMA34-GENERAL-M-260926.md` | `checks-lemma1/lemma34_tables_check.py` (needs tables): transfer 540 instances, 4,555 points, 90,923 comparator steps; projection 472 instances, 3,766 points; resource formula 980 zero atoms; 0 violations | proof written, unreviewed; no m >= 9 certificate here uses them |
| (m..1){0,m}: for every m >= 9 and all u0, u1 >= 1, d((0^u0, m, ..., 1, 0^u1)) <= T_m(m + u0 + u1); odd m by one word, even m by the 1/2-1/2 mixture | `WORDC-PROOF.md` + `LEMMA1-GENERAL-M-260926.md` | the two checks above | complete written proof, model-written, unreviewed |
| (m..1){1,m}: the same bound for every m >= 9 and every block-length vector | `WORDR1-PROOF.md` + `LEMMA1-GENERAL-M-260926.md` | the two checks above | complete written proof, model-written, unreviewed |
| No root-leaf certificate for m = 9 {0,4}: min of B + 3 beta_0 over all accepted sorting words is 75, while a root mixture needs < 74 (Session 29) | `negcert/NEGCERT.md`; completeness argument in the docstring of `negcert/negcert_check.py` | `negcert/negcert_check.py negcert/negcert-m9-04.json`: VERIFIED, about 16 s, stdlib only, no tables; `negcert/validate_small.py`: 21 of 21 brute-force cases at m = 3..6 agree | exact negative, portable checker, VERIFIED |
| word_G(m, g) certifies (m..1){0,g} in the outer band (Session 28) | none; `WORDR1-PROOF.md` section 11 says what a proof needs | `checks/wordg_formula_check.py`: m = 9..80, 1,600 rows, all 28 rule-row hypotheses and C2, C4, C6, C7 hold with 0 exceptions; the coarse C1, C3, C5 fail by design; out of sample at m = 81..120 the 26 nonempty hypotheses hold | conditional: 28 hypotheses, 0 exceptions, unproved |
| word_M(m, g, side) certifies contiguous runs at both ends of the middle band, m = 14..60 (Session 26) | none; `REVERSAL-CARRY.md` | `checks/reversal_carry.py`: 59 stored certificates; 160 closed-form rows by evaluator and audit at m <= 40; 207 by replay and criterion (7) at m = 41..60; no problems | conditional: rule read off data, unproved |
| k = 3 class survey: two-core certificates for all C(m+1,3) three-zero masks of m..1 at m = 9..11 (455 rows), plus the word_W closed form on the corner sub-band {0, g1, g2} (Session 31) | none; `REVERSAL-K3.md` | `checks/reversal_k3.py`: 455 stored certificates re-checked (evaluator, audit, replay), 50 misses recorded; word_W rows 122 by evaluator+audit+replay (m <= 24), 728 by replay+criterion (7) (m = 25..40) | conditional certificates unproved beyond the checked range; word_W band is a rule read off data, unproved |
| Interior masks (every zero of m..1 in gaps 1..m-1): k = 2, 3 all certified at the root over the two-core pool at every surveyed m (m = 9..13 for k=2, 9..12 for k=3); k = 4 has slope-bound misses at m = 9, 10 (Session 32) | none; `REVERSAL-INTERIOR.md` | `checks/reversal_interior.py`: 837 stored certified rows re-checked, 14 misses, completeness of every (k,m) cell verified | conditional: Conjecture I1 (k=2,3) holds on every checked cell; Conjecture I2 (k>=4 slope bound) has counterexamples, both unproved in general |
| Exact column generation over the exhaustive root-leaf LP: m = 10 {0,5} and m = 11 {0,6} root-certified (V < T+1); m = 11 {0,5}, m = 12 {0,5} and m = 12 {0,6} root-refuted exactly (V = T+1), the m = 12 pair by the C oracle only; m = 11 {0,5} is certified overall by a 4-leaf tree; m = 12 {0,5} and {0,6} stay BOUNDARY (family-level), each with one open leaf at lhs 1 (Sessions 33-35) | `MIDBAND-LOWERBOUND.md`, `MIDBAND-M12-14.md`, `MIDBAND-TREES-M12.md`; the C port and its validation in `negcert/fast/README.md` | `negcert/negcert_general.py` (m <= 11) and `negcert/fast/fast_check.py` (m = 12, C-backed) print VERIFIED for each certificate; `negcert/midband_positive_check.py` re-checks the two positives; `checks/midband_trees.py` re-checks the m = 11 {0,5} tree and the two m = 12 BOUNDARY families | exact negatives (m = 11 {0,5}, m = 12 {0,5}/{0,6}) and exact positives (m = 10 {0,5}, m = 11 {0,6}), all conditional only on Lemma 1 and criterion (7)/(8); m = 12 families remain BOUNDARY, not CERTIFIED |

**What the two chains say.** Combining the word_C proof with the general-m Lemma 1, (5) and (7) gives a written
proof with no conditional step of the bound for every block length of (m..1){0,m}, every m >= 9. The word_R1 proof
does the same for (m..1){1,m}. The repository records both as "proof written, unreviewed", not as theorems, until a
human mathematician has reviewed them.

**What the Lemma 1 audit found.** The only 8 in Lemma 1 is the root, which is notational. The manuscript proof of
Lemma 1 is a sketch; the note gives a full induction valid for m >= 2. The upper bound (5) holds for every word by the
triangle inequality; same-sign is needed only for equality. Criterion (7) follows by a one-line averaging argument that
the manuscript omits even at m = 8. Criterion (8) holds after replacing 6 by m-2. `lrx_m.py` matches the general-m
statements, and its m=8 defaults are stricter at m > 8, so they are conservative. Sections 5 and 6 of the manuscript
contain no m-dependent constant. No m >= 9 certificate in this repository uses Lemma 3, Lemma 4 or (11); they
matter for the m = 8 package, whose uses now have written proofs.

**Steps most worth a human reader's attention**, as flagged by the auditors: `LEMMA1-GENERAL-M-260926.md` section 4.1
(the induction), `LEMMA34-GENERAL-M-260926.md` section 4.3 items 2-3, `WORDC-PROOF.md` Lemma E, and `WORDR1-PROOF.md`
Lemma P.

**What is still not proved.** word_G and word_M are finite-range rules read off data. A proof of word_G needs a
partial-carry version of the sweep lemma, since 1,509 of 1,600 words have a partial core-1 carry. The middle of the
band stays open, apart from the families listed in section (b) and `REVERSAL-CARRY.md`. The radii, extremal
counts and T-1 distances of section (a) still rest on tables that are not shipped.
