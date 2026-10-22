---
id: dec-reason-off-settings
type: decision
status: adopted
date: 2026-10-21
title: おすすめ理由の ✕ で外したものを、設定の画面「外したおすすめ理由」に並べ、1 つずつ「戻す」で復活できるようにする
sources:
  - cloudflare/src/screens/lists.js
  - cloudflare/src/screens/settings.js
  - cloudflare/test/kind-off.test.js
  - cloudflare/test/e2e-walk.js
links:
  - depends_on: impl-kind-reason-off
---
起案者の指示（2026-10-21）「間違って✕で消しちゃったオススメ理由を復活させたい。設定ページに追加」。

**前の形（コードで確かめた）**
- 理由の ✕ は、行の種類によって入る先が違う（app.js の `rsx`）。
  - 人物の行: 「使わない言葉」（`/api/decline`、app_setting `declined`）。その名前が出る公演は、おすすめから丸ごと消える。
  - 形式・原作などの行: 「使わない理由」（`/api/kind_off`、app_setting `kind_off`）。公演は消さない。
  - お気に入りの行: お気に入りから外す。お気に入りの画面で足し直せるので、この一覧には出さない。
- 戻す道は、おすすめの画面の「効かせ方」の欄の中（`declinedBox`・`kindOffBox`、✕ で戻す）にしかなく、見つけにくかった。

**決めたこと**
- 設定の画面に、カード「外したおすすめ理由」（`#reason-off`、lists.js `reasonOffCardHtml`）を足した。人物・言葉と、形式・原作などに分けて並べ、それぞれに「戻す」を付ける。
- 「戻す」は既存の remove（`/api/decline`・`/api/kind_off`）を、app.js の既存の押し口（`.tag` の `data-dec="remove"`・`data-kindoff-remove`）から呼ぶ。新しい API は作っていない。
- おすすめの画面の欄はそのまま残す。

**無料枠**
- 設定の画面を開くたびに、D1 から app_setting を 2 行読む。書き込みは「戻す」1 回で 1 行。

**確かめたこと**
- cloudflare の試験 544 件（kind-off.test.js に、設定に出る → 戻すと消える、を足した）。
- e2e-walk に「おすすめ理由の ✕ → 設定で戻す」の段を足した。
