"""word_G(m, g) parameters (REVERSAL-K2.md s.2) applied to the three-zero state {0,g1,g2}, g in {g1, g2}, n = m+3.
Single word, criterion (7). Search side only."""
import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks')
from reversal_k2 import params_G
from reversal_orbit import core_word
from integrations import lrx_m as C


def wordG3(m, g1, g2, p, fin='R'):
    dt, s1, dk, d1, ds2, d2 = p
    n = m + 3
    t, k1 = (m - 3) // 4 + dt, m // 2 + dk
    if not 0 <= t <= m or k1 < 1:
        return None
    nr = (k1 + 1) // 2 if d1 == 'r' else k1 // 2
    mid = s1 + nr + 1 + (n - k1 - 1) // 2
    st = C.base_vector(list(range(m, 0, -1)), 1 | 1 << g1 | 1 << g2)
    return st, core_word(st, t, [(s1 % n, k1, d1), ((mid + ds2) % n, None, d2)], fin)


def ok(m, st, w):
    if not w:
        return None
    p = C.Profile(st, w)
    good, B, beta = C.mixture_criterion([(p.base, p.beta)], [1], 3, m=m)
    return good, p.base - C.budget(m, 3), list(p.beta)


if __name__ == '__main__':
    for m in range(9, 25):
        cov = []
        for g1 in range(1, m + 1):
            for g2 in range(g1 + 1, m + 1):
                hit = []
                for g in (g1, g2):
                    p = params_G(m, g)
                    if p:
                        r = wordG3(m, g1, g2, p)
                        if r and r[1]:
                            o = ok(m, *r)
                            if o and o[0]:
                                hit.append(g)
                if hit:
                    cov.append((g1, g2))
        print(m, len(cov), m * (m - 1) // 2, cov[:60], flush=True)
