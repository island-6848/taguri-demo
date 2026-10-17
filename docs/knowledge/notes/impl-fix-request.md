---
id: impl-fix-request
type: decision
status: adopted
date: 2026-10-17
title: 利用者の「公演修正依頼」をカードから受け、起案者に Gmail で知らせ、手元の管理画面で一覧・対応する
sources:
  - cloudflare/migrations/0030.sql
  - cloudflare/src/screens/fixrequest.js
  - cloudflare/test/fixrequest.test.js
  - web/app.js
  - tools/admin/admin.py
  - tools/admin/admin.html
links:
  - depends_on: impl-admin-tool
  - depends_on: fix-request-mail
---
起案者「ユーザーが『公演修正依頼』を送ってきたら私に通知が来て、この管理画面から編集できるようにしたい」→ 通知の届け先は「メール」（2026-10-17。選択肢に Web Push・Discord・Telegram・管理画面だけを出したうえで、起案者がメールと答えた）。
- 受け口: カードの下の「公演情報の誤りを知らせる」（web/app.js fixLinks。サービス版だけ）。どこが（日程・料金・会場・あらすじ・出演・スタッフ・ポスター・その他）と本文（1,000 字まで）。POST /api/fix_request（ログインした人だけ。保存が上限のときは既存の守りで断る）
- 保存: fix_request（migration 0030）。1 人 1 日 5 件まで（free-tier.js FIX_REQUESTS_PER_USER_DAY）。アカウントを消すと、依頼の本文と利用者を消す（対応の記録は残す。トリガー）
- 知らせ: 独自ドメインを使わない約束なので Cloudflare のメール送信は使えない（Email Routing のドメインが要る）。Worker から起案者の Gmail に SMTP（smtp.gmail.com:465・TLS、cloudflare:sockets の connect）でつなぎ、自分宛てに送る。鍵は Worker のシークレット SMTP_USER・SMTP_PASS（アプリ パスワード）・NOTIFY_TO。1 日 30 通まで（FIX_MAILS_PER_DAY、usage 表で送る前に数える）。メールには依頼した人の名前・アドレス・利用者の番号を入れない。設定が無い・送れないときも依頼は保存する（mailed=0）
- 管理画面: 左に「公演修正依頼」（未対応・直した・見送った・すべて）。押すと依頼の文と公演の編集が一緒に開き、直して保存 →「直した」/「見送る」（控えを書ける）。D1 の fix_request と admin_log、手元の log.jsonl に書く。開いているあいだは 5 分ごとに読み直して題名に件数
- 確かめたこと: Worker のテスト（fixrequest.test.js: 偽の SMTP で AUTH・宛先・件名・本文、依頼した人の番号が本文に無いこと、入力の誤り、1 人 1 日の上限、設定なし・認証失敗でも保存）、Python のテスト（一覧・対応・記録・未対応に戻す）、ブラウザ（カードの欄から送る、管理画面で開いて「直した」）。本物の Gmail には送っていない（シークレットは起案者が入れる）
