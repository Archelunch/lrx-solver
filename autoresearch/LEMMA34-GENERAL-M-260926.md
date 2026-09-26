# Lemma 3, formula (11), Lemma 4 and the section 7 resource search at general m: audit (2026-09-26)

Continues `autoresearch/LEMMA1-GENERAL-M-260926.md` (Session 27), which
audited Lemma 1, (4)-(6), Lemma 2 and criteria (7)/(8). Question: do the
remaining lemmas of the group's m = 8 proof use m = 8, and which repository
certificates depend on them?

Sources read: `downloads/recent/lrx_multiset_m8_complete.tex` (the group's
m = 8 manuscript, Russian; line numbers are lines of the .tex file),
`autoresearch/verify-m8-260924/checker/lrxm8.py`, `integrations/lrx_m.py`,
`integrations/lift_task.py`, `integrations/lift_evaluator.py`,
`integrations/projected_mixtures.py`, `integrations/bound_evaluator.py`,
`autoresearch/lift-m9-260924/build_frozen.py` and `add_tree_stratum.py`,
`research/claims.md` Sessions 8-11, 14, 17, 27.

The manuscript and its lemmas are the group's work. The general-m proofs in
section 4 below were written here by an Opus worker and have not been
reviewed by a human mathematician. The main conjecture remains open.

## Verdicts

| Item | Verdict |
|---|---|
| Order (9) and update rule (10) | m-independent as written. No constant. |
| Lemma 3 (comparison transfer) | m-independent as written. The manuscript proof is correct and complete in outline; 4.2 writes it out, including the two facts it leaves implicit (zero ranks stay ascending, so no zero-zero swap; the rank-identity end state is exactly the root). |
| Formula (11) | m-independent, with added argument (4.3). The manuscript's stretching paragraph (lines 322-338) is a sketch. Three steps are filled in here: A_j = sigma_j(Q) follows from #X = inv(Q); the cut stays uncrossed after lifting; stretching preserves (9) because P and Q give each zero atom the same rank. (11) is exact under the same-sign condition and an upper bound for every word. |
| sigma_j(P) <= sigma_j(Q) (lines 332-335) | True at general m (4.3, remark). Not needed for soundness: coefficients are recomputed. |
| Lemma 4 (projection) | m-independent as written; the manuscript proof is complete. |
| Commutation with stretching (lines 366-371) | True at general m after normalising rotation runs (4.5). The resulting F_child(z) <= F_parent(z) is proved for all z. Slopes and base do not increase when both words are same-signed. Not needed for soundness, because child costs are recomputed. |
| Transfer rows in trees and after projection | m-independent: (11) at a refined base plus Session 27's 4.4-4.5 (4.4 here). |
| Section 7 resource formula and table | m-independent derivation (4.6). The thresholds `30+6k` and `6` are T_8(8+k) and the slope, class (a). The enumerations themselves are m = 8 (class c). |

No step of the proofs of Lemma 3, (9)-(11), Lemma 4 or the section 7 resource
derivation uses m = 8. Sections 5 and 6 of the manuscript (lines 286-377)
contain no occurrence of 8, 6, 30, 31 or 8!. The only m-dependent reference
there is "(7) или (8)" (lines 343, 375), which Session 27 already handled.

Repository consequence (section 6): **no m >= 9 certificate in this
repository uses Lemma 3, Lemma 4 or (11)**. Every m >= 9 certificate is a
literal word on the child's unit or refined base, priced by `Profile`
(Lemma 1 with (4)-(6)) and decided by (7) or (8). Session 27's remark that
"certificates using them at m >= 9 stay conditional" therefore applies to an
empty set. Lemmas 3, 4 and (11) are used by the m = 8 work (Sessions 8, 9, 10
and the nine-gap check). For those, this note supplies written proofs, not
yet human-reviewed.

Table checks (section 5): 540 transfer instances (320 at m = 9, 220 at
m = 10), 60 projected-then-transferred instances, 472 projection instances
(272 at m = 9, 200 at m = 10), and 320 resource-formula words. Result:
0 violations.

## 1. Statements, manuscript text and repository reading

Setting as in Session 27: `n = m + r`, root `(1..m, 0^r)`, `L` left
rotation, `R = L^-1`, `X` swaps the first two entries. The budget is
`T_m(m+r) = m(m+1)/2 + (r-1)(m-2)`.

### Physical model and order (9) (lines 289-302)

> Зафиксируем физические позиции окружности. Вращения перемещают курсор,
> обмен меняет два соседних значения. Выберем разрез, через который опорное
> слово не обменивает элементы. Получаем линейное окно. Конечная физическая
> раскладка и конечный курсор задают целевые ранги 0,...,N-1. Нули
> сопоставляются нулевым целям по порядку в окне; без обменов двух нулей
> этот порядок сохраняется. Пусть Q --- ранги опорного входа, P --- ранги
> другого входа с теми же позициями нулей.
> H_P(j,s) = #{i<j : P_i < s},  P ⪯ Q ⟺ H_P(j,s) >= H_Q(j,s) для всех j,s.   (9)

In English: fix the physical positions of the circle. Rotations move a
cursor, and a swap exchanges two adjacent values. Choose a cut that the
reference word never swaps across; this gives a linear window. The final
layout and final cursor define target ranks. Zeros are matched to zero
targets in window order. Q holds the reference ranks, and P the ranks of
another input with the same zero positions.

Repository: `target_ranks` (`lrx_m.py:298-313`) and `prefix_dominates`
(`:321-334`). A cut is valid when the edge (cut-1, cut) is never swapped:
`Reference.cut_ok` (`:395-396`), with `used_edges` collected in `Profile`
(`:201`).

### Lemma 3 and (10) (lines 304-320)

> **Лемма 3.** Если P ⪯ Q и опорное слово сортирует Q, то те же вращения и
> сравнения на местах исходных обменов сортируют P. Обмен выполняется только
> для убывающей пары. Выполнено ровно inv(P) обменов.
> **Доказательство.** Сравнение в позициях j-1, j меняет только префиксное
> число длины j. Его новое значение при пороге s равно
> min(H_P(j-1,s)+1, H_P(j+1,s)).   (10)
> Эта функция не убывает по обоим аргументам и даёт максимальное число малых
> элементов, достижимое перестановкой пары. Следовательно, сравнение на P
> сохраняет (9) относительно любого обмена на Q. В конце Q имеет максимальные
> префиксные числа min(j,s), значит P тоже отсортирована. Каждое выполненное
> сравнение уменьшает число инверсий на один. Вращения и конечный курсор
> остались прежними. □

Repository: `conditional_run` (`lrx_m.py:358-380`), `Reference.transfer`
(`:406-430`), `lift_task.comparison_word` (`lift_task.py:48-66`).

### Formula (11) (lines 322-338)

> Предположим, что исходное число обменов равно inv(Q). Для нулевого атома j
> обозначим через sigma_j(P) число его инверсий с метками. Растяжение на z_j
> добавляет sigma_j(P) z_j инверсий ... По лемме 3 точная цена перенесённого
> слова равна
> B_Q - inv(Q) + inv(P) + sum_j (beta_j(Q) - sigma_j(Q) + sigma_j(P)) z_j.   (11)
> ... sigma_j(P) = h + s - 2H_p(h,s) ... Из (9) следует sigma_j(P) <= sigma_j(Q).
> Условие (9) сохраняется при растяжении: добавленные нулевые ранги дают
> одинаковые вклады в оба входа ... Разрез остаётся границей атомов. Поэтому
> (11) справедлива для любых положительных длин.

Lines 340-344 describe the certificate row: a reference word, an unused cut
and a rational weight. The checker executes the word, checks every prefix
and that #X = inv, recomputes (11), then applies (7) or (8). Different rows
may use different cuts.

Repository: `Reference.transfer` checks `#X = inv(Q)` and `A_j = sigma_j(Q)`
(`lrx_m.py:414-417`), checks (9) and the comparison run, and returns (11)
(`:428-430`). `literal_transfer` (`:432-458`) re-runs the lifted reference on
stretched P at sampled z. The same code appears in `lrxm8.py:375-450` with
m = 8.

### Lemma 4 and the paragraph after it (lines 350-377)

> Временно пометим удаляемые нулевые атомы. Буква L сохраняется, если первый
> атом не удалён; R --- если последний не удалён; X --- если оба атома
> сохранены. В остальных случаях буква пропускается.
> **Лемма 4.** Спроецированное слово сортирует спроецированный вход.
> **Доказательство.** После каждого шага новый видимый вектор совпадает с
> исходным текущим вектором после удаления помеченных атомов. ... □
> Проекция коммутирует с растяжением сохранённых атомов. ... Длина
> спроецированного слова не больше исходной при любых длинах. Для аффинных
> цен это даёт неувеличение каждого сохранённого коэффициента ...
> Базовая цена пересчитывается ... Проекция принимается только после
> проверки нового строгого неравенства (7), с учётом сравнительной экономии (11).

Repository: `project` (`lrx_m.py:462-485`, `lrxm8.py:454-477`). Child costs
are always recomputed by `Profile` on the projected word, and never inherited
from the parent.

### Section 7 resource search (lines 387-434)

> Для k=1,2,3 используется ресурсный поиск слов с |W| <= 30+6k и beta_j <= 6.
> ... Для свободно сокращённого слова без LR, RL, XX положим
> beta_j = 3A_j + B_j - 2F_j ... [increment table, lines 410-415] ...
> Все приращения неотрицательны: ветвь с ресурсом выше шести можно
> отбросить. ... Удаление циклической фазы ... Отсечение доминируемого
> суффикса тоже допустимо.

### Uses in the finite part (lines 472-498, 529-534)

Nine blocks: all 8! orders are checked directly. For nine down to five
blocks, Lemmas 3-4 cover families by projection. There are 4088
reverse-order reference trees, whose transfer domains were re-audited. The
four-block complement is closed by 262,499 comparison mixtures and 14 trees.
The closing sentence says: "Для каждого имеется сертификат, к которому
применяются леммы 1--4 и условия (7)--(8)."

## 2. Every place where 8, n = 8 + r, T_8, 6 or 8! enters (sections 5-9)

Class (a): notational, replace by the m version. Class (b): general with an
added argument. Class (c): genuinely m = 8 (finite data, enumeration, count).
Sections 1-4 were classified in Session 27.

| Lines | Text | Where used | Class |
|---|---|---|---|
| 286-344 | Lemma 3, (9), (10), (11), row format | transfer | no constant at all |
| 343 | "применяет (7) или (8)" | transfer rows | (a), via Session 27 4.4-4.5 |
| 322-338 | stretching paragraph for (11) | transfer at all lengths | (b): m-free, argument completed in 4.3 |
| 350-372 | Lemma 4, commutation, non-increase | projection | no constant; commutation (b), see 4.5 |
| 373-377 | "бюджет при уменьшении числа блоков тоже меняется", "(7)" | projection acceptance | (a): T_m(m+k') for the child's k' |
| 387-388 | `|W| <= 30+6k`, `beta_j <= 6` | resource search | (a): T_m(m+k) and m-2 |
| 392-396 | `beta_j = 3A_j + B_j - 2F_j` | resource search | (b): m-free derivation in 4.6 |
| 403-421 | increment table; "первый элемент равен единице" | resource search | m-free (label 1 is first in the root for every m) |
| 422-425 | "ресурс выше шести", "до 30+6k" | pruning | (a) |
| 427-434 | cyclic phase, dominated suffixes | pruning | m-free |
| 438-455 | 362880 / 1814400 / 6652800 bases; exceptions | k <= 3 enumeration | (c) |
| 472-479 | "все 8! порядков", 4088 trees | nine to five blocks | (c) |
| 481-498 | 20341007, 262513, 262499 mixtures, 14 trees | four blocks | (c) |
| 504-527 | union table | coverage | (c) |
| 529-534 | "леммы 1--4", `30+6 sum u_j = 6n-18` | conclusion | (a) budget; coverage (c) |

## 3. Step-by-step walk through the manuscript's proofs

**Lemma 3.** Step 1: the comparator at window positions (j-1, j) changes
only H(j, .) (line 309). Step 2: formula (10) for the new value (line 312).
Step 3: (10) is monotone in both arguments and is the maximum achievable by
permuting the pair, so dominance survives any swap on Q (lines 314-316).
Step 4: the final Q is the identity with H = min(j, s), which is the maximum,
so P ends sorted (lines 317-318). Step 5: each performed swap removes one
inversion (lines 318-319). No m appears. Two points are left implicit, and
4.2 states them. First, the rank identity at the end means the physical
root, because ranks are defined from the reference's final layout. Second,
zero ranks stay ascending, so the comparison word never swaps two zeros.
That second point matters for later pricing by Lemma 1.

**Formula (11).** Step 1: hypothesis #X(W) = inv(Q) (line 322). Step 2:
stretching atom j adds sigma_j z_j inversions (lines 323-326). Step 3: the
transferred length is (11) "by Lemma 3" (lines 326-330). Step 4: (9) and
the cut survive stretching (lines 335-338). No m appears. Three gaps are
filled in 4.3. The rotation count of the lifted reference needs
A_j = sigma_j(Q), which the manuscript does not state; the checker tests it,
and 4.3 shows it follows from step 1. Step 4 is asserted in one sentence.
"Exact price" holds under the same-sign condition only; in general (11) is
an upper bound.

**Lemma 4.** A per-letter invariant, three cases (lines 358-364). Complete
and m-free.

**Commutation and non-increase (lines 366-371).** Asserted, not proved.
Neither the repository nor the manuscript's acceptance rule (lines 373-377)
relies on them, because child costs are recomputed. They are proved in 4.5
for completeness.

**Section 7.** The formula follows from the macros (lines 394-396). The
table is obtained by subtracting the resource before and after a letter
(lines 418-419). Non-negative increments justify pruning (lines 421-422).
Relabelling and dominance justify the quotients (lines 427-434). None uses m.

## 4. General-m statements and proofs

Fix m >= 2. A base Q is a vector of the m labels and some zero atoms,
N = |Q|. A sorting word W for Q never swaps two zeros (a geodesic never
does, since that swap is the identity).

### 4.1 Physical model, window and ranks

Positions are Z_N, the cursor c starts at 0, `L`: c -> c+1, `R`: c -> c-1,
and `X` exchanges the contents of c and c+1. The visible vector is
`(a_c, a_{c+1}, ...)`. This is `run` in `lrx_m.py:45-60`. The cursor path
depends on W only, not on the contents. Let f be the final cursor. A cut
kappa is a position such that no `X` of W is applied with c = kappa - 1.
Window index w(p) = p - kappa mod N. Every `X` acts on window indices
(w, w+1) with 0 <= w <= N-2.

For a vector V with the same zero positions as Q, the rank sequence
rho_V on window indices is defined as follows. A label x has rank
f + x - 1 - kappa mod N. The zeros, in window order, take the zero targets
{f + m + i - kappa mod N}, sorted increasingly. rho_V is a permutation of
{0, ..., N-1}. If after running a word the contents have rank sequence equal
to the identity and the cursor is f, the visible vector is the root.

Since W sorts Q and never swaps two zeros or across the cut, the zero atoms
keep their window order. So at the end, the i-th zero sits on the i-th zero
target, and rho_Q is transformed into the identity by the transpositions of
W. Zero atoms of P and Q with the same window index have the same rank,
since both take zero targets in window order from the same positions.

### 4.2 Lemma 3 at general m

Statement: let W sort Q, never swap two zeros, and kappa be a cut. Let P
have the zeros of Q and satisfy rho_P ⪯ rho_Q in (9). Run W on P with every
`X` replaced by "swap iff the pair is descending in rho_P". Then:
(a) the result is the root, with final cursor f; (b) exactly inv(rho_P)
swaps are performed; (c) no swap exchanges two zeros; (d) the resulting
word has length rot(W) + inv(rho_P).

Proof. Only `X` changes contents, and an `X` at window pair (w, w+1)
changes only H(w+1, .). For the comparator on P,
`H'_P(w+1,s) = H_P(w,s) + [min(P_w,P_{w+1}) < s] = min(H_P(w,s)+1, H_P(w+2,s))`.
For the unconditional swap on Q,
`H'_Q(w+1,s) = H_Q(w,s) + [Q_{w+1} < s] <= min(H_Q(w,s)+1, H_Q(w+2,s))`.
The right side is monotone, so H_P >= H_Q persists. At the end rho_Q is the
identity, so H_Q(j,s) = min(j,s). Every sequence has H(j,s) <= min(j,s), so
H_P(j,s) = min(j,s) for all j and s, which forces the identity. By 4.1 this
is the root, proving (a). A performed comparator swaps an adjacent
descending pair, so inv drops by exactly 1; it ends at 0, proving (b).
Zero ranks start ascending in window order, and a comparator never reverses
an ascending pair, proving (c). (d) is immediate. Nothing depends on m. □

By (c), the comparison word is a legal input to Lemma 1. Pricing it
directly by `Profile` is therefore an alternative to (11); `lift_task` and
`build_frozen.py` do exactly that.

### 4.3 Formula (11) at general m

Hypotheses: those of 4.2, plus #X(W) = q = inv(rho_Q), and one picked zero
atom per block, with the same picks for P.

Claim A: A_j = sigma_j(Q) for every picked j. Each swap changes inv by ±1
and inv goes from q to 0 in q swaps, so every swap of W on Q is descending.
A pair (zero j, label a) is swapped only while it is inverted, and never
again after, since a second swap would create an inversion. Initially
non-inverted pairs are never swapped. So the number of swaps involving j,
A_j, equals sigma_j(Q).

Claim B: for z >= 0, let Qz = E_z(Q), Pz = E_z(P) and Wz = lift_z(W) (the
Lemma 1 word in the normal form of (4)). Then:

1. Wz sorts Qz and never swaps two zeros (Session 27, 4.1).
2. The physical boundary kappa_z, before the image of atomic position
   kappa, is a cut for Wz. In the fixed-position model, an atomic swap of
   adjacent atoms keeps the union of their two physical intervals fixed.
   Every swap of its macro, `X`, `L^z X (RX)^z` or `X (LX)^z R^z`, exchanges
   the label with a zero of the block, strictly inside that union. Atom
   boundaries not at a swapped atomic edge therefore never move. The atomic
   edge at kappa is never swapped, so kappa_z is never crossed.
3. rho_{Qz} and rho_{Pz} arise from rho_Q and rho_P by the same operations.
   Stretching picked atom j (window index w, rank v, equal in P and Q by 4.1)
   by one cell inserts a new entry of rank v + 1/2 at index w + 1, then
   renumbers. Indeed, the final layout of Wz is the expansion of the atomic
   final layout, and zero cells keep window order. For the inserted
   sequence, H'(j', s') = H(j'', phi(s')) + [j' > w+1][s' > v+1], with
   j'' = j' - [j' > w+1] and phi(s') = s' - [s' > v+1]. The correction term
   is the same for P and Q, so rho_{Pz} ⪯ rho_{Qz}.
4. inv(rho_{Pz}) = inv(rho_P) + sum_j sigma_j(P) z_j, and the same for Q.
   The new entry is adjacent to atom j in position and in value, so it is
   inverted with a label exactly when atom j is. It is inverted with no
   zero, because zero ranks ascend in window order.
5. #X(Wz) = q + sum_j A_j z_j (one `X` per macro plus z_j in its core),
   which equals inv(rho_{Qz}) by Claim A and item 4.

Lemma 3 applied to (Qz, Pz, Wz, kappa_z) gives a word sorting Pz of length
`rot(Wz) + inv(rho_{Pz})`. With `rot(Wz) = F_Q(z) - q - sum_j A_j z_j`:

    length = F_Q(z) - inv(Q) - sum_j sigma_j(Q) z_j + inv(P) + sum_j sigma_j(P) z_j
          <= B_Q - inv(Q) + inv(P) + sum_j (beta_j(Q) - sigma_j(Q) + sigma_j(P)) z_j,

using `F_Q(z) <= B_Q + sum beta_j z_j` (Session 27, 4.2). Equality holds
when W is same-signed. Pz is the family vector of P's family with block
lengths u = 1 + z (or o + z at a refined base). No step uses m. □

Remark (lines 332-335). sigma_j = (h - H_lab) + (s - H_lab), where h labels
precede the zero, s labels have smaller rank, and H_lab counts labels that
are both. Zeros contribute equally to H_P and H_Q at every (j, s), because
they have the same positions and the same ranks. So (9) gives
H_lab(P) >= H_lab(Q) at the zero's window index and rank, hence
sigma_j(P) <= sigma_j(Q), so (11) never has larger slopes than the
reference. This is not needed for soundness, because the coefficients are
recomputed.

### 4.4 Transfer with refinement, in mixtures and in trees

A row with origin o uses Q_r = refine(Q, o) and P_r = refine(P, o), which
have the same zero positions, with picks one per block. For u >= o, 4.3 at
z = u - o bounds d(v_P(u)) by the (11) cost C_i(u). Session 27's 4.4 (o = 1)
and 4.5 (o <= l) use only that each row gives a sorting word of length at
most its affine cost on the box. So (7) and (8) apply verbatim with
T_m and slope m - 2. Rows of one mixture may use different references and
cuts: each row gives its own sorting word, and Lemma 2 only averages
lengths. m-free.

### 4.5 Lemma 4 at general m, and the paragraph after it

Statement: let W sort a base V with no zero-zero swap, and D a set of zero
atoms whose deletion leaves at least one zero. Keep `L` iff the first atom
is not in D, `R` iff the last atom is not in D, and `X` iff both first
atoms are not in D. The projected word sorts V minus D and never swaps two
zeros.

Proof: for each letter, the visible vector after deletion evolves as
follows. For `L`/`R` moving a deleted atom, the deletion is unchanged. For
`X` involving a deleted atom, the order of the remaining atoms is unchanged.
Otherwise the same letter acts on the projection. The root minus D is the
child's root. A kept `X` acts on the same two kept atoms, so it is not a
zero-zero swap. m-free. □

Commutation (lines 366-368), made precise. Let NF(w) replace each rotation
run between consecutive `X` letters by its net power. Take picks on kept
atoms, stretch z on them, and leave deleted atoms at unit length. Then
`NF(proj(lift_z W)) = NF(lift_z(proj W))`. Proof: deleted atoms are unit
length, so a swap with one lifts to a lone `X`, which projection removes.
The macro of a swap between a label and a kept picked block moves only kept
cells, so projection keeps it intact. For a rotation run from a given
cursor, the signed number of kept cells it passes depends only on its net
displacement (it telescopes on the universal cover). So projecting and then
normalising agrees with normalising, projecting, and normalising. □

Consequence (lines 369-371): `F_child(z) = |NF(proj(lift_z W))| <=
|lift_z W| = F_parent(z)` for all z >= 0. When both words are same-signed,
both sides are affine and exact, so `B_child <= B_parent` and every kept
slope does not increase. The repository never uses this; `project` output
is always re-priced.

### 4.6 Section 7 resource formula at general m

Let W be freely reduced (no `LR`, `RL`, `XX`), with every zero its own
picked atom. Then every rotation run between swaps is one-directional. In
(4), c_gj collects three things: ±1 per pass of zero j through the front
(B_j passes in total, sign of the run); +1 at the end of the run before a
swap on (0_j, a); and -1 at the start of the run after a swap on (a, 0_j).
The letter at such a junction is always a pass of j. The `R` before `X` on
(0_j, a) brought j to the front, and the `L` after `X` on (a, 0_j) moves j
off the front. So a junction term either adds to |c_gj| (no cancellation)
or cancels one pass (an `RX` or `XL` junction, counted by F_j). Hence
`sum_g |c_gj| = B_j + A_j - 2F_j` and `beta_j = 3A_j + B_j - 2F_j`. The
increment table is the difference of this resource, corrected by h_j,
before and after a letter. The final h_j = 0 because label 1 is first in
the root, for every m. For a freely reduced word, `B_W = |W|`. So a search
hit with `|W| <= T_m(m+k)` and all resources `<= m-2` is a one-row
certificate for (7). No step uses m; only the thresholds do, as class (a).
The pruning arguments (lines 421-434) are relabelling and monotonicity
statements with no m.

## 5. Exact-table sanity checks

Script: `autoresearch/checks-lemma1/lemma34_tables_check.py`. It is
read-only and uses the stdlib, `integrations/lrx_m.py`, and the table reader
and random-tie geodesic from `lemma1_tables_check.py`. The complete tables
used are (9,1)..(9,6), (10,2) and (10,3); (10,1) does not exist, so m = 10
bases have at least 2 zeros. Ranks, prefix counts, the comparator run with
per-step checks of (9) and (10), the projection with its per-letter
invariant, sigma, inv and (11) are re-implemented in the script from the
manuscript text. They are compared with `lrx_m.Reference.transfer` and
`lrx_m.project`.

- **Part T** builds a reference Q (unit or refined base), W (random-tie
  geodesic, or one letter plus a geodesic), and a random cut with
  #X = inv(Q). About one (family, word) attempt in three has such a cut.
  P is built by 1-4 inversion-reducing label transpositions of rho_Q
  ("bruhat"), or as a random label order filtered by (9) ("filter"). For
  every z within table range it runs lift_z(W) as comparator on E_z(P). It
  checks E_z(P) ⪯ E_z(Q), the rule (10) at every comparator step, the
  reference being inversion-exact, the result sorting (also by literal
  execution), swaps = inv, length <= (11) (= when same-signed), and
  d(E_z P) <= length.
- **Part T2** is the same, with a reference obtained by projecting a
  geodesic, which is the route of the m = 8 package's union audit.
- **Part P** takes a parent word and a random nonempty proper deletion of
  zero atoms, including single atoms of refined blocks. It checks the
  per-letter invariant, sorting, `lrx_m.project` = own projection, and the
  commutation of 4.5 by normal forms. It also checks
  d(E_z child) <= F_child(z) <= B_child + beta_child.z.
- **Part R** checks `beta_j = 3A_j + B_j - 2F_j` and the increment table
  against `Profile(..., each_zero=True).beta` on geodesics.
- **Negative control:** a random P that is not ⪯ Q, run by comparison at
  z = 0.

Honest scope: as in Session 27, "d <= length" follows from "the word
sorts". The table comparison therefore cross-checks the executor, the
pricing, the rank construction and the tables. The per-step (10) checks,
the dominance after stretching, and inv = inv(P) + sigma.z are direct
checks of the proof's intermediate claims.

Output (`python autoresearch/checks-lemma1/lemma34_tables_check.py`, seed
260926, about 11 s):

```
Part T  Lemma 3 + (11) against exact distances (seed 260926)
  bruhat      m=9  instances 200
  bruhat      m=10 instances 140
  bruhat-ref  m=9  instances 45
  bruhat-ref  m=10 instances 60
  filter      m=9  instances 45
  filter      m=10 instances 20
  pre         m=9  instances 30
  instances per m: m=9 320, m=10 220 ; reference attempts (family,word) per m: {9: 930, 10: 918}
  stretched points z tested 4555 ; comparison X-steps checked against (9),(10) 90923
  q = inv(Q) cuts: A_j = sigma_j(Q) holds 2965, fails 0
  sigma_j(P) <= sigma_j(Q) (manuscript line 335): holds 540, fails 0
  failures: 0
  slack (11)(z) - d(E_z P): 0:208 1:85 2:605 3:179 4:619 5:243 6:729 7:238 8:522 9:167 10:338 11:109 12:171 13:54 14:87 15:25 16:56 17:27 18:28 19:9 20:13 21:5 22:9 23:5 24:4 25:5 26:1 28:5 29:2 30:2 31:1 33:1 34:1 41:1 42:1
  negative control (P not <= Q, z=0): comparison run fails to sort 540, sorts anyway 0

Part T2 projected reference then transfer (m=9)
  instances {('proj+trans', 9, 3): 15, ('proj+trans', 9, 4): 15, ('proj+trans', 9, 5): 15, ('proj+trans', 9, 6): 15} ; points 724 ; X-steps 14657
  A_j = sigma_j(Q) holds 111, fails 0 ; failures: 0
  slack (11)(z) - d(E_z P): 0:27 1:29 2:63 3:29 4:89 5:26 6:80 7:40 8:84 9:24 10:42 11:26 12:47 13:16 14:27 15:8 16:20 17:3 18:7 19:2 20:9 21:9 22:2 23:2 24:3 25:2 26:3 27:1 28:1 34:1 35:1 41:1

Part P  Lemma 4 projection against exact distances
  pre   m=9  instances 32
  pre   m=10 instances 20
  ref   m=9  instances 40
  ref   m=10 instances 60
  ref3  m=10 instances 40
  unit  m=9  instances 200
  unit  m=10 instances 80
  instances per m: m=9 272, m=10 200 ; parent letters with invariant checked 21868 ; child points z 3766
  proj(lift_z W) vs lift_z(proj W): normal forms differ at 0 points; raw words differ at 2187 (lift writes net rotations)
  side claims (not used for soundness): base non-increasing 472/472, slopes non-increasing 472/472, F_child(z) <= F_parent(z) 3766/3766
  failures: 0
  slack (B_child + beta_child.z) - d(E_z child): 0:942 1:222 2:653 3:176 4:394 5:165 6:229 7:104 8:135 9:62 10:114 11:48 12:84 13:31 14:58 15:35 16:48 17:25 18:24 19:18 20:31 21:21 22:10 23:13 24:16 25:14 26:7 27:7 28:8 29:2 30:13 31:6 32:7 33:2 34:3 35:1 36:3 37:2 38:8 39:3 40:3 41:3 42:3 43:1 44:2 45:1 46:1 47:3 48:1 53:1 56:1 68:1 83:1

Part R  section 7 resource formula beta_j = 3A_j + B_j - 2F_j and increment table (lines 392-425)
  words: m=9 200, m=10 120 ; zero atoms 980 ; failures: 0

10.3 s
RESULT: PASS (0 violations)
```

Reading:

- **Transfer:** 540 instances with 4,555 stretched points and 0 violations.
  The (10) rule and dominance held at all 90,923 comparator steps.
- **Claim A** held at all 2,965 inversion-exact cuts (plus 111 in T2).
- **Transferred words are shortest** at 208 of 4,555 points.
- **Negative control:** every one of 540 non-dominated P fails to sort, so
  the hypothesis (9) is not vacuous.
- **Projection:** 472 instances, 3,766 stretched child points, 0 violations.
  The normal-form commutation of 4.5 held at every point. The raw words
  differ only because `Profile.lift` writes net rotations.
- **Resource formula and table:** held for all 980 zero atoms.

Finite checks validate finite cases only.

## 6. Repository certificates and their conditionality

Found by searching all `.py` files for `Reference(`, `.transfer(`,
`prefix_dominates`, `comparison_word` and `project(`, and reading every hit.

**m >= 9: no dependence on Lemma 3, Lemma 4 or (11).**

- **Lift task (Session 11, 84 audited m = 9 families and all engine and
  control certificates).** `lift_evaluator.py` uses only `Profile`,
  `literal_lift_check`, `z_samples` and `mixture_criterion`
  (`lift_evaluator.py:269-292`). Child words are replayed on the child unit
  base and priced by Lemma 1. Lemmas 3-4 enter only when building the m = 8
  parents (`build_frozen.py` materialize_rows, `add_tree_stratum.py`). There
  they produce literal parent words that `lift_task.plain_row` re-prices by
  `Profile`, and parent weights are hints only. Conditional on Lemma 1 and
  (7) only.
- **Bound campaigns and trees (Sessions 15-17).** `bound_evaluator.py` and
  `bound3_*.py` use `Profile`, refinement, `mixture_criterion` and
  `leaf_criterion`. There is no transfer or projection. Conditional on
  Lemma 1, (6), (7) and (8) only.
- **Reversal, word_C, word_M and middle-band certificates (Sessions 19-26),
  and sort-m9 (Session 14, per-state words).** Literal words only.

So this audit removes no m >= 9 conditionality, because none existed. The
remaining conditionality of all m >= 9 certificates is Session 27's: the
general-m Lemma 1, (4)-(8) proofs, written and unreviewed.

**m = 8: these results use Lemmas 3, 4 and (11).**

- **Session 8:** 76 projected-mixture certificates. `projected_mixtures.comparison`
  prices by (11) and checks (7).
- **Session 9:** 5 policy-generated certificates, through the same code.
- **The supplied nine-gap theorem check:** 40,320 comparison replays in
  `nine_gap_audit.py`.
- **Session 10:** the replication of the group's full m = 8 package
  (k = 4..9 files via `Reference.transfer`, k5-mask302 via Lemma 4).

Before this note these relied on the manuscript's proof sketches. They now
have complete written proofs (4.2-4.5, valid for every m, in particular
m = 8). The status is "proof written, unreviewed", pending the same human
review as Session 27. The section 7 low-block enumerations (k <= 3) are
m = 8 finite data. Their derivation (4.6) is now written out, and the
repository replicated them only partly (Session 10).

**Future use at m >= 9.** Any later m >= 9 pipeline that prices through
(11) or accepts projected certificates would be conditional on 4.2-4.5.
This is the same review-pending status as Lemma 1, and not a further gap.
Two defaults need care in `lrx_m.py`. `mixture_criterion` and
`leaf_criterion` default to m = 8, which is conservative, as Session 27
noted. `Reference.transfer` needs no m.

## 7. What would still be needed

- **Human review of 4.2-4.6.** The proofs are elementary. The step most
  worth a careful read is 4.3 item 2 (the cut is not crossed after lifting,
  argued in the fixed-position model) together with item 3 (the insertion
  form of stretched ranks).
- **Nothing at m >= 9 waits on this audit.** Coverage of all families at
  any m >= 9 is the open part, and the general conjecture remains open.
- **The m = 8 finite part is not re-audited here.** Sections 7-8 of the
  manuscript are the group's; the repository's replication status is as
  recorded in Session 10.
