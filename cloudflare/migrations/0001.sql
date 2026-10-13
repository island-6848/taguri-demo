PRAGMA foreign_keys = ON;
CREATE TABLE users (id TEXT PRIMARY KEY, recovery_hash TEXT NOT NULL UNIQUE, created_at INTEGER NOT NULL);
CREATE TABLE sessions (hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, expires_at INTEGER NOT NULL);
CREATE INDEX session_expiry ON sessions(expires_at);
CREATE TABLE records (user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, id TEXT NOT NULL, title TEXT NOT NULL, date TEXT NOT NULL, time TEXT NOT NULL DEFAULT '', venue TEXT NOT NULL DEFAULT '', rating TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '', updated_at INTEGER NOT NULL, PRIMARY KEY(user_id,id));
CREATE INDEX record_date ON records(user_id,date DESC,id);
CREATE TABLE favourites (user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, name TEXT NOT NULL, kind TEXT NOT NULL, PRIMARY KEY(user_id,name,kind));
CREATE TABLE catalogue (id TEXT PRIMARY KEY, title TEXT NOT NULL, date TEXT NOT NULL, venue TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '');
CREATE INDEX catalogue_date ON catalogue(date,id);
-- Bound persistent data even if concurrent requests bypass application counts.
CREATE TRIGGER record_limit BEFORE INSERT ON records
WHEN NOT EXISTS(SELECT 1 FROM records WHERE user_id=NEW.user_id AND id=NEW.id)
AND (SELECT count(*) FROM records WHERE user_id=NEW.user_id)>=500
BEGIN SELECT RAISE(ABORT,'record limit'); END;
CREATE TRIGGER favourite_limit BEFORE INSERT ON favourites
WHEN NOT EXISTS(SELECT 1 FROM favourites WHERE user_id=NEW.user_id AND name=NEW.name AND kind=NEW.kind)
AND (SELECT count(*) FROM favourites WHERE user_id=NEW.user_id)>=200
BEGIN SELECT RAISE(ABORT,'favourite limit'); END;
CREATE TRIGGER account_limit BEFORE INSERT ON users
WHEN (SELECT count(*) FROM users)>=100
BEGIN SELECT RAISE(ABORT,'preview account limit'); END;
