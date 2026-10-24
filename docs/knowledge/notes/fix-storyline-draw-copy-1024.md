---
id: fix-storyline-draw-copy-1024
type: finding
status: confirmed
date: 2026-10-24
title: Storyline の図をスマホで横スクロールできる直し（dec-storyline-title-scroll）が画面に効いていなかった。画面で図を動かすのは手で写した web/storyline-draw.js で、直したのは画面では動かない <script> の側だけだった
sources:
  - web/storyline-draw.js
  - web/app.js
  - cloudflare/scripts/write_icons.py
  - cloudflare/test/test_storyline_draw.py
links:
  - affects: dec-storyline-title-scroll
---
起案者の指摘（2026-10-24）「スマホで横スクロールでこない」（dec-storyline-title-scroll をマージしたあと）。

分かったこと（コードと実ブラウザー）:
- 眺めるの画面は HTML を innerHTML で入れるので、図に付けた <script>（storyline.py の SCRIPT、Worker の STORYLINE_JS）は動かない。図を動かすのは app.js の fixupStoryline が読み込む /storyline-draw.js（web/storyline-draw.js の写し）
- web/storyline-draw.js は SCRIPT を手で写したもので、書き出す仕組みが無かった。前の直し（d3.zoom の touchable(() => false)）は SCRIPT にだけ入り、このファイルには入っていなかった
- 前の確かめは、図の HTML に入った <script> を動かす作りのページで行ったので、食い違いに気づかなかった

直し方:
- scripts/write_icons.py が SCRIPT から web/storyline-draw.js も書き出す（先頭に「手で直さない」の注）。sync_public_ui.py で cloudflare/public に写す
- test/test_storyline_draw.py: web/storyline-draw.js が SCRIPT から書き出したものと同じか、Worker の STORYLINE_JS と同じか、指の操作を d3 に渡していないかを確かめる（CI の Python の試験に入る）

確かめたこと: 画面と同じく /storyline-draw.js で図を描くページを Chromium（390px）で開き、指の操作を CDP で送った。master の版は図の上を左・上へなぞっても 0 のまま（本番の症状と同じ）。直した版は横に 325px、ページが 312px 動いた。
