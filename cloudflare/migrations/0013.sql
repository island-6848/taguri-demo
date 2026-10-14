-- Posters kept in R2 (bucket bound as POSTERS, object key = `file`), one row
-- per stage. Written by scripts/deliver_posters.py after the object is uploaded;
-- the Worker reads it to draw <img src="/img/<file>"> and serves /img/<file>
-- from R2 (app._poster on Render serves the same path from data/review/img).
CREATE TABLE poster (stage_id TEXT PRIMARY KEY, file TEXT NOT NULL);
