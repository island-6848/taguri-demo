-- 新規登録のときに同意した利用規約・プライバシーの説明の版と日時（起案者の指示 2026-10-17「規約は新規登録の際に、
-- 規約に同意して始める、にチェックボックスいれてもらってから登録できるようにする」。src/terms.js）。
-- これより前に作ったアカウントは NULL（同意のチェックが無かったころ）
ALTER TABLE users ADD COLUMN terms_version TEXT;
ALTER TABLE users ADD COLUMN terms_at INTEGER;
