---
id: dec-cap-allows-shrinking
type: decision
status: adopted
date: 2026-10-18
title: D1 が保存の上限（4 GB）に達しても、外す・消す・空にする操作と、ログアウト・アカウントの削除は通す。足す操作は止めたまま（#88）
sources:
  - cloudflare/src/worker.js
  - cloudflare/src/screens/lists.js
  - cloudflare/test/free-tier-d1.test.js
links:
  - depends_on: dec-account-cap-counted
  - depends_on: dec-free-tier-only
---
master b8fb7c7 の見直し（2026-10-18, issue #88）で、上限に達すると Worker の API が record/delete 以外をすべて 503 にしていた。ログアウト（/api/logout・/api/logout/all）・アカウントの削除・お気に入りを外す（remove:true）まで止まり、「見ることと消すことはできます」という案内と食い違っていた。画面の書き込み（nativeRoute）も drop_work・purge_work・unseen・agree しか通さなかった。

決めたこと（worker.js の `shrinkingAction`・`shrinkingPath`）:
- 画面の書き込み: これまでの 4 つに加えて、favourite・decline・kind_off の `action: 'remove'`、ticket の `action: 'del'`、account で表示名かアイコンを空にするとき（app_setting の行を消す）を通す
- Worker の API: /api/record/delete に加えて、/api/logout・/api/logout/all・/api/account/delete（セッションや行を消すだけ）と、/api/favourite・/api/reaction の `remove: true` を通す
- 足す操作（add・登録・取り込み・評価・名前を付ける）は今までどおり 503
- 外す操作でも行を増やさないように、favourite・decline・kind_off は、外す名前が控えに無ければ app_setting に書かない（以前は空の控えを 1 行作り得た）

D1 は越えても請求されない〔d1-free-limits〕が、上限の手前で止める仕組みは弱めていない（通すのは行を減らすか、同じ行を小さく書き直すものだけ）。test/free-tier-d1.test.js が両方の道で確かめる。
