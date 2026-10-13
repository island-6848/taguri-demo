---
id: public-export-leak
type: finding
status: confirmed
date: 2026-10-13
title: 公開版の書き出しが他の利用者の記録まで渡していた（修正済み）
sources:
  - tools/taguri/test_demo_stability.py
  - docs/service-launch-verification.md
links:
  - affects: comp-export
verifies:
  - S03
---
`/export.json` が全員分の表を返し、`/data.zip` が保存領域を丸ごと渡していた。人工の利用者 2 人で再現し、本人の行だけに直した。再発を防ぐ検査がある。
