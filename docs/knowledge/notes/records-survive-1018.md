---
id: records-survive-1018
type: finding
status: confirmed
date: 2026-10-18
title: migration（0001〜0034 のどこからでも）・毎日の配送・再配備・定期実行の片付けは、本人の記録を消さず変えない（ローカルの試験で確認。本番・隔離環境の D1 は未実施）
sources:
  - https://github.com/island-6848/taguri-demo/issues/137
  - cloudflare/test/migrations-keep-records.test.js
  - cloudflare/test/test_delivery_keeps_records.py
  - cloudflare/test/redeploy-keeps-records.test.js
  - cloudflare/test/cleanup.test.js
  - docs/verification/records-survive-2026-10-18.md
links:
  - affects: comp-d1
  - supports: dec-sweep-recheck
  - raises: q-d1-migration-failure
---
リポジトリのコードと試験の実行結果で確かめた（2026-10-18、master `2cc2125` ＋このブランチ。Node 22.22.0 の node:sqlite、Python 3.13 の sqlite3）。

分かったこと:
- migration: 0001〜N を当てて利用者の表（users と user_id の列がある表すべて）に 2 人分の行を入れ、残りを当てても、前からある値・行の数は変わらない（N = 1〜33 の全部）。意図した書き換えは 0025（reaction.source の付け直し）と 0034（works.rated_at を評価のある行だけ updated_at から始める）だけ。新しい列は宣言した既定値。外部キーも壊れない。新しい migration は自動で対象になり、値を書き換える migration は試験に期待する値を書かないと落ちる。既定値の無い NOT NULL 列を足す migration・利用者の行を書き換える migration を仮に足すと落ちることも確かめた
- 配送: deliver_catalogue（一覧）・build_recommend_index（全部と差分）・build_cards・build_stage_labels・deliver_past・deliver_posters の作る SQL が書く表は、公演の表と rec_meta だけ。利用者の表は 1 行も変わらない。scripts/ のソースにも利用者の表へ書く文は無い。catalog.yml が --command で流す SQL は SELECT だけ
- 再配備: src/ に CREATE・ALTER・DROP は無い。推薦の作り置き（rec_cache）は印の先頭の VERSION が違えば読まれず、作り直される。記録の表は変わらない
- 片付け（cleanup.js）: 記録の表に 1 行でもあれば消さない。設定・パスキー・作り置きだけのアカウントは消す（privacy.html の 6 のとおり）。ログインの期限（30 日）は片付けの 1 か月を越えない。選んでから消すまでに記録を足した人を消すおそれがあったので直した（dec-sweep-recheck）

分からなかったこと・未実施: 本番・隔離環境の D1 で流すこと、途中で失敗した migration・配送の再実行、コードの巻き戻し、別のブラウザーでの再ログイン。venue_pref・venue_census を書く配送は文面の検査だけ。tools/admin が本番に書く文は対象外。
