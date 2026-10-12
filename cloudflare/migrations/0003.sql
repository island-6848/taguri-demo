-- Person-score index built in batch by scripts/build_recommend_index.py.
-- Every row carries the catalogue version (ver). The builder inserts a new
-- version, then switches rec_meta.current, then deletes older versions, so a
-- failed or partial upload leaves the previous version in use.
CREATE TABLE rec_meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
-- Public display fields and run dates of one candidate stage.
CREATE TABLE rec_stage (
 ver TEXT NOT NULL, stage_id TEXT NOT NULL,
 title TEXT NOT NULL, grp TEXT NOT NULL DEFAULT '',
 start TEXT NOT NULL DEFAULT '', end TEXT NOT NULL DEFAULT '',
 credits TEXT NOT NULL DEFAULT '[]', entry TEXT NOT NULL DEFAULT '{}',
 PRIMARY KEY(ver, stage_id)
);
-- (role, person) -> candidate stages. role_w and role_group are resolved in
-- batch so the Worker needs no copy of the role tables.
CREATE TABLE rec_credit (
 ver TEXT NOT NULL, role TEXT NOT NULL, person TEXT NOT NULL, stage_id TEXT NOT NULL,
 role_w REAL NOT NULL, role_group TEXT NOT NULL,
 PRIMARY KEY(ver, role, person, stage_id)
);
-- stage -> parsed credits, for building a user's roster from linked records.
-- Covers past stages (credits/linked) as well as candidates.
CREATE TABLE rec_people (
 ver TEXT NOT NULL, stage_id TEXT NOT NULL, people TEXT NOT NULL,
 PRIMARY KEY(ver, stage_id)
);
