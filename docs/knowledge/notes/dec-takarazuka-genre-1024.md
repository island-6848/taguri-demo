---
id: dec-takarazuka-genre-1024
type: decision
status: adopted
date: 2026-10-24
title: ジャンル「宝塚」を「宝塚歌劇団」に改め、東京宝塚劇場・宝塚大劇場でかかる公演も主催にかかわらず入れる。あらすじの札の先頭にも #宝塚歌劇団
sources:
  - tools/review/user_recommender.py
  - cloudflare/scripts/build_cards.py
  - cloudflare/migrations/0046.sql
  - tools/taguri/test_user_recommendation.py
links:
  - depends_on: dec-genre-axis
  - affects: comp-recommender
---
起案者の指示（2026-10-24）「特例で東京宝塚劇場と兵庫の宝塚劇場でやってる演目のジャンルは「宝塚歌劇団」として。あらすじにも#宝塚歌劇団、のタグをつける。」

- `user_recommender.is_takarazuka(group, venues)`: 主催が宝塚歌劇団、または劇場が「東京宝塚劇場」「宝塚大劇場」を含むとき。〔dec-genre-axis〕の「スタッフ欄だけでは入れない」はそのまま。
- `genres()` が返す名前は「宝塚歌劇団」（前は「宝塚」）。おすすめ理由・✕ の鍵は `#ジャンル\t宝塚歌劇団` になる。
- 前の名前で ✕ を押した人の設定（app_setting の kind_off）は、migration 0046 で新しい名前に書き換える。
- カード（build_cards）のあらすじの札: **主催が宝塚歌劇団の公演だけ**、「宝塚歌劇団」を先頭に置く。劇場だけで宝塚歌劇団のジャンルになる公演には付けない。
  - 起案者の指示（同じ日、後から）「あらすじのところにはその2つのタグつけないで。例外として、主催が宝塚歌劇団の場合のみ、あらすじの抽出ワードにも宝塚歌劇団を含めてよい」。
  - 「その2つ」は〔dec-member-affil-tag〕の出身・所属の札（宝塚歌劇団・STARTO ENTERTAINMENT）。
  - あらすじの抽出ワード（カードの札と索引の #題材）から、宝塚・STARTO の書き方の言葉を外す（UR.synopsis_words）。主催が宝塚歌劇団の公演の「宝塚歌劇団」だけ残す。
- 本番の索引・カードに出るのは、次に索引を作り直して届けたとき。
