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

2026-10-15 の追加の指示「購入済み押してもお気に入りから消さないで」: 購入済みにした公演もお気に入りの一覧に残す。ボタンの代わりに「購入済み ── 購入済み公演で行く日を入れる」の印を出す（cards.ownedMark）。buckets は favOwned に分けて持ち、お気に入りの画面だけが favourites と合わせて出す。カレンダー・開幕リマインドは購入済みとして 1 回だけ出す（favourites には入れない）。

2026-10-15 の追加の指示「お気に入りのページのレイアウト変更して。購入済み公演と似た感じ」: お気に入りのカードも app.js の compactTickets（おすすめ・興味あり・購入済み公演と同じ詰めた形）に通す。ポスターと公式サイトは左、題名・会期・劇場は右、その下に出演・くわしく・理由・購入済みのボタンが並ぶ。

2026-10-15 の追加の指示「お気に入りページの「なぜお知らせしているか」の欄消して、「なぜお知らせしているか」の中のお気に入りって丸で囲んであるところの色で、理由の人名とか団体とかだけハッシュタグで羅列して」: お気に入りのカードは、理由の見出しと一覧の代わりに、当たった名前を「#名前」の札で並べる（cards.compose の tags、.favtags/.ftag。色は「お気に入り」の札と同じ --s2）。
