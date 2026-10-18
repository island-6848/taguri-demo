---
id: workerd-entry-exports
type: finding
status: confirmed
date: 2026-10-18
title: workerd は Worker の入り口のモジュール（src/worker.js）の名前付き export をすべて入り口として読む。数や文字を export すると起動しない
sources:
  - cloudflare/test/runtime-smoke.js
  - cloudflare/test/worker-exports.test.js
links:
  - affects: workers-builds-applies-migrations
---
2026-10-18、#128 の修正で `export const FIREBASE_DELETE_DAYS = 30` を src/worker.js に足したところ、CI の runtime-smoke（workerd）が
「Incorrect type for map entry 'FIREBASE_DELETE_DAYS': ... not of type 'function or ExportedHandler'」で起動しなくなった（相手のセッションが見つけた）。
node の試験（node --test）では import できるので気付けない。export を外して直し（cfab3ee）、手元の runtime-smoke.js が通ることを確かめた。
再発防止: test/worker-exports.test.js が、worker.js の default 以外の export が関数でなければ失敗する。数・文字は別のファイルに置く。
その版で本番の配信（Workers Builds）が失敗したかは、ここからは確かめられない（失敗なら前の版が動き続ける）。
