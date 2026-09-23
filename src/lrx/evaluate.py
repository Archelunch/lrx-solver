"""Finite exhaustive evaluation of absolute projection caps, not universal proofs."""

import hashlib
import json
import time
from math import inf
from pathlib import Path

from .certificates import CertificateValidator
from .exact_dp import ExactHqDp, ResourceLimit
from .reference_bfs import bfs_visible
from .state import distance_upper_bound, insert_zero, state_counts


def source_hash():
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def evaluate_projection(m, r, q=None, max_cells=1_000_000):
    start = time.perf_counter()
    counts = state_counts(m, r)
    report = {
        "m": m,
        "r": r,
        "counts": counts,
        "status": "INCOMPLETE",
        "conjecture_domain": m >= 8 and r >= 2,
        "code_hash": source_hash(),
    }
    try:
        h = ExactHqDp(m, r, max_memo=max_cells)
        smaller = bfs_visible(m, r - 1, max_vertices=counts["smaller"])
        if smaller.status != "COMPLETE":
            raise ResourceLimit("Smaller radius is not certified")
        p = max(smaller.distances.values())
        q = p if q is None else q
        cap = q + m - 2
        report.update(
            projection_cap=q,
            smaller_radius=p,
            full_budget=cap,
            conjectured_budget=distance_upper_bound(m, r),
        )
        values, choices = {}, {}
        for u in h.states:
            for j in range(m + r):
                cost = h.compute_H_q(q, u, j)
                v = insert_zero(u, j)
                if v not in values or cost < values[v]:
                    values[v], choices[v] = cost, (u, j)
        finite = [cost for cost in values.values() if cost != inf]
        worst = sorted(values, key=lambda v: (-values[v], v))[:5]
        examples = []
        for v in worst:
            cost = values[v]
            u, j = choices[v]
            word = h.witness(q, u, j)
            if word is not None:
                cert = CertificateValidator(m, r).replay_word(word, (u, j))
                if not cert.terminal or cert.projection_length > q or len(word) != cost:
                    raise AssertionError("Witness failed independent replay")
            examples.append(
                {
                    "vector": v,
                    "mark": j,
                    "restricted_length": None if cost == inf else cost,
                    "no_admissible_lift": cost == inf,
                    "word": word,
                }
            )
        report.update(
            status="COMPLETE",
            covered=len(values),
            no_admissible_lift=sum(v == inf for v in values.values()),
            finite_over_budget=sum(v > cap for v in finite),
            max_finite_length=max(finite, default=None),
            max_finite_residual=max((v - cap for v in finite), default=None),
            examples=examples,
            dataset_hash=hashlib.sha256(
                json.dumps(sorted(values)).encode()
            ).hexdigest(),
        )
        report["lifting_bound_holds_on_this_graph"] = (
            report["no_admissible_lift"] == 0 and report["finite_over_budget"] == 0
        )
    except ResourceLimit as exc:
        report["reason"] = str(exc)
    report["wall_seconds"] = time.perf_counter() - start
    return report
