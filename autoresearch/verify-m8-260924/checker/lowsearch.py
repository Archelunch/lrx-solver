"""Resource-bounded word search for unit bases with k=1,2,3 zeros (theorem section 7).

Class searched: freely reduced words (no LR, RL, XX), no swap of two zeros,
|W| <= 30+6k, running resource hat-beta_j <= 6 for every zero j, with the
increment table of section 7.  Every found word is re-checked independently
with lrxm8.Profile(each_zero=True): it sorts, |W| <= 30+6k, beta_j <= 6.
A failed exhaustive search means only "no word in this class", never infeasibility.

Pruning: g + 1 + dist(child) <= 30+6k where dist is the exact unconstrained
LRX distance to the root (BFS over vectors with identical zeros), and
dominance on (vector, previous letter) by (length, resources).
"""
import sys
from collections import deque
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lrxm8 import Profile  # noqa: E402

ZB = 9  # zero ids 9, 10, 11 during search
ALLOWED = {None: 'LRX', 'L': 'LX', 'R': 'RX', 'X': 'LR'}
COLLAPSE = bytes.maketrans(bytes([9, 10, 11]), bytes([0, 0, 0]))


def root(k):
    return bytes(list(range(1, 9)) + [0] * k)


def distance_table(k):
    """Exact BFS distance to the root over vectors with identical zeros."""
    r = root(k)
    dist = {r: 0}
    frontier = [r]
    d = 0
    while frontier:
        d += 1
        nxt = []
        for v in frontier:
            for w in (v[1:] + v[:1], v[-1:] + v[:-1], v[1:2] + v[0:1] + v[2:]):
                if w not in dist:
                    dist[w] = d
                    nxt.append(w)
        frontier = nxt
    return dist


def step(v, p, a, k):
    """Apply letter a after previous letter p. Returns (w, inc tuple) or None if forbidden."""
    f, s, last = v[0], v[1], v[-1]
    inc = [0] * k
    if a == 'L':
        if f >= ZB and p != 'X':
            inc[f - ZB] += 1
        return v[1:] + v[:1], inc
    if a == 'R':
        if f >= ZB and p == 'X':
            inc[f - ZB] += 1
        if last >= ZB:
            inc[last - ZB] += 1
        return v[-1:] + v[:-1], inc
    if f >= ZB and s >= ZB:
        return None
    if f >= ZB:
        inc[f - ZB] += 1 if p == 'R' else 3
    if s >= ZB:
        inc[s - ZB] += 2
    return v[1:2] + v[0:1] + v[2:], inc


class Search:
    def __init__(self, k, dist, node_budget=None):
        self.k, self.dist, self.L = k, dist, 30 + 6 * k
        self.target = root(k)
        self.budget = node_budget

    def run(self, base):
        """base: sequence with zeros 0. Returns (status, word, resources, nodes).
        status: 'found' | 'none_in_class' | 'budget'."""
        v, z = [], ZB
        for x in base:
            if x == 0:
                v.append(z)
                z += 1
            else:
                v.append(x)
        v = bytes(v)
        self.memo = {}
        self.nodes = 0
        self.word = []
        self.hit = None
        self.out_of_budget = False
        if self.dist[v.translate(COLLAPSE)] <= self.L:
            self._dfs(v, None, 0, (0,) * self.k)
        if self.hit is not None:
            return 'found', ''.join(self.word), self.hit, self.nodes
        return ('budget' if self.out_of_budget else 'none_in_class'), None, None, self.nodes

    def _dfs(self, v, p, g, r):
        if v.translate(COLLAPSE) == self.target:
            self.hit = r
            return True
        self.nodes += 1
        if self.budget and self.nodes > self.budget:
            self.out_of_budget = True
            return False
        key = (v, p)
        seen = self.memo.get(key)
        if seen:
            for g2, r2 in seen:
                if g2 <= g and all(a <= b for a, b in zip(r2, r)):
                    return False
            seen.append((g, r))
        else:
            self.memo[key] = [(g, r)]
        kids = []
        for a in ALLOWED[p]:
            res = step(v, p, a, self.k)
            if res is None:
                continue
            w, inc = res
            r2 = tuple(x + y for x, y in zip(r, inc))
            if max(r2) > 6:
                continue
            h = self.dist[w.translate(COLLAPSE)]
            if g + 1 + h > self.L:
                continue
            kids.append((h, a, w, r2))
        kids.sort()
        for h, a, w, r2 in kids:
            self.word.append(a)
            if self._dfs(w, a, g + 1, r2):
                return True
            self.word.pop()
            if self.out_of_budget:
                return False
        return False


def independent_check(base, word, k):
    """Re-verify a found word with the Lemma 1 / (4)-(5) implementation."""
    prof = Profile(list(base), word, each_zero=True)
    return prof.base <= 30 + 6 * k and len(word) <= 30 + 6 * k and max(prof.beta) <= 6, prof
