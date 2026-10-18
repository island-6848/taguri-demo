---
id: dec-theme-rollup
type: decision
status: adopted
date: 2026-10-18
title: 評価から分かった細かい題材の好みを語彙表の上位へ積み上げ、3 つ以上の枝で同じ向きなら上位の好みとして下の言葉へ効かせる
sources:
  - cloudflare/src/vocab.js
  - cloudflare/src/recommend.js
  - cloudflare/test/vocab.test.js
links:
  - affects: impl-theme-vocab
  - affects: dec-theme-kinds-6p2
---
起案者の問い（2026-10-18）「細かい粒度が溜まっていったら必然的にそのツリーより上の粗い粒度のものも推薦に使われるようになる？」。それまでは使われていなかった。語彙表をたどるのはお気に入りを下へ広げるときだけで、評価から学ぶ題材の好みは言葉ごとにばらばらだった（宇宙船・ロボット・タイムスリップを高く評価しても、「宇宙人」の公演は上がらない）。起案者の判断「仕組みの案の 1,2 どっちもやりたい」「それなら SF って出しちゃっていいよ」。

- 積み上げ（vocab.rolledThemeWords）: 題材の言葉の好み（personValues の #題材 の行）を、その言葉の概念から上位へ、離れるほど弱く（DEPTH_W 0.6・0.35…）配る
- 3 つ以上の枝: 上位とその下の **3 つ以上の概念**で同じ向きの好みがあるときだけ、上位の好みにする（ROLLUP_MIN_BRANCHES）。1 本の作品や 1 つの枝だけで「科学全般が好き」としない。宇宙ものの作品だけなら SF までは上げない
- 細かい好みが勝つ: 自分の値を持つ言葉には、上位の好みを広げない（SF が好きでもロボットが低評価なら、ロボットは自分の値のまま）。上位が二つ当たる言葉は、重いほう（ふつうは近い上位）だけ
- 苦手も同じ向きで積み上げる（3 つ以上の枝で低評価なら上位でも下げる）。関連（近未来など）には広げない
- 使い方: 上位の好みを、その下の言葉（語彙表の下位）が付いた公演に効かせる（scoreFromIndex。索引の読み出しが上位の下の言葉の分だけ増え、書き込みは増えない）。理由には上位の名前を出す（「題材「SF」」）。1 公演 1 つの上位につき 1 回
- 考え方の出どころ: 分類の木で好みを上へ伝える Ziegler ら（2004、Taxonomy-driven computation of product recommendations）と、まばらな好みを上位で補う Kanagal ら（2012、Supercharging recommender systems using taxonomies）。どちらも Claude の知識による引用で、このセッションでは原典を確かめていない（unverified）
- 再生で外せるようにした（REPLAY_ABLATIONS に rollup）。当たりが良くなるかは、評価が増えてから再生で測る
- 知っておくこと: Python の参照実装（user_recommender）には写していない。一致試験の作り物の題材は語彙表に無いので試験は通るが、本番の題材では JS だけが積み上げる
- 控えの版を screen-v35 に上げた（積み上げを入れた順位を作り直させるため）
