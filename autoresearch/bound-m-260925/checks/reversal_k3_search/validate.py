"""Check gen3 against reversal_orbit_search (fast.gen_pool + front_fast) and core_word / word3 agreement."""
import sys, time, random
sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search')
sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks')
import gen3
from fast import gen_pool, front_fast, C
from reversal_orbit import core_word
from integrations.bound_task import make_family

bad = 0
for m, mask in [(9, 1 | 16 | 256), (10, 1 | 32 | 1024), (11, 2 | 8 | 1024), (12, 2 | 32 | 512), (9, 3 | 512)]:
    fam = make_family(list(range(m, 0, -1)), mask)
    st = fam['unit_base']; k = fam['k']; pk = list(range(k))
    t0 = time.process_time(); a = front_fast(st, gen_pool(st), pk); t1 = time.process_time()
    F = gen3.pool(st, pk); b = gen3.confirm(st, F.pareto(), pk); t2 = time.process_time()
    A = sorted((x[0], x[1]) for x in a); B = sorted((x[0], x[1]) for x in b)
    print(m, mask, 'old', len(A), round(t1 - t0, 2), 's new', len(B), round(t2 - t1, 2), 's same front', A == B)
    bad += A != B
    # re-derive every front word from params
    for bb, bt, w, (zf, cores, fin) in b:
        if gen3.word3(st, cores, fin, zf) != w:
            bad += 1; print('rederive mismatch', cores, fin)
        if len({c[3] for c in cores}) == 1:
            cw = core_word(st, cores[0][3], [(c[0], c[1], c[2]) for c in cores], fin)
            if cw != w:
                bad += 1; print('core_word mismatch', cores)
# refined base + picks
fam = make_family(list(range(10, 0, -1)), 1 | 32 | 1024)
st = C.refine(fam['unit_base'], [2, 1, 1]); pk = [1, 2, 3]
a = front_fast(st, gen_pool(st), pk); b = gen3.confirm(st, gen3.pool(st, pk).pareto(), pk)
print('refined same front', sorted((x[0], x[1]) for x in a) == sorted((x[0], x[1]) for x in b))
# random states, three-core / percore / zfree words replay and price correctly
random.seed(1)
n3 = 0
for trial in range(30):
    m = random.choice([9, 10, 11]); gs = sorted(random.sample(range(m + 1), 3))
    fam = make_family(list(range(m, 0, -1)), sum(1 << g for g in gs)); st = fam['unit_base']
    F = gen3.pool(st, [0, 1, 2], cuts=[random.randrange(m + 1)], seeds1=[random.randrange(m + 3)],
                  seeds2=[random.randrange(m + 3)], seeds3=[random.randrange(m + 3)], three=True, percore=True, zfree=(False, True))
    for bb, bt, w, (zf, cores, fin) in F.best.values() and [(v[0], k_, v[1], v[2]) for k_, v in F.best.items()]:
        n3 += 1
        pr = C.Profile(st, w, [0, 1, 2])
        if (pr.base, tuple(pr.beta)) != (bb, bt) or gen3.word3(st, cores, fin, zf) != w or not C.is_root(C.run(st, w)):
            bad += 1; print('bad', m, gs, cores, fin)
print('random words checked', n3, 'problems', bad)
