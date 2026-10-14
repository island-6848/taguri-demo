-- Past stages read from CoRich stage pages by tools/review/fetch_past_stages.py
-- (2019 onwards, a few thousand a day) and uploaded by scripts/deliver_past.py.
-- Used only to link a user's record to the stage they saw, automatically:
-- same title (rate_performances.title_key) and the viewing date inside the run.
-- `people` is measure_nets.parse_credits of the page's credits, in the same form
-- as rec_people.people. Not versioned: rows are only added or replaced.
CREATE TABLE past_stage (
 stage_id TEXT PRIMARY KEY, title TEXT NOT NULL, tkey TEXT NOT NULL,
 start TEXT NOT NULL DEFAULT '', end TEXT NOT NULL DEFAULT '',
 venue TEXT NOT NULL DEFAULT '', grp TEXT NOT NULL DEFAULT '', pref TEXT NOT NULL DEFAULT '',
 people TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX past_stage_tkey ON past_stage(tkey);
-- stage_auto: the link was made automatically (shown as "自動で結び付けました").
-- stage_off: the user removed a link, so never link this record automatically again.
ALTER TABLE works ADD COLUMN stage_auto INTEGER NOT NULL DEFAULT 0;
ALTER TABLE works ADD COLUMN stage_off INTEGER NOT NULL DEFAULT 0;
