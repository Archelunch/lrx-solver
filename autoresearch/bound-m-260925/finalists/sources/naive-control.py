"""Naive family certifier (control a): one bubble-sort word on the unit base.

certify(family) returns the bubble sort of the unit base in the fixed frame
(integrations/sort_control_naive.py, inlined so the file runs alone in the
sandbox). Zeros sort after every label and equal keys never swap, so the word
has no zero-zero swap. One word; the evaluator prices it by Lemma 1.
"""


def sort_word(v):
    a = list(v)
    n = len(a)
    m = max(a)
    key = [x if x else m + 1 for x in a]
    out = []
    c = 0

    def move_to(t):
        nonlocal c
        k = (t - c) % n
        out.append('L' * k if k <= n - k else 'R' * (n - k))
        c = t

    end = n - 1
    while end > 0:
        last = 0
        for i in range(end):
            if key[i] > key[i + 1]:
                move_to(i)
                out.append('X')
                key[i], key[i + 1] = key[i + 1], key[i]
                last = i
        end = last
    move_to(0)
    return ''.join(out)


def certify(family):
    return {'words': [sort_word(family['unit_base'])]}
