---
id: dec-calendar-timeline
type: decision
status: adopted
date: 2026-10-15
title: 公演カレンダーを月ごとの格子から 1 枚の続いた格子にし、「持っている」は実線・「興味あり」「お気に入り」は点線にそろえる
sources:
  - cloudflare/src/screens/calendar.js
  - tools/taguri/stage_calendar.py
  - web/theme.css
  - web/app.js
links:
  - affects: comp-frontend
---
起案者の指示（2026-10-15）は次の 3 つ。
- 「公演カレンダー今お気に入りが点線になってるけど、区切りとしては既に持っている/お気に入り・興味あり。点線と実線の使い分け統一して」
- 「10月とか（）の中のお気に入りの件数とか改行されてるから1列になるように」
- 「月ごとにわけて描画してるけど、月またいでやってる作品が見づらい。改善」

作りは次のとおり。
- 線: 「すでに持っている」は実線。「興味あり」「お気に入り」はどちらも点線にした（.bar.trk を dashed に）。色は今までどおり。
- 格子（stage_calendar._timeline / calendar.timeline）:
  - 今月の 1 日から、最後の楽日の月の末日まで（最大 12 か月）を 1 枚にする。
  - 1 公演は 1 行・1 本の帯になる。
  - 見出しは 2 段。1 段目が月の名前（横に送っても題名の列の右に留まる）、2 段目が日と曜日。月の境目には縦の線を引く。
  - 並びは都道府県順、県の中は締切の近い順（前と同じ）。2026-10-24 に〔dec-calendar-order-live-first〕で変えた。
- 件数: 格子の上に「N 件」と、種類の絵記号＋数を 1 行で出す（読み上げには種類の名前を残す）。
- 開いたときの位置（app.js の fixupMonthScroll）: 今日の位置に送る。今日から画面 1 枚ぶんの内に行く日があれば、その日が入る位置に送る。
- Python の stage_calendar と Worker の calendar.js は同じ HTML を出す（calendar.test.js）。
