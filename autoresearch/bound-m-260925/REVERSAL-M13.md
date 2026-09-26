# Reversal with two outer zeros: m-uniform certificates from m = 13 on

Date 2026-09-26. Offline construction. There were no provider calls, no tables, no LLM-generated code and no commits.
Lemma 1, the cost formulas (4)-(6) and criteria (7)/(8) are the research group's (m=8 manuscript).
`integrations/lrx_m.py` and `integrations/bound3_evaluator.py` apply them with m as a parameter.
The main conjecture stays open.

The family is (m..1){0,m}, mask 1 | 1<<m. Its unit state is u_m = (0, m, m-1, ..., 1, 0), with
T = m(m+1)/2 + m - 2 and slope bound s = m - 2. REVERSAL-WORDS.md certified it at m = 9..12 and left
m = 13..16 open, with gap 6/5 at m = 13.

- Script: `checks/reversal_m13.py`, which refuses to overwrite and runs in 2 s.
- Data: `checks/reversal-m13-words.json`.
- Reproduce with `PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_m13.py`.

## 1. Result

**The family is CERTIFIED at every m = 9..40 by one generator, `word_C(m, a)`.** Each row passed
`bound3_evaluator.score_output` on the single root leaf with unit origins. Each CERTIFIED row was then
confirmed by the independent `bound3_audit.audit_claim`, which printed `[True, 'ok']` for all 32 rows.
Each row was also re-checked with `lrx_m.mixture_criterion(m=m)`.

- **Odd m.** One word certifies: a = (m-3)/2, length T - 1, slopes (m-2, m-3). The evaluator reports lhs -1.
- **Even m.** Two words with weights 1/2, 1/2 certify: a = (m-2)/2 has length T - 1 and slopes (m-1, m-2),
  and a = (m-4)/2 has length T + 1 and slopes (m-3, m-4). The mean is B = T with slopes (m-2, m-3),
  so lhs is 0.

No tree and no refined origin is needed. The root leaf [1, inf)^2 certifies directly. So ideas (2) and (3)
of the task, double crossings and refined-origin trees, were not needed and were not run.

| m | T | s | words (a) | lengths | support (weight, B, beta) | status | lhs | audit |
|---|---|---|---|---|---|---|---|---|
| 13 | 102 | 11 | 5 | 101 | (1, 101, (11,10)) | CERTIFIED | -1 | agree |
| 14 | 117 | 12 | 6, 5 | 116, 118 | (1/2, 116, (13,12)), (1/2, 118, (11,10)) | CERTIFIED | 0 | agree |
| 15 | 133 | 13 | 6 | 132 | (1, 132, (13,12)) | CERTIFIED | -1 | agree |
| 16 | 150 | 14 | 7, 6 | 149, 151 | (1/2, 149, (15,14)), (1/2, 151, (13,12)) | CERTIFIED | 0 | agree |
| 17 | 168 | 15 | 7 | 167 | (1, 167, (15,14)) | CERTIFIED | -1 | agree |
| 18 | 187 | 16 | 8, 7 | 186, 188 | (1/2, 186, (17,16)), (1/2, 188, (15,14)) | CERTIFIED | 0 | agree |
| 19 | 207 | 17 | 8 | 206 | (1, 206, (17,16)) | CERTIFIED | -1 | agree |
| 20 | 228 | 18 | 9, 8 | 227, 229 | (1/2, 227, (19,18)), (1/2, 229, (17,16)) | CERTIFIED | 0 | agree |

- **m = 9..12 and m = 21..40.** These rows have the same shape and all are CERTIFIED with audit agreement.
  The full rows are in the JSON under `certificates`.
- **Pool scan.** At m = 9..20 the LP was also given the whole family a = 0..m, which is m + 1 words.
  It returns the same support, so for this generator the pair or single word above is what the LP picks.
- **Shortest words at small m.** At m = 9, 10, 11 the certificate words of length T - 1 are among the
  enumerated shortest words of REVERSAL-WORDS.md. The m = 10 word of length T + 1 is not.
  None of the new words equals word_A, word_B or word_E.

Like every certificate in this run, these are conditional on the group's Lemma 1 and criterion (7) with m
as a parameter. They cover this one family only. A certified row proves d(v) <= T_m(n) for every state
of the family at every block length.

## 2. Why A and E failed and C works

The traces of word_E and word_A on fixed cells show two different ways of moving labels past the zero block.

- **word_E moves the zeros through labels.** Its long R sweep carries zero b across labels 1..6. Its
  shrinking zigzag carries zero a. A zero carried through a label costs 2 for the swap plus 1 for the
  cursor's return across the block. That gives beta = 3a + 1 with a about m/2, so the slope is about 3m/2.
- **word_A moves labels through the zeros.** A label carried across the block by a continuing sweep
  costs exactly 2 per zero, because the Lemma 1 crossing terms cancel inside the sweep. But only 4 labels
  cross, and the remaining m - 4 labels are reversed in place by one zigzag. That costs about (m-4)^2
  letters, so the length overshoots T by about (m-10)^2/2.
- **word_C balances the two.** It carries a, about m/2 - 1, labels across the zeros inside a zigzag core
  that contains the zero block, so beta = (2a+1, 2a). It reverses the remaining r = m - a labels in place
  with a second zigzag. The length is about a^2 + r^2 + O(m). That is a quadratic in a whose minimum sits
  within one unit of T - 1 at a = (m-3)/2 for odd m and a = (m-2)/2 for even m.

Length minus T over the whole generator family, all words replayed:

| m | a = 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|
| 13 | +11 (7,6) | +3 (9,8) | **-1 (11,10)** | -1 (13,12) | +3 (15,14) | +11 | +23 |
| 14 | +17 (7,6) | +7 (9,8) | **+1 (11,10)** | **-1 (13,12)** | +1 (15,14) | +7 | +17 |
| 15 | +23 | +11 (9,8) | +3 (11,10) | **-1 (13,12)** | -1 (15,14) | +3 | +11 |
| 16 | +31 | +17 (9,8) | +7 (11,10) | **+1 (13,12)** | **-1 (15,14)** | +1 | +7 |

Bold marks the certificate words. The slope is (2a+1, 2a) throughout, except at a = 1 for even m.

## 3. Generator source

The generator is a pure stdlib function of (m, a), copied verbatim from `checks/reversal_m13.py`.

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

The simulation only emits letters. The word is then replayed independently by `lrx_m.run_naive` and
`lrx_m.run`. The sweep form of the m = 13 word is

    X1(0) R2 L3 R4 L5 R7(1,1,1,1,1,5,1) L2 R3 L4 R5 L6 R6(1,1,1,1,1,1,2~)

Core 1 is the sweeps of sizes 2..6 carrying 13, 1, 12, 2, 11 across the zeros. After a walk of 5,
core 2 is the zigzag of sizes 1..7 on labels 3..10. A final R walk of 2 follows.

The certificate words at m = 13..16:

```
m=13 a=5 (101)  XRXRXLXLXLXRXRXRXRXLXLXLXLXLXRXRXRXRXRXRRRRRXRXLXLXRXRXRXLXLXLXLXRXRXRXRXRXLXLXLXLXLXLXRXRXRXRXRXRXRR
m=14 a=6 (116)  XRXRXLXLXLXRXRXRXRXLXLXLXLXLXRXRXRXRXRXRXLXLXLXLXLXLXLLLLLXRXLXLXRXRXRXLXLXLXLXRXRXRXRXRXLXLXLXLXLXLXRXRXRXRXRXRXRRR
m=14 a=5 (118)  XRXRXLXLXLXRXRXRXRXLXLXLXLXLXRXRXRXRXRXRRRRRRXLXRXRXLXLXLXRXRXRXRXLXLXLXLXLXRXRXRXRXRXRXLXLXLXLXLXLXLXRXRXRXRXRXRXRXRR
m=15 a=6 (132)  XRXRXLXLXLXRXRXRXRXLXLXLXLXLXRXRXRXRXRXRXLXLXLXLXLXLXLLLLLXLXRXRXLXLXLXRXRXRXRXLXLXLXLXLXRXRXRXRXRXRXLXLXLXLXLXLXLXRXRXRXRXRXRXRXRRR
m=16 a=7 (149)  XRXRXLXLXLXRXRXRXRXLXLXLXLXLXRXRXRXRXRXRXLXLXLXLXLXLXLXRXRXRXRXRXRXRXRRRRRRXLXRXRXLXLXLXRXRXRXRXLXLXLXLXLXRXRXRXRXRXRXLXLXLXLXLXLXLXRXRXRXRXRXRXRXRRR
m=16 a=6 (151)  XRXRXLXLXLXRXRXRXRXLXLXLXLXLXRXRXRXRXRXRXLXLXLXLXLXLXLLLLLLXRXLXLXRXRXRXLXLXLXLXRXRXRXRXRXLXLXLXLXLXLXRXRXRXRXRXRXRXLXLXLXLXLXLXLXLXRXRXRXRXRXRXRXRXRRR
```

## 4. Exact replay checks

Every check below was run by `reversal_m13.py`.

- **Replay.** Every word of the scan, a = 0..m at m = 9..20, sorts u_m under both `run_naive` and `run`.
  No parameter value failed.
- **Evaluator.** `score_output` runs `lrx_m.Profile`, which rejects any zero-zero swap. It then checks the
  literal lifted execution at z = 0, e_j, 2e_j, e_1+e_2 and (1,1), checks the box points of the support,
  and solves the exact LP.
- **Evaluator self-check.** `leaf_criterion` re-checks the evaluator's LP optimum internally, and would
  assert on a disagreement.
- **Audit.** `bound3_audit.audit_claim` uses the independent lrxm8 checker at M = m. It re-parses the raw
  output, replays each support word with literal lifts, and checks criterion (8) directly and through the
  affine map to m = 8. It agrees on m = 9..40.
- **Closed forms, m = 9..200, replay only.** Every certificate word sorts u_m. Each is same-sign with
  A = (a, a) and length = base.
  - For odd m, the length is T - 1 and beta = (m-2, m-3).
  - For even m, a = (m-2)/2 gives T - 1 with beta = (m-1, m-2), and a = (m-4)/2 gives T + 1 with
    beta = (m-3, m-4).
  - There were 0 failures (`closed_form_replay_m9_200`).

So criterion (7) holds with the same margin at every m = 9..200: Bbar = T - 1 or T, and betabar = (m-2, m-3).
Only m = 9..40 were passed through the evaluator and the audit.

## 5. Conjectures (not proved; separated from the computed facts above)

1. **All m >= 9.** word_C certifies (m..1){0,m} for every m >= 9, with the same weights. This follows from
   the closed forms in section 4 if they hold for all m. They are verified by replay only for
   m = 9..200. A proof needs the letter count of word_C as a function of (m, a) and the Lemma 1 slope
   count, and both look elementary: two zigzags, one walk, one final walk.
2. **Length.** len word_C(m, a) - T = 2(a - (m-2)/2)^2 - 1 - (m mod 2)/2. This was checked by replay for
   every m = 9..60 and every a = 0..m except the single value a = 2*floor(m/2), where it fails. The
   minimum is T - 1 at a = (m-2)/2 for even m and at a = (m-3)/2, (m-1)/2 for odd m. Every step of
   2 in a away from the minimum costs about 8 letters and 4 slope units.
3. **Distance.** Together with REVERSAL-WORDS.md conjecture 1, word_C(m, (m-3)/2) for odd m and
   word_C(m, (m-2)/2) for even m would be shortest words, of length T - 1. That is exact at m = 9, 10, 11,
   where they are members of the enumerated shortest sets. It is unknown beyond m = 11.
4. **Other families.** The two-core idea generalizes: grow one core around each zero block and one core
   per remaining label arc. It may give m-uniform words for other reversal-type families. This is untested.

## 6. Limitations

- The certificates are conditional on the group's Lemma 1 and criteria (7)/(8) with m as a parameter.
  They cover the family (m..1){0,m} only.
- The evaluator and the audit were run for m = 9..40. Beyond that, m = 41..200, only replay and the
  closed-form Profile values were checked.
- Word lengths are replay-certified upper bounds. No distance beyond m = 11 is known.
- `autoresearch/bound-m-260925/.gitignore` ignores `checks/`. The new script and JSON must be force-added
  if they are to be committed.
