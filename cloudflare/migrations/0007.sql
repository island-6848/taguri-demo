-- Link a record to the stage it was (rec_people / rec_stage stage_id), so its
-- rating counts for the people in it. NULL = not linked (still counts in the
-- user's overall ◎ rate, as in the Python recommender).
ALTER TABLE records ADD COLUMN stage_id TEXT;
