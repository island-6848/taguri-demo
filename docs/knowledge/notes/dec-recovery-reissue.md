---
id: dec-recovery-reissue
type: decision
status: proposed
date: 2026-10-18
title: 復旧コードは、直近 10 分以内のログインで作り直せる。古いコードは 1 つの UPDATE で使えなくなり、ほかの端末はログアウトする（Google・メールで始めたアカウントには作らない）
sources:
  - https://github.com/island-6848/taguri-demo/issues/126
  - cloudflare/src/worker.js
  - cloudflare/public/migration-data/index.html
  - cloudflare/public/migration-data/app.js
  - cloudflare/src/screens/account.js
  - cloudflare/test/recovery-reissue.test.js
links:
  - affects: dec-account-deletion
  - depends_on: dec-rate-limit
---
分かったこと（コードで確認、2026-10-18）: 登録時の recovery_hash を本人が取り替える道が無く、すべての端末でログアウトしても復旧コードは有効なままだった（issue #126）。

実装したこと:
- `POST /api/recovery/reissue`（ログイン中・同じサイトから）。直近 10 分以内のログイン（`freshSession`、アカウントの削除やパスキーの追加と同じ）が要る。新しいコードを 1 回だけ返し、ハッシュだけを持つ
- 古いコードは `UPDATE users SET recovery_hash=新` の 1 文で無効になる。同時に古いコードで `/api/recover` しても、セッションの行は「コードがまだ同じとき」だけ入るので入れない（試験あり）
- 同じ batch で、この端末以外のセッションをすべて消す。この端末は続けて使える。Google・メールのリンク・パスキーはそのまま
- 画面: アカウントのページの「ログイン」に「復旧コードを作り直す」（復旧コードを持つアカウントだけ）。押すと `/migration-data/#recovery-reissue`（パスキーの設定と同じページ）
- D1 の保存の上限でも通す（行を書き換えるだけで増えない）。書き込みは 1 回の作り直しで数行、読みも数行で、無料枠には響かない

起案者に確かめたいこと（だから proposed）:
- ほかの端末を全部ログアウトさせるか（いまはそうした。古いコードで入られていた場合に締め出すため、控えめな方を選んだ）
- Google・メールで始めたアカウント（recovery_hash が `firebase:` で始まる）に、新しく復旧コードを作れるようにするか（いまは作らない。ログインの道を勝手に増やさない）
- 限界: コードを知った人も、そのコードでログインした直後なら作り直せる（コードはアカウントそのものの鍵なので）。本人が先に作り直せば、その人は締め出される
