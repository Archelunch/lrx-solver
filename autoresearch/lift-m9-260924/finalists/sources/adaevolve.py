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
    changed = True
    while changed:
        out = []
        changed = False
        for ch in word:
            if out and ((out[-1] + ch in ('LR', 'RL')) or (out[-1] == 'X' and ch == 'X')):
                out.pop()
                changed = True
            else:
                out.append(ch)
        word = ''.join(out)
    return word


def gadget(instance, parent_word, pair_order='after', head_dir='short', move_dir='short', align_dir='short'):
    m = instance['m']
    child = instance['child']['unit_base']
    n = len(child)
    pos, split = instance['insert']['position'], instance['insert']['split']
    p = child.index(m + 1)
    if head_dir == 'short':
        head = 'L' * p if p <= n - p else 'R' * (n - p)
    elif head_dir == 'L':
        head = 'L' * p
    else:
        head = 'R' * (n - p)
    v = _rot(child, head)
    q = v.index(m)
    # Determine target index for m+1 (currently at index 0)
    target_idx = q if pair_order == 'after' else (q - 1) % n
    if move_dir == 'short':
        move = 'XL' * target_idx if target_idx <= n - 1 - target_idx else 'RX' * (n - 1 - target_idx)
    elif move_dir == 'XL':
        move = 'XL' * target_idx
    else:
        move = 'RX' * (n - 1 - target_idx)
    v = _rot(v, move)
    base, word = _lifted(instance['parent']['unit_base'], parent_word, pos if split == 'both' else None)
    pair = []
    atoms = [m, m + 1] if pair_order == 'after' else [m + 1, m]
    for x in base:
        pair.extend(atoms if x == m else [x])
    shifts = [s for s in range(n) if v[s:] + v[:s] == pair]
    if not shifts:
        return None
    s = shifts[0]
    if align_dir == 'short':
        align = 'L' * s if s <= n - s else 'R' * (n - s)
    elif align_dir == 'L':
        align = 'L' * s
    else:
        align = 'R' * (n - s)
    cand = _reduce(head + move + align + _pair_word(base, word, m))
    return cand if len(cand) <= 4000 else None


import itertools


def lift(instance):
    """Lift parent certificate rows using dual pairing orders and itertools.permutations routing exploration."""
    rows = instance['parent']['certificate']['rows']
    child = instance['child']['unit_base']
    target_sorted = list(range(1, instance['m'] + 2)) + [0] * instance['child']['k']
    words = []
    seen = set()

    # Use itertools.permutations and product to explore dual pairing orders and direction choices
    routing_options = ['short', 'L', 'R']
    perm_dirs = list(itertools.permutations(routing_options, 2))
    
    # Configurations structured as (pair_order, head_dir, move_dir, align_dir)
    configs = []
    # Primary canonical configs with both pairing orders
    for p_ord in ['after', 'before']:
        configs.append((p_ord, 'short', 'short', 'short'))
        configs.append((p_ord, 'short', 'XL', 'short'))
        configs.append((p_ord, 'short', 'RX', 'short'))
        for h, a in perm_dirs:
            configs.append((p_ord, h, 'short', a))
            configs.append((p_ord, h, 'XL', a))
            configs.append((p_ord, h, 'RX', a))

    # Pass 1: Ensure coverage across parent rows with alternating pairing orders
    for r in rows:
        for cfg in configs:
            w = gadget(instance, r['word'], *cfg)
            if w and w not in seen:
                if _rot(child, w) == target_sorted:
                    seen.add(w)
                    words.append(w)
                    break

    # Pass 2: Alternate between 'after' and 'before' to create complementary slope variations
    for cfg in configs:
        for r in rows:
            w = gadget(instance, r['word'], *cfg)
            if w and w not in seen:
                if _rot(child, w) == target_sorted:
                    seen.add(w)
                    words.append(w)
                    if len(words) >= 16:
                        return {'words': words}

    return {'words': words}
