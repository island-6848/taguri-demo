-- 推薦を本番の利用者のデータで測るための記録（起案者の指示 2026-10-17「実データで測る方法を設計して」「1も2もお願い」。
-- 設計は docs/research/real-data-eval-plan.md の §5）。分析から外れる設定（app_setting の analysis_optout）を選んだ人の分は書かない。
--
-- 答えたときの順位・点・推薦の版。答えを書くその行に入れるので、書き込みは増えない。
--   rank: おすすめの控え（rec_cache）の並びでの順位（1 から。都道府県で絞る前）。控えに無い公演は NULL
--   score: そのときの点（b）。ver: 画面の版 '|' 索引の版。arm: 2 つの並べ方を混ぜて出すとき（§4）に、どちらから来たか。今は NULL
ALTER TABLE reaction ADD COLUMN rank INTEGER;
ALTER TABLE reaction ADD COLUMN score REAL;
ALTER TABLE reaction ADD COLUMN ver TEXT;
ALTER TABLE reaction ADD COLUMN arm TEXT;
-- その日に出した公演の並び。利用者 × 日 × 画面（recommend・reminder）に 1 行。答えなかった公演も分かる（H2・H4 の分母）。
--   ids: stage_id の JSON 配列（その日に初めて出した順。同じ日に開き直して増えた分は後ろに足す。300 件まで）
--   writes: その日にこの行を書いた回数。6 回までで、それより後に出した分は残さない（無料枠の書き込みを 1 人 1 日 12 行までに抑える）
-- 新しい日の行を書くときに、その人の 180 日より古い行を消す
CREATE TABLE rec_shown (
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  screen TEXT NOT NULL,
  ids TEXT NOT NULL,
  ver TEXT,
  writes INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, label, screen)
);
