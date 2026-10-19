---
id: dec-search-part-paging
type: decision
status: adopted
date: 2026-10-19
title: 探すの「次の 5 件」は、その一覧だけを読み直して差し替える（part=up・pp）
sources:
  - cloudflare/src/screens/search.js
  - web/app.js
  - cloudflare/test/title-leads.test.js
links:
  - affects: comp-cf-worker
---
起案者の指摘（2026-10-19）「『次の5件のとき』いちいち画面全部を再読込する必要ある？その部分だけ読み込めないの？ロード時間が長い」。

- サーバー: `/api/screen/search` に `part=up`（これから観られる公演）・`part=pp`（過去の公演）を付けると、その一覧の枠 `<section class="hitpart">` だけを作って返す。観た記録・カレンダー・人の索引・ウェブの検索・もう一方の一覧は読まない
- 画面: `.hitpart` の中の「次の n 件」「前の n 件」（`.mpage`）を押すと、その枠だけを取り直して差し替え、アドレスも進める（戻るで前のページ）。読めなかったときは、これまでどおり画面ごと読み直す。リンクそのものは画面全体のアドレスのままなので、新しいタブでも開ける
- 無料枠: 1 回の押下で読む量は前より減る（D1 の読み取りも Worker の CPU も、その一覧の分だけ）。新しい保存・定期実行はない
- 確かめたこと: Worker のテスト（part=pp で枠だけ・2 ページ目・リンクに part を残さない）。実際のブラウザーでの押下は、この時点では試していない
