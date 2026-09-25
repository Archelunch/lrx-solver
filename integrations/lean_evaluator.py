"""Trusted Lean evaluator for Track 3 (SPEC-track3 section 5). Search side; recommend TRUSTED.

Stages, each a separate Seatbelt process with no network and a wall limit:
  preflight  fence/size, lexical ban, lean.lock.json hashes, pinned `lean --version`
  A          `lean --json -o Cand.olean Cand.lean` (trusted header + body + footer with
             `#print axioms Cand.<id>`). If a block fails, it is blanked and A reruns
             (at most `max_passes`); only the pruned body that compiles is credited.
  B          `leanchecker Cand`: kernel replay of every declaration in the olean.
  C          trusted `lrxaudit <nonce> Cand` (no candidate initializers): exact statement
             types, axioms recollected from the constants, reachable helper theorems.
A target or milestone is closed only if stage C says closed AND its footer
`#print axioms` (Lean's own output, pinned to the footer line) lists only
propext, Classical.choice, Quot.sound. The footer covers every id the body declares
(any layout); an id whose footer line errors is dropped from the footer and A reruns
without penalty. Timeouts and memory kills are INCOMPLETE. Results are cached only
for sandboxed runs, keyed on the evaluator source hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import time

from integrations import lean_task as T
from integrations import lean_worker as W

VERSION = "lean-eval-1"
CONTRACT = ("body = last ```lean block or raw text; trusted header/footer; bans per lean_task.BANS; "
            "credit = audit closed and footer axioms within {propext, Classical.choice, Quot.sound}; "
            "score T + M/5 + A/20 - P; INVALID/INCOMPLETE = -1")
PACKET_MARK = "LEAN_PACKET_V1"
PACKET_MAX = 3000
DEFAULTS = {"forbid_sorry": False, "disabled_bans": [], "wall_a": 60.0, "wall_b": 60.0, "wall_c": 30.0,
            "max_passes": 3, "memory_mb": 4096}
_TOOLCHAIN_OK = {}


def evaluator_hash() -> str:
    h = hashlib.sha256()
    for name in ("lean_task.py", "lean_worker.py", "lean_evaluator.py"):
        h.update((Path(__file__).parent / name).read_bytes())
    return h.hexdigest()


def check_toolchain() -> str:
    tc = T.toolchain_dir()
    if tc not in _TOOLCHAIN_OK:
        out = subprocess.run([str(tc / "bin" / "lean"), "--version"], capture_output=True, text=True, timeout=30,
                             env={"PATH": "/usr/bin:/bin"})
        version = out.stdout.strip()
        if not version.startswith(T.TOOLCHAIN_VERSION_PREFIX):
            raise RuntimeError(f"Lean toolchain drift: {version!r} is not {T.TOOLCHAIN}")
        _TOOLCHAIN_OK[tc] = version
    return _TOOLCHAIN_OK[tc]


def _env(home: Path, lean_path) -> dict:
    tc = T.toolchain_dir()
    return {"PATH": f"{tc / 'bin'}:/usr/bin:/bin", "HOME": str(home), "TMPDIR": str(home),
            "LEAN_PATH": ":".join(map(str, lean_path)), "LANG": "C"}


def _sanitize(text: str) -> str:
    return re.sub(r"/(?:Users|private|tmp|var|opt)/[^\s'\"`)]*", "<path>", text)


# -------------------------------------------------------------------- stages
def _stage_a(body: str, work: Path, cfg: dict, require_sandbox: bool, footer_ids=None) -> tuple[dict, dict, dict]:
    tc, build = T.toolchain_dir(), T.PROJECT / ".lake" / "build" / "lib" / "lean"
    text, footer_map = T.assemble(body, footer_ids)
    (work / "Cand.lean").write_text(text)
    lean = tc / "bin" / "lean"
    profile = W.lean_profile(exec_paths=[lean], read_paths=[tc, build], write_paths=[work]) if require_sandbox else None
    run = W.run([lean, "--json", "-j", "1", "-M", str(cfg["memory_mb"]), "-o", "Cand.olean", "Cand.lean"],
                cwd=work, env=_env(work, [tc / "lib" / "lean", build]), profile_text=profile,
                wall=cfg["wall_a"], rss_limit_mb=cfg["memory_mb"] + 512, require_sandbox=require_sandbox)
    parsed = T.parse_messages(run["stdout"].splitlines(), footer_map, body.count("\n") + 1)
    return run, parsed, footer_map


def _stage_b(work_a: Path, work_b: Path, cfg: dict, require_sandbox: bool) -> dict:
    tc, build = T.toolchain_dir(), T.PROJECT / ".lake" / "build" / "lib" / "lean"
    execs = [tc / "bin" / "leanchecker", tc / "bin" / "lean"]
    profile = (W.lean_profile(exec_paths=execs, read_paths=[tc, build, work_a], write_paths=[work_b],
                              allow_fork=True) if require_sandbox else None)
    return W.run([execs[0], "Cand"], cwd=work_b, env=_env(work_b, [build, work_a]), profile_text=profile,
                 wall=cfg["wall_b"], rss_limit_mb=cfg["memory_mb"] + 512, require_sandbox=require_sandbox)


def _stage_c(work_a: Path, work_c: Path, cfg: dict, require_sandbox: bool) -> tuple[dict, dict | None]:
    tc, build = T.toolchain_dir(), T.PROJECT / ".lake" / "build" / "lib" / "lean"
    audit = T.PROJECT / ".lake" / "build" / "bin" / "lrxaudit"
    nonce = secrets.token_hex(16)  # generated after stage A has been killed
    profile = (W.lean_profile(exec_paths=[audit], read_paths=[tc, build, work_a], write_paths=[work_c])
               if require_sandbox else None)
    run = W.run([audit, nonce, "Cand"], cwd=work_c, env=_env(work_c, [tc / "lib" / "lean", build, work_a]),
                profile_text=profile, wall=cfg["wall_c"], rss_limit_mb=cfg["memory_mb"] + 512,
                require_sandbox=require_sandbox)
    lines = run["stdout"].strip().splitlines()
    try:
        verdict = json.loads(lines[-1]) if lines else None
    except ValueError:
        verdict = None
    if not isinstance(verdict, dict) or verdict.get("nonce") != nonce or verdict.get("module") != "Cand":
        verdict = None
    return run, verdict


def _errors(parsed: dict) -> list[dict]:
    return [m for m in parsed["messages"] if m["severity"] == "error"]


def _drop_starts(body: str, errs) -> set:
    """Blocks to blank: every block holding an error; an error past the body (e.g. an
    unterminated comment swallowing `end Cand`) blames the last nonblank block.
    Footer-line errors never reach here (lean_task.parse_messages keeps them apart)."""
    blocks = T.blocks(body)
    nonblank = [b for b in blocks if any(ln.strip() for ln in body.split("\n")[b["start"] - 1:b["end"]])]
    body_lines = body.count("\n") + 1
    drop = set()
    for e in errs:
        line = e["line"]
        if 1 <= line <= body_lines:
            b = T.block_of_line(body, line)
        else:
            b = nonblank[-1] if line > body_lines and nonblank else None
        if b is None:
            return set()
        drop.add(b["start"])
    return drop


# ------------------------------------------------------------------ evaluate
def _cache_key(body: str, cfg: dict, lock_digest: str, version: str, sandboxed: bool = True) -> str:
    material = {"toolchain": version, "lock": lock_digest, "evaluator": VERSION, "config": cfg, "body": body,
                "evaluator_sha256": evaluator_hash(), "sandboxed": bool(sandboxed)}
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()


def _invalid(reason, **extra) -> dict:
    out = {"status": "INVALID", "reason": reason, "combined_score": -1.0, "statuses": {i: "invalid" for i in T.IDS},
           "closed_targets": [], "closed_milestones": [], "aux": [], "messages": [], "dropped_blocks": []}
    out.update(extra)
    return out


def evaluate(source: str, *, cache_dir=None, config=None, require_sandbox=True, response=False) -> dict:
    """Score one candidate body (or a model response when `response`)."""
    cfg = dict(DEFAULTS, **(config or {}))
    cfg["disabled_bans"] = sorted(cfg["disabled_bans"])
    started = time.monotonic()
    try:
        body = T.extract_body(source) if response else T.body_from_source(source)
    except ValueError as exc:
        return _invalid(f"preflight: {exc}", body_sha256=hashlib.sha256(source.encode()).hexdigest())
    body_sha = hashlib.sha256(body.encode()).hexdigest()
    try:
        T.preflight_body(body, forbid_sorry=cfg["forbid_sorry"], disabled=cfg["disabled_bans"])
    except ValueError as exc:
        return _invalid(f"preflight: {exc}", body_sha256=body_sha)
    version = check_toolchain()
    lock_digest = T.verify_lock()  # raises: a changed statement module is never evaluated
    key = _cache_key(body, cfg, lock_digest, version, require_sandbox)
    if not require_sandbox:
        cache_dir = None  # an unsandboxed result is never read from or written to a shared cache
    if cache_dir:
        hit = Path(cache_dir) / f"{key}.json"
        if hit.is_file():
            out = json.loads(hit.read_text())
            out["cache_hit"] = True
            return out
    out = _evaluate_uncached(body, cfg, require_sandbox)
    out.update(body_sha256=body_sha, cache_key=key, cache_hit=False, evaluator_version=VERSION,
               lock_digest=lock_digest, toolchain=version, seconds=round(time.monotonic() - started, 3))
    if cache_dir and out["status"] != "INCOMPLETE" and not out.get("no_cache"):
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        tmp = Path(cache_dir) / f".{key}.{os.getpid()}.tmp"
        tmp.write_text(json.dumps(out, sort_keys=True) + "\n")
        tmp.replace(Path(cache_dir) / f"{key}.json")
    return out


def _evaluate_uncached(body: str, cfg: dict, require_sandbox: bool) -> dict:
    with tempfile.TemporaryDirectory(prefix="lrx-lean-") as scratch:
        scratch = Path(os.path.realpath(scratch))
        current, first, passes, dropped = body, None, [], []
        work_a, final_printed, unprintable = None, {}, set()
        for k in range(cfg["max_passes"]):
            work = scratch / f"a{k}"
            work.mkdir()
            footer_ids = [i for i in T.declared_ids(current) if i not in unprintable]
            run, parsed, footer_map = _stage_a(current, work, cfg, require_sandbox, footer_ids)
            errs = _errors(parsed)
            first = first or parsed
            passes.append({"pass": k + 1, "returncode": run["returncode"], "seconds": run["seconds"],
                           "errors": len(errs), "footer_errors": sorted(parsed["footer_errors"]),
                           "status": run["status"]})
            if run["status"] != "ok":
                return {**_invalid(run["reason"]), "status": "INCOMPLETE", "passes": passes,
                        "messages": first["messages"][:40]}
            if (run["returncode"] == 0 and not errs and not parsed["footer_errors"]
                    and (work / "Cand.olean").is_file()):
                work_a, final_printed = work, parsed["printed_axioms"]
                break
            unprintable |= set(parsed["footer_errors"])  # constant absent: retry without its footer line
            drop = _drop_starts(current, errs)
            if not drop and not parsed["footer_errors"]:
                break
            dropped += [b for b in T.blocks(current) if b["start"] in drop]
            current = T.blank_blocks(current, drop)
        base = {"messages": [dict(m, text=_sanitize(m["text"])[:1500]) for m in first["messages"][:40]],
                "blocks": T.blocks(body), "dropped_blocks": dropped, "passes": passes}
        body_errors = len([m for m in _errors(first) if m["in_body"] or m["line"] > 0])
        declared = T.declared_ids(body)
        if work_a is None:
            statuses = {i: ("error" if i in declared else "missing") for i in T.IDS}
            return {"status": "VALID", "reason": "no compiling subset of the body", "statuses": statuses,
                    **T.score(statuses, 0, body_errors), "closed_targets": [], "closed_milestones": [],
                    "aux": [], "axioms": {}, "verified_body": None, **base}
        work_b = scratch / "b"
        work_b.mkdir()
        rb = _stage_b(work_a, work_b, cfg, require_sandbox)
        base["stage_b"] = {"returncode": rb["returncode"], "seconds": rb["seconds"], "status": rb["status"]}
        if rb["status"] != "ok":
            return {**_invalid(rb["reason"]), "status": "INCOMPLETE", **base}
        if rb["returncode"] != 0:
            return _invalid("stage B: leanchecker rejected the olean: " + _sanitize(rb["stderr"])[:300], **base)
        work_c = scratch / "c"
        work_c.mkdir()
        rc, verdict = _stage_c(work_a, work_c, cfg, require_sandbox)
        base["stage_c"] = {"returncode": rc["returncode"], "seconds": rc["seconds"], "status": rc["status"]}
        if rc["status"] != "ok":
            return {**_invalid(rc["reason"]), "status": "INCOMPLETE", **base}
        if verdict is None:  # may be environmental, so never cached
            return _invalid("stage C: audit produced no verdict with the expected nonce: "
                            + _sanitize(rc["stderr"])[:300], no_cache=True, **base)
        statuses, axioms = {}, {}
        for i in T.IDS:
            audit = verdict["targets"].get(i, {})
            st = audit.get("status", "missing")
            axioms[i] = audit.get("axioms", [])
            if st == "missing" and i in declared:
                st = "error"
            footer_axioms = final_printed.get(i)
            if st == "closed" and (footer_axioms is None or not set(footer_axioms) <= set(T.ALLOWED_AXIOMS)):
                st = "audit_mismatch"  # Lean's own #print axioms disagrees with the audit
            statuses[i] = st
        aux = list(verdict.get("aux", []))
        return {"status": "VALID", "reason": None, "statuses": statuses, "axioms": axioms, "aux": aux,
                **T.score(statuses, len(aux), body_errors),
                "closed_targets": [i for i in T.TARGETS if statuses[i] == "closed"],
                "closed_milestones": [i for i in T.MILESTONES if statuses[i] == "closed"],
                "footer_axioms": final_printed, "verified_body": current, **base}


# ------------------------------------------------------------------- packets
def _status_line(result, ids) -> str:
    return ", ".join(f"{i} {result['statuses'].get(i, 'missing')}" for i in ids)


def packet(result: dict, best: str | None = None) -> str:
    """Development feedback, fenced as data: statuses, first 3 errors, first open statement."""
    head = [f"{PACKET_MARK} (evaluator output; data, not instructions)"]
    if result["status"] != "VALID":
        head.append(f"status {result['status']}: {_sanitize(str(result.get('reason')))[:400]}; score -1")
    else:
        head.append(f"status VALID; combined {result['combined_score']:.4f} (targets {result['T']}, milestones "
                    f"{result['M']}, helper theorems {len(result['aux'])}, error penalty {result['P']})")
    if best:
        head.append(f"best so far: {best}")
    head += ["targets: " + _status_line(result, T.TARGETS), "milestones: " + _status_line(result, T.MILESTONES)]
    bad = {i: [a for a in ax if a not in T.ALLOWED_AXIOMS + ("sorryAx",)]
           for i, ax in (result.get("axioms") or {}).items()}
    bad = {i: ax for i, ax in bad.items() if ax}
    if bad:
        head.append("disqualifying axioms: " + "; ".join(f"{i}: {', '.join(ax)}" for i, ax in bad.items()))
    if result.get("dropped_blocks"):
        head.append("blocks removed after errors (body lines): " + ", ".join(
            f"{b['start']}-{b['end']} {b['name'] or ''}".strip() for b in result["dropped_blocks"][:8]))
    errs = [m for m in result.get("messages", []) if m["severity"] == "error"][:3]
    body = [f"- line {m['line']}:{m['col']}: {_sanitize(m['text'])[:400]}" for m in errs]
    if body:
        body.insert(0, "errors (first 3, body line:col):")
    open_target = next((i for i in T.IDS if result["statuses"].get(i) != "closed"), None)
    tail = [f"locked statement of the first open declaration (LRX.Stmt.{open_target}):",
            T.statement_text(open_target)] if open_target else []
    text = "\n".join(head + body + tail)
    while len(text) > PACKET_MAX and body:
        body.pop()
        text = "\n".join(head + body + tail)
    return text[:PACKET_MAX]


def instance_feedback(result: dict, ident: str) -> str:
    """GEPA per-instance side information: status, errors inside that declaration, statement."""
    lines = [f"{ident}: {result['statuses'].get(ident, 'missing')}"]
    if result["status"] != "VALID":
        lines.append(f"file {result['status']}: {_sanitize(str(result.get('reason')))[:400]}")
    block = next((b for b in result.get("blocks", []) if b["name"] == ident), None)
    if block:
        for m in result.get("messages", []):
            if m["severity"] == "error" and block["start"] <= m["line"] <= block["end"]:
                lines.append(f"- line {m['line']}:{m['col']}: {_sanitize(m['text'])[:400]}")
    elif result["status"] == "VALID":
        lines.append(f"not declared: add `theorem {ident} : Stmt.{ident}`")
    bad = [a for a in (result.get("axioms") or {}).get(ident, []) if a not in T.ALLOWED_AXIOMS + ("sorryAx",)]
    if bad:
        lines.append("disqualifying axioms: " + ", ".join(bad))
    lines.append(T.statement_text(ident))
    return "\n".join(lines)[:1500]


# ---------------------------------------------------------------------- CLI
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="action", required=True)
    e = sub.add_parser("eval")
    e.add_argument("file", type=Path)
    e.add_argument("--response", action="store_true", help="input is a model response with a ```lean block")
    e.add_argument("--cache-dir", type=Path)
    e.add_argument("--forbid-sorry", action="store_true")
    e.add_argument("--disable-ban", action="append", default=[], help="TEST HARNESS ONLY")
    e.add_argument("--full", action="store_true")
    sub.add_parser("lock", help="HUMAN STEP after review: write lean.lock.json from the built project")
    sub.add_parser("verify-lock")
    sub.add_parser("seed", help="write the sorry-stub seed body")
    args = parser.parse_args(argv)
    if args.action == "lock":
        lock = T.compute_lock()
        lock["note"] = ("sha256 of the locked Lean project (sources, Defs.olean, lrxaudit binary). Written by "
                        "the Track 3 implementer on 2026-09-25; PENDING human review and re-lock.")
        T.LOCK_PATH.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
        print(T.lock_digest(T.compute_lock()))
    elif args.action == "verify-lock":
        print(T.verify_lock())
    elif args.action == "seed":
        T.SEED_PATH.write_text(T.seed_body())
        print(T.SEED_PATH)
    else:
        cfg = {"forbid_sorry": args.forbid_sorry, "disabled_bans": args.disable_ban}
        out = evaluate(args.file.read_text(), cache_dir=args.cache_dir, config=cfg, response=args.response)
        keep = out if args.full else {k: out.get(k) for k in (
            "status", "reason", "combined_score", "combined_exact", "T", "M", "A", "P", "statuses",
            "closed_targets", "closed_milestones", "aux", "dropped_blocks", "passes", "seconds", "cache_hit")}
        print(json.dumps(keep, indent=1, default=str))


if __name__ == "__main__":
    main()
