"""Queryable archive for development evaluations of generated programs.

Confirmation results have a separate one-shot output path. This archive has no
confirmation write API: every inserted row is explicitly a development row.
"""

import difflib
import hashlib
import json
import sqlite3
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
        parent_source = ""
        if parent_id is not None:
            parent = self.db.execute("SELECT source FROM candidates WHERE id=?", (parent_id,)).fetchone()
            if parent is None:
                raise ValueError("parent candidate not found")
            parent_source = parent["source"]
        diff = "".join(difflib.unified_diff(
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
        return out

    def search(self, query="", *, run_id=None, limit=10):
        if not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        sql = "SELECT id FROM candidates WHERE 1=1"
        args = []
        if run_id is not None:
            sql += " AND run_id=?"
            args.append(run_id)
        if query:
            sql += " AND (source LIKE ? OR feedback_json LIKE ? OR traces_json LIKE ? OR provenance_json LIKE ?)"
            args.extend(["%" + query + "%"] * 4)
        sql += " ORDER BY score DESC, id DESC LIMIT ?"
        args.append(limit)
        return [self.get(row[0]) for row in self.db.execute(sql, args)]


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
