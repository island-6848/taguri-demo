---
id: dec-index-only-run
type: decision
status: adopted
date: 2026-10-16
title: 推薦の索引の初回を早く入れるため、取得のワークフローに「索引だけ」の手動実行（mode index）を足す
sources:
  - cloudflare/scripts/deliver_catalogue.py
  - cloudflare/scripts/free_tier.py
  - cloudflare/test/test_deliver_catalogue.py
  - cloudflare/test/test_free_tier.py
  - tools/taguri/deploy/github-actions/catalog.yml
  - https://github.com/island-6848/taguri-crawler/blob/main/.github/workflows/catalog.yml
links:
  - depends_on: q-index-load-now
  - depends_on: dec-index-first-load
---
起案者「Aで」（2026-10-16、q-index-load-now の案 A）。
- deliver_catalogue.py `--index-only`: 公演一覧・都道府県・rec_meta の一覧の行・題名（stage_label）・カード（rec_card）は書かない。題名とカードの取り置き（15,000）も要らないので、その日の残り（`min(6 万, free_tier の d1_left)`）をまるごと索引の行数（÷3）にする。catalogue.sql は空になり、wrangler に送らない。一覧の行のハッシュは変えない（毎日の実行が送る）
- free_tier.py plan `--mode index`: 取り直し・過去の公演は読まない（past 0 分）。Actions の分数の点検は毎日の実行と同じで、上限に届く見込みなら動かさない。分数が読めないときも動かさない（毎日の実行は読めなくても動くが、急がない索引の実行は止める側にした）
- catalog.yml: workflow_dispatch の mode に index を足し、index のときは Rebuild・ポスター・過去の公演の取得と投入・名前の索引（・計測・バックアップ）を飛ばす。Free-tier check と state への書き戻しは毎回する（索引のハッシュと D1 の控えを次回に渡すため）
- 2 本同時には走らない（concurrency group catalog）。書く前に控えへ足すので、同じ UTC の日に毎日の実行と重なっても合計は上限を越えない
- 見込み: Actions は 1 回 5〜10 分（準備と書き戻しが大半）。D1 はその日の残りの分だけ
