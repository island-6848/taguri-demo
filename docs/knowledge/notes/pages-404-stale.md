---
id: pages-404-stale
type: finding
status: confirmed
date: 2026-10-14
title: デモ版で読み込み直すと昔の見た目が出たのは、深い URL に返る 404.html が古い写しで theme.css を読んでいなかったため（直した）
sources:
  - web/404.html
  - .github/workflows/pages.yml
  - cloudflare/scripts/sync_public_ui.py
---
起案者の指摘（2026-10-14）「再読み込みをした際に急に過去のデザインのページが出てきてしまうのはなぜ」。GitHub Pages は /taguri-demo/recommend のような深い URL に index.html ではなく 404.html を返す（画面の中で移ったときは index.html のまま app.js が中身を差し替えるので、読み込み直したときだけ起きる）。web/404.html は index.html の古い写しで、今の見た目の theme.css を読む行が無かった。404.html を index.html と同じにし、pages.yml で毎回 index.html から作り直すようにし、sync_public_ui.py --check（CI）でも違えば失敗するようにした。
サービス版（Worker）は深い URL でも index.html を返す（single-page-application）ので当たらない。GitHub Pages は CSS などを 10 分ほどブラウザに置くので、直した直後の数分は古い見た目が残ることがある。
