"""Independent audit of sort-m9 finalist words (does not import sort_evaluator or sort_backends).

For every returned word it re-executes L/R/X with its own list executor, checks
whether the final vector equals (1..m, 0^r), and for sorted words re-checks
length <= T_m(n) = m(m+1)/2 + (r-1)(m-2) and excess = length - d(v), with d(v)
read from a fresh src/lrx/table_bfs.DistanceTable load (sha256-verified against
the table's meta, and against the frozen manifest's recorded table hash). Each
table is loaded once and released before the next.
"""
from __future__ import annotations

from pathlib import Path


def execute(v, word):
    a = list(v)
    for ch in word:
        if ch == "L":
            a = a[1:] + a[:1]
        elif ch == "R":
            a = a[-1:] + a[:-1]
        elif ch == "X":
            a[0], a[1] = a[1], a[0]
        else:
            raise ValueError("letter outside L, R, X")
    return a


def target(m, r):
    return list(range(1, m + 1)) + [0] * r


def T(m, r):
    return m * (m + 1) // 2 + (r - 1) * (m - 2)


def check_row(state, row, d_table):
    """None if the evaluator's claims for this row agree with the independent recomputation."""
    m, r, v = state["m"], state["r"], state["v"]
    if d_table != state["d"]:
        return f"frozen d {state['d']} != table d {d_table}"
    word = row.get("word")
    if word is None:
        return "claimed valid without a word" if row["valid"] else None
    try:
        final = execute(v, word)
    except ValueError as exc:
        return str(exc)
    valid = final == target(m, r)
    if valid != row["valid"]:
        return f"valid claim {row['valid']} but independent replay gives {valid}"
    if not valid:
        return None if list(row.get("final") or []) == final else "final vector differs"
    if len(word) != row["length"]:
        return "length differs"
    if (len(word) <= T(m, r)) != row["within"] or row["budget"] != T(m, r):
        return "within-budget claim differs"
    if len(word) - d_table != row["excess"]:
        return f"excess claim {row['excess']} != {len(word) - d_table}"
    return None


def audit(states, rows_by_arm, table_paths):
    """states: id -> frozen state. rows_by_arm: arm -> evaluator rows (with words).
    table_paths: (m, r) -> (directory, frozen table sha256). Returns arm -> summary."""
    from src.lrx.table_bfs import DistanceTable

    out = {arm: {"rows": len(rows), "checked_words": 0, "agree": 0, "disagree": []}
           for arm, rows in rows_by_arm.items()}
    keys = sorted({(states[r["id"]]["m"], states[r["id"]]["r"]) for rows in rows_by_arm.values() for r in rows})
    for key in keys:
        directory, digest = table_paths[key]
        table = DistanceTable(Path(directory), *key, verify=True)
        if table.meta["table_sha256"] != digest:
            raise ValueError(f"table {key} differs from the frozen manifest")
        for arm, rows in rows_by_arm.items():
            for row in rows:
                s = states[row["id"]]
                if (s["m"], s["r"]) != key:
                    continue
                why = check_row(s, row, table.distance(s["v"]))
                out[arm]["checked_words"] += row.get("word") is not None
                if why is None:
                    out[arm]["agree"] += 1
                else:
                    out[arm]["disagree"].append({"id": row["id"], "reason": why})
        del table
    return out
