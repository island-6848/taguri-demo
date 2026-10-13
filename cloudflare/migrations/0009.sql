-- Title search for linking a record to a stage (/migration-api/stages).
-- tkey is rate_performances.title_key(title), computed in batch.
ALTER TABLE rec_stage ADD COLUMN tkey TEXT NOT NULL DEFAULT '';
-- Two-character piece of tkey -> [[stage_id, tkey, start, end], ...]. Every
-- title containing a query contains each of its pieces, so the stages under the
-- query's rarest piece are a superset of the matches; the Worker then checks
-- the whole key. Long lists are split into parts to keep statements small.
CREATE TABLE rec_gram (
 ver TEXT NOT NULL, gram TEXT NOT NULL, part INTEGER NOT NULL, entries TEXT NOT NULL,
 PRIMARY KEY(ver, gram, part)
);
