---
id: dec-reading-dual-form
type: decision
status: adopted
date: 2026-10-19
title: 朗読劇はほかの形式と兼ねる。題名に 朗読・リーディング があれば、ほかの形式に加えて朗読劇の札も付け、朗読劇の題名に「音楽劇」があれば音楽劇の札も付ける
sources:
  - tools/review/user_recommender.py
  - tools/taguri/test_user_recommendation.py
links:
  - answers: q-reading-music-form
  - depends_on: dec-form-rodokugeki
  - affects: dec-forms-1019
---
起案者の問い「リーディング音楽劇の場合どうする？ジャングル大帝とか」→ 案 (C)「両方の札を付ける」。

- user_recommender.stage_tags: form_of（札 1 つ）は変えず、題名に 朗読・リーディング があれば ("#形式", "朗読劇") も足す。form_of が朗読劇で、題名に「音楽劇」があれば ("#形式", "音楽劇") も足す
  - 「リーディング音楽劇『ジャングル大帝』」→ 朗読劇・音楽劇
  - 「リーディングミュージカル『〜』」→ ミュージカル・朗読劇
  - 「朗読劇『〜』」で作曲・音楽の作り手がいるだけ → 朗読劇だけ（BGM の作曲者がいる朗読劇は多いので、作り手だけでは音楽劇を足さない）
- 札が 2 つの公演は、評価がどちらの札にも付き、どちらかを「出さない」にした人には出ない。form_of を使うほかの所（能などの演目をあらすじの枠に出す program_text）は札 1 つのまま
- 題名に「音楽劇」とだけあり作曲・音楽の作り手が欄に無い公演に札を付けるか（〔q-reading-music-form〕の残り）は未決。いまは付かない
- 本番に出るのは次の取得で推薦の索引を作り直してから。無料枠: 朗読劇の公演の索引の行が数行ずつ増える（差分で書く）だけ
