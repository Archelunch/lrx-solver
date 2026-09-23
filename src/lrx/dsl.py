"""JSON expression DSL for candidates. Interpreted, never eval'd or exec'd.

Expression forms:
  integer                     constant in [-10^4, 10^4]
  "name"                      state variable (see STATE_VARS / TOKEN_VARS)
  ["op", arg, ...]            operator application (see OPS)

Token aggregates ["sum_tokens", e], ["max_tokens", e], ["min_tokens", e],
["count_tokens", e] evaluate e once per token t=1..m with TOKEN_VARS bound.
Booleans are integers 0/1. Division/mod by a non-positive value is an
evaluation error (candidate rejected on that state, never silently fixed).
"""

MAX_DEPTH = 10
MAX_NODES = 80
MAX_CONST = 10_000

STATE_VARS = {
    "n": "length",
    "m": "distinct tokens",
    "r": "number of zeros",
    "a": "value at position 0 (0 = zero)",
    "b": "value at position 1",
    "last": "value at position n-1",
    "pos1": "position of token 1",
    "fixed": "tokens at their target position",
    "hamming": "positions differing from the root",
    "inv": "inversions among tokens read from position 0",
    "cinv": "min over cyclic rotations of token-sequence inversions",
    "cdes": "cyclic descents of the cyclic token sequence",
    "disp_sum": "sum over tokens of circular distance to target",
    "disp_max": "max over tokens of circular distance to target",
    "cw_sum": "sum over tokens of clockwise (R-direction) distance to target",
    "ccw_sum": "sum over tokens of counter-clockwise distance to target",
    "zeros_block": "1 if all zeros are circularly contiguous",
    "zero_gap_max": "largest circular gap between consecutive zeros",
    "zero_gap_min": "smallest circular gap between consecutive zeros",
    "zero_first": "position of the first zero (-1 if r=0)",
    "zeros_in_prefix": "zeros among positions 0..m-1",
    "csorted": "1 if the vector is a rotation of the root",
    "rot_dist": "min L/R moves to root if csorted else -1",
    "is_root": "1 if the vector is the root",
    "T": "conjectured budget T_m(n)",
    "rot": "rules only: net L-count mod n since start",
    "steps": "rules only: moves emitted so far",
    "prev": "rules only: previous action (0 none, 1 L, 2 R, 3 X)",
    "r0": "rules register",
    "r1": "rules register",
    "r2": "rules register",
    "r3": "rules register",
}
TOKEN_VARS = {
    "t": "token label",
    "p": "token position",
    "tgt": "target position t-1",
    "cw": "(p - tgt) mod n",
    "ccw": "(tgt - p) mod n",
    "dmin": "min(cw, ccw)",
    "at_tgt": "1 if p == tgt",
    "gap_next": "(pos(t+1) - p) mod n, 0 for t=m",
    "zeros_next": "zeros strictly between p and pos(t+1) clockwise, 0 for t=m",
}
REGISTERS = ("r0", "r1", "r2", "r3")
ACTIONS = {"L": 1, "R": 2, "X": 3}

_BIN = {
    "sub": lambda x, y: x - y,
    "lt": lambda x, y: int(x < y),
    "le": lambda x, y: int(x <= y),
    "gt": lambda x, y: int(x > y),
    "ge": lambda x, y: int(x >= y),
    "eq": lambda x, y: int(x == y),
    "ne": lambda x, y: int(x != y),
}
_NARY = {
    "add": sum,
    "max": max,
    "min": min,
    "and": lambda xs: int(all(xs)),
    "or": lambda xs: int(any(xs)),
}
_UNARY = {"neg": lambda x: -x, "abs": abs, "not": lambda x: int(not x)}
OPS = (
    sorted(_BIN)
    + sorted(_NARY)
    + sorted(_UNARY)
    + ["mul", "floordiv", "mod", "if", "at", "pos", "cw_of", "ccw_of", "dmin_of"]
    + ["sum_tokens", "max_tokens", "min_tokens", "count_tokens"]
)
_AGG = {"sum_tokens", "max_tokens", "min_tokens", "count_tokens"}


class DslError(ValueError):
    pass


class EvalError(ArithmeticError):
    pass


def compile_expr(expr, allow_token=False, allowed_vars=None):
    """Validate and compile an expression into a closure f(env) -> int."""
    count = [0]
    fn = _compile(expr, 0, allow_token, count, allowed_vars)
    return fn


def _compile(e, depth, token, count, allowed):
    count[0] += 1
    if count[0] > MAX_NODES:
        raise DslError(f"expression exceeds {MAX_NODES} nodes")
    if depth > MAX_DEPTH:
        raise DslError(f"expression exceeds depth {MAX_DEPTH}")
    if type(e) is bool:
        e = int(e)
    if type(e) is int:
        if abs(e) > MAX_CONST:
            raise DslError("constant out of range")
        return lambda env, c=e: c
    if isinstance(e, str):
        if e in TOKEN_VARS:
            if not token:
                raise DslError(f"token variable {e!r} outside a *_tokens aggregate")
            return lambda env, k=e: env.token[k]
        if e not in STATE_VARS or (allowed is not None and e not in allowed):
            raise DslError(f"unknown variable {e!r}")
        return lambda env, k=e: env[k]
    if not isinstance(e, list) or not e or not isinstance(e[0], str):
        raise DslError(f"malformed expression {e!r:.60}")
    op, args = e[0], e[1:]
    inner_token = token or op in _AGG
    if op in _AGG and token:
        raise DslError("nested token aggregates are not allowed")
    sub = [_compile(a, depth + 1, inner_token, count, allowed) for a in args]

    def arity(k):
        if len(sub) != k:
            raise DslError(f"{op} takes {k} arguments")

    if op in _BIN:
        arity(2)
        f, x, y = _BIN[op], sub[0], sub[1]
        return lambda env: f(x(env), y(env))
    if op in _NARY:
        if not sub:
            raise DslError(f"{op} needs arguments")
        f = _NARY[op]
        if op == "and":
            return lambda env: int(all(s(env) for s in sub))
        if op == "or":
            return lambda env: int(any(s(env) for s in sub))
        return lambda env: f([s(env) for s in sub])
    if op in _UNARY:
        arity(1)
        f, x = _UNARY[op], sub[0]
        return lambda env: f(x(env))
    if op == "mul":
        arity(2)
        x, y = sub

        def mul(env):
            value = x(env) * y(env)
            if abs(value) > 10**12:
                raise EvalError("overflow")
            return value

        return mul
    if op in ("floordiv", "mod"):
        arity(2)
        x, y = sub
        is_div = op == "floordiv"

        def div(env):
            d = y(env)
            if d <= 0:
                raise EvalError("non-positive divisor")
            return x(env) // d if is_div else x(env) % d

        return div
    if op == "if":
        arity(3)
        c, x, y = sub
        return lambda env: x(env) if c(env) else y(env)
    if op == "at":
        arity(1)
        x = sub[0]
        return lambda env: env.v[x(env) % env.n]
    if op == "pos":
        arity(1)
        x = sub[0]
        return lambda env: env.pos_of(x(env))
    if op in ("cw_of", "ccw_of", "dmin_of"):
        arity(1)
        x = sub[0]
        return lambda env, kind=op: env.dist_of(x(env), kind)
    if op in _AGG:
        arity(1)
        x = sub[0]
        if op == "sum_tokens":
            return lambda env: sum(x(env.bind(t)) for t in env.tokens())
        if op == "max_tokens":
            return lambda env: max(x(env.bind(t)) for t in env.tokens())
        if op == "min_tokens":
            return lambda env: min(x(env.bind(t)) for t in env.tokens())
        return lambda env: sum(1 for t in env.tokens() if x(env.bind(t)))
    raise DslError(f"unknown operator {op!r}")


def budget(m, r):
    return m * (m + 1) // 2 + (r - 1) * (m - 2)


class Env:
    """Lazy per-state feature environment. Features are computed on demand."""

    __slots__ = ("v", "n", "m", "r", "_cache", "_pos", "extra", "token")

    def __init__(self, v, m, r, extra=None):
        self.v = v
        self.n = len(v)
        self.m = m
        self.r = r
        self._cache = {}
        self._pos = None
        self.extra = extra or {}
        self.token = None

    def positions(self):
        if self._pos is None:
            pos = [0] * (self.m + 1)
            for i, x in enumerate(self.v):
                if x:
                    pos[x] = i
            self._pos = pos
        return self._pos

    def pos_of(self, t):
        if 1 <= t <= self.m:
            return self.positions()[t]
        return -1

    def dist_of(self, t, kind):
        """Circular distance of token t to its target; 0 for zeros/out of range."""
        if not 1 <= t <= self.m:
            return 0
        d = (self.positions()[t] - (t - 1)) % self.n
        if kind == "cw_of":
            return d
        if kind == "ccw_of":
            return (self.n - d) % self.n
        return min(d, self.n - d)

    def tokens(self):
        return range(1, self.m + 1)

    def bind(self, t):
        self.token = _TokenView(self, t)
        return self

    def __getitem__(self, key):
        if key in self.extra:
            return self.extra[key]
        cache = self._cache
        if key not in cache:
            cache[key] = _FEATURES[key](self)
        return cache[key]


class _TokenView:
    __slots__ = ("env", "t", "_c")

    def __init__(self, env, t):
        self.env, self.t, self._c = env, t, None

    def __getitem__(self, key):
        env, t = self.env, self.t
        n, pos = env.n, env.positions()
        p = pos[t]
        tgt = t - 1
        if key == "t":
            return t
        if key == "p":
            return p
        if key == "tgt":
            return tgt
        if key == "cw":
            return (p - tgt) % n
        if key == "ccw":
            return (tgt - p) % n
        if key == "dmin":
            d = (p - tgt) % n
            return min(d, n - d)
        if key == "at_tgt":
            return int(p == tgt)
        if key == "gap_next":
            return 0 if t == env.m else (pos[t + 1] - p) % n
        if key == "zeros_next":
            if t == env.m:
                return 0
            gap = (pos[t + 1] - p) % n
            return sum(1 for k in range(1, gap) if env.v[(p + k) % n] == 0)
        raise KeyError(key)


def _token_seq(env):
    return [x for x in env.v if x]


def _inversions(seq):
    count = 0
    for i, x in enumerate(seq):
        for y in seq[i + 1 :]:
            if x > y:
                count += 1
    return count


def _cinv(env):
    seq = _token_seq(env)
    m = len(seq)
    base = _inversions(seq)
    best = base
    # Rotating the first element x to the back changes inversions by m+1-2x.
    for x in seq[:-1]:
        base += m + 1 - 2 * x
        best = min(best, base)
    return best


def _cdes(env):
    seq = _token_seq(env)
    return sum(1 for i in range(len(seq)) if seq[(i + 1) % len(seq)] < seq[i])


def _zero_positions(env):
    return [i for i, x in enumerate(env.v) if x == 0]


def _zero_gaps(env):
    z = _zero_positions(env)
    if not z:
        return []
    return [(z[(i + 1) % len(z)] - z[i]) % env.n or env.n for i in range(len(z))]


def _csorted(env):
    n, v = env.n, env.v
    p = env.positions()[1]
    root = tuple(range(1, env.m + 1)) + (0,) * env.r
    return int(all(v[(p + i) % n] == root[i] for i in range(n)))


def _rot_dist(env):
    if not env["csorted"]:
        return -1
    p = env.positions()[1]
    return min(p, env.n - p)


def _disp(env, mode):
    n, pos = env.n, env.positions()
    out = []
    for t in range(1, env.m + 1):
        d = (pos[t] - (t - 1)) % n
        out.append(
            d if mode == "cw" else (n - d) % n if mode == "ccw" else min(d, n - d)
        )
    return out


_FEATURES = {
    "n": lambda e: e.n,
    "m": lambda e: e.m,
    "r": lambda e: e.r,
    "a": lambda e: e.v[0],
    "b": lambda e: e.v[1],
    "last": lambda e: e.v[-1],
    "pos1": lambda e: e.positions()[1],
    "fixed": lambda e: sum(1 for t in range(1, e.m + 1) if e.positions()[t] == t - 1),
    "hamming": lambda e: sum(
        1 for i, x in enumerate(e.v) if x != (i + 1 if i < e.m else 0)
    ),
    "inv": lambda e: _inversions(_token_seq(e)),
    "cinv": _cinv,
    "cdes": _cdes,
    "disp_sum": lambda e: sum(_disp(e, "min")),
    "disp_max": lambda e: max(_disp(e, "min")),
    "cw_sum": lambda e: sum(_disp(e, "cw")),
    "ccw_sum": lambda e: sum(_disp(e, "ccw")),
    "zeros_block": lambda e: int(e.r == 0 or max(_zero_gaps(e)) == e.n - e.r + 1),
    "zero_gap_max": lambda e: max(_zero_gaps(e), default=0),
    "zero_gap_min": lambda e: min(_zero_gaps(e), default=0),
    "zero_first": lambda e: next((i for i, x in enumerate(e.v) if x == 0), -1),
    "zeros_in_prefix": lambda e: sum(1 for x in e.v[: e.m] if x == 0),
    "csorted": _csorted,
    "rot_dist": _rot_dist,
    "is_root": lambda e: int(e.v == tuple(range(1, e.m + 1)) + (0,) * e.r),
    "T": lambda e: budget(e.m, e.r),
}


def features(v, m, r):
    """All state-level features as a dict (for feedback and statistics)."""
    env = Env(tuple(v), m, r)
    return {k: env[k] for k in _FEATURES}
