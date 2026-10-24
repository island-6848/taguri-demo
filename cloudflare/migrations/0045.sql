-- 感想を AI（Claude Haiku 5.5）で読み取った結果（起案者の指示 2026-10-21「感想を送信することにチェックした場合のみ可能
-- （設定画面に同意非同意つくって）」「haikuにしたい」、dec-note-ai）。設定で同意した人（app_setting の note_ai='1'）の感想だけを、
-- 夜の定期実行で送る。感想の本文はここに写さない（works.note_impression にだけある）。
--   note_hash: 読み取った時の感想の文の印（文が変わったら読み直す。impression.noteHash）
--   feats: 候補の言葉と良し悪し [[言葉, 1|-1], …]（JSON）。候補に無い言葉は入らない
--   status: 'ok'・'none'（該当なし）・'refused'（AI が断った。読み直さない）・'bad'（答えの形が崩れた。次の夜にもう一度）
--   model・prompt_ver: どの版で読んだか（版が変われば読み直せるように）
-- 同意をやめたら、その人の行を全部消す（note-ai.consentAction）。
CREATE TABLE note_ai (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 work_key TEXT NOT NULL,
 note_hash TEXT NOT NULL,
 feats TEXT NOT NULL DEFAULT '[]',
 status TEXT NOT NULL,
 model TEXT NOT NULL,
 prompt_ver TEXT NOT NULL,
 analyzed_at TEXT NOT NULL,
 PRIMARY KEY (user_id, work_key)
);
