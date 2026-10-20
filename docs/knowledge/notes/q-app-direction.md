---
id: q-app-direction
type: question
status: open
date: 2026-10-20
title: 「本格的にアプリ化」をどう進めるか（ホーム画面に入れる Web アプリ＝PWA から始めるか）
links:
  - depends_on: f-app-store-fees
  - depends_on: f-ios-web-push
---
起案者の希望（2026-10-20）「本格的にアプリ化に進みたい」。

いま: manifest も service worker も無い（apple-touch-icon だけ）。ホーム画面に入れてもブラウザのページとして開く。

案（どれも無料の範囲）:
1. ホーム画面に入れられるようにする: manifest（名前・アイコン・開く画面・全画面表示）、service worker（画面の部品だけを手元に控え、記録や答えは控えない）、通信が無いときの一枚、入れ方の案内（iPhone は共有 →「ホーム画面に追加」）
2. アプリらしい見た目: 全画面で開いたときの上下の余白（ノッチ）、下のメニュー、読み込みの見せ方
3. 通知（Web Push）: 開幕リマインド・発売日・お気に入りの新着。鍵（VAPID）の秘密・通知先の保存（D1 の書き込み）・送る定期実行（Worker の cron と CPU 時間）が増えるので、無料枠を数えてから

ストアに出す（App Store・Google Play）は登録料がかかるので、約束のうえでは進めない（変えるなら起案者が決める）。workers.dev のドメインのまま入れると、あとで独自ドメインに移ったとき入れ直しになる（パスキーと同じ）。
