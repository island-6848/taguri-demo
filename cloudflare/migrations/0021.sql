-- 0021: per-user row caps for the tables that had none (dec-account-cap-counted).
-- Each row holds up to 4,000 characters (hand_credits up to 4 fields of 4,000), so without
-- a cap one account could fill D1's free 5 GB alone. The caps are far above what a
-- person keeps: one note and one hand-typed credit per record (works allows 2,000).
CREATE TRIGGER screen_visit_note_limit BEFORE INSERT ON visit_note
WHEN NOT EXISTS(SELECT 1 FROM visit_note WHERE user_id=NEW.user_id AND uid=NEW.uid)
AND (SELECT count(*) FROM visit_note WHERE user_id=NEW.user_id)>=2000
BEGIN SELECT RAISE(ABORT,'visit_note limit'); END;
CREATE TRIGGER screen_hand_credits_limit BEFORE INSERT ON hand_credits
WHEN NOT EXISTS(SELECT 1 FROM hand_credits WHERE user_id=NEW.user_id AND work_key=NEW.work_key)
AND (SELECT count(*) FROM hand_credits WHERE user_id=NEW.user_id)>=2000
BEGIN SELECT RAISE(ABORT,'hand_credits limit'); END;
CREATE TRIGGER screen_excluded_limit BEFORE INSERT ON excluded
WHEN NOT EXISTS(SELECT 1 FROM excluded WHERE user_id=NEW.user_id AND uid=NEW.uid AND program=NEW.program)
AND (SELECT count(*) FROM excluded WHERE user_id=NEW.user_id)>=2000
BEGIN SELECT RAISE(ABORT,'excluded limit'); END;
CREATE TRIGGER screen_merges_limit BEFORE INSERT ON merges
WHEN NOT EXISTS(SELECT 1 FROM merges WHERE user_id=NEW.user_id AND work_key=NEW.work_key)
AND (SELECT count(*) FROM merges WHERE user_id=NEW.user_id)>=2000
BEGIN SELECT RAISE(ABORT,'merges limit'); END;
CREATE TRIGGER screen_search_request_limit BEFORE INSERT ON search_request
WHEN NOT EXISTS(SELECT 1 FROM search_request WHERE user_id=NEW.user_id AND qkey=NEW.qkey)
AND (SELECT count(*) FROM search_request WHERE user_id=NEW.user_id)>=200
BEGIN SELECT RAISE(ABORT,'search_request limit'); END;
