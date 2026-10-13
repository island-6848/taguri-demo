---
id: q-workers-cpu-overrun
type: question
status: dropped
date: 2026-10-13
title: 無料プランで CPU 10 ミリ秒を超えると、実際にはどうなるか
links:
  - depends_on: q-workers-cpu-real
  - depends_on: q-real-catalog-stats
verifies:
  - S20
---
その要求だけが失敗するのか、多少の超過は許されるのかを公式文書と実測で確かめる。推薦の計算が時々超える程度なら、無料のまま始められるかが決まる。
同じ内容の q-workers-cpu-real に統合した。
