---
id: dec-import-calendar-mail
type: decision
status: adopted
date: 2026-10-14
title: 過去の公演は、Google カレンダー（iCal の非公開アドレス）と購入確認メール（貼る・.eml）から、ブラウザの中で読み取って取り込む
sources:
  - cloudflare/src/client/import-parse.js
  - cloudflare/src/client/import.js
  - cloudflare/src/screens/import.js
  - cloudflare/src/screens/settings.js
  - cloudflare/src/worker.js
  - cloudflare/test/import.test.js
links:
  - depends_on: gmail-restricted-scope
  - supports: dec-free-tier-only
---
起案者の指示（2026-10-14）「購入確認メールから過去の公演を取り込むを実現したい」→「無料でできる方法調べて」→「Google カレンダーから取り込みいいかも。メール取り込みもどうにか利用者の負担が少ない形で実現したい。購入サイトごとでもいい」。
- Gmail を直接読む（gmail.readonly）は制限付きスコープで、公開すると有料の第三者審査が要るので使わない。転送用アドレスは独自ドメインが要り（有料）、外部の受信サービスは本文（氏名・座席・金額）が第三者を通るので採らない
- Google カレンダー：「iCal 形式の非公開アドレス」を 1 回だけ Worker が読み、そのまま返す（CORS のため）。Google のアドレスの形だけ受け付け、リダイレクトは追わず、8MB で止める。保存しない。予定の題名から候補を作り、公演と一致した予定だけを出す
- 購入確認メール：本文を貼るか .eml を選ぶ。発行元ごとの規則は tools/tickets/extract_performances.py の移植。本文はブラウザから出ない
- 照合は自動の結び付け（q-auto-link-past）と同じ規則（題名の鍵が同じ・上演期間に入る公演が 1 つ）。記録に足すのは利用者が印を付けたものだけ
- 未着手：チケットサイトの購入履歴ページを貼る（サイトごとの書式の見本が要る）、スマホの「共有」から送る（Android の共有先・iPhone のショートカット）、カレンダーを毎日読みにいく（アドレスを預かることになるので要判断）
