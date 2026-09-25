"""Naive control gadget for the lift task (stdlib, self-contained, deterministic).

For each parent row word W: rotate label m+1 to the front, bubble it cyclically
until it sits right after label m, rotate the remaining atoms onto the parent
unit base (a 'both' split leaves two adjacent zeros, i.e. W lifted by Lemma 1
with z=1 on that block), then replay W treating the pair (m, m+1) as one atom:
L/R over the pair doubles, X with the pair uses a 4-letter transposition.
It is a control, not a target.
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
    """Lemma 1 lift of word on the unit base with one extra zero in block `stretch_gap`
    (None = no stretch).  Returns (stretched state, word)."""
    if stretch_gap is None:
        return list(state), word
    gaps, lab = [], 0  # gap of each zero
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
    for ch in word:  # physical cursor model; the stretched block is 2 zeros wide
        if ch == 'L':
            out.append('LL' if a[c] == tz else 'L')
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            out.append('RR' if a[c] == tz else 'R')
        else:
            c2 = (c + 1) % n
            if a[c] == tz:
                out.append('LXRX')      # (0^2, y) -> (y, 0^2)
            elif a[c2] == tz:
                out.append('XLXR')      # (y, 0^2) -> (0^2, y)
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
    """Replay word on state with label m replaced by the pair (m, m+1)."""
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
        out.append(ch)
        while len(out) >= 2:
            if (out[-2] + out[-1] in ('LR', 'RL')) or (out[-2] == 'X' and out[-1] == 'X'):
                out.pop()
                out.pop()
            else:
                break
    return ''.join(out)


# Bubble direction for label m+1: 'short' (fewer letters), 'right', 'left',
# paired with primary vs complementary head and alignment rotation paths.
CONFIGS = (
    ('short', False, False),
    ('right', False, False),
    ('left', False, False),
    ('short', True, False),
    ('short', False, True),
    ('right', True, False),
    ('left', True, False),
    ('short', True, True),
)


def gadget(instance, parent_word, direction='short', head_alt=False, align_alt=False):
    m = instance['m']
    child = instance['child']['unit_base']
    n = len(child)
    pos, split = instance['insert']['position'], instance['insert']['split']
    p = child.index(m + 1)
    if not head_alt:
        head = 'L' * p if p <= n - p else 'R' * (n - p)
    else:
        head = 'R' * (n - p) if p <= n - p else 'L' * p
    v = _rot(child, head)
    q = v.index(m)
    right = q <= n - 1 - q if direction == 'short' else direction == 'right'
    move = 'XL' * q if right else 'RX' * (n - 1 - q)
    v = _rot(v, move)
    base, word = _lifted(instance['parent']['unit_base'], parent_word, pos if split == 'both' else None)
    pair = []
    for x in base:
        pair.extend([m, m + 1] if x == m else [x])
    shifts = [s for s in range(n) if v[s:] + v[:s] == pair]
    s = shifts[0]
    if not align_alt:
        align = 'L' * s if s <= n - s else 'R' * (n - s)
    else:
        align = 'R' * (n - s) if s <= n - s else 'L' * s
    return _reduce(head + move + align + _pair_word(base, word, m))


def lift(instance):
    rows = instance['parent']['certificate']['rows']
    # Collect candidate variants for each parent row sorted by length (lower base/slope cost)
    by_row = []
    for r in rows:
        row_words = []
        for direction, head_alt, align_alt in CONFIGS:
            w = gadget(instance, r['word'], direction, head_alt, align_alt)
            if w not in row_words:
                row_words.append(w)
        row_words.sort(key=len)
        by_row.append(row_words)

    # Round-robin selection across parent rows to ensure full support for the certificate
    words = []
    seen = set()
    max_variants = max((len(rw) for rw in by_row), default=0)
    for i in range(max_variants):
        for rw in by_row:
            if i < len(rw):
                w = rw[i]
                if w not in seen:
                    seen.add(w)
                    words.append(w)
                    if len(words) >= 16:
                        break
        if len(words) >= 16:
            break

    return {'words': words,
            'note': 'naive control: bubble m+1 next to m, replay parent words with a paired atom'}
