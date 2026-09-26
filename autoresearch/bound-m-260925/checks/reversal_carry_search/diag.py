from common import *
def diag(st, w, picks=None):
    p = C.Profile(st, w, picks)
    print('base', p.base, 'T', C.budget(sum(1 for x in st if x), 2), 'beta', p.beta, 'A', p.A, 'len', len(w))
    for i, ((d, cz), kind) in enumerate(zip(p.segs, p.cores + [None])):
        if any(cz) or kind:
            print('  seg', i, 'd', d, 'cz', cz, 'then', kind)
if __name__ == '__main__':
    from explore1 import *
    m, g = 14, 7
    st = state(m, g)
    for p_, q_ in [(3, 3), (4, 2), (3, 2)]:
        seed = g + 1
        lo2, hi2 = q_ + 1, m + 1 - p_
        s2 = scheds(seed - lo2, hi2 - seed, 1)[0]
        s1 = scheds(p_ + 1, q_, 1)[0]
        w = sched_word(st, p_, [(seed, s2), (0, s1)], 'R')
        print(p_, q_, s2, s1, w)
        if w: diag(st, w)
