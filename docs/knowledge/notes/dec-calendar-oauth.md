---
id: dec-calendar-oauth
type: decision
status: adopted
date: 2026-10-14
title: Google カレンダーはボタン 1 つで取り込む：calendar.readonly を許可してもらい、ブラウザの中で Calendar API を読む（トークンはサーバーに送らない）
sources:
  - cloudflare/src/client/calendar-google.js
  - cloudflare/src/client/calendar-callback.js
  - cloudflare/src/client/import.js
  - cloudflare/public/oauth-calendar.html
  - cloudflare/src/worker.js
  - cloudflare/test/import.test.js
links:
  - depends_on: dec-import-calendar-mail
  - supports: dec-free-tier-only
---
起案者の指摘（2026-10-14）「スマホから見るとカレンダーの統合が表示されない。ボタン一つでカレンダーから取り込めるようにしたい」。iCal の非公開アドレスはパソコンの Google カレンダーの設定にしか無い。
- 押すと Google の許可の画面へ行き（OAuth の token 応答・state を sessionStorage で照合）、`/oauth/calendar` に戻る。戻った画面がブラウザの中で Calendar API（calendarList は自分が書ける暦だけ、events は過去 5 年・繰り返しを展開）を読み、予定（題名・日・時刻・場所）だけを sessionStorage で登録の画面へ渡す。照合と記録は iCal と同じ
- トークンはアドレスの # の後ろに来るので Worker には届かない。読んだらアドレスから消し、保存しない。Google のスクリプト（GIS）は読み込まない。CSP で googleapis.com への通信を許すのはこの画面だけ
- スコープは calendar.readonly（閲覧だけ）。Google の「機密性の高いスコープ」で、審査は無料（制限付きスコープの gmail.readonly と違い、第三者の評価は要らない）。審査が済むまでは「確認されていないアプリ」と出て 100 人まで
- iCal のアドレス・.ics ファイルは「アドレスやファイルから読み込む」に残す（パソコンで使う人・審査前の予備）
- 起案者の作業：Calendar API を有効に・同意画面にスコープ・リダイレクト URI・クライアント ID を wrangler.jsonc に。審査の申請
