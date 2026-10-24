---
id: f-past-synopsis-progress-1024
type: finding
status: confirmed
date: 2026-10-24
title: 過去の公演のあらすじは 10-24 時点で 30,633 件中 3,316 件を読み、あらすじが取れたのは 1,698 件。10-20 から読み取りがほぼ止まっている（定期実行の環境のセットアップスクリプトが構文エラーで、毎回 3 秒で失敗）
sources:
  - https://github.com/island-6848/taguri-crawler/tree/state
  - tools/review/fetch_past_stages.py
links:
  - depends_on: impl-theme-g5-reread
  - depends_on: peer-synopsis-routine
  - affects: q-synopsis-routine-quota
---
起案者の問い（2026-10-24）「過去の舞台のあらすじ取得と抽出どこまで進んだ？」。taguri-crawler の state ブランチ（2026-10-24 03:19 UTC の作業データ）を数えた。

- 一覧（1 周目）: past/stages.jsonl は 30,633 公演。progress.json は read 30,770・done false（cursor 113,348／top 512,453 で、古い番号を読み続けている）。年ごと: 2021 年 2,508・2022〜2025 年 約 6,400〜6,800・2026 年 1,755
- 本文を読み取り待ちに積む（2 周目）: story_line 4,385 行（一覧の約 14%）。待ちに過去の公演 1,082 件・これからの公演 69 件が残っている
- 読み取り（題材・あらすじ）: 過去の公演で題材の表に行があるのは 3,316 件（Claude が読んだ 3,034・本文が短いので規則で空にした 282）。あらすじが取れたのは 1,698 件、言葉があるのは 2,529 件
  - 年ごとに読んだ割合: 2026 年 1,755／1,755（全部）、2025 年 1,514／6,804（22%）、2024 年以前はほぼ 0（各年 13 件以下）
- 読んだ日: 10-18 2,153 件・10-19 1,088 件・10-20 66 件・10-22 9 件。**10-20 から止まっている**
- 原因: 定期実行「あらすじの読み取り（1 日 4 回・各 60 件）」（trig_01Y7a7jwMQpEgcCiTdkwwVaK）は動いているが、毎回 3 秒で失敗している。最後の実行（2026-10-24 10:08 UTC）の記録は「Setup script failed with exit code 2. … line 3: syntax error near unexpected token `npx'」。環境のセットアップスクリプトの 3 行目が壊れている。もう一つの「あらすじの読み取り（毎日）」（800 件、trig_014eMAXkksBvXuKB31mAuKht）は 10-18 から止めてある（enabled false）
- 直すのは起案者: 環境の設定（セッションの題の横の環境のメニュー → Edit → Setup script）。いつから壊れたかは確かめていない（10-20 以降の実行の記録は見ていない）
- 速さの目安: 1 日 4 回×60 件＝240 件。待ちの 1,151 件は約 5 日。一覧の残り（約 26,000 行）を全部読むには、待ちに積む速さ（取得の 1 日の枠）と読む速さの両方が今のままだと 3〜4 か月かかる見込み（見積もり）

2026-10-24 追記: セットアップスクリプトの中身は、Claude Code の許可の設定の書き方（`Bash(npx --yes wrangler@4.151.1 d1 execute taguri-demo --remote:*)` と `Bash(python3 scripts/deliver_posters.py:*)`）の 2 行だった。シェルとして読めないので失敗していた。起案者が消して空にした。手動で起動した回（15:22 UTC）は、セットアップを飛ばして Claude の起動まで進んだ。
