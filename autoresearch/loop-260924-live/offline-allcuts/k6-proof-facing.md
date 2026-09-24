# Why cut 11 closes one six-block family

This is a named-family construction, not a general cut-selection theorem.
The unit-block state for `k6-mask315-order31970` is

    (0,7,0,3,4,0,5,0,1,0,6,2,8,0).

The four-cut seed tries cuts 0, 3, 7, and 10. Its nearest prefer-right word at
cut 10 has 85 letters (35 X swaps) and direct slopes `(8,9,15,5,2,7)`.
Trying the adjacent cut 11 changes the linearization just before the `2` at
physical position 11. With prefer-right ties, it gives a complete 70-letter
word (28 X swaps; 28 L and 14 R) with direct slopes `(6,7,10,7,4,5)`:

    LXLXLXLLXRXLLLXRXRXRXRXRXRRRRXLXLXLXLXLXLXLXLLLLXRXRXRXRXLLLLLLXLXLXLX

The new word trades worse slopes at blocks 4 and 5 than the cut-10 word for
15 fewer letters and improvements at blocks 2, 3, and 6. The old finite-pool
optimum had tight slopes at blocks 2, 5, and 6, with exact dual multipliers
`(1/3,91/27,8/9)`. Its reduced-cost test is

    B + (1/3) beta_2 + (91/27) beta_5 + (8/9) beta_6 - 2561/27.

The cut-10 word scores `55/9 > 0`; the cut-11 word scores `-124/27 < 0`.
That negative value makes the new word useful to reoptimize the mixture. It
does not by itself certify the family; the exact weights below do.

| Word identity (SHA-256 prefix) | Origin | Weight | B | beta |
|---|---|---:|---:|---|
| `74c3f7e3ec27e647` | fixed catalog, direct repricing | 11/34 | 56 | (3,0,6,9,11,2) |
| `6930ed1a6f5b9a52` | fixed catalog, direct repricing | 5/34 | 66 | (0,3,9,12,8,1) |
| `aa3038a4e1c9f9d5` | fixed catalog, direct repricing | 13/68 | 74 | (10,13,4,1,2,11) |
| `070f046c47753cbb` | fixed catalog, direct repricing | 4/17 | 75 | (10,10,4,1,2,11) |
| `e1a7932f3930dcb3` | cut-11 prefer-right word above | 7/68 | 70 | (6,7,10,7,4,5) |

The weighted base is `1136/17 < 67`, with margin `3/17`; weighted slopes are
`(199/34,6,6,99/17,6,6)`. By the direct-word expansion and exact rational
mixture criterion, for every positive six-block length vector at least one
lifted support word has length at most `T_8(n)=30+6r`. The other four words,
all weights, and the full literal word appear in the trusted evaluation
`3fcc0f0d23ced3f0-evaluation.json`; the separate finalist audit replayed
the support and its nonunit expansions. Selecting cut 11 worked for this
state; the data do not establish an effective cut rule for other families.
