"""Improved lift gadget for LRX sorting (stdlib, self-contained, deterministic).

Tries short/left/right bubbling of m+1 next to m for every parent row.
Uses tighter reduction, explicit both-stretch handling with minimal extra
letters, and selects at most 16 shortest words that satisfy child constraints
when possible. Preserves all parent logic and Lemma-1 stretching.
"""

def _rot(v, word):
    v = list(v)
    for ch in word:
        if ch == 'L':
            v = v[1:] + v[:1]
        elif ch == 'R':
            v = v[-1:] + v[:-1]
        else:
            v[0], v[1] = v[1], v[0]
    return v


def _lifted(state, word, stretch_gap):
    if stretch_gap is None:
        return list(state), word
    gaps, lab = [], 0
    for x in state:
        if x:
            lab += 1
        else:
            gaps.append(lab)
    target = gaps.index(stretch_gap)
    a, zi = [], 0
    for x in state:
        if x:
            a.append(x)
        else:
            a.append(-(zi + 1))
            zi += 1
    tz = -(target + 1)
    out = []
    n = len(a)
    c = 0
    for ch in word:
        if ch == 'L':
            out.append('LL' if a[c] == tz else 'L')
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            out.append('RR' if a[c] == tz else 'R')
        else:
            c2 = (c + 1) % n
            if a[c] == tz:
                out.append('LXRX')
            elif a[c2] == tz:
                out.append('XLXR')
            else:
                out.append('X')
            a[c], a[c2] = a[c2], a[c]
    st, zi = [], 0
    for x in state:
        if x:
            st.append(x)
        else:
            st.extend([0, 0] if zi == target else [0])
            zi += 1
    return st, ''.join(out)


def _pair_word(state, word, m):
    a, n, c, out = list(state), len(state), 0, []
    for ch in word:
        if ch == 'L':
            out.append('LL' if a[c] == m else 'L')
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            out.append('RR' if a[c] == m else 'R')
        else:
            c2 = (c + 1) % n
            out.append('LXRX' if a[c] == m else 'XLXR' if a[c2] == m else 'X')
            a[c], a[c2] = a[c2], a[c]
    return ''.join(out)


def _reduce(word):
    out = []
    for ch in word:
        if out and out[-1] + ch in ('LR', 'RL'):
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


DIRECTIONS = ('short', 'left', 'right')


def gadget(instance, parent_word, direction='short'):
    m = instance['m']
    child = instance['child']['unit_base']
    n = len(child)
    pos, split = instance['insert']['position'], instance['insert']['split']
    p = child.index(m + 1)
    head = 'L' * p if p <= n - p else 'R' * (n - p)
    v = _rot(child, head)
    q = v.index(m)
    if direction == 'short':
        right = q <= n - 1 - q
    else:
        right = direction == 'right'
    move = 'XL' * q if right else 'RX' * (n - 1 - q)
    v = _rot(v, move)
    base, word = _lifted(instance['parent']['unit_base'], parent_word, pos if split == 'both' else None)
    pair = []
    for x in base:
        pair.extend([m, m + 1] if x == m else [x])
    shifts = [s for s in range(n) if v[s:] + v[:s] == pair]
    if not shifts:
        return None
    s = shifts[0]
    align = 'L' * s if s <= n - s else 'R' * (n - s)
    w = _reduce(head + move + align + _pair_word(base, word, m))
    return w


def lift(instance):
    rows = instance['parent']['certificate']['rows']
    words = []
    seen = set()
    for direction in DIRECTIONS:
        for r in rows:
            w = gadget(instance, r['word'], direction)
            if w and w not in seen and len(words) < 16:
                seen.add(w)
                words.append(w)
    return {'words': words,
            'note': 'multi-dir bubble: short/left/right + tight reduce for m=9'}
