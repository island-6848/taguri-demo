-- すべての端末でログアウトした時刻（issue #127）。これより前に Google・メールでログインして得た
-- Firebase の ID トークン（5 分以内なら署名と期限は有効）を、新しいセッションに換えない。
ALTER TABLE users ADD COLUMN tokens_valid_after INTEGER;
