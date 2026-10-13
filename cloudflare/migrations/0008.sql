-- Per-user cache of the latest recommendation result. Recomputed only when the
-- index version, the date (JST), or the user's records/reactions change.
CREATE TABLE rec_cache (
 user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 stamp TEXT NOT NULL,
 body TEXT NOT NULL,
 created_at INTEGER NOT NULL
);
