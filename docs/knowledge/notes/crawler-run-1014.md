---
id: crawler-run-1014
type: finding
status: confirmed
date: 2026-10-14
title: 無料枠の守りを入れた最初の Catalog（手動・daily）── D1・R2 は入り、過去の公演 7,016 件は読んだが D1 への取り込みが SQLITE_TOOBIG で落ちた（直した）
sources:
  - https://github.com/island-6848/taguri-crawler/actions/runs/38486187595
links:
  - verifies: dec-free-tier-only
  - affects: crawler-actions-minutes
  - affects: dec-posters-r2
  - affects: q-r2-poster-growth
---
taguri-crawler の run 38486187595（2026-10-13 23:45〜10-14 02:29 UTC、2 時間 44 分）のログを読んだ。
- **Plan within the free tier:** 通った。過去の公演に 135 分・7,043 枚を割り当てた（31 日の枠がまだ空いているため）
- **公演一覧 → D1:** 成功（2 分の取り直し＋20 秒）。毎日の公演一覧が初めて D1 に入った
- **ポスター → R2:** 2,000 枚を 28 分で入れた。保存 882,897,831 バイト（1 枚 平均 約 440 KB）・Class A 2,000 回。作業データは 11,045 → 9,050 ファイルに減った（書き戻しは 3 分）
- **過去の公演:** 7,043 枚を読み 7,016 件を残した（cursor 366463、まだ終わりではない。読み取り 129 分）
- **過去の公演 → D1:** 失敗。`statement too long: SQLITE_TOOBIG`。build_recommend_index._inserts が 1 文の大きさを**文字数**で数えていたため、日本語（UTF-8 で 1 字 3 バイト）の多い行で上限（9 万）の約 3 倍になっていた。**バイトで数えるように直した**（試験 test_deliver_past の StatementSizeTest）。取り込みの控えは保存されていないので、次の実行でこの 7,016 件をまとめて入れ直す（D1 の書き込みは 14,032 行。この日の控えには、失敗した分も数えてある ── 少なく数えることはない）
- **Free-tier check の表:** Actions 直近 31 日 374 分／上限 1,500、D1 の今日の取得の書き込み 18,032／80,000、R2 保存 0.88 GB／8 GB、Class A 2,000／30 万、Class B 0／300 万。どれも 8 割の手前
- ポスターの R2 の伸び: 1 枚 約 440 KB なので、8 GB の上限まで約 1.8 万枚。手元に残る分（約 2,400 枚）を入れても 2 GB ほど。新しいポスターが 1 日 50 枚なら 1 年弱で上限に届く見込み（q-r2-poster-growth。小さくしてから入れる・古いものを消す、を考える）

2026-10-15 追記（Catalog #5、run 38646724578、2026-10-14 22:18 → 2026-10-15 01:13 UTC、2 時間 55 分、成功）: https://github.com/island-6848/taguri-crawler/actions/runs/38646724578
- **公演一覧 → D1:** 1,338 件、変わった行 0（書き込み 3）。**索引・題名・カードは今回も "not built"**（FileNotFoundError '../d1-out/index.sql' ほか）。この回は直す前（8e61ad5）のコードで始まったため。次の回から入る見込み（index-never-delivered）
- **ポスター → R2:** 新しく 2,000 枚、縮め直し 500 枚、既にあった 2,000 枚（45 分）。保存 695,503,746 バイト（前回 882,897,831 から減った）。Class A 今月 4,500
- **過去の公演:** 6,834 枚を読み 6,831 件を残した（読み取り 2 時間 6 分、cursor 305477、まだ終わりではない。控えの合計 13,847 件）
- **過去の公演 → D1:** 成功。SQLITE_TOOBIG は直った。changes 10,001・rows_written 30,000・size_after 13,488,128 バイト
- **Free-tier check:** Actions 直近 31 日 553 分／1,500、D1 の今日の取得の書き込み 20,000／80,000、R2 保存 0.70 GB／8 GB、Class A 4,500／30 万、Class B 500／300 万。どれも 8 割の手前
- **見つけたこと:** D1 が数えた書き込み（30,000）が、控えの数（20,000）より多い。見積もりが主キーの索引の書き込みを数えていなかった（d1-writes-undercounted）
