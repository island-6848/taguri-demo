-- Additive auth metadata; never replaces users/sessions or private records.
CREATE TABLE IF NOT EXISTS auth_attempts (
 action TEXT NOT NULL, actor_hash TEXT NOT NULL, window INTEGER NOT NULL,
 attempts INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(action,actor_hash,window)
);
CREATE TABLE IF NOT EXISTS device_links (
 code_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 expires_at INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
 used_token TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS device_link_expiry ON device_links(expires_at);
-- Verified recovery hashes only. Optional original scrypt runs solely behind
-- secret pepper + protected legacy_user_map in Python Durable Object compute.
CREATE TABLE IF NOT EXISTS legacy_recovery (
 recovery_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS legacy_user_map (
 old_user_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS legacy_sessions (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 expires_at INTEGER NOT NULL
);
