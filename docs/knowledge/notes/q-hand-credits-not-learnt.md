---
id: q-hand-credits-not-learnt
type: question
status: open
date: 2026-10-18
title: 手で入れた出演者・作り手（hand_credits）は、推薦の学習に入らない。公演と結び付いていない記録の手入力、結び付いた記録の手直しをどう扱うか（#105、起案者の判断）
sources:
  - https://github.com/island-6848/taguri-demo/issues/105
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/screens/works.js
links:
  - affects: dec-reco-on-worker
---
コードで確かめたこと（2026-10-18）: ratedWorks は stage_id のある記録だけを使い、人物は索引（rec_people・past_stage）からだけ読む。loadWorks が読む hand（hand_credits）は推薦では使われない。
- 決めること: (1) 結び付いていない記録の手入力を学習に入れるか（入れれば、公演一覧に無い過去の公演も好みの材料になる。読み出しは本人の hand_credits の行だけ） (2) 結び付いた記録で、手入力と索引のどちらを優先するか（手入力で置き換える／足すだけ／索引のまま） (3) 名前の書き方が索引と違うとき（表記ゆれ）にどう合わせるか
- 推し: (1) は入れる（本人が補った情報で、量は小さい）。(2) は「手入力を優先して置き換え」で、cast_off（観た回にいなかった人）と同じ扱いにそろえる。入れない場合は日記帳の手入力の欄に「おすすめには使いません」と書く
