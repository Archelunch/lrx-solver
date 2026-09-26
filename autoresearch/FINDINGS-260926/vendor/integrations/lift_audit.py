"""Independent audit of claimed lift certificates from raw candidate outputs.

Deliberately does not import integrations/lift_evaluator.py, lift_task.py or
lrx_m.py. It loads the independent m=8 checker
(autoresearch/verify-m8-260924/checker/lrxm8.py) as a fresh module with M set
to the child label count, rebuilds each child unit base from the parent data,
replays every returned word literally, checks the Lemma 1 lift at z = 0, e_j,
2e_j and every adjacent pair e_j + e_{j+1}, and checks the claimed mixture
witness exactly: weights >= 0 summing to 1, weighted base < 39+7k (in general
T_m(unit)+1), every weighted slope <= m-2. A witness suffices for a claim; the
audit does not search for certificates the trusted scorer missed.
"""
from fractions import Fraction as Fr
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "autoresearch" / "verify-m8-260924" / "checker" / "lrxm8.py"
_CACHE = {}


def checker(m):
    """A private copy of lrxm8 with M = m (its logic is otherwise unchanged)."""
    if m not in _CACHE:
        spec = importlib.util.spec_from_file_location(f"_lrxm8_audit_m{m}", CHECKER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.M = m
        _CACHE[m] = mod
    return _CACHE[m]


def child_of(inst):
    """Rebuild (labels, mask, unit base, k) of the child from the parent and insertion."""
    labels, mask = list(inst["parent"]["labels"]), inst["parent"]["mask"]
    m, i, split = len(labels), inst["insert"]["position"], inst["insert"]["split"]
    gap_full = bool(mask >> i & 1)
    if (split == "none") == gap_full or split not in ("none", "left", "right", "both"):
        raise ValueError("split inconsistent with parent gap")
    new = [x for x in labels[:i]] + [m + 1] + labels[i:]
    bits = [(mask >> j) & 1 for j in range(m + 1)]
    child_bits = bits[:i] + {"none": [0, 0], "left": [1, 0], "right": [0, 1], "both": [1, 1]}[split] + bits[i + 1:]
    cmask = sum(b << j for j, b in enumerate(child_bits))
    C = checker(m + 1)
    return new, cmask, C.base_vector(new, cmask), sum(child_bits)


def budget(m, k):
    return m * (m + 1) // 2 + (k - 1) * (m - 2)


def audit_claim(inst, output, claim):
    """-> (agree: bool, reason: str). `output` is the raw lift() return; `claim` is the
    scorer's certificate {'words': [...], 'weights': [...]}."""
    try:
        labels, cmask, base, k = child_of(inst)
        m = len(labels)
        C = checker(m)
        if base != inst["child"]["unit_base"] or k != inst["child"]["k"]:
            return False, "instance child disagrees with independent reconstruction"
        if inst["child"]["budget_unit"] != budget(m, k):
            return False, "instance budget disagrees with T_m"
        if not isinstance(output, dict) or not isinstance(output.get("words"), list):
            return False, "raw output has no word list"
        words = output["words"]
        if not 1 <= len(words) <= 16 or any(type(w) is not str or len(w) > 4000 or set(w) - set("LRX")
                                            for w in words):
            return False, "raw output violates word caps"
        costs = {}
        zs = C.z_samples(k, pairs=k - 1)
        for w in words:
            prof = C.Profile(base, w)  # raises unless it sorts without a zero-zero swap
            C.literal_lift_check(prof, zs)
            costs[w] = (prof.base, prof.beta)
        ws = [Fr(x) for x in claim["weights"]]
        if len(ws) != len(claim["words"]) or any(x < 0 for x in ws) or sum(ws) != 1:
            return False, "claimed weights are not a probability vector"
        if any(w not in costs for w in claim["words"]):
            return False, "claimed word not among the returned words"
        B = sum(x * costs[w][0] for x, w in zip(ws, claim["words"]))
        slopes = [sum(x * costs[w][1][j] for x, w in zip(ws, claim["words"])) for j in range(k)]
        if not B < budget(m, k) + 1:
            return False, f"weighted base {B} not < {budget(m, k) + 1}"
        if any(s > m - 2 for s in slopes):
            return False, f"weighted slope above {m - 2}"
        return True, "ok"
    except Exception as exc:  # checker errors are disagreements, never crashes
        return False, f"{type(exc).__name__}: {exc}"
