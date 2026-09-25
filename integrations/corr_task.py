"""corr-cert instances (autoresearch/corr-cert-260924/TASK.md): dev/holdout m
sets and the JSON-safe encoding of a Theorem-3 certificate.

corrcert.py's cert dict uses Python tuple keys ((a, b) for lambda, (a, b, c)
for alpha/beta/gamma) and an int key for mu. Those are not valid JSON object
keys, and a candidate program only ever returns JSON-safe data (its output is
read back across a process boundary as plain data, never trusted code). So a
candidate's `coefficients(m) -> dict` must return the *encoded* form:

  {"m": m, "Q": Q,
   "lambda": {"a,b": int, ...},            key "a,b" for each pair a<b
   "mu": {"a": [mu_a(1), ..., mu_a(m-1)], ...},   key "a" for each 0<=a<m
   "alpha"/"beta"/"gamma": {"a,b,c": [v(1), ..., v(m-1)], ...}}

Keys are comma-joined decimal integers with no spaces, e.g. "0,3" or "1,4,7".
`decode_cert` turns this into corrcert's dict-of-tuples form (raising
ValueError on any shape mismatch, never silently repairing); `encode_cert` is
the inverse, used to write the seed program's literal output and to build
frozen manifests. This module is pure data plumbing; it does not run
untrusted code and does not score anything.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

# corrcert.py lives under a directory with hyphens, which is not a valid
# Python package name, so it cannot be imported by dotted path. Load it by
# file path instead (mirrors how lift/official backends load sibling code).
import importlib.util as _ilu

_CORRCERT_PATH = Path(__file__).resolve().parents[1] / "autoresearch" / "corr-cert-260924" / "corrcert.py"


def _load_corrcert():
    spec = _ilu.spec_from_file_location("corrcert", _CORRCERT_PATH)
    module = _ilu.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


corrcert = _load_corrcert()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _key(*parts) -> str:
    return ",".join(str(int(p)) for p in parts)


def _parse_key(key, n):
    parts = key.split(",")
    if len(parts) != n or not all(p.lstrip("-").isdigit() for p in parts):
        raise ValueError("bad coefficient key %r" % (key,))
    return tuple(int(p) for p in parts)


def encode_cert(cert: dict) -> dict:
    """corrcert dict-of-tuples -> JSON-safe dict-of-strings (candidate output shape)."""
    m = cert["m"]
    return {
        "m": m, "Q": cert["Q"],
        "lambda": {_key(a, b): int(v) for (a, b), v in cert["lambda"].items()},
        "mu": {str(a): [int(x) for x in v] for a, v in cert["mu"].items()},
        "alpha": {_key(*t): [int(x) for x in v] for t, v in cert["alpha"].items()},
        "beta": {_key(*t): [int(x) for x in v] for t, v in cert["beta"].items()},
        "gamma": {_key(*t): [int(x) for x in v] for t, v in cert["gamma"].items()},
    }


def decode_cert(m: int, raw) -> dict:
    """JSON-safe dict-of-strings -> corrcert dict-of-tuples. Raises ValueError, never repairs."""
    if not isinstance(raw, dict):
        raise ValueError("coefficients(m) must return a dict")
    for field in ("m", "Q", "lambda", "mu", "alpha", "beta", "gamma"):
        if field not in raw:
            raise ValueError("coefficients(m) output missing field %r" % field)
    if raw["m"] != m:
        raise ValueError("coefficients(m) returned m=%r, expected %r" % (raw["m"], m))
    if type(raw["Q"]) is not int or raw["Q"] <= 0:
        raise ValueError("Q must be a positive int")
    if not isinstance(raw["lambda"], dict) or not isinstance(raw["mu"], dict):
        raise ValueError("lambda and mu must be objects")
    lam = {}
    for key, value in raw["lambda"].items():
        if type(value) is not int:
            raise ValueError("lambda[%r] is not an int" % key)
        lam[_parse_key(key, 2)] = value
    mu = {}
    for key, value in raw["mu"].items():
        if not key.lstrip("-").isdigit() or not isinstance(value, list) or any(type(x) is not int for x in value):
            raise ValueError("mu[%r] is not an int-list keyed by a plain index" % key)
        mu[int(key)] = value
    out = {"m": m, "Q": raw["Q"], "lambda": lam, "mu": mu, "alpha": {}, "beta": {}, "gamma": {}}
    for field in ("alpha", "beta", "gamma"):
        if not isinstance(raw[field], dict):
            raise ValueError("%s must be an object" % field)
        table = {}
        for key, value in raw[field].items():
            if not isinstance(value, list) or any(type(x) is not int for x in value):
                raise ValueError("%s[%r] is not an int list" % (field, key))
            table[_parse_key(key, 3)] = value
        out[field] = table
    return out


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


# --------------------------------------------------------------- dev/holdout
DEVELOPMENT_M = list(range(4, 13))   # 4..12
HOLDOUT_M = list(range(13, 21))      # 13..20


def load_m_set(path) -> list[int]:
    """Load a frozen {"schema", "set", "m_values": [...]} file; validate shape."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != "lrx-corrcert-m-set-v1":
        raise ValueError("unrecognized m-set schema")
    values = data["m_values"]
    if not isinstance(values, list) or not values or any(type(v) is not int or v < 4 for v in values):
        raise ValueError("m_values must be a nonempty list of ints >= 4")
    return values


def write_m_set(path, set_name: str, m_values) -> None:
    Path(path).write_text(json.dumps(
        {"schema": "lrx-corrcert-m-set-v1", "set": set_name, "m_values": list(m_values)},
        indent=1, sort_keys=True) + "\n", encoding="utf-8")


def guard_not_holdout(path: Path) -> None:
    """Refuse to load anything named/pathed like the holdout set. Mirrors lift's
    `_verify_inputs` guard: engines and proposers may only ever see development."""
    if path.name == "holdout.json" or "holdout" in str(path):
        raise ValueError("engines and proposers may load only the frozen development m-set, never holdout")
