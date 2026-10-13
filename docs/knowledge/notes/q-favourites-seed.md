---
id: q-favourites-seed
type: question
status: open
date: 2026-10-13
title: 最初に入れる「お気に入り」から、評価が付く前の推薦を作るか（起案者の案）
links:
  - depends_on: lit-syskill-webert-prior
  - depends_on: q-hidden-gate
  - affects: comp-recommender
---
起案者の案（2026-10-13）: 推薦を始める前に「絶対追いかけてほしい」お気に入り（人・団体・主催・作品・題材・原作者）を入力するので、そこから初期の推薦だけを作る。案: お気に入りを「とても良かった」の仮の評価として扱い、評価が増えるほど弱める（Syskill & Webert の「本人が与えた初期の好みを評価で直す」と同じ形、lit-syskill-webert-prior）。お気に入りの人そのものの公演はすでに別の束（お気に入りに合う公演）で必ず出すので、推薦では「お気に入りの人とよく組む人・同じ劇団の公演」など一歩外側を勧める（公開の公演情報のつながりだけで作れる）。持ち主 1 人の過去の検証では申告を点に混ぜると下がったが n=1 なので根拠にしない（dec-no-n1-evidence）。効果は公開データでは確かめにくく、裏の答え合わせ（q-hidden-gate）で人ごとに確かめる。
