---
id: q-account-rankings-look-1021
type: question
status: answered
date: 2026-10-21
title: 起案者に、アカウントの団体・劇場のランキングが「前作ったときの見た目じゃない」と見える。master のコードは作ったときのまま。本番が古いのか、別の見た目を指しているのか
sources:
  - cloudflare/src/screens/account.js
  - cloudflare/public/theme.css
links:
  - affects: dec-account-rankings
---
起案者の指摘（2026-10-21）「アカウントページのこれまでの記録をランキングにするやつ実装されてない」「前作ったときの見た目じゃない」。

確かめたこと（リポジトリのコードと実行結果）:
- ランキングは aa70446（2026-10-20）で入り、master に入っている。それ以降、account.js と theme.css のランキングの部分は変わっていない
- cloudflare/test/account-stats.test.js の 4 件は通る
- 今のコードで画面を描いて写しを撮ると、順位の丸い札（1〜3 位は幕の色）・名前・棒・数の形で出る（作ったときの記録 dec-account-rankings のとおり）
- service worker（public/sw.js）は先に取りに行く作りで、古い CSS を出し続けることはない

分からないこと:
- 本番（app.taguri.workers.dev）がこの版で動いているか。このセッションの通信では本番に届かない（403）。Workers Builds の master の組み立てが通っているかは、起案者にダッシュボードで見てもらう
- 起案者が思っている「前の見た目」が、上の形と違うもの（別のセッションで見せた案など）かどうか

答え（2026-10-21）: 起案者が求めていたのは見た目の手直しで、「1作品のものは端折ってよい。同率の場合は併記して。つまりそれぞれ3行以内に抑えてください」。dec-account-rankings-top3 で直した。本番が古いかどうかは確かめていない。
