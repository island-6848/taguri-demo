---
id: dec-about-on-login
type: decision
status: adopted
date: 2026-10-14
title: 「たぐりとは」とログインを 1 ページ（/login）にまとめ、説明は使い方の流れの図にする。GitHub の使い方ガイドへのリンクを置く
sources:
  - cloudflare/public/login.html
  - cloudflare/public/auth.css
  - cloudflare/src/worker.js
  - cloudflare/test/gate.test.js
---
起案者の指示（2026-10-14）「たぐりとは、とログインのページをわけないで。たぐりとはの説明の下に、ログインの画面のやつそのまま持ってきて、1ページにまとめて。たぐりとは、の説明は図でわかりやすく。github にあるユーザーガイドのリンクも貼るように」。
- /login の上に「たぐりとは」（見出し・一文の説明・使い方の流れの図「記録する → おすすめが届く → 興味ありで選ぶ → 観にいく」を回る輪と中央の「使うほど好みに近づく」・安心して使える理由 3 つ・使い方ガイド（GitHub Pages の docs/000010-user-guide-taguri.html）へのリンク・「ログインして始める」）、その下にもとのログインの部分をそのまま置く
- 図は SVG を HTML に直接書く。/login は style-src 'self' なので、色は auth.css のクラスとテーマの変数（--curtain など）で付ける（ダークモードでもそのまま読める）
- /about は /login へ転送する。ログインしていない人のトップ（/）も /login へ。about.html は消した
- アカウント削除の入り直し（/login?purpose=delete）では、Worker が HTMLRewriter で「たぐりとは」の部分を外す（ログインの JS は変えない）
