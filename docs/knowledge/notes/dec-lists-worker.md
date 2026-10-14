---
id: dec-lists-worker
type: decision
status: adopted
date: 2026-10-14
title: 興味あり・お気に入り・購入済み公演を Worker に移す（同じ作り置きのカードを 4 通りに組む。名前の照合は SQL で）
sources:
  - cloudflare/src/screens/lists.js
  - cloudflare/src/screens/cards.js
  - cloudflare/scripts/build_cards.py
  - cloudflare/migrations/0018.sql
  - cloudflare/test/lists-screen.test.js
  - cloudflare/test/cards.test.js
  - cloudflare/test/test_build_cards.py
links:
  - depends_on: dec-recommend-worker-cards
  - affects: comp-native-screens
---
起案者の指示（2026-10-14）「残りの画面も順に移して」の 1 段目。
- **カード**: 作り置き（rec_card）の印を一般化し、おすすめ・興味あり・お気に入り・購入済みの 4 通りに組む。Python の build_cards.compose（参照）と Worker の cards.js が同じ組み立てをし、4 通りとも render_recommend.ticket と同じ HTML になることを試験で確かめる（test_build_cards.py・cards.test.js）
- **振り分け**（app._rebucket の公開版）: 作品（ツアー）ごとに、持っている → 購入済み、興味あり → 興味あり、興味なし → その他、登録した名前に当たる → お気に入り。お気に入りと「出さない語」に当たる公演はおすすめから外す。上演日の近い順、月の耳（month_pick）
- **名前の照合**（recommend2.declared_hits・declined_hit）: 全公演を Worker が見て回ると CPU の無料枠（10 ms）を越えるので、取得のときに正規化した団体名・クレジット・題材・あらすじをカードと一緒に入れ（migration 0018）、D1 の instr で当たった行だけを読む。登録した題材の中に、公演の題材の語が含まれる向きの照合（「家族の物語」に「家族」）はまだ
- **購入済み**: 行く日の欄（足す・確定・取り消し、上演期間の外は断る、ツアーの別会場の期間なら付け替える）。上演が終わる（確定した券の日か千秋楽）と、日記帳の行にして未評価に移す（_promote_owned_tickets。評価の画面を開いたときにも行う）
- **書き込み**: favourite（登録は app_setting の declared。古い「アカウント・記録」の favourites 表も読む）・decline・ticket
- まだのもの: 理由の文から拾った名前の候補（reasons.promotions）と、見送った理由から拾った語の候補（reasons.demotions）。メールの取り込み（持ち主専用）
無料枠: 照合は登録や語・カードの版が変わったとき、rec_card の全行を 1〜数回なめる（数千行の読み）。各画面は使い回しが効かないので開くたびに数十〜数百行を読む。1 日 500 万行の枠に対して小さい。
