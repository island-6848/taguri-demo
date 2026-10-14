---
id: sitemap-first-run
type: finding
status: confirmed
date: 2026-10-13
title: サイトマップ版の初回の Catalog（6,000 枚）は成功し、これからの公演 1,353 件・終わった公演 3,460 件を得た
sources:
  - https://github.com/island-6848/taguri-crawler/actions/runs/38404782069
links:
  - verifies: dec-corich-sitemap
  - affects: q-catalogue-api-limit
  - raises: q-crawler-state-size
---
taguri-crawler の Catalog 実行 38404782069（workflow_dispatch、weekly、2026-10-13 13:25〜16:41 UTC、成功）のログを読んだ。
- サイトマップの公演 141,633 件・最新の番号 512,453。新しいほうから 6,000 枚を読み、要求 6,006 件・失敗 0（403 なし）
- 候補 4,813 件 ── これから／上演中 1,353 件、終わった公演 3,460 件（180 日以内）。カレンダー 998 件のうち手元の候補に無い 336 件
- 「材料の取得」は 3 時間 12 分（読み取りは 1.1 秒間隔なので 6,000 枚で約 110 分。残りはポスター 4,386 枚の取得など）。上限 300 分には収まった
- ポスター: 取得 4,386・画像なし 427・失敗 0（stage-image.corich.jp）。終わった公演のポスターも取っている
- あらすじは読み取り待ちに回すので、この回で付いたものは 0（未取得 1,353 件）
- link_works（持ち主の記録の結び付け）は「失敗したので飛ばす（returncode=1）」── 実行環境に利用者の記録が無いため。想定どおりだが、毎回失敗の行が出る
- **作業データが 11,045 ファイル・2.0 GB**（catalog.tar.gz 2,018 MB）になり、state ブランチへの書き戻しに 3 分半かかった。大半はポスター画像と公演ページの HTML の控え（data/credits/pages）。GitHub は 1 回の push が 2 GB を超えると断るので、このままでは次の数回で書き戻せなくなるおそれがある（q-crawler-state-size）
- これからの公演が 1,353 件なので、Worker の /api/catalogue の 1,000 件の上限（q-catalogue-api-limit）は実際に足りない
- この実行は D1 へ入れる段を足す前のコミット（37f9131）で動いたので、D1 にはまだ入っていない。最初に入るのは今夜（19:17 UTC）の毎日の実行
