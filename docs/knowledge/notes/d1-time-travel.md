---
id: d1-time-travel
type: finding
status: confirmed
date: 2026-10-13
title: D1 は無料プランで 7 日前、有料プランで 30 日前まで戻せる（Time Travel）
sources:
  - https://developers.cloudflare.com/d1/reference/time-travel/
links:
  - affects: q-offsite-backup
  - affects: workers-d1-preview-state
verifies:
  - S07
  - S10
---
それより長く残すには R2 などへ書き出す。削除の説明（Workers 版の画面は「最大 30 日残る」と書いている）は、無料プランなら 7 日になる点に注意。（公式ページの記述を検索結果の引用で確かめた。作業環境の通信制限でページを直接は開けていない）
