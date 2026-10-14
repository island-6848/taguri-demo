---
id: dec-search-worker
type: decision
status: adopted
date: 2026-10-14
title: 探すを Worker に移す（これからの公演は D1 のカードを SQL で絞ってから当て、観た記録は評価一覧と同じ行で出す）
sources:
  - cloudflare/src/screens/search.js
  - cloudflare/src/screens/cards.js
  - cloudflare/scripts/build_cards.py
  - cloudflare/test/lists-screen.test.js
links:
  - depends_on: dec-lists-worker
  - affects: comp-native-screens
---
起案者の指示（2026-10-14）「残りの画面も順に移して」の 5 段目（眺める・たどる・観劇史年表より先にした）。見た目と文は app._search_body のまま。
- これからの公演: rec_card の正規化した文字列（題名・団体・クレジット・題材）と rec_stage の entry を SQL の instr で絞り、当たった行だけを app._hit_upcoming と同じ規則で確かめる。カードは作り置きのものを「ヒットした箇所」を上に出す形（ticket の why_html）で組む。compose の新しい形も 4 通りと同じく Python と一致を確かめた（test_build_cards.py・cards.test.js）
- 観た記録: 結び付けた公演のクレジット（diary.peopleByKey）で当て、評価一覧と同じ行（recRow に extra＝ヒットした箇所を足した）で出す。観た記録の題材の語（themes.jsonl の rated 側）は持ち主の取得の出力なので、本番では題材では当たらない
- 月の暦（観た記録／これからの公演の 2 つの耳）、名前を追う口（お気に入りへ）、見つからないときの「次の更新で探してもらう」（search_request。Python と同じ鍵 title_key・1 人 30 件まで）
- まだ: 取得の側が D1 の search_request を読んで探す仕組み（Python の aggregate_search_requests に当たる段）。依頼は D1 に貯まるだけで、まだ探されない → q-search-request-crawl
