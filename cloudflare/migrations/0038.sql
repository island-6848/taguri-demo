-- 利用者ごとのセッションと、同じ公演（tour）の会場をひく索引（issue #193）。
-- 全 migration を当てた手元の D1（wrangler の getPlatformProxy = workerd の SQLite）に、本番の大きさの行
-- （利用者 300 人 × 10 端末、rec_stage 4,818 行、rec_card 1,557 行）を入れて rows_read を測った（2026-10-18）:
--   sessions の user_id で消す・数える（worker.js startSession・account.js 端末数）  SCAN sessions 2,093〜5,706 行 → 8〜31 行
--   空のアカウントの片付け（cleanup.js、1 日 1 回）の sessions の相関副問い合わせ        307,172 行 → 499 行
--   rec_stage の tour IN（recommend.js 会場・search.js ツアーのほかの会場）            ver だけの SEARCH 4,818 行 → 88 行
--   rec_card の tour IN（lists.js buckets。日記帳・カレンダー・検索・リマインドの各画面） ver だけの SEARCH 1,558 行 → 89 行
-- 増える書き込み（同じ手元の D1 の rows_written）: 足した行・upsert した行ごとに 1。
--   sessions はログイン 1 回に 1、rec_stage は差分で変わった行ごとに 1（ふだん数百行、初回でも 4,818）、
--   rec_card は毎日作り直すので「これからの公演の数」の 1〜2 倍（約 1,600〜3,100 / 日、deliver_catalogue.py の見積もりに足した）。
-- users(created_at) は足さない: 利用者は 300 人まで（rate-limit.js）なので、1 日の登録数の数えは最大 300 行で頭打ち。
CREATE INDEX sessions_user_expiry ON sessions(user_id, expires_at DESC);
CREATE INDEX rec_stage_tour ON rec_stage(ver, tour);
CREATE INDEX rec_card_tour ON rec_card(ver, tour);
