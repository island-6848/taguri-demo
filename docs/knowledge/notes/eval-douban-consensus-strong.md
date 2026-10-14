---
id: eval-douban-consensus-strong
type: finding
status: confirmed
date: 2026-10-13
title: 作品そのものの評判（他の人の平均）は、人物の手がかりよりずっと強い（AUC 0.79 対 0.57）
sources:
  - docs/research/person-reco-eval.md
links:
  - raises: q-public-reputation-signal
---
docs/research/person-reco-eval.md。参考として測った「他の人の平均評価（本人の分を除く）」は 0.79。たぐりは利用者の記録を集めない方針なので使えないが、取得元の公開の評価・クチコミなら、利用者の記録を集めずに使える可能性がある。
