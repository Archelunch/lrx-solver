"""Dependency-free evaluator shims for external optimisers (GEPA, SkyDiscover,
OpenEvolve-style frameworks). Nothing here imports those packages; install
them in a separate venv (dependency authorization required) and point them at
these functions. The candidate is always JSON text, never code.

Assumed calling conventions (check against the installed version):
  SkyDiscover / OpenEvolve:  evaluate(program_path) -> {"combined_score": float, ...}
  GEPA optimize_anything:    evaluator(candidate_text) -> (score, side_info)
                             per-instance: evaluate_instance(candidate_text, graph)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.lrx.evaluator import evaluate as _evaluate  # noqa: E402
from src.lrx.feedback import compress  # noqa: E402
from src.lrx.prompt import extract_candidate  # noqa: E402

TRAIN_INSTANCES = ("m7r2", "m7r3", "m8r2", "m8r3", "m9r2", "m6r4")


def _parse(text):
    try:
        return extract_candidate(text) if "```" in text else json.loads(text)
    except ValueError as exc:
        return {"__parse_error__": str(exc)}


def evaluate_text(text, split="train"):
    """Return (score, side_info). side_info is the compact feedback dict."""
    spec = _parse(text)
    if "__parse_error__" in spec:
        return -1e6, {"valid": False, "error": spec["__parse_error__"]}
    result = _evaluate(spec, split=split)
    return float(result["score"]), compress(result)


def evaluate_instance(text, graph):
    """Score on one graph id (e.g. 'm8r2'), with the sanity tier as a gate."""
    spec = _parse(text)
    if "__parse_error__" in spec:
        return -1e6, {"valid": False, "error": spec["__parse_error__"]}
    result = _evaluate(spec, split="train", graphs={graph})
    return float(result["score"]), compress(result)


def evaluate(program_path):
    """SkyDiscover/OpenEvolve-style entry point over a JSON candidate file."""
    text = Path(program_path).read_text()
    score, side = evaluate_text(text)
    return {
        "combined_score": score,
        "feasible": bool(side.get("feasible_on_probes")),
        "feedback": json.dumps(side),
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(sys.argv[1])))
