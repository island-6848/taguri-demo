---
id: dec-trace-worker
type: decision
status: adopted
date: 2026-10-14
title: たどるを Worker に移す（trace.py を JS に移し、同じ記録で Python と同じ HTML・図になることを確かめる）
sources:
  - cloudflare/src/screens/trace.js
  - cloudflare/src/screens/records.js
  - cloudflare/src/screens/md5.js
  - cloudflare/test/trace.test.js
  - cloudflare/test/screens/trace_fixture.py
links:
  - depends_on: dec-native-cutover-now
  - affects: comp-native-screens
---
起案者の指示（2026-10-14）「残りの画面も順に移して」の 4 段目の 1 枚目。
- trace.py（名前の一覧・1 本の線の図・枝・たどってきた道）を JS に移した。図の撚れ・たるみは名前と番号の MD5 から決まるので、Worker に無い MD5 を JS で書いた（md5.js。図の形のためだけで、守りには使わない）。小数の書き方は Python と同じ丸め（py.fmtF）。手で作った 7 件の評価で、6 通りの画面が一字一句同じ（trace.test.js）
- 材料は measure_nets.load_rated の公開版（records.ratedRows: ◎○△× の記録、結び付けた公演のクレジット＋手で入れた分、劇場）
- 残るのは観劇史年表（chronicle.py）と眺める（charts・storyline・people・compare・render_lookback）
