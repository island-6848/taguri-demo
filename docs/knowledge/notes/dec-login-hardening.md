---
id: dec-login-hardening
type: decision
status: adopted
date: 2026-10-14
title: ログインの守りを固める：戻り先の検査を URL として行う・パスキー追加と Google・メールの結び付けは10分以内のログインが要る・結び付けはアカウントのページから明示したときだけ・利用者100人の上限を外す
sources:
  - cloudflare/src/worker.js
  - cloudflare/src/passkey.js
  - cloudflare/src/client/login.js
  - cloudflare/src/screens/account.js
  - cloudflare/public/login.html
  - cloudflare/migrations/0020.sql
  - cloudflare/test/gate.test.js
  - cloudflare/test/firebase-auth.test.js
  - cloudflare/test/passkey.test.js
---
起案者の指示（2026-10-14）「ログインの際にセキュリティの問題ないか調べて」→ 調べた結果の 1・2・3・5 を「修正して」。
- 戻り先（?next=）: 「/」で始まるかだけを見ていたため、「/<タブ>/evil.example」がブラウザでは「//evil.example」と読まれ、外のサイトへ飛ばせた（再現済み）。制御文字と「\」を含む値は捨て、URL として読んで同じオリジンに留まるときだけ、パス・クエリ・# を返す（Worker と login.js で同じ規則）
- パスキーの追加（登録の options と verify の両方）と Google・メールの結び付けは、この端末で10分以内（REAUTH_SEC、削除と同じ）にログインしたセッションでだけ受ける。盗まれた長期の Cookie だけでは、消えない入口を足せない
- 結び付けは、アカウントのページの「Google・メールを結び付ける」（/login?link=1）から {link:true} を送ったときだけ。メールのリンクを別のブラウザで開いた（アドレスを聞き直した）ときは結び付けない。結び付けていないアカウントでログイン中に、知らない Google でふつうにログインすると 409（共有端末で他人のアカウントに結び付けない・黙って別アカウントを作らない）。すでに別のアカウントで使われている Google は結び付けず、そのアカウントへ切り替えもしない
- 結び付けの画面では、10分を過ぎていれば復旧コードかパスキーで本人確認し直せる
- 0001.sql の利用者100人の上限（トリガー account_limit）を 0020 で外す。新規は1日あたりの上限（NEW_ACCOUNTS_PER_DAY）で抑える
- 残り（起案者の判断待ち・コンソールの設定）: メールのリンクでのログインをやめるか、Firebase の公開名を「たぐり」にする、メール／パスワードでの登録が無効か確かめる
