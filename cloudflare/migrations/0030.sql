-- 利用者からの「公演修正依頼」（起案者の指示 2026-10-17「ユーザーが『公演修正依頼』を送ってきたら私に通知が来て、
-- この管理画面から編集できるようにしたい」。通知はメール）。カードの「情報の誤りを知らせる」から送られ、
-- 起案者にメールで知らせ（src/screens/fixrequest.js）、手元の管理画面（tools/admin）で一覧・対応する。
--   kind: 日程・料金・会場・あらすじ・出演・ポスター・その他。status: open / done（直した）/ dropped（見送った）
--   note: 対応したときの控え（管理画面で書く）。mailed: 知らせのメールを送れたら 1
CREATE TABLE fix_request (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  stage_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  note TEXT,
  resolved_at TEXT,
  mailed INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX fix_request_open ON fix_request(status, created_at);
CREATE INDEX fix_request_user ON fix_request(user_id, created_at);
-- アカウントを消したら、その人の依頼の本文も消す（依頼そのものは対応の記録として残し、利用者と本文だけ外す）
CREATE TRIGGER fix_request_user_gone AFTER DELETE ON users BEGIN
  UPDATE fix_request SET user_id='', message='（アカウント削除により消去）' WHERE user_id=OLD.id;
END;
