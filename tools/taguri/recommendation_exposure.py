"""Authenticated recommendation delivery/contact telemetry, separate from presented."""
from __future__ import annotations
import datetime
import json
import re
import secrets

VERSION = "major-region-50pct-1000ms-v1"
RECOMMENDER_VERSION = "person-ordinal-v3+impression-v1"
SCHEMA = """
CREATE TABLE IF NOT EXISTS recommendation_presentations (
 presentation_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, created_at TEXT NOT NULL,
 regions TEXT NOT NULL, method_version TEXT NOT NULL, kind TEXT NOT NULL,
 recommender_version TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS recommendation_candidates (
 presentation_id TEXT NOT NULL, stage_id TEXT NOT NULL, rank INTEGER NOT NULL,
 PRIMARY KEY (presentation_id, stage_id));
CREATE TABLE IF NOT EXISTS recommendation_fetches (
 id INTEGER PRIMARY KEY, presentation_id TEXT NOT NULL, user_id TEXT NOT NULL,
 received_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS recommendation_visits (
 presentation_id TEXT NOT NULL, visit_id TEXT NOT NULL, user_id TEXT NOT NULL,
 source TEXT NOT NULL, started_at TEXT NOT NULL,
 PRIMARY KEY (presentation_id, visit_id));
CREATE TABLE IF NOT EXISTS recommendation_contacts (
 presentation_id TEXT NOT NULL, visit_id TEXT NOT NULL, stage_id TEXT NOT NULL,
 user_id TEXT NOT NULL, rank INTEGER NOT NULL, contacted_at TEXT NOT NULL,
 PRIMARY KEY (presentation_id, visit_id, stage_id));
CREATE UNIQUE INDEX IF NOT EXISTS recommendation_contacts_visit_candidate ON recommendation_contacts(user_id, visit_id, stage_id);
CREATE INDEX IF NOT EXISTS recommendation_contacts_user ON recommendation_contacts(user_id, contacted_at);
"""

def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds")


def _id(value, name):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", value):
        raise ValueError("invalid " + name)
    return value


class Store:
    """Caller serializes access with the server's DB lock. No client identity accepted."""
    def __init__(self, con):
        self.con = con
        con.executescript(SCHEMA)
        columns = {row[1] for row in con.execute("PRAGMA table_info(recommendation_presentations)")}
        if "recommender_version" not in columns:
            con.execute("ALTER TABLE recommendation_presentations ADD COLUMN recommender_version TEXT NOT NULL DEFAULT 'legacy-unknown'")
        con.commit()

    def register(self, user_id, rows, prefs, kind="recommend", start_rank=1):
        pid = secrets.token_urlsafe(24)
        with self.con:
            self.con.execute("INSERT INTO recommendation_presentations VALUES (?,?,?,?,?,?,?)",
                             (pid, user_id, _now(), json.dumps(list(prefs), ensure_ascii=False), VERSION, kind, RECOMMENDER_VERSION))
            self.con.executemany("INSERT INTO recommendation_candidates VALUES (?,?,?)",
                                 [(pid, str(c["stage_id"]), start_rank + i) for i, c in enumerate(rows)])
        return pid

    def _presentation(self, user_id, pid):
        _id(pid, "presentation_id")
        if not self.con.execute("SELECT 1 FROM recommendation_presentations WHERE presentation_id=? AND user_id=?",
                                (pid, user_id)).fetchone():
            raise ValueError("unknown presentation")

    def fetched(self, user_id, presentation_id):
        self._presentation(user_id, presentation_id)
        with self.con:
            self.con.execute("INSERT INTO recommendation_fetches(presentation_id,user_id,received_at) VALUES (?,?,?)",
                             (presentation_id, user_id, _now()))

    def begin(self, user_id, body):
        if not isinstance(body, dict) or set(body) != {"presentation_id", "visit_id", "source"}:
            raise ValueError("invalid visit fields")
        pid, vid = body["presentation_id"], _id(body["visit_id"], "visit_id")
        self._presentation(user_id, pid)
        source = body["source"]
        if source not in ("network", "cache", "local", "fill"):
            raise ValueError("invalid source")
        with self.con:
            self.con.execute("INSERT OR IGNORE INTO recommendation_visits VALUES (?,?,?,?,?)",
                             (pid, vid, user_id, source, _now()))
        return {"ok": True}

    def contact(self, user_id, body):
        if not isinstance(body, dict) or set(body) != {"presentation_id", "visit_id", "stage_id"}:
            raise ValueError("invalid contact fields")
        pid, vid, sid = body["presentation_id"], _id(body["visit_id"], "visit_id"), body["stage_id"]
        self._presentation(user_id, pid)
        if not isinstance(sid, str) or not sid or len(sid) > 80:
            raise ValueError("invalid stage_id")
        if not self.con.execute("SELECT 1 FROM recommendation_visits WHERE presentation_id=? AND visit_id=? AND user_id=?",
                                (pid, vid, user_id)).fetchone():
            raise ValueError("unknown visit")
        row = self.con.execute("SELECT rank FROM recommendation_candidates WHERE presentation_id=? AND stage_id=?",
                               (pid, sid)).fetchone()
        if row is None:
            raise ValueError("unknown candidate")
        with self.con:
            cur = self.con.execute("INSERT OR IGNORE INTO recommendation_contacts VALUES (?,?,?,?,?,?)",
                                   (pid, vid, sid, user_id, row[0], _now()))
        return {"ok": True, "duplicate": cur.rowcount == 0}
