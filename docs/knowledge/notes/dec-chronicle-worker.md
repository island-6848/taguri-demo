---
id: dec-chronicle-worker
type: decision
status: adopted
date: 2026-10-14
title: 観劇史年表を Worker に移す（公開版の形＝記録から数えた事実と図。LLM の読みは出さない）
sources:
  - cloudflare/src/screens/chronicle.js
  - cloudflare/src/screens/records.js
  - cloudflare/test/chronicle.test.js
  - cloudflare/test/screens/chronicle_fixture.py
links:
  - depends_on: dec-trace-worker
  - affects: comp-native-screens
---
起案者の指示（2026-10-14）「残りの画面も順に移して」の 4 段目の 2 枚目。
- chronicle.panel(owner=False)（Render の公開版と同じ形）を JS に移した。年ごとの事実（作品数・のべ回数・いちばん通った劇場・初めて行った劇場・◎ の作品に出ていて初めて観た作り手・くり返し観た作品・◎ の作品）、劇場を横のレーンにした図、年をまたいで続くもの、数字で見る表。手で作った記録 3 通りで Python と一字一句同じ（chronicle.test.js）
- LLM の読み（期の名前・年ごとの 1 行・締め）は Python でも持ち主だけ（chronicle.json は持ち主の記録から作る 1 ファイル）なので出さない。題材・トーンの語（themes.jsonl の観た側）も持ち主の取得の出力なので空
- 残るのは眺める（charts・storyline・people・compare・render_lookback）
