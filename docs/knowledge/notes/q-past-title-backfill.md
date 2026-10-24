---
id: q-past-title-backfill
type: question
status: answered
date: 2026-10-20
title: 前に取った過去の公演（約 1.8 万件）の題名に冠名・サブタイトルを足すため、公演ページを読み直すか
sources:
  - tools/review/fetch_past_stages.py
links:
  - depends_on: dec-title-crown-subtitle
---
過去の公演はページを残さず 1 行だけ控えている（fetch_past_stages.row_from_html「ページは残さないので」）。冠名・サブタイトルは取り直さないと入らない。読み直すと GitHub Actions の分数と CoRich への要求が増える（過去の公演は 1 日に数千件の枠で読んでいる）。起案者に聞く。

答え（2026-10-20）: 起案者が「過去の公演もお願いします」。〔dec-past-title-backfill〕で入れた。
