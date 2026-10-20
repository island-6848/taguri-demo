---
id: q-nonplay-in-reco
type: question
status: answered
date: 2026-10-19
title: 能・歌舞伎・落語・バレエ・オペラなどを、おすすめの候補に入れるか（いまは題名で外している）
sources:
  - tools/review/recommend.py
  - cloudflare/scripts/build_recommend_index.py
links:
  - depends_on: dec-forms-1019
---
tools/review/recommend.py の NOT_PLAY_TITLE（バレエ・オペラ・ダンス・文楽・歌舞伎・落語・独演会・寄席・講談・浪曲・漫才・能楽・狂言・コンサートなど）が題名にある公演は、推薦の索引・カード（build_recommend_index・build_cards・user_recommender）から外している。もとは「劇場3主催の演劇」を申告に合わせて数えるための決め事。

形式を分けたので、入れて「この形式を理由に出さない」で外せるようにする道もある。入れると索引とカードの行が増える（手元の取得データ 4,813 件のうち、言葉でざっと数えて 400〜500 件）。D1 の書き込みと読み取りの量を数えてから決める。起案者に聞く。
