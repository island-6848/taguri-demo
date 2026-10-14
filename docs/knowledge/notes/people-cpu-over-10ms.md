---
id: people-cpu-over-10ms
type: finding
status: confirmed
date: 2026-10-14
title: 相関図（people.panel）は重い記録で温まっても 19〜29 ミリ秒、最初の 1 回は 69〜89 ミリ秒かかり、Worker の CPU 10 ミリ秒に収まらない
sources:
  - cloudflare/src/screens/people.js
  - cloudflare/test/people.test.js
links:
  - supports: dec-records-worker
  - depends_on: workers-free-cpu-10ms
---
node 22 で people.panel(owner=False) の JS 版を測った（150 作品・中心の 56 名・線 193 本・切れ目 1 名。40 回温めたあとの 9 回の中央値、ほかの作業と同じ機械なので幅がある）。
- 力学配置（460 回 × 1540 組）6.2〜9.3 ミリ秒、重なりの掃除 0.1 ミリ秒、時間のつまみ（timeline）8〜13 ミリ秒
- 縮める前は timeline が 91 ミリ秒・全体 124 ミリ秒だった。関節点を Tarjan の方法で求める（ランダムな 3000 の網で総当たりと一致）・150 回の作り直しを差分 1 回にする、で同じ出力のまま縮めた
分からないこと: Cloudflare 上での実測（この環境からは測れない）。
