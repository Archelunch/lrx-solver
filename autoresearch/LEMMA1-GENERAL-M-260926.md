# Lemma 1, refinement, criteria (7)/(8) at general m: audit (2026-09-26)

Question (Session 24 reviewers): is the group's proof of Lemma 1 (with
refinement) and of criteria (7)/(8) independent of m, or does it use m = 8?
Every certificate in this repository for m >= 9 is conditional on the
general-m versions.

Sources read: `downloads/recent/lrx_multiset_m8_complete.tex` (the group's
m = 8 manuscript, Russian; line numbers below are lines of the .tex file),
`downloads/recent/LEMMA14_COUNTEREXAMPLE_20260917.md`, `integrations/lrx_m.py`,
`autoresearch/verify-m8-260924/checker/lrxm8.py`, `research/problem.md`,
`research/claims.md` Sessions 10, 15, 20, 24, 25.

The manuscript and all its lemmas are the group's work. The general-m
statements and the proofs in section 4 below are written here (audit by an
Opus worker, not reviewed by a human mathematician). The main conjecture
remains open.

## Verdicts

| Item | Verdict |
|---|---|
| Lemma 1 (lift macros) | m-independent as written. The only m-dependent symbol is the root `(1,...,8,0^{k+sum z})` in the last sentence (notational). The written proof is a sketch; a complete proof is given in 4.1. |
| Formula (4) | m-independent as written (no constants except the macro cost 2). |
| Formula (5) | m-independent as written. Added observation: the upper bound F_W(z) <= B_W + sum beta_j z_j holds for every word by the triangle inequality; the same-sign condition is needed only for equality, not for soundness. |
| Refinement (6) | m-independent as written. |
| Lemma 2 | m-independent; needs only that the budget is an integer. |
| Criterion (7) | m-independent with a one-line added argument (4.4): the constants 30, 31+6k and 6 are T_8(8+k), T_8(8+k)+1 and the slope of T_8 in r. With T_m(n) = m(m+1)/2 + (r-1)(m-2) they become T_m(m+k)+1 and m-2. The manuscript gives no written proof of (7) even at m = 8. |
| Criterion (8) | m-independent as written (the manuscript's one-sentence argument is general) after the same substitution T -> T_m, 6 -> m-2. |

No step of the proofs of Lemma 1, (4)-(6), Lemma 2, (7) or (8) uses m = 8
(class c). Every class (c) use of m = 8 in the manuscript is in the finite
part (sections 2 counts, 7, 8) or in the n >= 130 remark, which the manuscript
itself bypasses. The repository's parametric reading in `integrations/lrx_m.py`
matches the general-m statements in 4.

What remains: the proofs in 4 need human review; Lemmas 3 and 4 and
formula (11) were read and look m-free but are not audited step by step
here; finite checks (section 5) validate finite cases only.

The counterexample note refutes a different lemma, (14) of the group's
"connected proof" manuscript, and does not touch Lemma 1 or (7)/(8) (section 6).

## 1. Statements, manuscript text and repository reading

Setting (lines 123-128): `n = 8 + r`, labels `1..8` once, `r` equal zeros;
`L` rotates left, `R = L^-1`, `X` swaps the first two entries; words run left
to right; root `v0 = (1,...,8,0^r)`. Families (lines 150-169): labels order
`a`, set `S` of nonempty linear gaps among `0..8`, `k = |S|`, block lengths
`u in Z_{>=1}^k`; target (3): `d(v(a,S,u), v0) <= T(u) := 30 + 6 sum u_j`.

General-m reading: labels `1..m`, gaps `0..m`, `T_m(n) = m(m+1)/2 + (r-1)(m-2)`
(`budget`, `lrx_m.py:68`). At m = 8, `T_8(8+r) = 36 + 6(r-1) = 30 + 6r`, so
the target agrees with (1) and (3). The unit base (`u_j = 1`) is
`base_vector` (`lrx_m.py:73`).

### Lemma 1 (lines 179-204)

> В единичной базе временно различим нули. Атом j заменим блоком длины
> 1+z_j, где z_j>=0. Метки сохраняют длину один. Сортирующее слово без
> обменов двух нулей поднимается макросами: [table, lines 190-194]
> L через первый атом длины h -> L^h; R через последний атом длины h -> R^h;
> X на двух метках -> X; X на (0^{1+z_j},a) -> L^{z_j}X(RX)^{z_j};
> X на (a,0^{1+z_j}) -> X(LX)^{z_j}R^{z_j}.
> **Лемма 1.** Поднятое слово сортирует расширенную базу.
> **Доказательство.** После каждого макроса физический вектор равен
> расширению текущего атомарного вектора. Последние две строки переносят
> метку через соседний блок нулей и возвращают начало видимого вектора на
> нужную границу атомов. Остальные строки сохраняют инвариант
> непосредственно. В конце получается (1,...,8,0^{k+sum z_j}). □

(Translation: distinguish the zeros of the unit base; atom j becomes a block of
length 1+z_j; a sorting word that never swaps two zeros is lifted by the
macros; the lifted word sorts the stretched base. Proof: after each macro the
physical vector is the expansion of the current atomic vector.)

Repository: `Profile` (`lrx_m.py:157-239`) runs the word on the base with zero
ids, refuses a swap of two zeros (`:199-200`) and a non-sorting word (`:225-226`);
`Profile.lift` (`:248-261`) writes the lifted word with the two swap macros as
`X(RX)^z` and `X(LX)^z` and the boundary rotations `L^z`, `R^z` merged into the
neighbouring rotation segments; `literal_lift_check` (`:279-294`) executes it.

### Formula (4) (lines 206-218)

> Обозначим через A_j число исходных обменов с нулём j, через q --- число
> всех исходных обменов. Между исходными обменами ... сложим подписанные
> вращения, включая граничные вращения макросов. Для промежутка g
> получится d_g + sum_j c_{gj} z_j. ... точная длина равна
> F_W(z) = q + 2 sum_j A_j z_j + sum_g |d_g + sum_j c_{gj} z_j|.   (4)

Repository: `Profile.__init__` builds `segs = [(d_g, c_g)]` (`:182-223`):
an `L` over picked atom j adds 1 to `c_gj` (`:183-188`), an `R` subtracts 1
(`:189-194`), the `ZL` swap adds 1 to the closing segment (`:205-210`), the
`LZ` swap puts -1 into the next segment (`:211-216`); `exact_len` (`:241-243`)
is (4).

### Formula (5) (lines 220-229)

> ... в одном промежутке все ненулевые числа d_g, c_{g1},...,c_{gk} имеют
> один знак. Тогда на z_j>=0 F_W(z) = B_W + sum_j beta_j z_j,
> B_W = q + sum_g |d_g|, beta_j = 2A_j + sum_g |c_{gj}|.   (5)

Repository: `Profile.base`, `Profile.beta`, `same_sign` (`:227-236`), `affine` (`:245-246`).

### Refinement (6) (lines 231-238)

> Разрешается уточнить исходный блок j до o_j нулевых атомов. Выбрав один
> атом в каждой группе, растягиваем его ещё на u_j - o_j. При u_j >= o_j
> получаем то же физическое семейство и цену
> C_i(u) = B_i + sum_j gamma_{ij}(u_j - o_{ij}).   (6)
> ... Их коэффициенты вычисляются заново по (4)--(5).

Repository: `refine` (`:116-127`), `Profile(state, word, picks)` with one pick
per block (`:167-172`), `stretch` (`:130-140`).

### Lemma 2 and criterion (7) (lines 244-259)

> **Лемма 2.** Пусть слова W_i(u) сортируют один и тот же вход, а
> рациональные числа theta_i>=0 имеют сумму один. Если
> sum_i theta_i C_i(u) < T(u)+1, то d(v(u),v_0) <= T(u).
> Для единичных баз достаточны условия
> Bbar < 31+6k,   betabar_j <= 6 (1<=j<=k).   (7)
> Они доказывают (3) при всех u_j>=1.

Repository: `mixture_criterion(costs, weights, k, m)` (`lrx_m.py:497-505`):
`B < budget(m, k) + 1` and every `betabar_j <= m - 2`. At m = 8 this is
`B < 31 + 6k`, `betabar_j <= 6`, identical to `lrxm8.py:496`.

### Criterion (8) (lines 257-274)

> В листе область имеет вид prod_j [l_j,h_j]; допускается h_j = +infinity.
> Все уточнения удовлетворяют o_{ij} <= l_j. Положим Cbar(l) = sum_i
> theta_i C_i(l) и gammabar_j = sum_i theta_i gamma_{ij}. Лист подтверждён,
> если на неограниченных координатах gammabar_j <= 6, а
> Cbar(l) - T(l) + sum_{j:h_j<inf} max(0, gammabar_j - 6)(h_j - l_j) < 1.   (8)
> Действительно, левая часть --- максимум аффинной разности средней цены и
> бюджета в данном прямоугольнике. Применяется лемма 2. Два потомка
> полностью покрывают целочисленную область родителя; индукция по
> конечному дереву доказывает (3) для всех длин.

Repository: `leaf_criterion(rows, box, m)` (`lrx_m.py:508-525`) with
`s = m - 2`, `T = budget(m, 0) + s * sum l_j` (that is `T_m(m + sum l_j)`), the
origin check `o_ij <= l_j` (`:514-516`); `tree_leaves` (`:528-542`) splits
`[l,h]` into `[l,t]` and `[t+1,h]`.

Note on defaults: `mixture_criterion` and `leaf_criterion` default to `m=8`.
Called with m = 8 on a state with m' > 8 labels, both are stricter than the
m' criteria (`budget(8,k) < budget(m',k)`, `6 < m'-2`), so a missed `m`
argument is conservative, never unsound. The bound evaluators pass `m`
explicitly (`integrations/bound_evaluator.py:451-457`).

## 2. Every place where 8, n = 8 + r, T_8, 6 or 8! enters

Class (a): notational, replace 8 by m. Class (b): holds for all m >= m0 with
a short argument. Class (c): genuinely m = 8 (finite check, table, enumeration).

| Lines | Text | Where used | Class |
|---|---|---|---|
| 113-117 | "восемь различных меток"; "Общая гипотеза при переменном m>=8 остаётся открытой" | scope | (a) |
| 123, 128 | `n = 8 + r`, labels `1..8`, `v0 = (1,...,8,0^r)` | setting | (a) |
| 132-133 | `6n-18 = 30+6r = binom(n,2) - (r-1)(r+4)/2` | theorem (1) | (a) for the budget (equals T_8); the binomial identity is m = 8 arithmetic, used nowhere in the lemmas |
| 150-165 | nine gaps, `8!(2^9-1) = 20603520` families | finite partition | (a) for the partition (m+1 gaps, `m!(2^{m+1}-1)` families); the count is (c) |
| 169 | `T(u) := 30 + 6 sum u_j` | target (3) | (a): `T_m(m + sum u_j)` |
| 179-204 | Lemma 1 and proof; only `(1,...,8,0^{k+sum z_j})` | Lemma 1 | (a) |
| 206-238 | (4), (5), (6), cost `2A_j z_j` | pricing | no constant depending on m |
| 244-250 | Lemma 2 | integrality | no constant; needs T integer |
| 254-255 | `31+6k`, `6` | (7) | (a), argument in 4.4 |
| 265-268 | `gammabar_j <= 6`, `max(0, gammabar_j - 6)`, `T(l)` | (8) | (a), argument in 4.5 |
| 276-283 | search restricted to `sum u_j <= 121` via the earlier theorem `E_{n-8}(n) <= floor((23n+61)/4) <= 6n-18` for `n >= 130` | search only | (c), but the manuscript states the final certificates satisfy the unbounded (7)-(8), so the proof does not use it. The repository uses only the unbounded form. |
| 304-338 | Lemma 3, (9)-(11) | transfer | no m-dependent constant seen (not audited step by step) |
| 356-377 | Lemma 4, projection, "строгого неравенства (7)" | projection | no m-dependent constant besides (7) itself |
| 387-425 | resource search with `|W| <= 30+6k`, resource above 6 pruned, `beta_j = 3A_j + B_j - 2F_j`, increment table | finite m = 8 search | derivation m-free; the enumeration and its thresholds are (c) |
| 438-455 | 362880 / 1814400 / 6652800 bases, exceptions, trees | finite part | (c) |
| 472-498 | "все 8! порядков" for nine blocks; 4088 reference trees; 262513 four-block families | finite part | (c) |
| 504-534 | union table; "длины не выше 30+6 sum u_j = 6n-18" | conclusion | (c) table; (a) budget |
| 540-564 | worked family, W1, W2, weights 5/8, 3/8, `T(u) = 54 + 6 sum(u_j-1)` | example | (c) instance; reproduced by `lrx_m` in section 5, Part 0 |
| 592-595 | "не доказывает гипотезу для m=9,10,..." | scope | statement of scope |

So the answer to the reviewers' question: none of Lemma 1, (4), (5), (6),
Lemma 2, (7), (8) uses m = 8 in its proof. The constants 30, 31, 6 enter
only through the budget and its slope.

## 3. Step-by-step walk through the manuscript's proofs

**Lemma 1.** Step 1: distinguish zeros, stretch atom j to length 1+z_j
(line 179). No m. Step 2: macro table (lines 190-194). The macro costs
(h, 1, 1+2z, 1+2z plus the boundary z) do not depend on m. Step 3: invariant
"physical vector = expansion of the atomic vector after each macro"
(lines 199-200). The manuscript asserts it for the two swap macros in one
sentence and calls the other rows immediate; 4.1 verifies each macro. Step 4:
final vector `(1,...,8,0^{k+sum z_j})` (line 203): class (a). The hypothesis
"no swap of two zeros" is needed because two stretched zero blocks cannot be
exchanged by one macro; it is m-free.

**Formula (4).** Step 1: split the atomic word at its q swaps into q+1
rotation segments (line 208). Step 2: signed rotation of segment g, with the
boundary rotations `L^{z_j}` and `R^{z_j}` of the swap macros assigned to the
adjacent segments, is `d_g + sum_j c_gj z_j` (line 210). Step 3: replace each
segment by its net power (opposite rotations cancel) (line 211). Step 4:
each swap macro contributes `1 + 2z_j` letters (lines 216-218). No constant
depends on m.

**Formula (5).** Same-sign segments give `|d + sum c z| = |d| + sum |c| z` on
`z >= 0` (lines 220-229). m-free.

**Refinement (6).** A block of length `u_j >= o_j` is the refined block of
`o_j` unit atoms with one atom stretched by `u_j - o_j` (lines 231-234); the
cost is (4)-(5) of the refined word at `z = u - o`. m-free.

**Lemma 2.** A weighted mean bounds the minimum; lengths and budget are
integers (lines 248-250). m-free, requires `T(u) in Z`, true for `T_m`.

**Criterion (7).** Lines 252-257 state (7) and its consequence without a
proof. The implicit proof uses only: `C_i(u) <= B_i + sum_j beta_ij (u_j - 1)`
at the unit base (`o = 1`), `T(u) - T(1) = 6 sum (u_j - 1)`, and Lemma 2. The
6 is the slope of `T_8` in r: class (a).

**Criterion (8).** Lines 265-274: affine maximum over a box plus Lemma 2
plus induction on the finite tree. The 6 is again the budget slope: class (a).

## 4. General-m statements and proofs

Fix m >= 2, r >= 1, n = m + r, root `(1,...,m,0^r)`, and
`T_m(m + r) = m(m+1)/2 + (r-1)(m-2)`. Only two properties of T_m are used:

    (P1) T_m(m + r) is an integer;
    (P2) T_m(m + r) - T_m(m + r') = (m-2)(r - r').

Any budget with (P1) and (P2) for slope s works with m-2 replaced by s.

### 4.1 Lemma 1 at general m

Let B be a base with atoms: the m labels and some zeros, each atom of
length one, and let P be a set of distinguished (picked) zero atoms. For
`z in Z_{>=0}^P` let `E_z(x)` be the vector obtained from an atomic vector x
by replacing each picked atom j by `0^{1+z_j}`. Let W sort B, never swap two
zeros, and let `lift_z(W)` be the macro word of lines 190-194 (a letter
through a non-picked atom lifts to itself).

Claim: if the physical visible vector equals `E_z(x)` before an atomic
letter, it equals `E_z(x')` after its macro, where `x'` is the atomic vector
after the letter.

Write `x = (x1, x2, ..., xN)`, cyclic, with `N = m + #atoms of zero`.

- `L`, first atom of physical length h: `E_z(x) = (block(x1), E(rest))`,
  and `L^h` moves exactly that block to the end, giving
  `E_z(x2,...,xN,x1)`.
- `R`, last atom of length h: symmetric with `R^h`.
- `X` on two labels, or on a label and a non-picked zero: the first two
  physical entries are the two atoms themselves; `X` swaps them.
- `X` on `(0_j, a)`, j picked, `x = (0_j, a, y)`. Physical:
  `(0^{1+z}, a, Y)` with `Y = E_z(y)`.
  `L^z`: `(0, a, Y, 0^z)`. `X`: `(a, 0, Y, 0^z)`. From `(a, 0^s, Y, 0^t)`
  with `t >= 1`: `R` gives `(0, a, 0^s, Y, 0^{t-1})` and `X` gives
  `(a, 0^{s+1}, Y, 0^{t-1})`; starting at s = 1, t = z, after z rounds the
  result is `(a, 0^{1+z}, Y) = E_z(a, 0_j, y)`. (Y holds the other m-1
  labels, so it is nonempty for m >= 2.)
- `X` on `(a, 0_j)`, j picked, `x = (a, 0_j, y)`. Physical:
  `(a, 0^{1+z}, Y)`. `X`: `(0, a, 0^z, Y)`. From `(0, a, 0^s, Y, 0^t)` with
  `s >= 1`: `L` gives `(a, 0^s, Y, 0^{t+1})` and `X` gives
  `(0, a, 0^{s-1}, Y, 0^{t+1})`; starting at s = z, t = 0, after z rounds
  `(0, a, Y, 0^z)`; `R^z` gives `(0^{1+z}, a, Y) = E_z(0_j, a, y)`.

Every step is a statement about the first two entries and cyclic shifts of
a finite vector; neither m nor N appears. By induction over the letters of
W, `run(E_z(B), lift_z(W)) = E_z(run(B, W))`. The final atomic vector is the
m labels in order followed by all zero atoms in some order, so the physical
result is `(1,...,m,0^{r})`. The lemma holds for every m >= 2.

### 4.2 Formula (4) and the upper bound (5)

Write `W = S_0 X S_1 X ... X S_q` with rotation strings `S_g`. In the lifted
word the letters of `S_g` become `L^{h}` or `R^{h}`, h = 1 + z_j over picked
atom j and 1 otherwise, and the swap macros contribute `L^{z_j}` at the end
of `S_{g-1}` (swap of type `(0_j, a)`), `R^{z_j}` at the start of `S_g` (type
`(a, 0_j)`), and a core of `1 + 2 z_j` letters (`X(RX)^{z_j}` or `X(LX)^{z_j}`),
or `X` alone. The lifted rotation string of segment g is a word in L, R
whose composite is `L^{e_g}`, `e_g = d_g + sum_j c_gj z_j`, where `d_g` is the
signed count of letters of `S_g` and `c_gj` the signed count of those passing
atom j plus the macro boundary terms. Replacing it by `L^{e_g}` or
`R^{-e_g}` does not change the permutation. The resulting word sorts
`E_z(B)` and has length (4).

For every `z >= 0`, `|d_g + sum_j c_gj z_j| <= |d_g| + sum_j |c_gj| z_j`, hence

    F_W(z) <= B_W + sum_j beta_j z_j   for all words W and all z >= 0,

with equality when every segment is same-signed. The same-sign test in
(5) is therefore not needed for an upper-bound certificate. (In the
repository all 380 sampled geodesic words and all 835 stored m = 9
certificate words are same-signed anyway.) m does not appear.

### 4.3 Refinement (6)

Given a family block of length `u_j >= o_j`, take the refined base with
`o_j` zero atoms in block j and pick one of them. Stretching the picked atom
by `z_j = u_j - o_j` gives the family vector `v(u)` (zeros are
indistinguishable in the visible state). By 4.1-4.2 applied to the refined
base, `d(v(u)) <= F_{W}(u - o) <= B + sum_j gamma_j (u_j - o_j)`. m-free.

### 4.4 Criterion (7) at general m

Statement: let words `W_i` sort the unit base of a k-block family with
costs `(B_i, beta_i)` from (5), and rational `theta_i >= 0`, `sum theta_i = 1`, with

    Bbar = sum theta_i B_i < T_m(m+k) + 1,   betabar_j = sum theta_i beta_ij <= m - 2.

Then `d(v(u)) <= T_m(m + sum u_j)` for every `u in Z_{>=1}^k`.

Proof: put `z = u - 1 >= 0`. By 4.2, `|lift_z(W_i)| <= B_i + sum_j beta_ij z_j`.
Averaging, `sum theta_i |lift_z(W_i)| <= Bbar + sum_j betabar_j z_j
< T_m(m+k) + 1 + (m-2) sum_j z_j = T_m(m + sum u_j) + 1` by (P2), using
`betabar_j <= m-2` and `z_j >= 0`. Some i has `|lift_z(W_i)|` at most the
average, so `|lift_z(W_i)| < T_m(m + sum u_j) + 1`, and by (P1)
`|lift_z(W_i)| <= T_m(m + sum u_j)`. That word sorts `v(u)` by 4.1. □

### 4.5 Criterion (8) at general m

Statement: a leaf box `prod_j [l_j, h_j]` (`h_j` possibly infinite) with rows
`(theta_i, B_i, gamma_i, o_i)`, `o_ij <= l_j`, `Cbar(l) = sum theta_i (B_i +
sum_j gamma_ij (l_j - o_ij))`, `gammabar_j = sum theta_i gamma_ij`, is
confirmed if `gammabar_j <= m-2` on unbounded coordinates and

    Cbar(l) - T_m(m + sum l_j) + sum_{j: h_j < inf} max(0, gammabar_j - (m-2)) (h_j - l_j) < 1.

Then `d(v(u)) <= T_m(m + sum u_j)` for every integer u in the box.

Proof: for u in the box, `u_j >= l_j >= o_ij`, so 4.3 applies to every row.
The averaged bound minus the budget is, by (P2),

    D(u) = Cbar(l) - T_m(m + sum l_j) + sum_j (gammabar_j - (m-2)) (u_j - l_j).

Each term with finite `h_j` is at most `max(0, gammabar_j - (m-2))(h_j - l_j)`;
each term with infinite `h_j` is at most 0. So `D(u) < 1`, and Lemma 2 with
(P1) gives the bound as in 4.4. A split at t sends `[l, h]` to `[l, t]` and
`[t+1, h]`, which partition the integers of the parent interval; induction
on the finite tree covers the root box `[1, inf)^k`. □

The Σu <= 121 relaxation (lines 276-283) has no general-m analogue in the
manuscript; it is not needed because 4.5 is the unbounded form, which is
what `leaf_criterion` implements.

## 5. Exact-table sanity checks

Script: `autoresearch/checks-lemma1/lemma1_tables_check.py` (read-only,
stdlib plus `integrations/lrx_m.py` and `src/lrx/table_bfs.Ranker`; tables
memory-mapped). Tables used: complete one-byte BFS tables (9,1)..(9,6),
(10,2), (10,3); each meta file says `complete: true`.

- Part 0 prices the manuscript's section 8 example with `lrx_m`.
- Part A samples random families `(a,S)` and words sorting the (refined)
  unit base: random-tie shortest words from the tables ("geo"), one random
  letter followed by a shortest word ("pre", not geodesic), and refined
  bases with one or two blocks of `o_j = 2` atoms and a random picked atom
  ("ref", tests (6)). For every `z >= 0` with the stretched state inside
  table range, it checks that the lifted word literally sorts `v(z)` with
  length `F_W(z)`, and that `d(v(z)) <= F_W(z) <= B + beta.z`.
- Part B takes the 146 distinct m = 9 families with k <= 6 certified at the
  root in the bound-campaign finalist rows, recomputes every word's cost,
  re-checks (7) with the stored weights, and for every `u >= 1` with
  `sum u <= 6` checks `d(v(u)) <= T_9(n)` and `min_i F_i(u) <= T_9(n)`, and
  that the best lifted word sorts.

Honest scope: `d <= F` in Part A and `d <= T` in Part B follow logically
from "the lifted word sorts". The table comparison is therefore a check of
the executor, the pricing code and the tables against each other, not an
independent test of the lemma beyond literal execution. A violation would
have shown a bug in one of them, or a false lemma.

Output (`python autoresearch/checks-lemma1/lemma1_tables_check.py`, seed
260926, 4.2 s wall):

```
Part 0  manuscript section 8 example (m=8):
  W1 base 48 slopes [9, 6, 0, 8], W2 base 66 slopes [1, 2, 8, 0] ; manuscript: 48 (9,6,0,8), 66 (1,2,8,0) -> MATCH
  weights 5/8,3/8: Bbar = 219/4 (manuscript 219/4), betabar = ['6', '9/2', '3', '5'], criterion (7) at m=8: True

Part A  Lemma 1 / (4)-(6) against exact distances (seed 260926)
  geo  m=9  pairs 200  block-length vectors tested  2480
  geo  m=10 pairs  40  block-length vectors tested   120
  pre  m=9  pairs  60  block-length vectors tested   744
  ref  m=9  pairs  60  block-length vectors tested   422
  ref  m=10 pairs  20  block-length vectors tested    40
  total pairs 380, total (pair, z) points 3806
  same-sign condition of (5) holds for 380 words, fails for 0
  lifted word fails to sort or length != F_W(z): 0
  violations d(v(z)) > F_W(z): 0 ; F_W(z) > B + beta.z: 0 ; d(v(z)) > B + beta.z: 0
  slack (B + beta.z) - d(v(z)) over z != 0:  0:1300 1:304 2:517 3:160 4:274 5:86 6:170 7:80 8:88 9:42 10:49 11:30 12:67 13:21 14:33 15:17 16:35 17:19 18:30 19:16 20:12 21:6 22:12 23:6 24:12 25:6 26:4 27:1 28:8 29:4 30:4 31:2 32:2 34:2 35:3 36:1 40:1 41:1 45:1
  slack F_W(z) - d(v(z)) over z != 0:        0:1300 1:304 2:517 3:160 4:274 5:86 6:170 7:80 8:88 9:42 10:49 11:30 12:67 13:21 14:33 15:17 16:35 17:19 18:30 19:16 20:12 21:6 22:12 23:6 24:12 25:6 26:4 27:1 28:8 29:4 30:4 31:2 32:2 34:2 35:3 36:1 40:1 41:1 45:1
  (B + beta.z) - F_W(z) over z != 0:         0:3426

Part B  criterion (7) at m=9 against exact distances
  certified families re-checked by (7): 146 (per k: {2: 27, 3: 31, 4: 26, 5: 32, 6: 30}); criterion failures on recompute: 0
  T_9(unit)+1 - Bbar distribution: 1/25:2 1/5:1 1/2:1 21/32:1 2/3:1 1:6 13/12:1 9/8:1 24/17:1 3/2:1 11/7:1 7/4:1 9/5:1 19/10:1 2:4 42/17:1 8/3:1 159/56:1 35/12:1 3:5 10/3:1 18/5:1 11/3:1 27/7:1 4:8 62/15:1 127/30:1 121/27:1 9/2:2 23/5:1 14/3:1 109/23:1 19/4:1 29/6:1 5:8 26/5:2 37/7:1 53/10:1 28/5:1 17/3:1 6:4 37/6:1 19/3:1 32/5:1 109/17:1 20/3:1 27/4:1 7:5 274/39:1 130/17:1 123/16:1 55/7:1 71/9:1 8:4 9:3 46/5:1 37/4:1 28/3:2 10:2 41/4:1 31/3:1 85/8:1 32/3:1 259/24:1 11:2 236/21:1 57/5:1 12:2 25/2:1 38/3:1 13:1 40/3:1 29/2:1 15:2 91/6:1 16:1 50/3:1 151/9:1 17:1 53/3:1 18:1 149/8:1 19:2 20:1 62/3:2 65/3:1 22:1 449/20:1 24:3 25:3 28:1 31:1 107/3:1 46:1
  block-length vectors u >= 1 with sum u <= 6 tested: 1637
  violations d(v(u)) > T_9(n): 0 ; min_i F_i(u) > T_9(n): 0 ; lift failures: 0
  slack T_9(n) - d(v(u)):        3:2 4:7 5:11 6:27 7:33 8:47 9:55 10:55 11:59 12:62 13:73 14:75 15:84 16:90 17:74 18:52 19:69 20:55 21:63 22:54 23:61 24:55 25:40 26:43 27:34 28:30 29:42 30:37 31:27 32:23 33:20 34:13 35:19 36:15 37:12 38:18 39:8 40:13 41:10 42:8 43:12 44:7 45:6 46:8 47:2 48:4 49:3 50:1 52:4 53:2 54:1 56:1 58:1 59:2 60:1 63:1 64:1 65:1 66:1 67:1 70:1 73:1
  slack T_9(n) - min_i F_i(u):   0:11 1:11 2:35 3:44 4:57 5:78 6:74 7:70 8:71 9:86 10:80 11:90 12:83 13:70 14:65 15:59 16:56 17:53 18:56 19:43 20:34 21:40 22:28 23:28 24:35 25:23 26:25 27:21 28:15 29:18 30:21 31:14 32:10 33:15 34:10 35:9 36:10 37:9 38:9 39:10 40:9 41:6 42:4 43:9 44:4 45:7 46:2 48:2 49:4 52:2 53:1 56:1 57:1 59:1 60:1 61:1 63:1 64:1 66:1 67:1 70:1 73:1

RESULT: PASS (0 violations)
```

Reading: 380 (family, word) pairs, 3806 exact comparisons, 0 violations.
The lifted geodesic is itself a geodesic at 1300 of 3426 stretched points.
For (7), 146 m = 9 families and 1637 exact block-length vectors, 0
violations. The certified mixture is tight (`min_i F_i(u) = T_9(n)`) at 11
points, and the exact distance is at least 3 below the budget everywhere
tested. Finite checks validate finite cases only.

## 6. The LEMMA14 counterexample note

The note (dated 2026-09-17) concerns lemma (14) in §6 of a different group
manuscript, `LRX_CONNECTED_PROOF`: "for any finite permutation pi on b
positions, 2 Delta(pi) + K^2 <= b^2", with `Delta = sum |pi(i) - i|` and K
from its (11). Counterexample: `pi = [0,2,4,1,5,3]`, b = 6, Delta = 8, K = 5
at `(x,y) = (3,4)`, so `2*8 + 25 = 41 > 36`. The note reports 8 violations
among 69 admissible permutations at b = 6 and 3106 of 18011 at b = 9, and
says the "orbit" reading removes this instance but still leaves 162 of 873
violations at b <= 6. It says (16)-(18) and the payment of inner gaps in
§7-8 of that manuscript depend on (14).

Delta = 8 was recomputed here. K was not, because definition (11) of that
manuscript is not in the repository.

It does not touch Lemma 1, (4)-(8) or the m = 8 theorem. The m = 8 manuscript
states at lines 592-593: "Ни неверная лемма 2Delta+K^2<=b^2, ни утверждение
о диаметре чистого графа S_n не используются" (neither the false lemma nor
the S_n diameter claim is used). None of the proofs walked through in
sections 3-4 above refers to Delta, K or cycle loads.

## 7. What would still be needed

- **Human review of section 4.** The proofs are short and elementary, but
  they were written by a model. With that review, the repository's m >= 9
  certificates from root mixtures and trees (Sessions 15-25) are
  conditional only on correct execution of the stored words and exact
  recomputation of (4)-(5). They would no longer depend on an unproved
  general-m lemma.
- **Lemmas 3, 4 and formula (11) at general m.** They were read and contain
  no m-dependent constant. They were not audited step by step here, so
  certificates that use transfer or projection at m >= 9 need the same audit.
- **The general conjecture remains open.** This audit concerns the
  certificate machinery, not coverage of all families at any m >= 9.
