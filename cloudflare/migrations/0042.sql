-- 1 回の公演で複数の作品を上演した記録を、作品ごとに分けた中身（起案者の指示 2026-10-19「1 公演を 1 件として表示しつつ、
-- 評価や推薦、感想…は作品数分分けられる？ただしユーザーが分けたいとしたときの任意」、dec-split-pieces）。
-- 記録（works）は 1 公演 1 行のまま。分けた人の分だけ、作品ごとに 1 行を足す。分けていない記録には行が無い。
--   idx: 作品の並び（0 から）。title: 作品名。verdict・aspects・note: 作品ごとの評価・気になった所・感想
--   cast_in: この作品に出ていた出演者の名前の JSON 配列。'' は「公演の出演者の全員」
--   rated_at: 評価（verdict・aspects）を付けた・直した時刻（works.rated_at と同じ形）
-- 推薦は作品ごとの評価を、出た作品の数を ρ=0.4 で縮めた件数ぶんだけ数える（recommend.personValues）。
CREATE TABLE work_piece (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 work_key TEXT NOT NULL, idx INTEGER NOT NULL, title TEXT NOT NULL,
 verdict TEXT, aspects TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '', cast_in TEXT NOT NULL DEFAULT '',
 rated_at TEXT, updated_at TEXT NOT NULL,
 PRIMARY KEY (user_id, work_key, idx)
);
-- 1 記録 20 作品・1 人 2,000 行まで（works と同じ数。1 行は感想 4,000 字まで）。増える書き込みだけを止める（0037 と同じ形）
CREATE TRIGGER screen_work_piece_limit BEFORE INSERT ON work_piece
WHEN NOT EXISTS(SELECT 1 FROM work_piece WHERE user_id=NEW.user_id AND work_key=NEW.work_key AND idx=NEW.idx)
AND ((SELECT count(*) FROM work_piece WHERE user_id=NEW.user_id)>=2000
  OR (SELECT count(*) FROM work_piece WHERE user_id=NEW.user_id AND work_key=NEW.work_key)>=20)
BEGIN SELECT RAISE(ABORT,'work_piece limit'); END;
-- 推薦の材料なので、書くたびに rec_rev を進める（0035 と同じ）。評価なので works_rev（裏の答え合わせの使い回し）も進める
CREATE TRIGGER rec_rev_work_piece_insert AFTER INSERT ON work_piece BEGIN UPDATE users SET rec_rev=rec_rev+1, works_rev=works_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_work_piece_update AFTER UPDATE ON work_piece BEGIN UPDATE users SET rec_rev=rec_rev+1, works_rev=works_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_work_piece_delete AFTER DELETE ON work_piece BEGIN UPDATE users SET rec_rev=rec_rev+1, works_rev=works_rev+1 WHERE id=OLD.user_id; END;
