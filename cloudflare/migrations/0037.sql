-- 件数の上限は、増える書き込みだけを止める（issue #188）。0010 の ticket・reaction・missed のトリガーは総数だけを見ていたので、
-- 上限に届いた人は、既にある行の付け直し（INSERT ... ON CONFLICT DO UPDATE。BEFORE INSERT が先に動く）まで断られていた。
-- works・hand_credits・excluded など他の表と同じく、主キーの行がまだ無いときだけ数える。上限の数は変えない。
DROP TRIGGER IF EXISTS screen_ticket_limit;
CREATE TRIGGER screen_ticket_limit BEFORE INSERT ON ticket
WHEN NOT EXISTS(SELECT 1 FROM ticket WHERE user_id=NEW.user_id AND stage_id=NEW.stage_id AND date=NEW.date AND time=NEW.time)
AND (SELECT count(*) FROM ticket WHERE user_id=NEW.user_id)>=2000
BEGIN SELECT RAISE(ABORT,'ticket limit'); END;
DROP TRIGGER IF EXISTS screen_reaction_limit;
CREATE TRIGGER screen_reaction_limit BEFORE INSERT ON reaction
WHEN NOT EXISTS(SELECT 1 FROM reaction WHERE user_id=NEW.user_id AND label=NEW.label AND stage_id=NEW.stage_id)
AND (SELECT count(*) FROM reaction WHERE user_id=NEW.user_id)>=5000
BEGIN SELECT RAISE(ABORT,'reaction limit'); END;
DROP TRIGGER IF EXISTS screen_missed_limit;
CREATE TRIGGER screen_missed_limit BEFORE INSERT ON missed
WHEN NOT EXISTS(SELECT 1 FROM missed WHERE user_id=NEW.user_id AND title=NEW.title)
AND (SELECT count(*) FROM missed WHERE user_id=NEW.user_id)>=500
BEGIN SELECT RAISE(ABORT,'missed limit'); END;
