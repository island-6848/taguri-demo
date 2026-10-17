---
id: impl-terms-consent
type: decision
status: adopted
date: 2026-10-17
title: 利用規約（/terms）とプライバシーの説明（/privacy）をサービスの画面として置き、新規登録はログイン画面の「利用規約とプライバシーの説明に同意して始める」にチェックを入れたときだけ通す。同意した版と日時を users に残す
sources:
  - cloudflare/public/terms.html
  - cloudflare/public/privacy.html
  - cloudflare/public/login.html
  - cloudflare/src/terms.js
  - cloudflare/src/worker.js
  - cloudflare/src/passkey.js
  - cloudflare/src/client/login.js
  - cloudflare/migrations/0030.sql
  - cloudflare/test/worker.test.js
links:
  - depends_on: impl-eval-logging
  - depends_on: plan-real-data-eval
---
起案者「ほかの似たようなサービスの実際の文面も参照して。規約は新規登録の際に、規約に同意して始める、にチェックボックスいれてもらってから登録できるようにする」（2026-10-17）。

- **同意の取り方。**
  - ログイン画面に「利用規約とプライバシーの説明に同意して始める」のチェックを置いた。ログインと登録は同じボタンなので、チェックが要るのは新しくアカウントができるときだけ。
  - サーバ（`requireAgreement`）が、Google・メール・パスキー・復旧コードの 4 つの登録の入り口すべてで、版（`TERMS_VERSION`）が合っているかを確かめる。
  - パスキーは、端末に作らせる前（options）にも確かめる。作ったあとで断らないため。
  - 版が古い画面から来たときは 409 で、読み込み直してもらう。
  - 民法 548 条の 2（定型約款の組入れ）の「契約の内容とする旨の合意」を、このチェックで取る。
- **同意の記録。** users.terms_version・terms_at（migrations/0030）。これより前のアカウントは NULL。
- **既存の利用者。** 同意を求め直してはいない（指示は新規登録のとき）。
- **参照した他社の文面。** 他社のページは、この環境から直接は開けなかった（ネットワークの許可が無い）。そのため、検索結果の抜粋で確かめた。
  - Spotify：「新機能、技術、改善を評価および開発するため。これには、アルゴリズムや機械学習モデルの開発およびトレーニングが含まれます」。
  - ドワンゴ（EEA 向け）：「個人情報を集計して個人を識別することができない統計的な資料を作成し、…サービス品質の向上」。
  - ブクログ：「単体では特定の個人を識別できないように加工した上で、…サービス開発の参考資料」。
  - 個人情報保護委員会：「サービスの向上」のような書き方では、目的を特定したことにならない（Q&A 2-1、経産分野ガイドライン）。統計データへの加工そのものは、利用目的にしなくてよい（Q&A 2-5）。
  - 取り入れたこと：目的を具体的に書いた（推薦の計算の改善・当たりの確かめ）。使う情報と使わない情報、出し方、外れ方を書いた。外部のサービス（Cloudflare・Firebase・Google カレンダー）と、ブラウザの中で読むものを書いた。
- **まだ決まっていないこと。** 問い合わせ用のメールアドレス（いまは X の @return1_end）。
