"""Relative-coordinate parameter tuples from the survey supports of masks {0,g1,g2} (m = 9..11), ranked by the
number of masks whose support contains them. Search side only.
Tuple: (cut anchor, dt, s1 anchor, ds1, k1 anchor, dk, d1, s2 anchor, ds2, d2, fin).  Anchors:
  cut: 'j' = (m-3)//4, 'm' = m, 'g1', 'g2';  seeds: 'z0' = 0, 'z1' = g1+1, 'z2' = g2+2, 'e' = n-1 (cells);
  k1: 'h' = m//2, 'g1', 'g2', 'r2' = m-g2."""
import json, collections, sys


def anchors(m, g1, g2):
    n = m + 3
    return ({'j': (m - 3) // 4, 'm': m, 'g1': g1, 'g2': g2},
            {'z0': 0, 'z1': g1 + 1, 'z2': g2 + 2, 'e': n - 1},
            {'h': m // 2, 'g1': g1, 'g2': g2, 'r2': m - g2})


def rel(m, g1, g2, t, cores, fin, lim=3):
    n = m + 3
    ca, sa, ka = anchors(m, g1, g2)
    (s1, k1, d1, _), (s2, _, d2, _) = cores
    out = []
    for cn, cv in ca.items():
        for sn, sv in sa.items():
            ds1 = (s1 - sv + n // 2) % n - n // 2
            if abs(ds1) > lim:
                continue
            for kn, kv in ka.items():
                if abs(k1 - kv) > lim:
                    continue
                for s2n, s2v in sa.items():
                    ds2 = (s2 - s2v + n // 2) % n - n // 2
                    if abs(ds2) > lim:
                        continue
                    out.append((cn, t - cv, sn, ds1, kn, k1 - kv, d1, s2n, ds2, d2, fin))
    return out


def absolute(m, g1, g2, tup):
    n = m + 3
    ca, sa, ka = anchors(m, g1, g2)
    cn, dt, sn, ds1, kn, dk, d1, s2n, ds2, d2, fin = tup
    t, s1, k1, s2 = ca[cn] + dt, (sa[sn] + ds1) % n, ka[kn] + dk, (sa[s2n] + ds2) % n
    if not 0 <= t <= m or k1 < 1:
        return None
    return t, [(s1, k1, d1, t), (s2, None, d2, t)], fin


if __name__ == '__main__':
    cnt = collections.Counter()
    for m in (9, 10, 11):
        for l in open('survey-m%d.jsonl' % m):
            r = json.loads(l)
            g0, g1, g2 = r['gaps']
            if g0 != 0 or r['status'] != 'CERTIFIED':
                continue
            seen = set()
            for sup in r['support']:
                zf, cores, fin = sup[3]
                if zf or len(cores) != 2 or cores[1][1] is not None or cores[0][3] != cores[1][3]:
                    continue
                seen.update(rel(m, g1, g2, cores[0][3], cores, fin))
            cnt.update(seen)
    top = cnt.most_common(int(sys.argv[1]) if len(sys.argv) > 1 else 400)
    json.dump([[list(t), c] for t, c in top], open('harvest-top.json', 'w'))
    print(len(cnt), top[:10])
