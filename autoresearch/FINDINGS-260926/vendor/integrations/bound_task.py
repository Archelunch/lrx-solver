"""Bound-m families (autoresearch/bound-m-260925/TASK.md): pure data, no scoring.

A family (a, S) is a label order a (a permutation of 1..m) and a nonempty gap
mask S (bit g <-> gap g, the one after g labels, is nonempty). Its unit base has
one zero per gap of S; the family covers every state with l_j >= 1 zeros in
block j. Budget T = T_m(m+k), slope bound m-2 (the group's criterion (7) with m
as a parameter; see TASK.md).
"""
from integrations import lrx_m as C
from integrations.lift_task import family_id

SCHEMA = 'lrx-bound-families-v1'
VISIBLE = ('id', 'm', 'labels', 'mask', 'gaps', 'k', 'unit_base', 'budget_unit', 'slope_bound')


def gaps_of(mask, m):
    return [g for g in range(m + 1) if (mask >> g) & 1]


def make_family(labels, mask, **meta):
    labels = list(labels)
    m = len(labels)
    if m < 2 or sorted(labels) != list(range(1, m + 1)) or any(type(x) is not int for x in labels):
        raise ValueError('labels must be a permutation of 1..m')
    if type(mask) is not int or not 0 < mask < 1 << (m + 1):
        raise ValueError('mask must be a nonzero integer with bits 0..m')
    gaps = gaps_of(mask, m)
    k = len(gaps)
    fam = {'id': family_id(labels, mask), 'm': m, 'labels': labels, 'mask': mask, 'gaps': gaps, 'k': k,
           'unit_base': C.base_vector(labels, mask), 'budget_unit': C.budget(m, k), 'slope_bound': m - 2}
    fam.update(meta)
    return fam


def visible(fam):
    """The candidate-visible part of a family (no class, inv or provenance)."""
    return {x: fam[x] for x in VISIBLE}


def check_family(fam):
    """Recompute every visible field from (labels, mask); reject any disagreement. Returns visible(fam)."""
    want = make_family(fam['labels'], fam['mask'])
    if visible(fam) != want:
        raise ValueError('%s: family fields disagree with recomputation' % fam.get('id'))
    labels, mask, blocks = C.parse_state(want['unit_base'])  # reversed direction
    if labels != want['labels'] or mask != want['mask'] or [len(b) for b in blocks] != [1] * want['k']:
        raise ValueError('%s: unit base does not rebuild the family' % fam.get('id'))
    return want


def family_of_state(v):
    """(labels, mask, block lengths) of a visible vector: the unique family that holds it."""
    labels, mask, blocks = C.parse_state(list(v))
    return labels, mask, [len(b) for b in blocks]


def inversions(labels):
    n = len(labels)
    return sum(1 for i in range(n) for j in range(i + 1, n) if labels[i] > labels[j])
