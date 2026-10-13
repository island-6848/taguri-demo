---
id: reco-v2-index-compatible
type: finding
status: confirmed
date: 2026-10-13
title: 推薦の計算 person-graded-v2 は、D1 の索引の作り（表と行）を変えない
sources:
  - https://github.com/island-6848/taguri-demo/blob/claude/demo-records-setup-yqo65u/cloudflare/scripts/build_recommend_index.py
links:
  - affects: dec-d1-catalogue-delivery
---
推薦側のセッション（session_011h35PdoJgoX8yQQagUsiJf）から共有（2026-10-13）: 起案者の指示で推薦の計算を person-graded-v2 に変えた（ブランチ claude/demo-records-setup-yqo65u、master には未マージ）。
master との差分を見ると、cloudflare/scripts/build_recommend_index.py で変わるのは要求ごとの計算（score_from_index）だけで、build_index・to_sql・表（rec_stage・rec_credit・rec_people・rec_gram）は変わらない。したがって deliver_catalogue.py が入れる索引は v2 のマージ後もそのまま使える。Worker 側の計算（recommend.js）と rec_cache の鍵は v2 で変わる。
画面の移植で Python の推薦画面を正解にしている場合、マージ後は v2 の出力が正解になる。
2026-10-13 追記（推薦側のセッションから）: v2 のブランチを段 1 の master（c473394）の上に載せ直し、衝突なく JS 54 件・cloudflare の Python・test_user_recommendation が通った。v2 には評価の段階を利用者が選べる対応（「値/段階数」、◎○△× は 4 段階）も入っている。master に入れるかは起案者の判断待ち。段 2（おすすめ）の移行はこれを正解にして進めるので、入るまで待つ。
2026-10-13 追記（推薦側のセッションから・PR #13 c8a6e28）: 推薦は person-ordinal-v3 になった。build_index が rec_credit・rec_people に公演の種類の行（role が「#形式」「#原作」「#翻訳」「#会場」、role_group="theme"）を足す。表の形は同じで、公演あたり数行増える（deliver_catalogue.py の書き込みの見積もりは stats の rows_written から取るので、そのまま効く）。日記帳の出演者は rec_people を読むので、「#」で始まる役職を除くようにした（load_rated の parse_credits はそれを返さない）。段 2 の正解は v3 の出力になる。
2026-10-13 追記（推薦側・PR #13）: (1) GET /migration-api/onboarding を新設（登録して最初の評価で見せる過去作の候補、最大 20 件。最初の 1 回だけ見せる・「観ていない」で飛ばすのは画面側の仕事）。索引作成のときに rec_meta 'onboarding' を書く（build_recommend_index.py --today）。deliver_catalogue.py は今は --today を渡していないので、PR #13 が master に入ったら渡す必要があるか確かめる。(2) /api/recommend の応答に variant（画面には出さない）と n_seeds が増え、お気に入りだけでも推薦が出る（reasons の n は 0 になりうる）。(3) rec_cache の印が person-ordinal-v3+fav1 に。段 2 の移植で使う。
