"""Naive deterministic LRX sorter (control a, campaign seed).

sort_word(v) returns a word over L, R, X that sorts v (labels 1..m once, zeros
elsewhere) to (1..m, 0^r). L rotates left, R rotates right, X swaps the first
two entries. Strategy: plain bubble sort in the fixed frame of v. A pointer c
marks which frame position is currently first; X swaps frame positions c and
c+1, L/R move the pointer. Zeros sort after every label. Each pass stops at the
last swap of the previous pass, and the pointer takes the shorter way round.
Correct for every input; far from the budget T_m(n) on most states.
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
