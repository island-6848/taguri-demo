---
id: dec-link-card
type: decision
status: adopted
date: 2026-10-19
title: リンクのカード（OGP・X のカード）は全ページ同じ 1 枚。Worker が HTML に足し、クローラーにはログインの画面を 200 で返す
sources:
  - cloudflare/src/link-card.js
  - cloudflare/src/worker.js
  - cloudflare/public/assets/og.png
  - cloudflare/test/link-card.test.js
links:
  - depends_on: f-link-card-spec
  - affects: comp-cf-worker
---
起案者の指示（2026-10-19）「リンク、Twitterとかで共有した時に出るURLのカード？みたいなやつ設定して」。

- 画像 `public/assets/og.png`（1200×630。ロゴ・「観たかった舞台を、見逃さない。」・「観劇の記録から、次の一本を届けるアプリ」）。ログインなしで読める
- タグ: og:type・site_name・title・description・url・image（絶対 URL）・image:width/height/alt・locale と、twitter:card=summary_large_image・title・description・image。Worker が配る HTML（アプリ・ログイン・規約・プライバシー）すべての `<head>` に HTMLRewriter で足す（src/link-card.js）。web/index.html はデモ（GitHub Pages）と共用なので触らない
- 中身はどのページも同じ。貼られたリンクはログイン前の人にも見えるので、記録・公演・人の名前は載せない
- ログインしていないリンクのクローラー（Twitterbot・facebookexternalhit/line-poker・Slackbot・Discordbot など、PREVIEW_BOT）には、/login への 302 の代わりにその場でログインの画面を返す。人には今までどおり 302
- 無料枠: クローラーの読み込みは Worker の要求 1 回と静的ファイル 1 回。D1・R2 は読まない
- 確かめたこと: Worker のテスト（タグ・画像の大きさ・クローラーに 200・人に 302・規約にもタグ）。本番で X や LINE に貼っての表示は未確認
