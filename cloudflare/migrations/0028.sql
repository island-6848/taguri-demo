-- 管理者が手で直した公演の情報（起案者の指示 2026-10-17「管理者画面を作成して。…ポスターがない画像に自分で足したり、
-- 詳細を編集したり、あらすじを追加したりする。個人で手動で追加したものは…自動的にデータベースやログに書き込まれる」）。
-- 書くのは手元の管理画面（tools/admin）だけ。カード（rec_card）は取得のたびに作り直されるので、手で直した分は
-- この表に置き、画面に出すとき（cards.cardTemplates・fallback.stageInfo）に重ねる。消えないように別の表にしてある。
--   synopsis: あらすじ（NULL は直していない）。themes: 題材の語の JSON 配列（NULL は直していない）。
--   info: {venue, pref, period, url, fields: {欄: 値}} の JSON（直した欄だけ）
CREATE TABLE stage_override (
  stage_id TEXT PRIMARY KEY,
  synopsis TEXT,
  themes TEXT,
  info TEXT,
  updated_at TEXT NOT NULL
);
-- 手で直したことの記録（何を・いつ・前の値と新しい値）。手元の data/admin/log.jsonl と同じ中身
CREATE TABLE admin_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  stage_id TEXT,
  action TEXT NOT NULL,
  detail TEXT NOT NULL
);
