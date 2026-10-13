-- Readable names of catalogue stages for the original screens: app.stage_label
-- ("題名／劇場／日付") shown in a record's edit box once it is linked to a stage.
-- Built in batch by scripts/build_stage_labels.py from the public catalogue
-- (candidates.jsonl and picked.jsonl, the same rows app._suggest_pool reads),
-- versioned like rec_*: the builder inserts a version, switches
-- rec_meta 'stage_label' to it, then deletes the older ones. `title` is the
-- stage's title as app.link_stage returns it (the first stage row of
-- app._suggest_pool for that id).
CREATE TABLE stage_label (
 ver TEXT NOT NULL, stage_id TEXT NOT NULL, label TEXT NOT NULL, title TEXT NOT NULL DEFAULT '',
 PRIMARY KEY(ver, stage_id)
);
