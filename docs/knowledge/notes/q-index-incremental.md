---
id: q-index-incremental
type: question
status: open
date: 2026-10-15
title: 推薦の索引を毎日まるごと入れ替える作りは、D1 の書き込みの無料枠（1 日 10 万行）に収まるか。公演ごとの差分だけ書く作りに変えるか
links:
  - depends_on: d1-writes-undercounted
---
いまは版（ver）ごとに rec_stage・rec_credit・rec_people・rec_gram を全部入れ、前の版を消す。書き込みは約 4 ×（行数）。行数がまだ分からない（初回の投入で index-stats の rows_written が分かる）。2 万行を越えるなら、変わった公演の行だけを書く差分の作りが要る。次の Catalog の報告の "index" を見て決める。
