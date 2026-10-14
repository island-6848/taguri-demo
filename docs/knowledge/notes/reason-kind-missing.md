---
id: reason-kind-missing
type: finding
status: confirmed
date: 2026-10-14
title: デモ版のおすすめに「理由を出せていません」が増えたのは、v3 の点に足した公演の種類（#形式・#原作・#翻訳・#会場・#値段）が理由の行に出ていなかったため。種類の行を足した
sources:
  - tools/review/user_recommender.py
  - tools/review/render_recommend.py
  - tools/review/test_reason_works.py
links:
  - depends_on: eval-genre-preference
---
起案者の指摘（2026-10-14）「デモの推薦結果に『理由を出せていません』のものが増えすぎた」。
- 原因: v3（user_recommender.prepare）の点 b は「人物の上位 3 つ＋下位 3 つ＋種類の平均」。理由の行（render_recommend.reason_rows）は人物（why_b、点を上げた人だけ）・内容（why_c）・申告・感想しか出さず、種類（why_kind）を出していなかった。v3 では why_c（あらすじの語）も空にしたので、**評価した人が一人も出ていない公演が、形式・劇場・料金帯が合うだけで上位に入ると、理由が空になる**。PR #13 で種類と料金帯を点に入れてから増えた
- 直したこと: 点を上げた種類を強い順に 2 つ、「種類」の行として出す（例「形式 ミュージカル（『作品A』・『作品B』）」）。添える作品名は人物の行と同じ作り（measure_nets.person_titles を種類のキーで引く）。点を下げた種類は出さない
- 残ること: 理由は出るが、「劇場が同じ」「料金帯が同じ」だけで上位に来ること自体が多すぎないかは別の問い。デモの実データで、種類だけの公演が上位 15 件の何割かを数えて決める
