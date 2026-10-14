---
id: impl-person-ordinal-v3
type: finding
status: confirmed
date: 2026-10-13
title: 推薦の計算を person-ordinal-v3 に変えた（評価を順序として読み、公演の種類の好みを足す）
sources:
  - tools/review/user_recommender.py
  - cloudflare/src/recommend.js
  - cloudflare/scripts/build_recommend_index.py
links:
  - depends_on: eval-design-choices
  - affects: comp-recommender
  - answers: q-theme-preference
---
評価は同じ段階の中での順位（((下の数)+½(同じ数))/n−½、×√12）。公演の種類のタグを題名・クレジット・劇場から決める: #形式（ミュージカル・朗読・人形劇・ダンス・古典・お笑い、題名に無ければ作曲・音楽などの役職で音楽劇）、#原作（原作もの／オリジナル）、#翻訳、#会場。タグは人物と同じく本人の値を平均し、公演の点に平均を重み 1.0 で足す（役職のまとめ「作品の内容」の効かせ方で変えられる）。公開の映画評価データ（選ぶのに使っていない 500 人・2 抽出）で今の計算より +0.024〜0.036、良くなった人 63〜76%（ジャンルで代用）。舞台のタグでの効果は未確認。Python 3.12 以降の sum() は浮動小数の誤差を補正するため、Worker と一致させるために単純な足し算（plain_sum）にした。劇団のタグは過去の公演に劇団名が無いので入れていない。
