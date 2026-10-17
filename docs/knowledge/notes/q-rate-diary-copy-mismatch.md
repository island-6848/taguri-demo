---
id: q-rate-diary-copy-mismatch
type: question
status: open
date: 2026-10-17
title: 評価一覧・未評価・日記帳の文が、画面の実際の名前・動きと食い違っている所がある
sources:
  - cloudflare/src/screens/rate.js
  - cloudflare/src/screens/diary.js
  - cloudflare/src/screens/row.js
---
yomiyasu で評価一覧・未評価・感想・日記帳の文を書き直したとき（2026-10-17、起案者の指示「サイトの全部の文章を書き直して」）に見つけた。
意味は変えない約束なので、文の中身は直さずに残した。直すかどうかは起案者が決める。

- 未評価と日記帳の説明は、各行の「公演詳細を直す」から直せると書いている。サービス版（Worker）の行の欄の名前は「記録を直す」（row.js の editHtml）。Python 版の欄の名前は確かめていない。
- 未評価の説明は、「行かなかった」を付けた記録が「日記帳に残っていますので、その行の『やはり観た』で戻してください」と書いている。日記帳の画面（diary.js の worksScreen）は「行かなかった」の記録を出さず、日記帳の冒頭の文（recordsLede）も「『日記帳』には出さず、『設定』の『行かなかった公演』にまとめてあり」と書いている。どちらかが古い。
