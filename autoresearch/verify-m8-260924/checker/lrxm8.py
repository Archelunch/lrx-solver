"""Independent stdlib checker for the LRX m=8 multiset package.

Written from the theorem text (LRX_MULTISET_M8_COMPLETE_THEOREM_RU.md,
sections 2-6), not from the package scripts.  Exact integers and Fractions.

Conventions
  * visible vector v; L: (v1..vn)->(v2..vn,v1); R = L^-1; X swaps v1,v2.
  * labels 1..8, zeros 0.  Inside atomic runs zero atoms carry ids 100+i
    (i = global index of the zero in the linear state).
  * gap g = number of labels before a zero; mask bit g <-> gap g nonempty.
  * physical model (Lemma 3): fixed positions 0..N-1, cursor starts at 0,
    L: cursor+1, R: cursor-1, X swaps positions cursor, cursor+1 (mod N).
"""
from fractions import Fraction as Fr

M = 8
ZID = 100


class CheckError(Exception):
    pass


def is_zero(x):
    return x == 0 or x >= ZID


# ---------------------------------------------------------------- vectors
def run_naive(vec, word):
    v = list(vec)
    for ch in word:
        if ch == 'L':
            v = v[1:] + v[:1]
        elif ch == 'R':
            v = v[-1:] + v[:-1]
        elif ch == 'X':
            v[0], v[1] = v[1], v[0]
        else:
            raise CheckError('bad letter %r' % ch)
    return v


def run(vec, word):
    """Cursor implementation of the same semantics (checked against run_naive in tests)."""
    a = list(vec)
    n = len(a)
    c = 0
    for ch in word:
        if ch == 'X':
            j = c + 1 if c + 1 < n else 0
            a[c], a[j] = a[j], a[c]
        elif ch == 'L':
            c = c + 1 if c + 1 < n else 0
        elif ch == 'R':
            c = c - 1 if c else n - 1
        else:
            raise CheckError('bad letter %r' % ch)
    return a[c:] + a[:c]


def is_root(v):
    return len(v) > M and list(v[:M]) == list(range(1, M + 1)) and all(is_zero(x) for x in v[M:])


def base_vector(labels, mask):
    v = [0] if mask & 1 else []
    for i, x in enumerate(labels, 1):
        v.append(x)
        if (mask >> i) & 1:
            v.append(0)
    return v


def parse_state(state):
    """-> (labels, mask, blocks) ; blocks[j] = list of global zero indices of j-th nonempty gap."""
    labels, blocks, gaps = [], [], []
    zi = 0
    for x in state:
        if is_zero(x):
            g = len(labels)
            if gaps and gaps[-1] == g:
                blocks[-1].append(zi)
            else:
                gaps.append(g)
                blocks.append([zi])
            zi += 1
        else:
            labels.append(x)
    if sorted(labels) != list(range(1, M + 1)):
        raise CheckError('state labels are not a permutation of 1..8')
    mask = 0
    for g in gaps:
        mask |= 1 << g
    return labels, mask, blocks


def with_ids(state):
    out, zi = [], 0
    for x in state:
        if is_zero(x):
            out.append(ZID + zi)
            zi += 1
        else:
            out.append(x)
    return out


def refine(base, origin):
    """Replace the zero of block j of a unit base by origin[j] zeros."""
    out, j = [], 0
    for x in base:
        if is_zero(x):
            out.extend([0] * origin[j])
            j += 1
        else:
            out.append(x)
    if j != len(origin):
        raise CheckError('origin length mismatch')
    return out


def stretch(state, picks, z):
    """Picked zero (global index picks[j]) becomes a block of 1+z[j] zeros."""
    extra = {p: z[j] for j, p in enumerate(picks)}
    out, zi = [], 0
    for x in state:
        if is_zero(x):
            out.extend([0] * (1 + extra.get(zi, 0)))
            zi += 1
        else:
            out.append(x)
    return out


def stretch_posmap(state, picks, z):
    extra = {p: z[j] for j, p in enumerate(picks)}
    pos, zi, cur = [], 0, 0
    for x in state:
        pos.append(cur)
        if is_zero(x):
            cur += 1 + extra.get(zi, 0)
            zi += 1
        else:
            cur += 1
    return pos, cur


# ------------------------------------------------------ Lemma 1 + (4)-(5)
class Profile:
    """Atomic run of `word` on `state` with stretch picks; formula (4)-(5)."""
    __slots__ = ('n', 'k', 'q', 'A', 'segs', 'cores', 'picks', 'base', 'beta',
                 'same_sign', 'used_edges', 'final_cursor', 'state')

    def __init__(self, state, word, picks=None, each_zero=False):
        labels, mask, blocks = parse_state(state)
        if each_zero:  # every zero is its own stretchable atom (section 7 resource class)
            blocks = [[i] for i in range(sum(len(b) for b in blocks))]
        k = len(blocks)
        if picks is None:
            if any(len(b) != 1 for b in blocks):
                raise CheckError('refined state without picks')
            picks = [b[0] for b in blocks]
        if len(picks) != k or any(p not in blocks[j] for j, p in enumerate(picks)):
            raise CheckError('picks do not select one zero per block')
        a = with_ids(state)
        n = len(a)
        pb = {ZID + p: j for j, p in enumerate(picks)}
        segs, cores = [], []
        d, cz = 0, [0] * k
        A = [0] * k
        q = 0
        c = 0
        used = set()
        for ch in word:
            if ch == 'L':
                j = pb.get(a[c])
                d += 1
                if j is not None:
                    cz[j] += 1
                c = c + 1 if c + 1 < n else 0
            elif ch == 'R':
                c = c - 1 if c else n - 1
                j = pb.get(a[c])
                d -= 1
                if j is not None:
                    cz[j] -= 1
            elif ch == 'X':
                c2 = c + 1 if c + 1 < n else 0
                x, y = a[c], a[c2]
                zx, zy = x >= ZID, y >= ZID
                if zx and zy:
                    raise CheckError('word swaps two zeros')
                used.add(c)
                q += 1
                nxt = [0] * k
                kind = None
                if zx:
                    j = pb.get(x)
                    if j is not None:  # X on (0^{1+z},a) -> L^z X (RX)^z
                        cz[j] += 1
                        A[j] += 1
                        kind = ('ZL', j)
                elif zy:
                    j = pb.get(y)
                    if j is not None:  # X on (a,0^{1+z}) -> X (LX)^z R^z
                        A[j] += 1
                        nxt[j] = -1
                        kind = ('LZ', j)
                segs.append((d, cz))
                cores.append(kind)
                d, cz = 0, nxt
                a[c], a[c2] = y, x
            else:
                raise CheckError('bad letter %r' % ch)
        segs.append((d, cz))
        fin = a[c:] + a[:c]
        if not is_root(fin):
            raise CheckError('word does not sort the state')
        same = True
        for d, cz in segs:
            nz = [t for t in [d] + cz if t]
            if nz and not (all(t > 0 for t in nz) or all(t < 0 for t in nz)):
                same = False
        self.n, self.k, self.q, self.A = n, k, q, A
        self.segs, self.cores, self.picks = segs, cores, list(picks)
        self.base = q + sum(abs(d) for d, _ in segs)
        self.beta = [2 * A[j] + sum(abs(cz[j]) for _, cz in segs) for j in range(k)]
        self.same_sign = same
        self.used_edges = used
        self.final_cursor = c
        self.state = list(state)

    def exact_len(self, z):
        return self.q + 2 * sum(a * t for a, t in zip(self.A, z)) + sum(
            abs(d + sum(c * t for c, t in zip(cz, z))) for d, cz in self.segs)

    def affine(self, z):
        return self.base + sum(b * t for b, t in zip(self.beta, z))

    def lift(self, z):
        parts = []
        for g, (d, cz) in enumerate(self.segs):
            net = d + sum(c * t for c, t in zip(cz, z))
            parts.append('L' * net if net >= 0 else 'R' * (-net))
            if g < len(self.cores):
                kind = self.cores[g]
                if kind is None:
                    parts.append('X')
                elif kind[0] == 'ZL':
                    parts.append('X' + 'RX' * z[kind[1]])
                else:
                    parts.append('X' + 'LX' * z[kind[1]])
        return ''.join(parts)


def z_samples(k, pairs=3):
    """z = 0, e_j, 2e_j for every j, and e_i+e_{i+1} for the first `pairs` i."""
    zs = [tuple([0] * k)]
    for j in range(k):
        for t in (1, 2):
            e = [0] * k
            e[j] = t
            zs.append(tuple(e))
    for i in range(min(pairs, k - 1)):
        e = [0] * k
        e[i] = e[i + 1] = 1
        zs.append(tuple(e))
    return zs


def literal_lift_check(prof, zs):
    """Execute lifted words on stretched inputs; return letters executed."""
    letters = 0
    for z in zs:
        w = prof.lift(z)
        v = stretch(prof.state, prof.picks, z)
        if not is_root(run(v, w)):
            raise CheckError('lifted word fails to sort at z=%s' % (z,))
        if len(w) != prof.exact_len(z):
            raise CheckError('lift length != F_W(z) at z=%s' % (z,))
        if prof.same_sign and len(w) != prof.affine(z):
            raise CheckError('lift length != affine cost at z=%s' % (z,))
        if len(w) > prof.affine(z):
            raise CheckError('lift length exceeds affine upper bound at z=%s' % (z,))
        letters += len(w)
    return letters


# ------------------------------------------------ Lemma 3 comparison transfer
def target_ranks(vec, f, cut):
    """Target rank of the element at each window index (window starts at physical cut)."""
    n = len(vec)
    nl = sum(1 for x in vec if not is_zero(x))
    R = [0] * n
    zpos, ztgt = [], sorted((f + nl + i - cut) % n for i in range(n - nl))
    for p, x in enumerate(vec):
        w = (p - cut) % n
        if is_zero(x):
            zpos.append(w)
        else:
            R[w] = (f + x - 1 - cut) % n
    zpos.sort()
    for w, t in zip(zpos, ztgt):
        R[w] = t
    return R


def inversions(R):
    n = len(R)
    return sum(1 for i in range(n) for j in range(i + 1, n) if R[i] > R[j])


def prefix_dominates(P, Q):
    """P <= Q in the sense of (9): H_P(j,s) >= H_Q(j,s) for all j,s."""
    n = len(P)
    hp = [0] * (n + 1)
    hq = [0] * (n + 1)
    for j in range(n):
        for s in range(P[j] + 1, n + 1):
            hp[s] += 1
        for s in range(Q[j] + 1, n + 1):
            hq[s] += 1
        for s in range(n + 1):
            if hp[s] < hq[s]:
                return False
    return True


def sigma(R, vec, cut, zero_global_index):
    """Inversions of a zero atom with labels, in window rank order."""
    n = len(vec)
    zi, p0 = 0, None
    for p, x in enumerate(vec):
        if is_zero(x):
            if zi == zero_global_index:
                p0 = p
            zi += 1
    w0 = (p0 - cut) % n
    r0 = R[w0]
    s = 0
    for p, x in enumerate(vec):
        if is_zero(x):
            continue
        w = (p - cut) % n
        if (w < w0 and R[w] > r0) or (w > w0 and R[w] < r0):
            s += 1
    return s


def conditional_run(vec, word, R, cut):
    """Execute rotations as given; X only when the pair is descending in target rank."""
    n = len(vec)
    rk = [R[(p - cut) % n] for p in range(n)]
    val = list(vec)
    c = 0
    swaps = rot = 0
    for ch in word:
        if ch == 'X':
            j = c + 1 if c + 1 < n else 0
            if j == cut:
                raise CheckError('swap across the cut')
            if rk[c] > rk[j]:
                rk[c], rk[j] = rk[j], rk[c]
                val[c], val[j] = val[j], val[c]
                swaps += 1
        elif ch == 'L':
            c = c + 1 if c + 1 < n else 0
            rot += 1
        else:
            c = c - 1 if c else n - 1
            rot += 1
    return val[c:] + val[:c], swaps, rot


class Reference:
    """Reference input Q (one zero per block unless picks given) with its sorting word."""

    def __init__(self, state, word, picks=None):
        self.state = list(state)
        self.word = word
        self.prof = Profile(state, word, picks)
        self.n = self.prof.n
        self.f = self.prof.final_cursor
        self.picks = self.prof.picks
        self._rq = {}

    def cut_ok(self, cut):
        return 0 <= cut < self.n and (cut - 1) % self.n not in self.prof.used_edges

    def q_data(self, cut):
        if cut not in self._rq:
            RQ = target_ranks(self.state, self.f, cut)
            iq = inversions(RQ)
            sq = [sigma(RQ, self.state, cut, p) for p in self.picks]
            self._rq[cut] = (RQ, iq, sq)
        return self._rq[cut]

    def transfer(self, P, cut):
        """Lemma 3 + formula (11).  Returns (base, beta, invP)."""
        if not self.cut_ok(cut):
            raise CheckError('cut %d is crossed by a swap' % cut)
        if len(P) != self.n or [is_zero(x) for x in P] != [is_zero(x) for x in self.state]:
            raise CheckError('P has different zero positions than Q')
        RQ, iq, sq = self.q_data(cut)
        pr = self.prof
        if pr.q != iq:
            raise CheckError('#X=%d != inv(Q)=%d' % (pr.q, iq))
        if list(pr.A) != sq:
            raise CheckError('A_j != sigma_j(Q)')
        RP = target_ranks(P, self.f, cut)
        if not prefix_dominates(RP, RQ):
            raise CheckError('P is not <= Q in prefix order (9)')
        fin, swaps, _ = conditional_run(P, self.word, RP, cut)
        ip = inversions(RP)
        if not is_root(fin):
            raise CheckError('comparison word does not sort P')
        if swaps != ip:
            raise CheckError('executed swaps %d != inv(P) %d' % (swaps, ip))
        sp = [sigma(RP, P, cut, p) for p in self.picks]
        base = pr.base - iq + ip
        beta = [pr.beta[j] - sq[j] + sp[j] for j in range(pr.k)]
        return base, beta, ip

    def literal_transfer(self, P, cut, zs, base, beta):
        """Stretch Q and P, lift Q's word, compare-execute on P; check length vs (11)."""
        letters = 0
        for z in zs:
            w = self.prof.lift(z)
            Qz = stretch(self.state, self.picks, z)
            Pz = stretch(P, self.picks, z)
            pos, nz = stretch_posmap(self.state, self.picks, z)
            cz = pos[cut]
            fz = (w.count('L') - w.count('R')) % nz
            RQ = target_ranks(Qz, fz, cz)
            RP = target_ranks(Pz, fz, cz)
            finq, sq, _ = conditional_run(Qz, w, RQ, cz)
            if not is_root(finq) or sq != w.count('X') or sq != inversions(RQ):
                raise CheckError('stretched reference not an inversion-exact sort at z=%s' % (z,))
            if not prefix_dominates(RP, RQ):
                raise CheckError('stretched P not <= Q at z=%s' % (z,))
            finp, sp, rot = conditional_run(Pz, w, RP, cz)
            if not is_root(finp) or sp != inversions(RP):
                raise CheckError('stretched comparison fails at z=%s' % (z,))
            want = base + sum(b * t for b, t in zip(beta, z))
            if self.prof.same_sign and rot + sp != want:
                raise CheckError('stretched comparison length %d != (11) %d at z=%s' % (rot + sp, want, z))
            if rot + sp > want:
                raise CheckError('stretched comparison length exceeds (11) at z=%s' % (z,))
            letters += rot + sp
        return letters


# ----------------------------------------------------------- Lemma 4 projection
def project(state, word, delete):
    """Delete the zero atoms with global indices in `delete`. Returns (child_state, child_word, keep_map)."""
    a = with_ids(state)
    n = len(a)
    dead = {ZID + p for p in delete}
    out = []
    c = 0
    for ch in word:
        if ch == 'L':
            if a[c] not in dead:
                out.append('L')
            c = c + 1 if c + 1 < n else 0
        elif ch == 'R':
            c = c - 1 if c else n - 1
            if a[c] not in dead:
                out.append('R')
        else:
            c2 = c + 1 if c + 1 < n else 0
            if a[c] not in dead and a[c2] not in dead:
                out.append('X')
            a[c], a[c2] = a[c2], a[c]
    keep = [p for p, x in enumerate(with_ids(state)) if x not in dead]
    child = [state[p] for p in keep]
    return child, ''.join(out), keep


def zero_positions(state):
    return [p for p, x in enumerate(state) if is_zero(x)]


# ------------------------------------------------------- criteria (7), (8)
def fr(x):
    return Fr(x)


def mixture_criterion(costs, weights, k):
    """costs: list of (base, beta) at unit lengths.  (7): Bbar < 31+6k, betabar_j <= 6."""
    ws = [fr(w) for w in weights]
    if any(w < 0 for w in ws) or sum(ws) != 1:
        raise CheckError('weights not a probability vector')
    B = sum(w * b for w, (b, _) in zip(ws, costs))
    beta = [sum(w * bt[j] for w, (_, bt) in zip(ws, costs)) for j in range(k)]
    ok = B < 31 + 6 * k and all(b <= 6 for b in beta)
    return ok, B, beta


def leaf_criterion(rows, box):
    """rows: list of (weight, base, beta, origin); box: list of (l, h) with h=None for +inf.  (8)."""
    k = len(box)
    ws = [fr(r[0]) for r in rows]
    if any(w < 0 for w in ws) or sum(ws) != 1:
        raise CheckError('leaf weights not a probability vector')
    for _, _, _, o in rows:
        if any(o[j] > box[j][0] for j in range(k)):
            raise CheckError('origin exceeds leaf lower corner')
    C = sum(w * (b + sum(bt[j] * (box[j][0] - o[j]) for j in range(k)))
            for w, (_, b, bt, o) in zip(ws, rows))
    g = [sum(w * r[2][j] for w, r in zip(ws, rows)) for j in range(k)]
    T = 30 + 6 * sum(l for l, _ in box)
    excess = C - T + sum(max(Fr(0), g[j] - 6) * (box[j][1] - box[j][0])
                         for j in range(k) if box[j][1] is not None)
    ok = excess < 1 and all(g[j] <= 6 for j in range(k) if box[j][1] is None)
    return ok, C, g, excess


def tree_leaves(tree, box):
    """Yield (leaf, box) with complete coverage of the parent box by construction."""
    if tree['kind'] == 'split':
        ax, t = tree['axis'], tree['cut']
        l, h = box[ax]
        if not (l <= t and (h is None or t + 1 <= h)):
            raise CheckError('split threshold outside box')
        left = list(box)
        left[ax] = (l, t)
        right = list(box)
        right[ax] = (t + 1, h)
        yield from tree_leaves(tree['left'], left)
        yield from tree_leaves(tree['right'], right)
    else:
        yield tree, box
