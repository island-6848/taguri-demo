-- The original screens' per-user tables, moved from Render's SQLite
-- (tools/review/rate_performances.py, feedback.py, tools/taguri/app.py,
-- serve.py) to D1. Same columns as there, so the Worker's port of each screen
-- reads what the Python one reads. Tables only the owner's mail import uses
-- (attendance, splits, presented, fixes) are not moved. updated_at keeps the
-- Python format 'YYYY-MM-DD HH:MM:SS' (Japan time).
CREATE TABLE works (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 work_key TEXT NOT NULL, title TEXT NOT NULL, first_date TEXT, last_date TEXT,
 times INTEGER NOT NULL DEFAULT 1, verdict TEXT, chosen TEXT,
 note_impression TEXT NOT NULL DEFAULT '', note_motive TEXT NOT NULL DEFAULT '',
 updated_at TEXT NOT NULL, stage_id TEXT, venue TEXT NOT NULL DEFAULT '', time TEXT NOT NULL DEFAULT '',
 verdict_source TEXT NOT NULL DEFAULT 'legacy_unknown', note_source TEXT NOT NULL DEFAULT 'legacy_unknown',
 PRIMARY KEY (user_id, work_key)
);
CREATE TABLE excluded (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 uid TEXT NOT NULL, program TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY (user_id, uid, program)
);
CREATE TABLE merges (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 work_key TEXT NOT NULL, into_key TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY (user_id, work_key)
);
CREATE TABLE hand_credits (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 work_key TEXT NOT NULL, fields TEXT NOT NULL DEFAULT '{}', poster TEXT NOT NULL DEFAULT '',
 updated_at TEXT NOT NULL,
 PRIMARY KEY (user_id, work_key)
);
CREATE TABLE visit_note (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 uid TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
 PRIMARY KEY (user_id, uid)
);
CREATE TABLE reaction (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 label TEXT NOT NULL, stage_id TEXT NOT NULL,
 interest INTEGER, known INTEGER, owned INTEGER,
 decider TEXT, decider_who TEXT, decider_axes TEXT, decider_shown INTEGER,
 note TEXT, note_no TEXT, source TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY (user_id, label, stage_id)
);
CREATE TABLE viewed (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 label TEXT NOT NULL, bundle TEXT NOT NULL, first_at TEXT NOT NULL, source TEXT NOT NULL,
 PRIMARY KEY (user_id, label, bundle)
);
CREATE TABLE ticket (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 stage_id TEXT NOT NULL, date TEXT NOT NULL, time TEXT NOT NULL DEFAULT '',
 source TEXT NOT NULL, confirmed INTEGER NOT NULL DEFAULT 0, uid TEXT NOT NULL DEFAULT '',
 updated_at TEXT NOT NULL,
 PRIMARY KEY (user_id, stage_id, date, time)
);
CREATE TABLE missed (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 title TEXT NOT NULL, created_at TEXT NOT NULL, note TEXT,
 stage_id TEXT, venue TEXT, period TEXT, fields_json TEXT, synopsis TEXT, lookup_note TEXT, looked_up_at TEXT,
 PRIMARY KEY (user_id, title)
);
CREATE TABLE rank_weight (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 grp TEXT NOT NULL, step TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY (user_id, grp)
);
CREATE TABLE app_setting (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 key TEXT NOT NULL, value TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY (user_id, key)
);
CREATE TABLE search_request (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 qkey TEXT NOT NULL, query TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY (user_id, qkey)
);
-- Bound what one account can store (the Python service had no such limits).
CREATE TRIGGER screen_works_limit BEFORE INSERT ON works
WHEN NOT EXISTS(SELECT 1 FROM works WHERE user_id=NEW.user_id AND work_key=NEW.work_key)
AND (SELECT count(*) FROM works WHERE user_id=NEW.user_id)>=2000
BEGIN SELECT RAISE(ABORT,'works limit'); END;
CREATE TRIGGER screen_ticket_limit BEFORE INSERT ON ticket
WHEN (SELECT count(*) FROM ticket WHERE user_id=NEW.user_id)>=2000
BEGIN SELECT RAISE(ABORT,'ticket limit'); END;
CREATE TRIGGER screen_reaction_limit BEFORE INSERT ON reaction
WHEN (SELECT count(*) FROM reaction WHERE user_id=NEW.user_id)>=5000
BEGIN SELECT RAISE(ABORT,'reaction limit'); END;
CREATE TRIGGER screen_missed_limit BEFORE INSERT ON missed
WHEN (SELECT count(*) FROM missed WHERE user_id=NEW.user_id)>=500
BEGIN SELECT RAISE(ABORT,'missed limit'); END;
