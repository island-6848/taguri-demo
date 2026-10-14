---
id: crawler-actions-minutes
type: finding
status: confirmed
date: 2026-10-13
title: 取得の Actions は毎日の更新が 1 回 約 9 分。過去の公演を 1 日 6,000 枚読むと月 3,600 分を越え、無料の 2,000 分に収まらない
sources:
  - https://github.com/island-6848/taguri-crawler/actions/runs/38483279440
  - https://github.com/island-6848/taguri-crawler/actions/runs/38404782069
links:
  - supports: dec-free-tier-only
  - affects: dec-auto-link-past
  - affects: gha-private-free-minutes
---
taguri-crawler の実行の記録（GitHub の API で読んだ、非公開）。
- 2026-10-13 23:16 UTC の毎日の Catalog（38483279440）: ジョブ 8 分 11 秒（取り直し 2 分、作業データの書き戻し 5 分半 ── 2 GB のため）。課金の数え方（ジョブごとに分へ切り上げ）で 9 分
- 初回の 6,000 枚（38404782069）: 196 分
- 今月（10 月）これまでの合計: 約 215 分（Diagnose 5 回の約 5 分を含む）
- 過去の公演のページは 1.1 秒に 1 枚なので、6,000 枚で約 110〜120 分。別のワークフローだと準備と書き戻しで毎回 +10 分。毎日なら月 3,600〜4,000 分になり、Catalog（月 300〜800 分の見込み）と合わせて無料の 2,000 分を大きく越える
これで、起案者の「1 日 6,000 件」（dec-auto-link-past）は無料枠と両立しないと分かった（dec-free-tier-only で、無料枠に収まる分だけ読むことにした）。
