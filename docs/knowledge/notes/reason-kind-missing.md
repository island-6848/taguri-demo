---
id: reason-kind-missing
type: finding
status: confirmed
date: 2026-10-14
title: デモ版のおすすめに「理由を出せていません」が増えたのは、v3 で公演の種類（#形式・#原作・#翻訳・#会場・#値段）の点だけで上位に入れるようにしたのに、理由の行に種類を出していなかったため。クレジットの無い公演が劇場だけで上位に来ていた。点を上げた人物か公演そのものの種類が無い公演は出さないようにし、種類を理由に出す
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
- 起案者の画面（2026-10-14）: 舞台「IF」（IMM THEATER）と「Wゲーム」（本多劇場）。どちらもクレジットが無く（出演・スタッフの行が無い）、種類は劇場（と料金帯）だけ。記録 100 件近くの中で好きな劇場なので点が 0 を越え、上位に入っていた。v2 では人物が合わない公演は点が 0 で外れていた
- 決めたこと: **おすすめにするのは、点を上げた人物か、点を上げた公演そのものの種類（#形式・#原作・#翻訳・#題材＝user_recommender.CONTENT_AXES）がある公演だけ**。劇場と料金帯は条件であって中身ではないので、並びを直すだけにする（has_reason）。「ミュージカルを高く付ける人には、知らない人のミュージカルも上げる」（test_kind_preference_reaches_shows_without_shared_people）は残る
- 同じ規則を 3 か所に入れた: デモ版（user_recommender.finish）・索引の点（build_recommend_index.score_from_index）・Worker（recommend.js）。Worker の理由は人物の 3 つまでの空きを種類で埋める（role が「#形式」などの形で返る）。推薦の版の印に +why1
