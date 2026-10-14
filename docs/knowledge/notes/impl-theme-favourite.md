---
id: impl-theme-favourite
type: finding
status: confirmed
date: 2026-10-14
title: 題材のお気に入りも推薦の種にした。あらすじの要素の語を #題材 のタグとして索引に入れ、双方向の部分一致で引く（+fav3）
sources:
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/src/recommend.js
  - cloudflare/test/test_recommend_index.py
links:
  - answers: q-theme-favourite
  - depends_on: eval-favourite-kinds
  - depends_on: impl-favourite-seed
  - affects: comp-recommender
---
索引を作るときに、これからの公演のあらすじの要素（themes.jsonl、手で入れた分を重ねた net_c.load_themes の candidate 側）を正規化（RC.nz）し、2 文字以上・最大 6 語を ("#題材", 語) のタグとして rec_credit / rec_people に入れる（公演の種類と同じ扱い、重み GENRE_W）。題材のお気に入りは、名前を含む語か名前に含まれる語（2 文字以上）を持つ公演を種にする（net_c.declared_hits と同じ双方向の照合。あらすじの本文は索引に無いので本文との照合はしない）。Worker は rec_credit の role='#題材' を 1 回なめて引く。Python の参照と Worker が同じ種・同じ点を出すことを一致テストで確かめた。限界: あらすじの要素があるのはこれからの公演だけで、評価した過去の公演には無いので、#題材 の好みは評価からはほとんど学べない（種としてだけ効く）。Render の Python 版の推薦には入れていない。D1 の書き込みは #題材 の行の分（公演あたり最大 6 行）増える。
