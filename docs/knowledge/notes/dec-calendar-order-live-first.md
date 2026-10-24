---
id: dec-calendar-order-live-first
type: decision
status: adopted
date: 2026-10-24
title: 公演カレンダーの並びを、上演中は千穐楽の近い順、そのあとにこれから開く公演を初日の近い順にする（都道府県ごとの並びはやめた）
sources:
  - cloudflare/src/screens/calendar.js
  - tools/taguri/stage_calendar.py
  - cloudflare/test/calendar.test.js
links:
  - depends_on: dec-calendar-timeline
---
起案者の指示（2026-10-24）「公演カレンダーの並び順、上演中のものは千秋楽が近いものから順に並べて、そのあとに開幕の初日が近い順に並べて」。

- 上演中: 初日が今日まで（今日が初日を含む）。千穐楽の近い順に並べ、千穐楽が同じなら初日の早い順、題名の順にする。
- これから: 初日の近い順に並べ、初日が同じなら千穐楽の近い順、題名の順にする。
- 前の並びは、都道府県ごと（起案者の指摘 2026-08-25「都道府県順に並び変えて」）で、県の中は締切の近い順だった。今回の指示で置き換えた。場所の絞り込み（都道府県の札）はそのまま。
- サービス版（calendar.js）と持ち主の画面（stage_calendar.py）を同じ並びにした。calendar.test.js が、両方の HTML が同じであることと、並びそのものを確かめる。
