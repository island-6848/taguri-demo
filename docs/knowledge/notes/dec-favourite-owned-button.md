---
id: dec-favourite-owned-button
type: decision
status: adopted
date: 2026-10-15
title: お気に入りの一覧の公演に「購入済みにする」ボタンを置く（読むだけの一覧をやめる）
sources:
  - cloudflare/src/screens/cards.js
  - cloudflare/src/screens/lists.js
  - tools/review/render_recommend.py
  - cloudflare/scripts/build_cards.py
links:
  - depends_on: dec-owned-only-owned-list
  - affects: comp-frontend
---
起案者の指示（2026-10-15）は「お気に入りから、購入済みを登録できるようにして」。

これまでのお気に入りの一覧は「読むだけです。押すボタンはありません」としていた。
- 置くのは「購入済みにする」の 1 つだけ。興味あり・興味なしは置かない。お気に入りは名前で拾った公演の通知であり、順位で切った枠ではないため。
- 押した結果は、おすすめの「すでに持っている」と同じ（reaction.owned = 1、`/api/react`）。ツアーのほかの会場にも同じ答えを写す。公演はお気に入りの一覧から外れ、購入済み公演に移る。行く日は購入済み公演の側で入れる。
- 押したあとの文言は「購入済み公演に移しました」（app.js）。
- Python のデモ版（render_recommend.owned_button）にも同じボタンを置き、カードの一致テスト（test_build_cards・cards.test.js）を保つ。
