"""Queryable archive for development evaluations of generated programs.

Confirmation results have a separate one-shot output path. This archive has no
confirmation write API: every inserted row is explicitly a development row.
"""

import difflib
import hashlib
import json
import sqlite3
from fractions import Fraction
from pathlib import Path


class DevelopmentArchive:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY,
            run_id TEXT NOT NULL,
            engine TEXT NOT NULL,
            parent_id INTEGER,
            source_sha256 TEXT NOT NULL,
            source TEXT NOT NULL,
            source_diff TEXT NOT NULL,
            score REAL NOT NULL,
            claim_status TEXT NOT NULL,
            feedback_json TEXT NOT NULL,
            traces_json TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            created_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_candidates_run ON candidates(run_id, score DESC)")
        self.db.commit()

    def close(self):
        self.db.close()

    def add(self, *, run_id, engine, source, score, feedback, traces,
            provenance, claim_status="finite_development", parent_id=None,
            split="development"):
        if split != "development":
            raise ValueError("archive accepts development evaluations only")
        if claim_status not in ("finite_development", "invalid", "incomplete"):
            raise ValueError("claim status must be a development status")
        if not isinstance(source, str) or not source:
            raise ValueError("source must be nonempty")
        if not isinstance(feedback, dict) or not isinstance(traces, (list, dict)):
            raise TypeError("feedback and traces must be structured data")
        if not isinstance(provenance, dict):
            raise TypeError("provenance must be structured data")
        parent_source = None
        if parent_id is not None:
            parent = self.db.execute("SELECT source FROM candidates WHERE id=?", (parent_id,)).fetchone()
            if parent is None:
                raise ValueError("parent candidate not found")
            parent_source = parent["source"]
        # An unknown parent is not an empty program.  Only store a source diff
        # when the actual parent source is present in this archive.
        diff = "" if parent_source is None else "".join(difflib.unified_diff(
            parent_source.splitlines(keepends=True), source.splitlines(keepends=True),
            fromfile="parent", tofile="candidate"))
        with self.db:
            cursor = self.db.execute("""INSERT INTO candidates
                (run_id,engine,parent_id,source_sha256,source,source_diff,score,
                 claim_status,feedback_json,traces_json,provenance_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
                    run_id, engine, parent_id, hashlib.sha256(source.encode()).hexdigest(),
                    source, diff, float(score), claim_status,
                    json.dumps(feedback, sort_keys=True), json.dumps(traces, sort_keys=True),
                    json.dumps(provenance, sort_keys=True)))
        return cursor.lastrowid

    def get(self, candidate_id):
        row = self.db.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()
        if row is None:
            return None
        out = dict(row)
        for key in ("feedback", "traces", "provenance"):
            out[key] = json.loads(out.pop(key + "_json"))
        out["lineage_status"] = "known_parent" if out["parent_id"] is not None else "unknown_parent"
        # Old archives contain a synthetic empty-to-source diff for roots. Do
        # not present it as a real parent diff; leave the old database intact.
        if out["parent_id"] is None:
            out["source_diff"] = ""
        return out

    @staticmethod
    def _case_traces(row, case_id=None):
        traces = row["traces"]
        if isinstance(traces, dict):
            traces = traces.get("families", traces.get("traces", [traces]))
        if not isinstance(traces, list):
            return []
        if case_id is None:
            return [trace for trace in traces if isinstance(trace, dict)]
        return [trace for trace in traces if isinstance(trace, dict)
                and (trace.get("case_id") or trace.get("case", {}).get("id")) == case_id]

    @classmethod
    def _coverage(cls, row):
        return len({trace.get("case_id") or trace.get("case", {}).get("id")
                    for trace in cls._case_traces(row)
                    if trace.get("case_id") or trace.get("case", {}).get("id")})

    def search(self, query="", *, run_id=None, limit=10, case_id=None,
               objective="coverage", exclude_source_sha256=()):
        """Return distinct sources; raw scores are never compared across coverage.

        The numeric score is meaningful only within a fixed evaluation scope.
        `coverage` prefers complete evaluations. `failure` prefers a target
        case miss, and `novelty` prefers recent distinct sources. Exact
        complementarity ranking is available through `select_context`.
        """
        if not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        if objective not in ("coverage", "failure", "novelty"):
            raise ValueError("unknown archive search objective")
        sql = "SELECT id FROM candidates WHERE 1=1"
        args = []
        if run_id is not None:
            sql += " AND run_id=?"
            args.append(run_id)
        if query:
            sql += " AND (source LIKE ? OR feedback_json LIKE ? OR traces_json LIKE ? OR provenance_json LIKE ?)"
            args.extend(["%" + query + "%"] * 4)
        sql += " ORDER BY id DESC"
        excluded = set(exclude_source_sha256)
        rows = []
        for item in self.db.execute(sql, args).fetchall():
            row = self.get(item[0])
            if row["source_sha256"] in excluded or (case_id and not self._case_traces(row, case_id)):
                continue
            rows.append(row)
        # The same source is often evaluated once per case. Pick its richest
        # target trace, then return at most one row per source hash.
        def richness(row):
            target = self._case_traces(row, case_id)
            return (self._coverage(row), len(json.dumps(target)), row["id"])
        unique = {}
        for row in rows:
            key = (row["source_sha256"], case_id)
            if key not in unique or richness(row) > richness(unique[key]):
                unique[key] = row
        def rank(row):
            target = self._case_traces(row, case_id)
            failed = any(t.get("status") not in ("CERTIFICATE", "certified", "ok")
                         for t in target)
            if objective == "failure":
                return (failed, self._coverage(row), row["id"])
            if objective == "novelty":
                return (row["id"], self._coverage(row))
            return (self._coverage(row), row["id"])
        return sorted(unique.values(), key=rank, reverse=True)[:limit]

    @staticmethod
    def _reduced_cost(trace, dual):
        if not dual:
            return None
        values = []
        for item in trace.get("accepted_words", []):
            profile = item.get("profile", {})
            gamma = profile.get("gamma", [])
            try:
                cost = Fraction(profile["base"]) - Fraction(dual["nu"])
                cost += sum(Fraction(mu) * Fraction(gamma[int(index)])
                            for index, mu in zip(dual["tight"], dual["mu"], strict=True))
            except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError):
                continue
            values.append((cost, item))
        return min(values, key=lambda pair: pair[0]) if values else None

    def select_context(self, case_id, *, limit=2, max_chars=6000,
                       objective="complementarity", dual=None,
                       incumbent_source_sha256=None):
        """Build a bounded development-only excerpt for one fixed case.

        Selection is one incumbent plus distinct-source examples. `dual` is a
        frozen development finite-pool screen, never a proof or LP result.
        The full traces remain queryable in the SQLite archive.
        """
        if not case_id or not 1 <= limit <= 10 or max_chars < 500:
            raise ValueError("invalid context bounds or case id")
        if objective not in ("complementarity", "failure", "novelty"):
            raise ValueError("unknown context objective")
        rows = self.search(case_id=case_id, limit=100, objective="novelty")
        if not rows:
            return {"text": "", "selected": [], "case_id": case_id,
                    "objective": objective, "chars": 0}
        incumbent = next((r for r in rows if r["source_sha256"] == incumbent_source_sha256), None)
        if incumbent is None:
            incumbent = next((r for r in rows if r["provenance"].get("role") == "incumbent"), None)
        if incumbent is None:
            incumbent = max(rows, key=lambda r: (self._coverage(r), r["id"]))

        def merit(row):
            trace = self._case_traces(row, case_id)[0]
            reduced = self._reduced_cost(trace, dual)
            miss = trace.get("status") not in ("CERTIFICATE", "certified", "ok")
            valid = row["claim_status"] == "finite_development"
            if objective == "complementarity":
                # An exact reduced-cost screen precedes case failure and
                # novelty. Missing profiles rank after measured profiles.
                return (reduced is not None, -reduced[0] if reduced else Fraction(0),
                        valid, miss, row["id"])
            if objective == "failure":
                return (miss, valid, row["id"])
            return (row["id"], valid)

        others = [r for r in rows if r["source_sha256"] != incumbent["source_sha256"]]
        chosen = [incumbent] + sorted(others, key=merit, reverse=True)[:limit - 1]

        def excerpt(row, field_chars):
            trace = self._case_traces(row, case_id)[0]
            reduced = self._reduced_cost(trace, dual)
            words = trace.get("accepted_words", [])
            best = reduced[1] if reduced else (words[0] if words else None)
            payload = {
                "archive_id": row["id"], "source_sha256": row["source_sha256"],
                "role": "incumbent" if row is incumbent else "distinct_candidate",
                "engine": row["engine"], "claim_status": row["claim_status"],
                "case_status": trace.get("status"), "evaluated_case_count": self._coverage(row),
                "score": row["score"], "score_scope": "development_case_count",
                "lineage_status": row["lineage_status"],
                "parent_id": row["parent_id"],
                "source_excerpt": row["source"][:field_chars],
                "source_total_chars": len(row["source"]),
                "source_diff_excerpt": row["source_diff"][:field_chars] if row["parent_id"] else "",
                "feedback_excerpt": json.dumps(row["feedback"], sort_keys=True)[:field_chars],
                "case": trace.get("case", {"id": case_id}),
                "raw_trace_excerpt": json.dumps({
                    "accepted_word_count": len(words),
                    "best_screened_word": best,
                    "rejected_word_count": len(trace.get("rejected_words", [])),
                    "lp": trace.get("lp"), "certificate": trace.get("certificate"),
                }, sort_keys=True)[:field_chars],
                "reduced_cost": str(reduced[0]) if reduced else None,
                "reduced_cost_scope": "frozen_development_finite_pool_filter" if reduced else None,
            }
            return payload

        # Deterministic size reduction keeps provenance and case identity, but
        # never silently presents a clipped field as the complete raw trace.
        selected = [{"id": row["id"], "source_sha256": row["source_sha256"],
                     "case_id": case_id, "evaluated_case_count": self._coverage(row),
                     "lineage_status": row["lineage_status"]} for row in chosen]
        for field_chars in (900, 600, 350, 150, 0):
            payload = {"case_id": case_id, "objective": objective,
                       "selection_note": "distinct source hashes; exact finite-pool screen is not a certificate",
                       "examples": [excerpt(row, field_chars) for row in chosen]}
            rendered = json.dumps(payload, sort_keys=True)
            if len(rendered) <= max_chars:
                return {"text": rendered, "selected": selected,
                        "case_id": case_id, "objective": objective, "chars": len(rendered)}
        raise ValueError("context bound too small for selected provenance")


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--run-id")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    archive = DevelopmentArchive(args.archive)
    try:
        print(json.dumps(archive.search(args.query, run_id=args.run_id, limit=args.limit), indent=2))
    finally:
        archive.close()


if __name__ == "__main__":
    main()
