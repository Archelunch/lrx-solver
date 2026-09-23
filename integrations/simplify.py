"""Conservative search-side JSON rewrites, interpreted by the existing DSL."""

from src.lrx.dsl import TOKEN_VARS


def _token_dependent(expr):
    if isinstance(expr, str):
        return expr in TOKEN_VARS
    return isinstance(expr, list) and any(_token_dependent(x) for x in expr[1:])


def simplify_positions(value):
    """Replace token-independent position sums with guarded direct lookups.

    sum_t (t == E ? position(t) : 0) = max(0, pos(E)). The max preserves
    the sum's zero for absent labels, because pos returns -1 for those.
    Expressions containing token variables are deliberately left alone.
    """
    if isinstance(value, dict):
        return {key: simplify_positions(item) for key, item in value.items()}
    if not isinstance(value, list):
        return value
    value = [simplify_positions(item) for item in value]
    if len(value) != 2 or value[0] != "sum_tokens":
        return value
    body = value[1]
    if not isinstance(body, list) or len(body) != 4 or body[0] != "if" or body[2:] != ["p", 0]:
        return value
    condition = body[1]
    if not isinstance(condition, list) or len(condition) != 3 or condition[:2] != ["eq", "t"]:
        return value
    expr = condition[2]
    if _token_dependent(expr):
        return value
    return ["max", 0, ["pos", expr]]
