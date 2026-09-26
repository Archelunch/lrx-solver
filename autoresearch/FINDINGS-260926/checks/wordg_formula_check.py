"""Closed-form hypotheses for word_G(m, g) (REVERSAL-K2.md section 2): length - T and Lemma 1 slopes.

Not a proof. For every m in the range and every g where word_G is defined, this script executes word_G (imported
from reversal_k2.py), prices it with lrx_m.Profile, and tests formulas in (m, g) that were read off the data.
Each hypothesis is attached to one row of the rule table (m mod 4, row index, first-match semantics of
params_G) plus an optional sub-condition. It reports, per hypothesis, the number of (m, g) in its domain and the
exceptions. Some coarse hypotheses are included on purpose to show where they fail.

Notation: j = floor(m/4), r = m - g, T = T_m(m+2) = m(m+1)/2 + m - 2, beta = (beta_0, beta_1) with beta_0 the zero
in gap 0 and beta_1 the zero in gap g.

Stdlib only; no provider calls; writes nothing.

    PYTHONPATH=. python autoresearch/bound-m-260925/checks/wordg_formula_check.py          # m = 9..80
    PYTHONPATH=. python autoresearch/bound-m-260925/checks/wordg_formula_check.py 9 120
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrations import lrx_m as C  # noqa: E402
from reversal_k2 import RULES, RULES_TEXT, word_G  # noqa: E402


def row_of(m, g):
    j, r = m // 4, m - g
    for i, (var, cond, _) in enumerate(RULES[m % 4]):
        if cond(g if var == 'g' else r, j):
            return i
    return None


# (name, rho, row, sub-condition(m, g, j, r), formula(m, g, j, r) -> (len - T, beta_0, beta_1))
# A formula entry None means "not claimed".
ALL = lambda m, g, j, r: True  # noqa: E731
HYP = [
    # ---- m = 0 mod 4
    ('0.g1      g=1:            len-T = -1,   beta = (m-2, m-5)', 0, 0, ALL,
     lambda m, g, j, r: (-1, m - 2, m - 5)),
    ('0.g       2<=g<=j-2:      len-T = 2-g,  beta = (m-2, m-4-g)', 0, 1, lambda m, g, j, r: g <= j - 2,
     lambda m, g, j, r: (2 - g, m - 2, m - 4 - g)),
    ('0.g-top   g=j-1:          len-T = -g,   beta = (m-3, m-5-g)', 0, 1, lambda m, g, j, r: g == j - 1,
     lambda m, g, j, r: (-g, m - 3, m - 5 - g)),
    ('0.gj      g=j (j>=4):     len-T = 2-g,  beta = (m-2, m-10-g)', 0, 2, ALL,
     lambda m, g, j, r: (2 - g, m - 2, m - 10 - g)),
    ('0.r       1<=r<=j-2:      len-T = 1-r,  beta = (m-2, m-3-r)', 0, 3, ALL,
     lambda m, g, j, r: (1 - r, m - 2, m - 3 - r)),
    ('0.rj-1    r=j-1:          len-T = 1-r,  beta = (m-4, m-5-r)', 0, 4, ALL,
     lambda m, g, j, r: (1 - r, m - 4, m - 5 - r)),
    ('0.rj      r=j:            len-T = 1-r,  beta = (m-2, m-7-r)', 0, 5, ALL,
     lambda m, g, j, r: (1 - r, m - 2, m - 7 - r)),
    # ---- m = 1 mod 4
    ('1.g1      g=1:            len-T = -3,   beta = (m-2, m-5)', 1, 0, ALL,
     lambda m, g, j, r: (-3, m - 2, m - 5)),
    ('1.g       2<=g<=j-2:      len-T = 2-g,  beta = (m-2, m-2-g)', 1, 1, lambda m, g, j, r: g <= j - 2,
     lambda m, g, j, r: (2 - g, m - 2, m - 2 - g)),
    ('1.g-top   g=j-1:          len-T = 1-g,  beta = (m-3, m-3-g)', 1, 1, lambda m, g, j, r: g == j - 1,
     lambda m, g, j, r: (1 - g, m - 3, m - 3 - g)),
    ('1.gj      g=j, j>=3:      len-T = -g,   beta = (m-2, m-8-g)', 1, 2, lambda m, g, j, r: j >= 3,
     lambda m, g, j, r: (-g, m - 2, m - 8 - g)),
    ('1.gj9     g=j=2 (m=9):    len-T = 0,    beta = (7, 1)', 1, 2, lambda m, g, j, r: j == 2,
     lambda m, g, j, r: (0, 7, 1)),
    ('1.r0      r=0:            len-T = -1,   beta = (m-2, m-3)', 1, 3, lambda m, g, j, r: r == 0,
     lambda m, g, j, r: (-1, m - 2, m - 3)),
    ('1.r       1<=r<=j-1:      len-T = 1-r,  beta = (m-2, m-3-r)', 1, 3, lambda m, g, j, r: r >= 1,
     lambda m, g, j, r: (1 - r, m - 2, m - 3 - r)),
    ('1.rj      r=j:            len-T = -1-r, beta = (m-2, m-5-r)', 1, 4, ALL,
     lambda m, g, j, r: (-1 - r, m - 2, m - 5 - r)),
    # ---- m = 2 mod 4
    ('2.g1      g=1:            len-T = -1,   beta = (m-3, m-6)', 2, 0, lambda m, g, j, r: g == 1,
     lambda m, g, j, r: (-1, m - 3, m - 6)),
    ('2.gj      g=j:            len-T = -2-g, beta = (m-2, m-6-g)', 2, 0, lambda m, g, j, r: g == j,
     lambda m, g, j, r: (-2 - g, m - 2, m - 6 - g)),
    ('2.g       2<=g<=j-1:      len-T = 2-g,  beta = (m-2, m-4-g)', 2, 1, ALL,
     lambda m, g, j, r: (2 - g, m - 2, m - 4 - g)),
    ('2.r       1<=r<=j-1:      len-T = 1-r,  beta = (m-2, m-3-r)', 2, 2, ALL,
     lambda m, g, j, r: (1 - r, m - 2, m - 3 - r)),
    ('2.rj      r=j:            len-T = 1-r,  beta = (m-3, m-6-r)', 2, 3, ALL,
     lambda m, g, j, r: (1 - r, m - 3, m - 6 - r)),
    # ---- m = 3 mod 4
    ('3.g1      g=1:            len-T = -3,   beta = (m-2, m-5)', 3, 0, ALL,
     lambda m, g, j, r: (-3, m - 2, m - 5)),
    ('3.g       2<=g<=j-1:      len-T = 2-g,  beta = (m-2, m-2-g)', 3, 1, ALL,
     lambda m, g, j, r: (2 - g, m - 2, m - 2 - g)),
    ('3.gj      g=j, j>=3:      len-T = -g,   beta = (m-2, m-8-g)', 3, 2, lambda m, g, j, r: j >= 3,
     lambda m, g, j, r: (-g, m - 2, m - 8 - g)),
    ('3.gj11    g=j=2 (m=11):   len-T = 0,    beta = (9, 3)', 3, 2, lambda m, g, j, r: j == 2,
     lambda m, g, j, r: (0, 9, 3)),
    ('3.r0      r=0:            len-T = -1,   beta = (m-2, m-3)', 3, 3, lambda m, g, j, r: r == 0,
     lambda m, g, j, r: (-1, m - 2, m - 3)),
    ('3.r       1<=r<=j-1:      len-T = 1-r,  beta = (m-2, m-3-r)', 3, 3, lambda m, g, j, r: 1 <= r <= j - 1,
     lambda m, g, j, r: (1 - r, m - 2, m - 3 - r)),
    ('3.r-top   r=j:            len-T = -r,   beta = (m-3, m-4-r)', 3, 3, lambda m, g, j, r: r == j,
     lambda m, g, j, r: (-r, m - 3, m - 4 - r)),
    ('3.rj+1    r=j+1 (j>=3):   len-T = 3-r,  beta = (m-2, m-9-r)', 3, 4, ALL,
     lambda m, g, j, r: (3 - r, m - 2, m - 9 - r)),
]

# Coarse or unified hypotheses, expected to fail somewhere; reported to show exactly where.
COARSE = [
    ('C1 every rule row "2<=g<=j-1" (all m mod 4): len-T = 2-g',
     lambda m, g, j, r, i: RULES_TEXT[m % 4][i].startswith('2<=g<=j-1'), lambda m, g, j, r: (2 - g, None, None)),
    ('C2 2<=g<=j-2, all m mod 4: len-T = 2-g, beta = (m-2, m-2-g-2[m even])',
     lambda m, g, j, r, i: RULES_TEXT[m % 4][i].startswith('2<=g<=j-1') and g <= j - 2,
     lambda m, g, j, r: (2 - g, m - 2, m - 2 - g - 2 * (1 - m % 2))),
    ('C3 every r-interval row (0<=r, 1<=r ...) incl. its ends: len-T = 1-r',
     lambda m, g, j, r, i: RULES_TEXT[m % 4][i][:3] in ('0<=', '1<='), lambda m, g, j, r: (1 - r, None, None)),
    ('C4 1<=r<=j-2, all m mod 4: len-T = 1-r, beta = (m-2, m-3-r)',
     lambda m, g, j, r, i: 1 <= r <= j - 2 and RULES_TEXT[m % 4][i][:3] in ('0<=', '1<='),
     lambda m, g, j, r: (1 - r, m - 2, m - 3 - r)),
    ('C5 beta_0 = m-2 on every row', lambda m, g, j, r, i: True, lambda m, g, j, r: (None, m - 2, None)),
    ('C6 B = length (Lemma 1 base equals the word length)', lambda m, g, j, r, i: True, None),
    ('C7 B <= T and beta_0, beta_1 <= m-2 (criterion (7) numbers, weight 1)', lambda m, g, j, r, i: True, None),
]


def main():
    lo_m = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    hi_m = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    rows = []
    for m in range(lo_m, hi_m + 1):
        T = C.budget(m, 2)
        for g in range(1, m + 1):
            w = word_G(m, g)
            if w is None:
                continue
            st = C.base_vector(list(range(m, 0, -1)), 1 | 1 << g)
            pr = C.Profile(st, w)
            ok7 = C.mixture_criterion([(pr.base, pr.beta)], [1], 2, m=m)[0]
            rows.append(dict(m=m, g=g, j=m // 4, r=m - g, i=row_of(m, g), lT=len(w) - T, b0=pr.beta[0],
                             b1=pr.beta[1], B=pr.base, n=len(w), T=T, ok7=ok7))
    print('word_G rows m = %d..%d: %d' % (lo_m, hi_m, len(rows)))

    # per-row summary
    print('\nper rule row: count, range of len-T, max beta_0 - (m-2), max beta_1 - (m-2)')
    for rho in range(4):
        for i, text in enumerate(RULES_TEXT[rho]):
            sel = [x for x in rows if x['m'] % 4 == rho and x['i'] == i]
            if not sel:
                print('  m=%d mod 4  %-30s  (no rows)' % (rho, text))
                continue
            print('  m=%d mod 4  %-30s  n=%4d  len-T in [%d, %d]  slack0 %d  slack1 %d' % (
                rho, text, len(sel), min(x['lT'] for x in sel), max(x['lT'] for x in sel),
                max(x['b0'] - x['m'] + 2 for x in sel), max(x['b1'] - x['m'] + 2 for x in sel)))

    def test(sel, f):
        exc = []
        for x in sel:
            want = f(x['m'], x['g'], x['j'], x['r'])
            got = (x['lT'], x['b0'], x['b1'])
            if any(wv is not None and wv != gv for wv, gv in zip(want, got)):
                exc.append((x['m'], x['g'], got))
        return exc

    print('\nrow hypotheses (formulas in m, g; j = floor(m/4), r = m-g):')
    covered = set()
    n_fail = 0
    for name, rho, i, cond, f in HYP:
        sel = [x for x in rows if x['m'] % 4 == rho and x['i'] == i and cond(x['m'], x['g'], x['j'], x['r'])]
        covered.update((x['m'], x['g']) for x in sel)
        exc = test(sel, f)
        n_fail += bool(exc) or not sel
        print('  %-62s n=%4d exceptions=%d %s' % (name, len(sel), len(exc), exc[:4] if exc else ''))
    missing = [(x['m'], x['g']) for x in rows if (x['m'], x['g']) not in covered]
    print('  rows not covered by any row hypothesis: %d %s' % (len(missing), missing[:6]))
    print('  row hypotheses with exceptions or empty domain: %d of %d' % (n_fail, len(HYP)))

    print('\ncoarse / unified hypotheses:')
    for name, cond, f in COARSE:
        sel = [x for x in rows if cond(x['m'], x['g'], x['j'], x['r'], x['i'])]
        if name.startswith('C6'):
            exc = [(x['m'], x['g'], x['B'] - x['n']) for x in sel if x['B'] != x['n']]
        elif name.startswith('C7'):
            exc = [(x['m'], x['g']) for x in sel if not (x['B'] <= x['T'] and max(x['b0'], x['b1']) <= x['m'] - 2
                                                         and x['ok7'])]
        else:
            exc = test(sel, f)
        print('  %-72s n=%4d exceptions=%d %s' % (name, len(sel), len(exc), exc[:4] if exc else ''))
    sys.exit(1 if n_fail or missing else 0)


if __name__ == '__main__':
    main()
