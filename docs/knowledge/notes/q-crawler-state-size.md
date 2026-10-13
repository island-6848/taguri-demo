---
id: q-crawler-state-size
type: question
status: answered
date: 2026-10-13
title: 取得の作業データ（state ブランチ）が 2 GB になった。ポスターと公演ページの HTML の控えをどうするか
links:
  - depends_on: sitemap-first-run
---
初回のサイトマップ版で作業データが 11,045 ファイル・2.0 GB になった（sitemap-first-run）。毎回まるごと force push しているので、GitHub の 1 回の push の上限（2 GB）にすぐ届く。終わった公演のポスターまで取っている。
案: ① 公演ページの HTML の控え（data/credits/pages）を state に入れない（あらすじの読み取り待ちに要る分だけ残す）② ポスターは「これから」の公演の分だけ残し、終わった公演のポスターは取らない・消す ③ ポスターは R2 など別の置き場に移す（q-worker-posters と一緒に決める）。どれも fetch_candidates・posters.py・crawler_state.py の変更で、毎晩の実行が失敗しはじめる前に直したい。
