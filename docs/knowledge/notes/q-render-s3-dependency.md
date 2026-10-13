---
id: q-render-s3-dependency
type: question
status: open
date: 2026-10-13
title: Render のデモ版は、起動し直すと動かなくなるのではないか
links:
  - depends_on: no-aws
  - affects: q-demo-trial-design
---
serve_cloud.py は起動のたびに S3 からカタログを取り込み、失敗すると起動しない。AWS を使っていないなら、次の再デプロイや、無料プランの休止からの起動で失敗しうる。今動いているのは、取り込み済みのまま起きているからかもしれない。そのため「Render を最新のコードで起動し直して」というお願いは取り消した。Render の環境変数の鍵と S3 のバケットがまだ生きているかを確かめる。
