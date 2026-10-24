---
id: dec-word-cloud-tags
type: decision
status: adopted
date: 2026-10-24
title: 眺めるの「ことばの雲」は、あらすじの本文を語に切るのをやめ、あらすじから読み取ったタグ（カードのハッシュタグと同じ語）を、付いている公演の数で並べる
sources:
  - cloudflare/src/screens/words.js
  - cloudflare/src/screens/records.js
  - cloudflare/src/screens/figs.js
  - cloudflare/test/words.test.js
links:
  - supersedes: dec-word-cloud
  - depends_on: impl-hashtag-list
  - depends_on: dec-synopsis-reader-claude
---
起案者の指示（2026-10-24）「ワードクラウドはあらすじ抽出でタグに出ている単語リストから構成してほしい」。

- 材料（records.tagsFor）: 観た公演ごとのタグ。引く順はカードの札と同じで、管理者が手で入れた題材（stage_override.themes。空の並びなら「題材なし」としてほかから足さない）→ 作り置きのカード（rec_card.ws、1 行に 1 語。ハッシュタグの一覧 tagged.js と同じ列）→ 過去の公演の #題材（past_stage.people）。1 公演の中の同じ語（nz でそろえて同じもの）は 1 つにする
- 数え方（words.countTags）: 1 つの公演に付いていれば 1 と数え、多い順に 45 語。2 公演以上に付いた語が 12 語以上あれば、1 公演だけの語は外す。タグのある公演が 5 公演に満たなければ描かない
- やめたこと: あらすじの本文を Intl.Segmenter で語に切る・決まり文句の除外表（STOP）・漢字か片仮名だけに絞る規則。タグは読み取りの段で本文に実在するかを確かめた語なので、要らない
- 見出しは「ことばの雲 ── 観た舞台のタグから」、枠の札は「N 公演のタグ」。語の title は「#語：N 公演に付いている」
- 無料枠: 読むのは観た公演の行だけ（stage_override・rec_card・past_stage を主キーで。前はあらすじのために catalogue・past_stage を読んでいたので、ほぼ同じ）。ページに載せる量は、あらすじの本文（最大約 180KB）からタグの語だけになり小さくなった
- 索引の #題材（rec_people）は 1 公演 6 語まで・2 文字以上で、カードの札と食い違うので使わない（tagged.js と同じ判断）
- 確かめたこと: words.test.js（数え方・配置・枠の文・3 つの引き先と手で「題材なし」にした公演）。npm test・Python の試験が通る。電話の幅で描いた写しを見た
