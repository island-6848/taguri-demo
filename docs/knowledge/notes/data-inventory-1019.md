---
id: data-inventory-1019
type: finding
status: confirmed
date: 2026-10-19
title: 保存先は D1（taguri-demo、38 表）・R2（taguri-posters・taguri-backup）・Firebase Authentication。D1 の利用者ごとの表は 21、全員共有の公演データは 14、運営・数え上げは 3
sources:
  - https://github.com/island-6848/taguri-demo/tree/master/cloudflare/migrations
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/wrangler.jsonc
  - https://github.com/island-6848/taguri-demo/blob/master/docs/free-tier-budget.md
links:
  - affects: d1-user-isolation-1019
---
master の migrations 0001〜0038 を手元の SQLite に順に当てて、最終形の表と列を出した（2026-10-19）。意味は各 migration のコメントと src の読み書きから。

- 利用者ごと（user_id 付き）: users・sessions・passkeys・webauthn_challenges・works・records・favourites・reactions・reaction・ticket・missed・visit_note・hand_credits・merges・excluded・rank_weight・app_setting・search_request・rec_cache・rec_shown・viewed
- 全員共有の公演データ（取得の実行が入れる）: catalogue・rec_meta・rec_stage・rec_credit・rec_people・rec_gram・rec_card・stage_label・past_stage・poster・venue_pref・venue_census・stage_override・admin_log
- 運営: fix_request（利用者の user_id を持つ）・usage（無料枠の数え）
- records・favourites・reactions は最初のデモの表。いまの画面は主に works・reaction を使う（favourites は推薦でまだ読む）。viewed は src から読み書きが見つからなかった
- app_setting の key: display_name・avatar・rating_scale・declared・declared_roles・declined・kind_off・pref_filter・analysis_optout

分からなかったこと: 本番の D1 の行数（本番に問い合わせていない）。
