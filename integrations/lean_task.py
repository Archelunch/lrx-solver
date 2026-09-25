"""Track 3 (Lean in the loop): task constants, candidate contract, lock, and pure helpers.

No Lean process runs here. The locked statement module is
autoresearch/lean-loop-260925/lrxlean/LrxLean/Defs.lean; its hashes (and those of
the trusted audit executable) live in autoresearch/lean-loop-260925/lean.lock.json
and are checked before every evaluation. Lemma 1 and Lemma 4 are the research
group's results; these statements formalise them and say nothing about the open
conjecture. See autoresearch/lean-loop-260925/SPEC-track3.md.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TRACK_DIR = ROOT / "autoresearch" / "lean-loop-260925"
PROJECT = TRACK_DIR / "lrxlean"
LOCK_PATH = TRACK_DIR / "lean.lock.json"
SEED_PATH = TRACK_DIR / "seed.lean"
TOOLCHAIN = "leanprover/lean4:v4.34.0"
TOOLCHAIN_VERSION_PREFIX = "Lean (version 4.34.0, "
TARGETS = ("L1", "L2", "L3")
MILESTONES = ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M9")
IDS = TARGETS + MILESTONES
ALLOWED_AXIOMS = ("propext", "Classical.choice", "Quot.sound")
MAX_BODY_BYTES = 32768
MAX_BODY_LINES = 1500
HEARTBEATS = 400000
HEADER = ("import LrxLean.Defs\n"
          f"set_option maxHeartbeats {HEARTBEATS}\n"
          "set_option maxRecDepth 2048\n"
          "open LRX\n"
          "namespace Cand\n")
HEADER_LINES = HEADER.count("\n")
LOCKED_FILES = ("lean-toolchain", "lakefile.toml", "LrxLean.lean", "LrxLean/Defs.lean",
                "LrxLean/Conformance.lean", "Audit.lean",
                ".lake/build/lib/lean/LrxLean/Defs.olean", ".lake/build/bin/lrxaudit")


def toolchain_dir() -> Path:
    """The pinned toolchain, called directly (never through the elan proxy)."""
    override = os.environ.get("LRX_LEAN_TOOLCHAIN_DIR")
    return Path(override) if override else Path.home() / ".elan" / "toolchains" / "leanprover--lean4---v4.34.0"


def toolchain_available() -> bool:
    t = toolchain_dir()
    return (t / "bin" / "lean").is_file() and (PROJECT / ".lake" / "build" / "bin" / "lrxaudit").is_file()


# ------------------------------------------------------------------- lexical ban
# Defence in depth before any process starts; the audit (axioms, exact types,
# kernel replay) is the real guarantee. Word rules run on the body with comments
# blanked (strip_comments); the ``` and # rules always run on the raw text.
_WORDS = ("import", "axiom", "implemented_by", "extern", "initialize", "set_option", "macro",
          "macro_rules", "syntax", "elab", "elab_rules", "notation", "infix", "infixl", "infixr",
          "prefix", "postfix", "run_cmd", "run_elab", "run_meta", "native_decide", "ofReduceBool",
          "trustCompiler", "opaque", "partial", "namespace", "section", "end", "csimp", "_root_",
          "bv_decide", "mutual")
BANS = tuple((w, re.compile(r"(?<![\w.'])" + re.escape(w) + r"(?![\w'])")) for w in _WORDS) + (
    ("unsafe", re.compile(r"(?<![\w.'])unsafe")),
    ("builtin_", re.compile(r"(?<![\w.'])builtin_")),
    ("@[init", re.compile(r"@\[\s*init")),
    ("+native", re.compile(r"\+\s*native")),
    ("debug.", re.compile(r"(?<![\w.'])debug\.")),
    ("# command", re.compile(r"(?<![\w.'])#[A-Za-z_]")),
    ("open Lean/IO/System/Std", re.compile(r"\bopen\b[^\n]*\b(Lean|IO|System|Std)\b")),
    ("Lean./IO./System./Std. identifier", re.compile(r"(?<![\w.'])(Lean|IO|System|Std)\.")),
    ("``` fence", re.compile(r"```")),
)
SORRY_BANS = (("sorry", re.compile(r"(?<![\w.'])sorry(?![\w'])")),
              ("admit", re.compile(r"(?<![\w.'])admit(?![\w'])")))


RAW_RULES = ("``` fence", "# command")
_CHAR = re.compile(r"'(?:\\(?:x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|.)|[^'\\\n])'")


def strip_comments(body: str):
    """The body with `--` and nested `/- -/` comments blanked (newlines kept), or None.

    Mirrors Lean 4's lexer for strings, char literals and «» names so no code is
    ever taken for a comment. Anything it cannot lex with certainty (interpolated
    or raw strings, a stray quote, unterminated literals or comments) returns None,
    and the caller then bans on the raw text (fail closed).
    """
    out, i, n = [], 0, len(body)
    while i < n:
        c = body[i]
        if body.startswith("--", i):
            j = body.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif body.startswith("/-", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if body.startswith("/-", j):
                    depth, j = depth + 1, j + 2
                elif body.startswith("-/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            if depth:
                return None
            out.append(re.sub(r"[^\n]", " ", body[i:j]))
            i = j
        elif c == '"':
            prev = body[i - 1] if i else ""
            if prev == "#" or prev == "!" or prev.isalnum() or prev == "_":
                return None  # raw r"..", r#".."#, s!/m!/f! interpolation, or a name glued to a quote
            j = i + 1
            while j < n and body[j] != '"':
                j += 2 if body[j] == "\\" else 1
            if j >= n or "{" in body[i:j]:
                return None
            out.append(body[i:j + 1])
            i = j + 1
        elif c == "«":
            j = body.find("»", i)
            if j < 0:
                return None
            out.append(body[i:j + 1])
            i = j + 1
        elif c == "'" and not (i and (body[i - 1].isalnum() or body[i - 1] in "_'.!?")):
            m = _CHAR.match(body, i)
            if not m:
                return None
            out.append(m.group(0))
            i = m.end()
        else:
            out.append(c)
            i += 1
    return "".join(out)


def lexical_violations(body: str, *, forbid_sorry: bool = False, disabled=()) -> list[str]:
    """Names of every ban rule the body hits (empty list = passes).

    Word rules ignore comments when the comment scan is certain; the ``` and #
    rules (and every rule, when the scan gives up) run on the raw text.
    """
    rules = BANS + (SORRY_BANS if forbid_sorry else ())
    stripped = strip_comments(body)
    code = body if stripped is None else stripped
    return [name for name, rx in rules
            if name not in disabled and rx.search(body if name in RAW_RULES else code)]


def preflight_body(body, *, forbid_sorry=False, disabled=()) -> str:
    if not isinstance(body, str) or not body.strip():
        raise ValueError("empty Lean body")
    if len(body.encode()) > MAX_BODY_BYTES:
        raise ValueError(f"Lean body exceeds {MAX_BODY_BYTES} bytes")
    if body.count("\n") >= MAX_BODY_LINES:
        raise ValueError(f"Lean body exceeds {MAX_BODY_LINES} lines")
    hits = lexical_violations(body, forbid_sorry=forbid_sorry, disabled=disabled)
    if hits:
        raise ValueError("banned construct: " + ", ".join(hits))
    return body


_FENCE = re.compile(r"```[ \t]*(lean4?|)[ \t]*\n(.*?)```", re.IGNORECASE | re.DOTALL)


def extract_body(content, finish_reason=None) -> str:
    """The last fenced ```lean block of a model response; truncated output is never repaired."""
    if finish_reason in ("length", "max_tokens"):
        raise ValueError("proposal was truncated by the model output limit")
    if not isinstance(content, str):
        raise ValueError("proposal had no text content")
    blocks = [m.group(2) for m in _FENCE.finditer(content)]
    if not blocks:
        raise ValueError("proposal must contain a fenced ```lean block with the whole Lean body")
    body = blocks[-1]
    if len(body.encode()) > MAX_BODY_BYTES:
        raise ValueError("proposal exceeds the Lean body size cap")
    return body


def body_from_source(source: str) -> str:
    """Verifier input: a raw body (GEPA/SkyDiscover program text) or a response with a fence."""
    return extract_body(source) if "```" in source else source


# ------------------------------------------------------------------ assembly
_DECL = re.compile(r"^(?:(?:theorem|lemma|def|abbrev|instance|example|structure|inductive|class|attribute|"
                   r"open|variable|universe|private|protected|noncomputable|nonrec)\b|@\[|/--)")
_NAMED = re.compile(r"^\s*(?:/--.*?-/\s*)?(?:@\[[^\]]*\]\s*)?(?:(?:private|protected|noncomputable|nonrec)\s+)*"
                    r"(?:theorem|lemma|def|abbrev)\s+«?([A-Za-z_][\w.']*)")
_DECLARES = re.compile(r"(?<![\w.'])(?:theorem|lemma|def|abbrev)\s+«?(" + "|".join(IDS) + r")»?(?![\w.'»])")


def blocks(body: str) -> list[dict]:
    """Top-level blocks: each starts at a column-0 declaration keyword line (1-based body lines).

    A docstring/attribute-only block is merged into the declaration that follows it.
    """
    lines = body.split("\n")
    starts = [i for i, line in enumerate(lines) if line[:1] not in ("", " ", "\t") and _DECL.match(line)]
    if not starts or starts[0] != 0:
        starts = [0] + starts
    out = []
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(lines)
        text = lines[s:e]
        named = next((m.group(1) for m in map(_NAMED.match, text) if m), None)
        if out and out[-1]["name"] is None and out[-1]["doc_only"]:
            prev = out.pop()
            s = prev["start"] - 1
        out.append({"start": s + 1, "end": e, "name": named,
                    "doc_only": named is None and text[0].startswith(("/--", "@["))})
    return [{"start": b["start"], "end": b["end"], "name": b["name"]} for b in out]


def declared_ids(body: str) -> list[str]:
    """Target/milestone ids the body declares anywhere (any indentation, name on a later
    line, after a docstring), ignoring comments when the comment scan is certain."""
    code = strip_comments(body)
    names = set(_DECLARES.findall(body if code is None else code))
    return [i for i in IDS if i in names]


def blank_blocks(body: str, drop_starts) -> str:
    """Replace the given blocks with empty lines, preserving line numbers."""
    lines = body.split("\n")
    for b in blocks(body):
        if b["start"] in drop_starts:
            for i in range(b["start"] - 1, b["end"]):
                lines[i] = ""
    return "\n".join(lines)


def block_of_line(body: str, line: int):
    for b in blocks(body):
        if b["start"] <= line <= b["end"]:
            return b
    return None


def assemble(body: str, ids=None) -> tuple[str, dict]:
    """Trusted header + body + trusted footer; returns (file text, footer line -> id).

    The footer prints axioms for `ids` (default: declared_ids(body)); Lean writes no
    olean when a footer line errors, so the evaluator retries without such ids.
    """
    if not body.endswith("\n"):
        body += "\n"
    ids = declared_ids(body) if ids is None else [i for i in IDS if i in ids]
    first_footer = HEADER_LINES + body.count("\n") + 2  # after "end Cand"
    footer = "end Cand\n" + "".join(f"#print axioms Cand.{i}\n" for i in ids)
    return HEADER + body + footer, {first_footer + k: i for k, i in enumerate(ids)}


_AXIOMS = re.compile(r"^'Cand\.(\w+)' (?:depends on axioms: \[(.*)\]|does not depend on any axioms)\s*$", re.DOTALL)


def parse_messages(lines, footer_map: dict, body_line_count: int) -> dict:
    """Split `lean --json` output into body messages and footer #print axioms results.

    A footer result is accepted only at the exact footer line of its own #print
    command, so a `trace` message from the body cannot forge it. Any other message
    on a footer line (e.g. an unknown constant) goes to `footer_errors`, never to the
    body messages: it adds no penalty and triggers no pruning.
    """
    body_msgs, printed, other, footer_errors = [], {}, [], {}
    for raw in lines:
        try:
            m = json.loads(raw)
        except ValueError:
            other.append(str(raw)[:200])
            continue
        if not isinstance(m, dict):
            continue
        line = (m.get("pos") or {}).get("line", 0)
        col = (m.get("pos") or {}).get("column", 0)
        data = str(m.get("data", ""))
        sev = m.get("severity", "")
        if line in footer_map and sev == "information":
            hit = _AXIOMS.match(data)
            if hit and hit.group(1) == footer_map[line]:
                printed[hit.group(1)] = [a.strip() for a in (hit.group(2) or "").split(",") if a.strip()]
                continue
        if line in footer_map:
            if sev == "error":
                footer_errors[footer_map[line]] = data[:300]
            continue
        rel = line - HEADER_LINES
        body_msgs.append({"severity": sev, "line": rel, "col": col, "text": data,
                          "in_body": 1 <= rel <= body_line_count})
    return {"messages": body_msgs, "printed_axioms": printed, "unparsed": other, "footer_errors": footer_errors}


# ------------------------------------------------------------------- scoring
def score(statuses: dict, aux_count: int, body_errors: int) -> dict:
    """Exact score: T + 1/5 M + 1/20 A - P (SPEC-track3 section 5); one target outweighs all partial credit."""
    t = Fraction(sum(statuses.get(i) == "closed" for i in TARGETS), len(TARGETS))
    m = Fraction(sum(statuses.get(i) == "closed" for i in MILESTONES), len(MILESTONES))
    a = Fraction(min(10, aux_count), 10)
    p = min(Fraction(1, 20), Fraction(body_errors, 100))
    total = t + Fraction(1, 5) * m + Fraction(1, 20) * a - p
    return {"T": str(t), "M": str(m), "A": str(a), "P": str(p), "combined_exact": str(total),
            "combined_score": float(total)}


# ---------------------------------------------------------------- statements
def statement_text(ident: str) -> str:
    """Locked statement text of LRX.Stmt.<ident>, read from Defs.lean."""
    text = (PROJECT / "LrxLean" / "Defs.lean").read_text()
    m = re.search(r"^def " + re.escape(ident) + r" : Prop :=.*?(?=^def |^/--|^/-!|^end Stmt)", text,
                  re.MULTILINE | re.DOTALL)
    return m.group(0).strip() if m else ""


def seed_body() -> str:
    """Stub candidate: every target and milestone stated, every proof `sorry` (scores 0)."""
    parts = ["-- Candidate body. The evaluator wraps it in a trusted header (LrxLean.Defs, open LRX,",
             "-- scope Cand) and footer. Prove each `theorem <id> : Stmt.<id>`; add helper theorems",
             "-- freely. Use `theorem` (not `lemma`); no imports, options, attributes on init, or # commands.", ""]
    for i in IDS:
        parts += [f"theorem {i} : Stmt.{i} := by", f"  unfold Stmt.{i}", "  sorry", ""]
    return "\n".join(parts)


# ---------------------------------------------------------------------- lock
def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_lock(project: Path = PROJECT) -> dict:
    return {"toolchain": TOOLCHAIN, "files": {name: _sha_file(project / name) for name in LOCKED_FILES}}


def lock_digest(lock: dict) -> str:
    return hashlib.sha256(json.dumps(lock, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_lock(project: Path = PROJECT, lock_path: Path = LOCK_PATH) -> str:
    """Raise unless every locked file matches lean.lock.json; return the lock digest."""
    if not lock_path.is_file():
        raise RuntimeError(f"{lock_path} is missing; run `python -m integrations.lean_evaluator lock` after review")
    locked = json.loads(lock_path.read_text())
    expected = {"toolchain": locked.get("toolchain"), "files": locked.get("files")}
    actual = compute_lock(project)
    if expected != actual:
        bad = sorted(k for k in LOCKED_FILES if (expected.get("files") or {}).get(k) != actual["files"].get(k))
        raise RuntimeError("locked Lean project changed: " + (", ".join(bad) or "toolchain"))
    return lock_digest(actual)
