ALTER TABLE catalogue ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}';
CREATE TABLE reactions (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 stage_id TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('interest','no','owned')),
 updated_at INTEGER NOT NULL, PRIMARY KEY(user_id,stage_id)
);
CREATE TRIGGER reaction_limit BEFORE INSERT ON reactions
WHEN NOT EXISTS(SELECT 1 FROM reactions WHERE user_id=NEW.user_id AND stage_id=NEW.stage_id)
AND (SELECT count(*) FROM reactions WHERE user_id=NEW.user_id)>=500
BEGIN SELECT RAISE(ABORT,'reaction limit'); END;
