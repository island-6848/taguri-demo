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

進み具合（2026-10-14）:
- 1・2 は済み。起案者の知らせで本番の URL は https://app.taguri.workers.dev/ になった（アカウントの名前 taguri、Worker の名前 app）。古い URL は https://taguri-demo.on6848-tech.workers.dev（Worker の ID d16a314e3873447d8d23ae7a23ab9c61 は変わらない）
- 3 は済み（wrangler.jsonc の name を app に。D1 の名前 taguri-demo はそのまま）。この作業の箱からは workers.dev に繋げないので、開けるかは起案者が確かめる
- 5: 起案者は変数を変えたが、TAGURI_SERVICE_API の置き場所が見つからなかった。リポジトリ taguri-demo の Settings → Secrets and variables → Actions の「Variables」の札（Secrets の札ではない）にあり、無ければ New repository variable で作る。pages.yml がこれを config.js に埋める（未設定なら「準備中」）
- 4 は済み（起案者の知らせ、2026-10-14）: Firebase の Authorized domains に app.taguri.workers.dev を足した
- 残り: 起案者が新しい URL で開いて、Google でログインできるかを確かめる。翌朝の catalog-age.yml（TAGURI_HEALTH_URL）が新しい URL で通るかを見る
