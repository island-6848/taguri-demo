---
id: dec-account-page
type: decision
status: adopted
date: 2026-10-14
title: 本人だけが見るアカウントの画面（/account）を Worker に作る
sources:
  - cloudflare/src/screens/account.js
  - web/app.js
  - web/theme.css
  - cloudflare/test/cutover.test.js
links:
  - depends_on: dec-native-cutover-now
  - affects: comp-native-screens
  - affects: comp-frontend
---
起案者の指示（2026-10-14）「アカウントのページを作成して（プロフィールページみたいなもの）」。公開範囲は AskUserQuestion で「自分だけ」（ほかの案は「他の人にも公開できる」）。
中身: 表示名（app_setting の display_name。30 文字まで、この画面にだけ出る。空で消える）・始めた日・観た作品／評価した作品／感想／お気に入り／興味ありの数（各画面へのリンク）・よく観ている団体とよく行く劇場（上位 5）・ログインの方法（Google またはメール・パスキー・復旧コード）・ログイン中の端末の数・ログアウト（この端末／すべて）・パスキーの管理（いまは /migration-data/#passkeys へのリンク）・アカウントの削除（/login?purpose=delete）。
Python のサービス版にはこの画面が無いので、一致の試験はない。本人の行だけを読むことと、他人に見えないことを cutover.test.js が確かめる。入り口はパソコン幅の行き先の最後と、スマホ幅の右上（歯車の左の人の絵）。デモ版（Render）には出さない（IS_DEMO）。
新しい表は作らない（D1 の書き込みは表示名を保存したときの 1 行だけ）。
