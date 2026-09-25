"""Lift instances (autoresearch/lift-m9-260924/TASK.md): insert label m+1 into a
certified m-family.  Pure data construction; no scoring here.

Gap g = number of labels before a zero; mask bit g <-> gap g nonempty.
Inserting label m+1 at label position i splits parent gap i into child gaps
i (left of the new label) and i+1 (right of it); gaps j > i shift to j+1.
"""
from integrations import lrx_m as C

SPLITS = ('left', 'right', 'both', 'none')


def child_family(labels, mask, position, split):
    """-> (child labels, child mask).  split must be 'none' iff gap i is empty."""
    m = len(labels)
    if sorted(labels) != list(range(1, m + 1)) or not 0 <= mask < 1 << (m + 1):
        raise ValueError('parent is not a family (labels 1..m, mask bits 0..m)')
    if type(position) is not int or not 0 <= position <= m:
        raise ValueError('insert position must be 0..m')
    full = (mask >> position) & 1
    if split not in SPLITS or (split == 'none') == bool(full):
        raise ValueError('split %r does not match parent gap %d' % (split, position))
    low = mask & ((1 << position) - 1)
    high = (mask >> (position + 1)) << (position + 2)
    mid = {'none': 0, 'left': 1, 'right': 2, 'both': 3}[split] << position
    return labels[:position] + [m + 1] + labels[position:], low | mid | high


def family_id(labels, mask):
    sep = '' if len(labels) <= 9 else '.'
    return 'm%d-mask%d-labels%s' % (len(labels), mask, sep.join(map(str, labels)))


def splits_for(mask, position):
    return ('left', 'right', 'both') if (mask >> position) & 1 else ('none',)


def plain_row(labels, mask, word, weight='1', **meta):
    """Parent certificate row: a literal word on the parent unit base, with base
    and slopes recomputed from the word (Lemma 1 affine cost)."""
    state = C.base_vector(labels, mask)
    prof = C.Profile(state, word)  # raises CheckError unless it sorts
    row = {'weight': str(weight), 'word': word, 'base': prof.base, 'slopes': list(prof.beta)}
    row.update(meta)
    return row


def comparison_word(P, ref_state, ref_word, cut):
    """Literal word obtained on P by the Lemma 3 comparison run of a reference
    word (rotations as given, X only on descending pairs)."""
    ref = C.Reference(ref_state, ref_word)
    R = C.target_ranks(P, ref.f, cut)
    if not ref.cut_ok(cut) or not C.prefix_dominates(R, ref.q_data(cut)[0]):
        raise C.CheckError('comparison premise fails')
    n, c, out = len(P), 0, []
    rk = [R[(p - cut) % n] for p in range(n)]
    for ch in ref_word:
        if ch == 'X':
            j = (c + 1) % n
            if rk[c] > rk[j]:
                rk[c], rk[j] = rk[j], rk[c]
                out.append('X')
        else:
            c = (c + (1 if ch == 'L' else -1)) % n
            out.append(ch)
    return ''.join(out)


def build_instance(parent, position, split):
    labels, mask = list(parent['labels']), parent['mask']
    m = len(labels)
    cl, cm = child_family(labels, mask, position, split)
    k = bin(cm).count('1')
    return {
        'id': 'lift-%s-i%d-%s' % (parent['id'], position, split),
        'm': m,
        'parent': {'id': parent['id'], 'labels': labels, 'mask': mask,
                   'unit_base': C.base_vector(labels, mask),
                   'certificate': parent['certificate']},
        'insert': {'label': m + 1, 'position': position, 'split': split},
        'child': {'id': family_id(cl, cm), 'labels': cl, 'mask': cm,
                  'unit_base': C.base_vector(cl, cm), 'k': k,
                  'budget_unit': C.budget(m + 1, k), 'slope_bound': m - 1},
    }


def build_instances(parent):
    """All insertion positions and splits of one parent family."""
    m = len(parent['labels'])
    return [build_instance(parent, i, s) for i in range(m + 1) for s in splits_for(parent['mask'], i)]


def check_instance(inst):
    """Recompute the child from the parent; reject any disagreement.  Parent rows
    must be literal sorting words; their base/slopes are recomputed, not trusted."""
    p = inst['parent']
    want = build_instance(p, inst['insert']['position'], inst['insert']['split'])
    if inst['insert'].get('label') != want['insert']['label'] or inst.get('m') != want['m']:
        raise ValueError('%s: insert label or m disagrees' % inst.get('id'))
    if inst['id'] != want['id'] or inst['child'] != dict(inst['child'], **want['child']) \
            or p.get('unit_base', want['parent']['unit_base']) != want['parent']['unit_base']:
        raise ValueError('%s: child or id disagrees with recomputation' % inst.get('id'))
    rows = []
    for row in p['certificate']['rows']:
        prof = C.Profile(want['parent']['unit_base'], row['word'])
        rows.append({'word': row['word'], 'base': prof.base, 'slopes': list(prof.beta),
                     'claimed': [row.get('base'), row.get('slopes')]})
    return want, rows
