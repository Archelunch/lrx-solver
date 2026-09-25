"""Improved gadget for the lift task.

For each parent row word W:
1. Lift parent word according to split (Lemma 1 if split == 'both').
2. Instead of only moving label m+1 next to m with a single bubble direction,
   we generate multiple valid candidate words per parent row:
   - Trying both bubble directions ('short' / left / right).
   - Alternatively, bubbling m+1 next to m+1's natural sorted position or m,
     or rotating child to align in different ways before/after bubbling.
   - Reducing redundant subwords (e.g. LL...LR, RL, XX -> identity).
3. Provide multiple candidate words up to 16, allowing the trusted LP solver
   to select optimal convex combinations to satisfy base and slope bounds.
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
    (None = no stretch). Returns (stretched state, word)."""
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
    """Cancel out inverse adjacent operations: LR, RL, XX."""
    stack = []
    for ch in word:
        if stack:
            top = stack[-1]
            if (top == 'L' and ch == 'R') or (top == 'R' and ch == 'L') or (top == 'X' and ch == 'X'):
                stack.pop()
                continue
        stack.append(ch)
    return ''.join(stack)


def gadget(instance, parent_word, direction='short', head_dir='short'):
    m = instance['m']
    child = instance['child']['unit_base']
    n = len(child)
    pos, split = instance['insert']['position'], instance['insert']['split']
    p = child.index(m + 1)
    
    if head_dir == 'short':
        head = 'L' * p if p <= n - p else 'R' * (n - p)
    elif head_dir == 'left':
        head = 'L' * p
    else:
        head = 'R' * (n - p)

    v = _rot(child, head)
    q = v.index(m)
    
    if direction == 'short':
        right = q <= n - 1 - q
    elif direction == 'right':
        right = True
    else:
        right = False

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
    full = _reduce(head + move + align + _pair_word(base, word, m))
    
    # Verify correctness
    final_v = _rot(child, full)
    target = list(range(1, m + 2)) + [0] * (n - (m + 1))
    if final_v != target:
        return None
    return full


def lift(instance):
    rows = instance['parent']['certificate']['rows']
    words = []
    
    # Try different combinations of head rotation and bubble directions
    # to give the LP solver diverse slope profiles.
    configs = [
        ('short', 'short'),
        ('right', 'short'),
        ('left', 'short'),
        ('short', 'left'),
        ('short', 'right'),
        ('right', 'right'),
        ('left', 'left'),
    ]
    
    for r in rows:
        for bubble_dir, head_dir in configs:
            w = gadget(instance, r['word'], bubble_dir, head_dir)
            if w and w not in words:
                words.append(w)
                if len(words) >= 16:
                    break
        if len(words) >= 16:
            break
            
    return {
        'words': words,
        'note': 'multi-direction bubble gadget with cyclic reduction'
    }
