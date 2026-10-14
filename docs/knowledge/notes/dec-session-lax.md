---
id: dec-session-lax
type: decision
status: adopted
date: 2026-10-14
title: ログインの Cookie を SameSite=Strict から Lax に変えた（ほかのアプリのリンクから開くたびにログインを求めていた）
sources:
  - cloudflare/src/worker.js
  - cloudflare/test/firebase-auth.test.js
  - cloudflare/test/passkey.test.js
  - docs/cloudflare-security-review.md
links:
  - affects: dec-login-hardening
---
起案者の問い（2026-10-14）「開き直すたびにログイン求められるのなぜ？普通のサイトって一定期間は再ログインしなくても使えるよね」。
- セッションは 30 日（Max-Age と D1 の expires_at）で、期間は普通のサイトと同じだった。原因は Cookie の SameSite=Strict: ほかのサイト・アプリ（LINE・メール・チャットのリンクなど）から開いた最初の読み込みには、ブラウザが Strict の Cookie を付けない。Worker の gate はログインしていないと見て /login へ送っていた。ブックマークや URL の直接入力では付くので、開き方によって出たり出なかったりした（仕様は MDN・RFC 6265bis の SameSite の説明どおり。本番の実機で再現はしていない）
- Lax にした。Lax は別サイトからのトップレベルの GET には Cookie を付け、別サイトからの POST や埋め込みには付けない。書き込みはすべて POST で、Origin が同じサイトでなければ 403（worker.js の 2 か所と original-ui.js）なので、CSRF の守りは下がらない
- 残る違い: 別サイトからのリンクで ?f=1&pref=… の付いた画面を開くと、絞り込みの保存（GET で書く）が本人の Cookie で走りうる。害は絞り込みが変わるだけで、Strict でもログイン画面からの戻り先で同じことが起きていた
- 分からないこと: iPhone のホーム画面に追加した場合など、端末ごとの Cookie の持ち方（q-safari-cookies）。直らない端末があれば開き方を聞いて確かめる
