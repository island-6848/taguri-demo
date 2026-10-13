---
id: render-ui-server-rendered
type: finding
status: confirmed
date: 2026-10-13
title: 元の画面は Python が HTML を組んで JSON で返している（約 2.5 万行）
sources:
  - tools/taguri/serve.py
  - tools/taguri/app.py
  - web/app.js
links:
  - affects: comp-public-server
---
/api/screen/* が {ok,title,body_html} を返し、web/app.js が innerHTML で差し込む。移すには保存先だけでなく画面を組む部分の書き直しが要る。公開版の利用者にはメール取り込みが無いので、記録は手で足した行だけになり、移す範囲は絞れる。
