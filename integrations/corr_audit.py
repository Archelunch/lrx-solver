"""Independent audit of claimed corr-cert certificates from raw candidate outputs.

Deliberately does not import integrations/corr_evaluator.py or
integrations/corr_task.py. It loads its own fresh copy of the exact checker
(autoresearch/corr-cert-260924/corrcert.py, unchanged, off the trusted core)
and reimplements the JSON-safe key decoding from scratch, so a bug shared
between the scorer's corr_task.decode_cert and this module could not produce
a false agreement. Only called on m the scorer already claims PASS on; it
does not search for certificates the trusted scorer missed.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "autoresearch" / "corr-cert-260924" / "corrcert.py"
_CACHE: dict = {}


def checker():
    """A fresh, independently loaded copy of corrcert.py (module identity not shared
    with integrations.corr_task's copy)."""
    if "corrcert" not in _CACHE:
        spec = importlib.util.spec_from_file_location("_corrcert_audit", CHECKER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _CACHE["corrcert"] = mod
    return _CACHE["corrcert"]


def _key(key: str, n: int) -> tuple:
    parts = key.split(",")
    if len(parts) != n or not all(p.lstrip("-").isdigit() for p in parts):
        raise ValueError("bad coefficient key %r" % (key,))
    return tuple(int(p) for p in parts)


def _decode(m: int, raw) -> dict:
    """Independent re-implementation of the JSON-safe -> corrcert dict-of-tuples decode."""
    if not isinstance(raw, dict):
        raise ValueError("coefficients(m) must return a dict")
    for field in ("m", "Q", "lambda", "mu", "alpha", "beta", "gamma"):
        if field not in raw:
            raise ValueError("output missing field %r" % field)
    if raw["m"] != m:
        raise ValueError("output m=%r, expected %r" % (raw["m"], m))
    if type(raw["Q"]) is not int or raw["Q"] <= 0:
        raise ValueError("Q must be a positive int")
    if not isinstance(raw["lambda"], dict) or not isinstance(raw["mu"], dict):
        raise ValueError("lambda and mu must be objects")
    lam = {}
    for key, value in raw["lambda"].items():
        if type(value) is not int:
            raise ValueError("lambda[%r] is not an int" % key)
        lam[_key(key, 2)] = value
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
            table[_key(key, 3)] = value
        out[field] = table
    return out


def audit_claim(m: int, output) -> tuple[bool, str]:
    """-> (agree, reason). Call only for m the trusted scorer already claims PASS on:
    re-decode the raw candidate output independently and re-check (5)/(6)/epsilon<1
    with a freshly loaded corrcert.py. Any decode failure or exception is a
    disagreement, never a crash."""
    try:
        cert = _decode(m, output)
        res = checker().check_certificate(m, cert)
    except Exception as exc:  # checker/decode errors are disagreements, never crashes
        return False, f"{type(exc).__name__}: {exc}"
    if res["proves"]:
        return True, "ok"
    detail = f"epsilon={res['epsilon']}"
    if res["violations"]:
        detail += f", first violation {res['violations'][0]}"
    return False, detail
