---
id: f-form-rodoku-1019
type: finding
status: confirmed
date: 2026-10-19
title: 形式（#形式）に「朗読」がある（札の名前は「朗読劇」ではなく「朗読」）。題名に 朗読 か リーディング があれば付く。題材の語彙表にも別に「朗読劇」（語り口の軸）がある
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/tools/review/user_recommender.py
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/src/vocab/concepts.json
  - https://github.com/island-6848/taguri-demo/blob/master/tools/review/recommend.py
links:
  - depends_on: dec-forms-1019
---
起案者の問い（2026-10-19）「形式に『朗読劇』ある？」に、master のコードを読んで答えた。

- user_recommender._FORM_TITLE の ("朗読", 朗読|リーディング)。題名だけで見る（劇場・主催の名前の規則は無い）。上から最初に当たったものなので、落語・寄席、能・狂言、歌舞伎、文楽、オペラ、バレエ、ミュージカル、お笑い、ダンスの語が題名にあればそちらになる（「朗読ミュージカル」はミュージカル）。人形劇より先
- 題名に「朗読」「リーディング」が無い朗読劇（あらすじや説明にだけ書いてある）には付かない
- 題材の語彙表（concepts.json）の「朗読劇」は 語り口 の軸の言葉（リーディング・朗読・リーディング公演・語りの劇）。あらすじからの読み取りで付く題材側の札で、形式とは別
- 推薦の索引から外す題名の語（recommend.NOT_PLAY_TITLE）に 朗読 は無いので、朗読の公演はおすすめの候補に入る

分からなかったこと: 実データで朗読の札が付いた公演の数（手元に取得データが無い）。
