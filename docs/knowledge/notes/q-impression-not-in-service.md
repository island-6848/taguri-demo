---
id: q-impression-not-in-service
type: question
status: open
date: 2026-10-18
title: 感想の本文による好みの補正（impression preferences）は、サービス版の推薦（Worker）に届いていない。つなぐか、未対応と書くか（#104、起案者の判断）
sources:
  - https://github.com/island-6848/taguri-demo/issues/104
  - cloudflare/src/screens/recommend.js
  - docs/impression-preferences.md
  - tools/taguri/app.py
links:
  - affects: dec-reco-on-worker
---
コードで確かめたこと（2026-10-18）: ratedWorks が scoreFromIndex に渡すのは verdict・aspects・people・時刻だけで、note_impression を渡さない。画面の実装の冒頭にも「the impression re-ranking」は未移植と書いてある。オーナーの画面（tools/taguri/app.py の _apply_impression_preferences → impression_preferences.rerank）だけが補正する。README・docs/impression-preferences.md の説明はサービス版には当てはまらない。
- 案 1: Worker に移す（感想の語 → 題材の語 → 候補の #題材 で並べ直す）。本文は外へ送らない方針のまま D1 の中だけで済むが、毎回の計算に感想の本文の読み出しと語の照合が加わる（CPU 10 ms の上限に注意、〔q-reco-screen-cpu-20-ratings〕）
- 案 2: サービス版では未対応と README・画面の説明に書く（いちばん小さい）
- 推し: まず案 2 で説明を正し、案 1 は「順位が変わる」だけでなく「当たりが良くなる」ことを手元の再生（H1）で確かめてから
