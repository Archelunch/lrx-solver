"""Tiny self-contained registry + tables for evaluator/campaign tests."""

import json
import os
import tempfile
from pathlib import Path

from src.lrx import evaluator

TINY_REGISTRY = {
    "version": 1,
    "probe": {"random": 30, "hard": 10, "hard_layers": 2},
    "graphs": [
        {"m": 3, "r": 2, "role": "sanity", "table": True},
        {"m": 2, "r": 3, "role": "sanity", "table": True},
        {"m": 4, "r": 2, "role": "train", "table": True},
        {"m": 3, "r": 3, "role": "train", "table": True},
        {"m": 4, "r": 3, "role": "heldout", "table": True},
        {"m": 5, "r": 3, "role": "heldout", "table": False},
    ],
}


class TinyData:
    """Context manager: builds tiny tables in a temp dir and points the
    evaluator (and spawned workers, via env vars) at them."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.registry = base / "registry.json"
        self.lock = base / "tables.lock.json"
        self.tables = base / "generated"
        self.registry.write_text(json.dumps(TINY_REGISTRY))
        self.saved = {
            k: os.environ.get(k)
            for k in ("LRX_REGISTRY", "LRX_TABLES_LOCK", "LRX_TABLE_DIR")
        }
        os.environ["LRX_REGISTRY"] = str(self.registry)
        os.environ["LRX_TABLES_LOCK"] = str(self.lock)
        os.environ["LRX_TABLE_DIR"] = str(self.tables)
        evaluator._TABLES.clear()
        evaluator._PROBES.clear()
        evaluator.build_registry_tables()
        self.base = base
        return self

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        evaluator._TABLES.clear()
        evaluator._PROBES.clear()
        self.tmp.cleanup()
