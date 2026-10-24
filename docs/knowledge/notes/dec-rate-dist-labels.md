---
id: dec-rate-dist-labels
type: decision
status: adopted
date: 2026-10-24
title: 評価一覧の分布は見出しを「評価の分布」にし、説明の段落と「数字で見る」の表をやめ、帯の下に段階ごとの札「★n n%」を置く
sources:
  - cloudflare/src/screens/rate.js
  - web/app.js
  - web/theme.css
  - tools/taguri/charts.py
links:
  - affects: dec-rate-dist-no-fit
---
起案者の指示（2026-10-24）「評価一覧のページで、付けた評価の分布→評価の分布に変更。『基準は「自分に合っていたか」で…おすすめの材料になります。』削除。数字で見るも削除。横帯グラフ、角帯の下に『★n n%』のラベルをつけて」。

- 見出しを「評価の分布」に。説明の段落と「数字で見る」の表は出さない
- 段階と件数は表の代わりに帯の data-rows（[[段階, 件数], …]）に置き、app.js（divergeVerdicts）がそれで帯と札を描く
- 札は各段階の真下に「★n n%」（未評価は「未評価 n%」）。前の凡例（件数入り）と、帯の中の割合はやめた。同じ数を 2 度書くため。件数は帯に触れると出る（title）
- 狭い段階が続いて札が重なるときは、重なる札を次の段（3 段まで）に下げ、細い線で帯とつなぐ。電話の幅（390px、10% の段階が 4 つ続く例）で写して重ならないのを確かめた
- Python（charts.verdict_panel）も同じ形にした（screens.test.js の照合のため）
