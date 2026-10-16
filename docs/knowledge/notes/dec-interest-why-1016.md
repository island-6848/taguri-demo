---
id: dec-interest-why-1016
type: decision
status: adopted
date: 2026-10-16
title: 興味ありのカードに、おすすめで押したときの理由を出す（reaction.why）
sources:
  - cloudflare/migrations/0026.sql
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/screens/lists.js
links:
  - affects: comp-frontend
  - depends_on: dec-interest-card-1015
---
起案者の質問（2026-10-16）「おすすめ画面では理由がちゃんと出てるのに、興味ありに移ったらおすすめ理由が空欄になるのなんで？」

原因:
- おすすめ理由はカードに書いて置いておらず、おすすめの画面を出すたびに計算している（recommend.reasonRows）。
- 興味ありを押した公演は「答えた公演」になり、おすすめの計算から外れる。興味ありの画面は理由を計算していなかったので、「理由を出せていません」が残った。

作り:
- おすすめの画面で興味ありを押したとき（source が 'screen'）、押す前のおすすめの控え（rec_cache）からその公演の理由（人 4・種類 2 と作品名）を JSON で reaction.why に残す（migration 0026）。
  - 控えは印を確かめずに読む（D1 の読み取り 1 行）。
  - 書き込みは興味ありと同じ行なので回数は増えない。
- 興味ありの画面（lists.interestScreen）は reaction.why を reasonRows で出す。
- reaction.why の無い行（この変更より前に押した分）は、おすすめの控えの answered_why から出す（VERSION screen-v11）。
  - 興味ありの公演は自分も種になっているので、作品名から自分の題名を除き、ほかの作品が無い人と種類は外す（lists.ownlessWhy）。
  - 開幕リマインド・探すから足した行は、これまでどおり「〜からの追加」とだけ書く。
