---
id: storyline-cpu-over-10ms
type: finding
status: confirmed
date: 2026-10-14
title: 眺めるの「人の流れ」（StoryFlow の配置）は、重い記録だと Worker の CPU 10 ミリ秒に収まらない（温まって約 12 ミリ秒・最初の 1 回は約 80 ミリ秒）
sources:
  - cloudflare/src/screens/storyline.js
  - cloudflare/test/storyline.test.js
links:
  - supports: dec-records-worker
  - depends_on: workers-free-cpu-10ms
---
storyline.panel を JS に移し（Python と一字一句同じ・storyline.test.js）、node 22 で panel() だけを測った。作った記録は 150 作品・5 年・3 つの世界・4 回以上出てくる人 58 名（26/20/12 名、セッション 69/55/24）。ほかの作業と同じ機械で測ったので幅がある。
- 最初の 1 回: 79〜87 ミリ秒
- 3 回温めたあとの 9 回の中央値: 25〜45 ミリ秒。30 回温めたあと: 12〜17 ミリ秒（いちばん速くて約 11）
- テスト用の 52 行の記録: 最初 19・温めて 8 ミリ秒
最初にそのまま移した形は中央値 160 ミリ秒だった。同じ出力のまま、名前を整数にして型付き配列に置く・挿入位置の交差を差分で数える・隣の場面との交差を覚えておく・世界の分け方を人ごとの最初のセッションでつなぐ、などで縮めた。残りは手順そのもの（掃き 20 往復は束が揺れて途中で止まらない＋詰め約 16 回）。
Worker の機械は別物なので数字は目安。分からないこと: Cloudflare 上での実測（この環境からは測れない）。
