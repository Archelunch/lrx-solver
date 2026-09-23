"""Optional cache around the unchanged evaluator; never caches held-out data.

Only completed evaluations are reusable. Time-limited evaluations must be
retried, not frozen into the archive. Cache files are derived evidence, not
certificates, and are namespaced by evaluator, data paths and candidate.
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path

from src.lrx import evaluator
from src.lrx.candidates import Candidate, canonical_json


def evaluate_cached(spec, split="train", cache_dir=None):
    if not cache_dir or split not in ("sanity", "train"):
        return evaluator.evaluate(spec, split=split)
    cand = Candidate(spec)
    identity = [cand.hash, split, evaluator.evaluator_hash(),
                [str(p.resolve()) for p in evaluator.paths()]]
    key = hashlib.sha256(canonical_json(identity).encode()).hexdigest()
    path = Path(cache_dir) / (key + ".json")
    try:
        envelope = json.loads(path.read_text())
        result = envelope["result"]
        checksum = hashlib.sha256(canonical_json(result).encode()).hexdigest()
        if (envelope["key"] == key and envelope["sha256"] == checksum
                and result.get("candidate_hash") == cand.hash):
            return dict(result, cache_hit=True, source_seconds=result.get("seconds"), seconds=0.0)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    result = evaluator.evaluate(spec, split=split)
    if result.get("valid") and not any(g.get("incomplete") for g in result.get("graphs", [])):
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {"key": key, "result": result,
                    "sha256": hashlib.sha256(canonical_json(result).encode()).hexdigest()}
        with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as f:
            temporary = f.name
            json.dump(envelope, f)
        os.replace(temporary, path)
    return dict(result, cache_hit=False)
