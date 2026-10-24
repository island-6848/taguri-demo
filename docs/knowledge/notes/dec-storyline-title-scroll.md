---
id: dec-storyline-title-scroll
type: decision
status: adopted
date: 2026-10-24
title: 眺めるの「同じ作品で一緒だった人の流れ」を「Storyline」にし、説明の文を消す。図は d3 の拡大縮小に指の操作を渡さず、スマホでは横・縦にスクロールできるようにする
sources:
  - tools/taguri/storyline.py
  - cloudflare/src/screens/storyline.js
  - web/style.css
links:
  - affects: dec-overview-without-venue-ranking
---
起案者の指示（2026-10-24）「眺めるのページの『同じ作品で一緒だった人の流れ』を『Storyline』にして。図をスマホでもスクロールできるようにして。下の文章消して」。

- 見出しを「Storyline」にし、図の上の説明の文（線と束の読み方・色の分かれ方・直近 1 年・線にしている人数・操作の説明）を消した。色の凡例と期間は残した。文を作っていた recentLine / _recent_line は使わなくなったので消した。Python（storyline.py）と Worker（storyline.js）の両方を同じに直し、一字一句の比べ（storyline.test.js）は通る
- スクロールできなかった理由（実ブラウザーで確かめた）: 図の svg に d3.zoom を掛けていて、d3 が指の操作（touchstart/touchmove）を受け取って既定の動きを止めていた。そのため図の上では、入れ物（.sl、横に流れる）の横スクロールも、ページの縦スクロールも効かなかった
- 直し方: d3.zoom を touchable(() => false) にし、指の操作は d3 に渡さない。.sl に touch-action:pan-x pan-y を付けた。スマホでは横のスクロールで時間をたどる。マウスのドラッグとホイールでの拡大縮小は前のまま。線・束を押す（click）のは指でも効く
- 確かめたこと: Chromium（390px・指の操作を CDP で送る）で、図の上を左へなぞると図が 307px 横に動き、上へなぞるとページが 311px 動いた。直す前の形では、どちらも 0 だった。npm test・Python の試験が通る
