"""Canonical carry family v2: core-2 schedules built as strict alternation with Zg's free insertion and the
one-sided tail, plus every single adjacent transposition of that string."""
import sys, time, json
from common import *
from canon import word_K


def core2_canon(side, m, g, p, q, seed, first):
    """Alternating schedule for core 2; the insertion of Zg (free, no swap) does not take a turn."""
    n = m + 2
    lo2, hi2 = q + 1, n - p - 1
    zg = g + 1
    lcells = list(range(seed - 1, lo2 - 1, -1)) + ([(lo2 - 1 - i) % n for i in range(p)] if side == 'lo' else [])
    rcells = list(range(seed + 1, hi2 + 1)) + ([(hi2 + 1 + i) % n for i in range(q)] if side == 'hi' else [])
    s, li, ri, cur = '', 0, 0, first
    while li < len(lcells) or ri < len(rcells):
        if cur == 'l' and li < len(lcells) or ri == len(rcells):
            s += 'l'; li += 1
            if lcells[li - 1] == zg and li < len(lcells):
                s += 'l'; li += 1
            cur = 'r'
        else:
            s += 'r'; ri += 1
            if rcells[ri - 1] == zg and ri < len(rcells):
                s += 'r'; ri += 1
            cur = 'l'
    return s


def variants(s):
    out = {s}
    for i in range(len(s) - 1):
        if s[i] != s[i + 1]:
            out.add(s[:i] + s[i + 1] + s[i] + s[i + 2:])
    return out


def family2(m, g, sides=('lo', 'hi'), dpq=(0, 1, 2, 3), swaps=True):
    n = m + 2
    for side in sides:
        for big in range(1, m // 2 + 2):
            for d in dpq:
                if side == 'lo':
                    p, q = big, big + d
                    s1s = {'r' * d + 'lr' * p, 'r' * max(d - 1, 0) + 'rl' * p + ('r' if d else ''), 'l' + 'rl' * (p - 1) + 'r' * (d + 1)}
                else:
                    q, p = big, big + d
                    s1s = {'l' * d + 'rl' * q, 'l' * max(d - 1, 0) + 'lr' * q + ('l' if d else ''), 'r' + 'lr' * (q - 1) + 'l' * (d + 1)}
                if p > m - g or q > g: continue
                s1s = {s for s in s1s if s.count('l') == p and s.count('r') == q}
                lo2, hi2 = q + 1, n - p - 1
                for s1 in s1s:
                    for seed in range(lo2, hi2 + 1):
                        seen = set()
                        for first in 'lr':
                            base = core2_canon(side, m, g, p, q, seed, first)
                            for s2 in (variants(base) if swaps else {base}):
                                if s2 in seen: continue
                                seen.add(s2)
                                for fin in 'LR':
                                    w = word_K(m, g, side, p, q, s1, seed, s2, fin)
                                    if w: yield w, (side, p, q, s1, seed, s2, fin)


def front2(m, g, **kw):
    st = state(m, g); items = {}
    for w, par in family2(m, g, **kw):
        k = price(st, w)
        if k is None: continue
        key = (k[0],) + k[1]
        if key not in items or len(w) < len(items[key][0]):
            items[key] = (w, par)
    return pareto(items)


if __name__ == '__main__':
    out = open(sys.argv[3], 'a') if len(sys.argv) > 3 else None
    for m in range(int(sys.argv[1]), int(sys.argv[2]) + 1):
        row = []; t0 = time.process_time()
        for g in range(m // 4 + 1, m - m // 4):
            t1 = time.process_time()
            fr = front2(m, g); keys = list(fr)
            r = root_lp(m, keys); T = C.budget(m, 2)
            sup = [(keys[i][0] - T, keys[i][1:], fr[keys[i]][1], str(x)) for i, x in enumerate(r['weights']) if x]
            row.append('%d:%s' % (g, ('C%s' % r['value']) if r['status'] == 'CERTIFIED' else ('gap%s' % r['gap'])))
            if out:
                out.write(json.dumps({'m': m, 'g': g, 'status': r['status'], 'lhs': str(r.get('value')),
                                      'gap': str(r['gap']), 'support': [[x[0], list(x[1]), list(x[2]), x[3]] for x in sup],
                                      'words': [fr[keys[i]][0] for i, x in enumerate(r['weights']) if x],
                                      'cpu': round(time.process_time() - t1, 1)}) + '\n'); out.flush()
        print(m, ' '.join(row), '%.0fs' % (time.process_time() - t0), flush=True)
