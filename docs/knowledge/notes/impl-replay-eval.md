---
id: impl-replay-eval
type: decision
status: adopted
date: 2026-10-18
title: 推薦の再生（replay）を作った。日 t までの記録だけに切った写しで Worker と同じ rankedGroups を node で動かし、t より後 1 週間の答えを利用者ごとの AUC で当てる。部品 4 つを外した計算とも比べる（H5）。利用者 1 人から判定を出す
sources:
  - tools/review/replay_eval.py
  - cloudflare/scripts/replay_rank.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/test/test_replay_eval.py
  - cloudflare/scripts/replay_job.py
  - cloudflare/test/test_replay_job.py
  - tools/taguri/deploy/github-actions/replay.yml
  - docs/research/real-data-eval-plan.md
links:
  - depends_on: plan-real-data-eval
  - depends_on: impl-eval-logging
---
起案者「再生の仕組み、作って。利用者は1人からでも」（2026-10-18）。plan-real-data-eval の §3 と H5。

- **使い方。** `python3 tools/review/replay_eval.py backup.sql replay --index index.sql [--extra past.sql] [--owner U]`
  - backup.sql は復号した毎日の控え。
  - index.sql は `build_recommend_index.py --output` で、手元の作業データから作る。
  - 本番の D1 は読まないので、無料枠を使わない。
- **写しの作り方。**
  - 全部の migrations の形の SQLite に、控えの記録（共通の列だけ）・索引・任意の SQL を入れる。
  - 区切りの日 t ごとに写しを作り、利用者の表から日 t（日本時間）より後に書かれた行を消す。消す行は updated_at・created_at・first_at で決める。
- **計算。** `replay_rank.js` が `rankedGroups` を、today = t + 1 日で利用者 × 計算ごとに呼ぶ。
  - 答えた公演・お気に入りの名前の公演を外す、ツアーを 1 枠にまとめる、並べ直す、までを本番と同じに通る。
  - 点ではなく、表示の 1 枠ごとの順位で比べる。並べ直し（spread）は点を変えず、順位だけを変えるため。
  - 400 枠に入らない公演は圏外。圏外どうしは同点として数える。
- **指標。**
  - AUC は、同じ区切りの中の（正例, 負例）の組だけで数え、利用者ごとに区切りをまたいで足す。
  - 画面は reminder（主）・other（参考）・all に分ける。
  - H1 は符号検定。H5 は利用者ごとの差の Wilcoxon（正確な分布）を、4 つの部品で Holm の補正にかける。
- **部品外し（ctx.ablate）。** `scoreFromIndex` の split・expand に、画面側の spread（spreadLeads を通さない）と gate（裏の答え合わせを base に固定）を足した（REPLAY_ABLATIONS）。
  - 本番は ctx.ablate を渡さないので、動きは変わらない。
  - ablate のある計算は rec_cache を読まず、書かない。
- **決めを変えた点**（計画に日付つきで追記した）。
  - 判定を出す人数は 1 人から（--min-users の既定 1）。
  - 区切りは 1 週間（記録が数週間分しか無いため）。
- **限界。**
  - 索引は日 t のものではなく、今日作ったもの。控えに索引は無く、作業データの state 枝も履歴を持たない。そのため、日 t より後に載った公演や、あとから足された出演者も候補に入る。
  - favourites には時刻が無く、日 t より後のお気に入りも入る。
- **パソコン無しで動かす（2026-10-18 追記）。** 起案者「パソコン環境じゃなくても動かせるようにして」。
  - 非公開の taguri-crawler の Actions に、手で動かす **Replay**（replay.yml）を置いた。スマートフォンから Run workflow で動かし、結果はその実行の Summary に出る（集計だけ）。
  - 利用者の記録は、控えを復号する代わりに D1 から書き出す（backup_d1 と同じ表）。読む行が REPLAY_MAX_ROWS（30 万行）を越えるなら、読まずに止まる。
  - 索引は作業データから作る。past_stage は data/past/stages.jsonl から手元で作り、D1 からは読まない。
  - 最初の段は `free_tier.py plan --mode replay`。毎日の取得の分を取っておいて、20 分が残るときだけ動かす。
  - 調べて分かったこと：本番の catalog.yml には「Back up the user records」の段が無い。雛形にはある。そのため、毎日の控えはまだ一度も作られていない。
