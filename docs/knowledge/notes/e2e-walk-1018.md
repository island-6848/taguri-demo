---
id: e2e-walk-1018
type: finding
status: confirmed
date: 2026-10-18
title: サービス版の主要操作をローカルの Worker と実ブラウザーで通した（41 段、不具合 5 件を直した）
sources:
  - https://github.com/island-6848/taguri-demo/issues/134
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/test/e2e-walk.js
  - https://github.com/island-6848/taguri-demo/blob/master/docs/verification/e2e-walk-2026-10-18.md
links:
  - raises: q-ticket-to-rating
  - raises: q-migration-data-page
  - affects: comp-passkeys
  - affects: dec-account-page
---
issue #134 の 1 回目。`cloudflare/test/e2e-walk.js` が、まっさらなローカル D1（wrangler dev、`--persist-to` の一時フォルダ）に試験用の公演一覧を入れ、Chromium（パスキーは仮想認証器）で登録 → 規約の再同意 → 記録（手入力・探すの過去の公演・候補）→ 星・感想（保存の失敗と送り直し）→ おすすめの興味あり／なし → お気に入り → 開幕リマインド → 購入済み・行く日の追加と削除 → 場所・効かせ方 → iCal・.eml の取り込み → 書き出し → ログアウト・再ログイン（パスキー・復旧コード）→ 利用者 B との分離 → 削除まで通す。各段で画面と D1 の行の両方を見る。

分かったこと（リポジトリのコードと実行結果。ローカルだけで、本番では確かめていない）:
- 直した不具合: 題名の候補が出ない（欄に結ぶのが画面を差し込む前）、ふつうのログインに復旧コードの欄が無い、お気に入りの枠が足すたびに畳まれる、アカウントの画面の /login・/migration-data/ などへのリンクが「見つかりません」、/api/import_status が 404。
- 分離・削除: B から A のものは見えず、名指しの書き込みは 400。削除後は A の行がどの表にも残らず、前のセッション・復旧コード・パスキーは使えない。

分からなかったこと・通していないもの: Google・メールのリンク（Firebase）、Google カレンダー、R2 のポスター、日付を進めたときの動き（env.CLOCK は wrangler の vars から渡せない）、スマホの幅、おすすめの順位の中身。
