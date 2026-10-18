-- パスキーの問い（webauthn_challenges）を、接続元ごとにも数える（安全の点検 2026-10-17 の残り、issue #73）。
-- これまでは全員で 1000 件までだったので、1 か所からの要求で埋めると、ほかの人がパスキーで入れなくなった。
-- 接続元の住所そのものは持たない（日と住所のハッシュの先頭 12 バイト。rate-limit.js の新規登録の数えと同じ）。
ALTER TABLE webauthn_challenges ADD COLUMN addr TEXT;
CREATE INDEX webauthn_challenge_addr ON webauthn_challenges(addr);
