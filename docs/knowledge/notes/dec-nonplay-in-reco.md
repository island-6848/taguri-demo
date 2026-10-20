---
id: dec-nonplay-in-reco
type: decision
status: adopted
date: 2026-10-20
title: 能・狂言・歌舞伎・文楽・落語・寄席・バレエ・ダンス・オペラ・お笑いも、おすすめの候補に入れる（外すのはコンサートなどだけ）
sources:
  - tools/review/recommend.py
  - tools/review/recommend2.py
  - tools/review/user_recommender.py
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/scripts/build_cards.py
  - cloudflare/test/test_recommend_index.py
links:
  - answers: q-nonplay-in-reco
  - depends_on: dec-forms-1019
  - affects: comp-cf-worker
---
起案者の指示（2026-10-19）「おすすめから除外しないで」。

- 推薦の索引（build_recommend_index）・カード（build_cards）・候補（user_recommender・recommend2）で題名を見て外す語を、NOT_PLAY_TITLE から NOT_STAGE_TITLE（コンサート・歌謡ショー・音楽祭・リサイタル）に替えた。舞台の上演でない催しだけを外す
- 能・狂言などは形式（form_of）の札が付くので、要らない人は「この種類を理由に出さない」で外せる。演目はあらすじの枠に出る〔dec-noh-program〕
- NOT_PLAY_TITLE は、申告の照合（recommend.is_play。劇場3主催の演劇）にだけ残す
- 無料枠: 手元の取得データ（data/review/candidates.jsonl、終わっていない分）で数えると、候補 1,278 件に 71 件（約 5%）、索引の行はおよそ 29,000 行に約 670 行（約 2%）が足される見込み。D1 の書き込みは取得の段が 1 日 8 万行（free_tier.CAPS）の手前で止める仕組みのまま。本番の件数は次の取得の「Free-tier check」で確かめる
