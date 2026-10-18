---
id: dec-signup-cap-atomic
type: decision
status: adopted
date: 2026-10-18
title: 新規登録の上限（総数・1 日・接続元）は、利用者の行を足す書き込みの中で確かめる。下見は読むだけで、枠は登録が通ったときだけ数える
sources:
  - https://github.com/island-6848/taguri-demo/issues/124
  - https://github.com/island-6848/taguri-demo/issues/125
  - cloudflare/src/rate-limit.js
  - cloudflare/src/worker.js
  - cloudflare/src/passkey.js
  - cloudflare/test/rate-limit.test.js
  - cloudflare/test/passkey.test.js
links:
  - supports: dec-rate-limit
  - depends_on: dec-account-cap-counted
  - supports: dec-free-tier-only
---
分かったこと（コードと試験で確認、2026-10-18）:
- これまでは `checkNewAccount` が users と usage を SELECT して判定し、別の書き込みで接続元の数を足し、さらに別の batch で利用者の行を入れていた。同時に来た要求は同じ残り枠を読むので、接続元 3 件・1 日 30 件・総数 300 件を越えて通り得た（issue #124）。0020 で古いトリガーを外したので、DB 側で総数を止めるものも無かった
- パスキーの新規登録は、署名を確かめる前に `checkNewAccount` を呼んでいたので、断られる応答でも接続元の枠が減った（issue #125）

決めたこと（実装済み）:
- `checkNewAccount` は読むだけの下見にした（断る理由を文で返すため）。何も数えない
- 利用者の行は `guardedUserInsert`: `INSERT INTO users(...) SELECT ... WHERE 総数<上限 AND その日の数<上限 AND 接続元の数<上限`。続く文（接続元の数を足す・セッション・パスキー）は「その利用者の行があるとき」だけ効く形にして、同じ batch に入れる。D1 の batch は 1 つのトランザクションとして順に実行されるので、判定と確保が食い違わない
- batch のあと、行が入っていなければ（ほかの登録が先に枠を使った）下見をもう一度して理由を返す（無ければ 503「混み合っています」）。断られたときはセッションを作らず、端末の前のセッションも消さない
- 登録の 3 つの経路（復旧コード `/api/register`・Google/メール `firebaseSignIn`・パスキー `registerVerify`）すべて同じ形。パスキーは署名を確かめてから枠を数える
- 試験: どの要求も下見を読み終えてから書くように止めた「いちばん食い違いやすい順」で、同じ接続元から同時に 10 件 → 3 件だけ・数も 3、別々の接続元から 6 件 → 1 日の上限 2 件・総数の上限ちょうど。不正なパスキー応答を 5 回送っても接続元の数は 0 のままで、そのあと 3 件登録できる

無料枠への影響（数えた）: 書き込みは増えない（断られた要求は何も書かなくなったので減る）。読みは 1 件の登録につき、条件の中の数え直し（users 全体 300 行ほど＋その日の分）と確かめの 1 行が増える。1 日 30 件の上限まで登録があっても 1 日 1 万行ほどで、1 日 500 万行の 0.2%。

分からないこと・残り: D1 の保存の大きさ（4 GB で止める `d1RoomLeft`）は下見で読むだけで、書き込みの条件には入れていない（大きさは D1 が返す値で、SQL からは見えない。上限の手前 8 割で止めるので、同時の数件で越えることはない）。
