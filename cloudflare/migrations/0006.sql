-- When each session was created, so destructive actions (account deletion)
-- can require a fresh sign-in. Existing sessions stay NULL = not fresh.
ALTER TABLE sessions ADD COLUMN created_at INTEGER;
