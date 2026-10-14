-- 0022: a memo written before seeing an owned stage (購入済み公演「観る前のメモ」,
-- 起案者の指示 2026-10-14). Kept apart from note (なぜ気になったか) and note_no.
ALTER TABLE reaction ADD COLUMN note_pre TEXT;
