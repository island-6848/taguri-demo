---
id: dec-calendar-credits-daily
type: decision
status: adopted
date: 2026-10-14
title: ステイジーズカレンダーから入った公演も、公式サイトから出演・スタッフを毎回取る。トップに名前が無ければ同じサイトのキャスト・スタッフのページを 2 枚まで辿る。投稿サイトは辿らない
sources:
  - tools/taguri/fetch_stage_calendar.py
  - tools/taguri/run.py
  - tools/taguri/test_calendar_credits.py
links:
  - depends_on: reason-kind-missing
  - affects: q-crawler-state-size
---
起案者の指示（2026-10-14「1 で進めて」）。きっかけ: デモのおすすめに、出演・スタッフが 1 つも無い公演（舞台「IF」・加藤健一事務所『Wゲーム』）が劇場だけで上位に入り、理由が出なかった。どちらも CoRich の候補に無く、ステイジーズカレンダーから入った公演（カレンダーは題名・団体・劇場・期間・公式サイトのリンクだけを持つ）と見られる（デモの candidates／calendar の id が cal で始まるかで確かめられる。この作業環境からは読めない）。
- もとの作り: カレンダーの公演の出演・スタッフは `--credits` のときだけ（週 1 の `--fetch`）、公式サイトの**トップだけ**を読んでいた。測る側（fetch_official_credits.run）は前から 1 段辿っていたのに、取り込みは辿っていなかった
- 変えたこと: (1) 毎回の実行で取る（読んだページと届かなかった先は控えるので、2 回目からは新しい公演のぶんだけ通信する）。(2) トップに出演・演出・脚本・作が 1 つも無ければ、同じホストの「キャスト」「スタッフ」「公演情報」などのリンクを 2 枚まで読む（別のサイトへは行かない）。(3) x.com・Instagram などの投稿サイトは辿らない（JavaScript で描くので名前は取れない。2026-08 の実測で 470 件中 x.com が 74 件、取れたのは 0）
- 作法は変えない: robots.txt・名乗り・同じ相手へは 1.1 秒に 1 回（polite_http）
- 残ること: 公式サイトは書き方がばらばらなので取りこぼしは残る（画像の出演者表など）。取れた割合は取得のログの「クレジットが取れたのは n/m 件」で見る。辿る分だけ data/credits/official_pages（作業データの state ブランチに残る）が増えるので、作業データの大きさ（q-crawler-state-size）を見る
