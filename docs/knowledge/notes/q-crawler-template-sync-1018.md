---
id: q-crawler-template-sync-1018
type: question
status: open
date: 2026-10-18
title: 雛形の catalog.yml・restore-drill.yml の直し（issue #139）を本番の taguri-crawler に写したか
links:
  - depends_on: dec-free-tier-audit-fixes-1018
---
2026-10-18 の点検の時点で、本番の 3 つ（catalog.yml・replay.yml・restore-drill.yml）は雛形と同じ中身だった（ファイルの SHA が一致）。今回、雛形の catalog.yml（state を取り出せないときに止める）と restore-drill.yml（plan --mode drill を通す・actions: read）を直したので、写すまで本番とずれる。写したら `diff` が空なのを確かめ、answered にする。restore-drill.yml の plan は master の free_tier.py に `--mode drill` が入ってから動く（入る前に写すと引数の誤りで止まる）。
