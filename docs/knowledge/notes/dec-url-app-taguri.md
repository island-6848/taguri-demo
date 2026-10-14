---
id: dec-url-app-taguri
type: decision
status: adopted
date: 2026-10-14
title: サービス版の URL は無料のまま app.taguri.workers.dev にする（独自ドメインは取らない）
links:
  - answers: q-domain-taguri-com
  - depends_on: workers-dev-subdomain-rename
  - supports: dec-free-tier-only
---
起案者の指示（2026-10-14）「2で、app.taguri.workers.devにして」。taguri.com は年額がかかるので取らない（無料だけの約束どおり）。
手順（Cloudflare では Worker の名前が wrangler.jsonc の name と合っていないと Workers Builds が失敗するので、ダッシュボードで変えてから設定を合わせる。失敗しても動いている版はそのまま残り、止まりはしない）:
1. 起案者: Workers & Pages の「Your subdomain」の Change で、アカウントの名前を taguri にする（空いていれば）
2. 起案者: Worker「taguri-demo」の Settings → General で名前を app に変える
3. Claude: cloudflare/wrangler.jsonc の name を app にして master に押す（D1 の名前 taguri-demo は変えない ── 取得の作業が名前で引いている）
4. 起案者: Firebase の Authentication → Settings → Authorized domains に app.taguri.workers.dev を足す（Google のログインのため）
5. 起案者: GitHub のリポジトリの変数 TAGURI_SERVICE_API を https://app.taguri.workers.dev に、TAGURI_HEALTH_URL を https://app.taguri.workers.dev/api/health にする（デモ版から入るサービス版の行き先と、毎日のカタログの見張り）
変わること: URL が変わるので、ログインしている人は一度ログインし直しになる（Cookie はドメインごと）。古い URL で作ったパスキーは使えなくなる（パスキーはドメインに結び付く〔passkey-rpid-domain〕）。古い URL は使えなくなる。
