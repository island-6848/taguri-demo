---
id: index-never-delivered
type: finding
status: confirmed
date: 2026-10-15
title: 本番の D1 には推薦の索引が一度も入っていなかった。取得の Catalog が deliver_catalogue.py に相対パス（../d1-out）を渡し、索引・題名・カードを作る段が別の場所（cwd=ROOT）から開いて FileNotFoundError で落ちていた
sources:
  - https://github.com/island-6848/taguri-crawler/actions/runs/38486187595/job/115600305243
  - cloudflare/scripts/deliver_catalogue.py
  - cloudflare/test/test_deliver_catalogue.py
links:
  - answers: q-interest-no-reco-prod
  - affects: impl-interest-seed
---
起案者に /api/screen/recommend の diag を見てもらうと null だった（2026-10-15）。diag が null になるのは rankedGroups が rec_meta の 'current'（索引の版）を見つけられないときだけ（コードで確認）。取得の Catalog #4（2026-10-13 23:45 UTC）のログ: 「Deliver the catalogue to D1」の段で build_recommend_index.py と build_stage_labels.py が `FileNotFoundError: '../d1-out/index.sql'`・`'../d1-out/labels.sql'`、報告は "index": "not built (see the log above)"。段そのものは exit 0 なので成功に見えていた。公演一覧（catalogue、1,344 件）は入っていた。
- 原因: ワークフローは cloudflare/ から `--out ../d1-out` を渡すが、deliver_catalogue.py は索引・題名・カードを作る子の処理を cwd=ROOT（リポジトリの根）で走らせ、相対パスがリポジトリの外を指していた
- 直し: main で --data・--out を絶対パスにする。相対パスで渡したときに絶対パスで build に渡ることを試験にした（直す前の版では失敗することを確かめた）
- 影響: 本番は推薦（今週のおすすめ）が誰にも出ない。stage_label（元の画面の公演名）とおすすめのカード（rec_card）も入っていない見込み。開幕リマインド・公演カレンダーなどは一覧（catalogue）の補い（fallback）で動いていた
- 次: 取得のワークフローは公開リポジトリの master のコードを取り出すので、次の定期の Catalog（毎日 19:17 UTC＝日本時間 4:17）で索引が入る見込み。state の index が空なので「unchanged」で飛ばされはしない。D1 の書き込みの残りが足りないと "skipped" になるので、Free-tier check の表と報告の "index" を見る
- 分からないこと: 索引の書き込み行数が 1 日の残りに収まるか（初回は全行）
