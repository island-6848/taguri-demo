-- 共有リンク（起案者の指示 2026-10-21「共有できるようにしたい。公演単体か、または指定のページをパブリックで公開するか選べるように」、
-- dec-share-links）。リンクを知る人だけが、ログインなしで読める（検索エンジンには載せない）。いつでも取り消せる。
--   token: 推測できない 22 文字（128 ビット）。URL は /s/<token>
--   kind: 'stage'（公演 1 件のカード）・'works'（観劇記録の一覧）・'records'（眺める）・'favourites'（お気に入り）・'chronicle'（年表・評価）
--   target: kind='stage' のときの stage_id。ほかは ''
--   label: kind='stage' のときの見出しの種類（'owned' 購入しました・'interest' 興味あり・'watched' 観ました）。ほかは ''
--   show_verdict・show_note・show_name: 評価・感想・表示名とアイコンを出すか（共有するときに本人が選ぶ。既定は出さない）
--   revoked_at: 取り消した時刻（行は残さず消す運用だが、取り消しの印として使える形にしておく）
-- 公開ページは毎回、本人のいまの記録から作る（写しは置かない）。消した記録・取り消したリンクはすぐ見えなくなる。
CREATE TABLE share (
 token TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 kind TEXT NOT NULL, target TEXT NOT NULL DEFAULT '', label TEXT NOT NULL DEFAULT '',
 show_verdict INTEGER NOT NULL DEFAULT 0, show_note INTEGER NOT NULL DEFAULT 0, show_name INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, revoked_at TEXT
);
CREATE INDEX share_user ON share(user_id);
-- 1 人 100 件まで（増える書き込みだけを止める。0037 と同じ形）
CREATE TRIGGER screen_share_limit BEFORE INSERT ON share
WHEN NOT EXISTS(SELECT 1 FROM share WHERE token=NEW.token)
AND (SELECT count(*) FROM share WHERE user_id=NEW.user_id)>=100
BEGIN SELECT RAISE(ABORT,'share limit'); END;
