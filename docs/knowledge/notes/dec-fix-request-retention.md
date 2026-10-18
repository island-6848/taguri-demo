---
id: dec-fix-request-retention
type: decision
status: proposed
date: 2026-10-18
title: 公演修正依頼の保存に上限と期限を付ける（1 人の未対応 10 件・1 人 50 件・全体 2,000 件。対応済みは 30 日で本文、180 日で行を消す）
sources:
  - https://github.com/island-6848/taguri-demo/issues/129
  - cloudflare/src/screens/fixrequest.js
  - cloudflare/src/free-tier.js
  - cloudflare/test/fixrequest.test.js
  - cloudflare/public/privacy.html
links:
  - depends_on: impl-fix-request
  - affects: comp-d1
---
issue #129。前は 1 人 1 日 5 件・本文 1,000 字だけで、日をまたげば行と本文が増え続けた。期限も無かった。
数字は起案者が決めていないので、無料枠に安全な側の値を選んだ。だから proposed。

## 決めた値（`free-tier.js`）
- 1 人の未対応（open）は 10 件まで（`FIX_OPEN_PER_USER`）。起案者が確かめれば、また送れる。
- 1 人が保存できる依頼は 50 件まで（`FIX_STORED_PER_USER`。対応済みも、行が消えるまでは数える）。
- 全体で 2,000 件まで（`FIX_STORED_TOTAL`）。本文は 1,000 字（UTF-8 で約 3 KB）までなので、約 6 MB。D1 の止める線（4 GB）の 0.2 % 足らず。
- 対応済み（done・dropped）は、直してから 30 日で本文を「（対応済みのため消去）」に替え、180 日で行ごと消す。未対応は消さない（上の数で抑える）。

## 守り方
- 上限は `INSERT … SELECT … WHERE (数) < 上限` の 1 文に入れた。数えてから入れるまでに別の依頼が来ても越えない（D1 は 1 文ずつ順に動かす）。
- 期限は Worker の毎日の定期実行（`purgeFixRequests`、`worker.js` の scheduled）が見る。D1 の書き込みは 1 日 2 文と、変えた行の数だけ。
- アカウントの削除は前と同じく、0030 のトリガーで送った人と本文を消す。試験を足した。
- 毎日の暗号化した控え（taguri-backup、30 日・入れ物の決まりで 35 日）と Cloudflare の自動の控え（7 日）には、消した本文もその期間は残る。privacy.html の 6 に依頼の期限を足した（控えの期間はすでに書いてある）。

migration は足していない（表とトリガーは 0030 のまま）。

## 起案者に確かめてほしいこと
- 値（10・50・2,000・30 日・180 日）でよいか。
- privacy.html の書き足しで、規約の版（TERMS_VERSION）を上げ、同意を取り直す必要があるか。今は版を上げていない（保存を短くする方向の変更のため）。
