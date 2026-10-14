---
id: dec-poster-quality
type: decision
status: adopted
date: 2026-10-14
title: ポスターは WebP に縮めてから R2 に入れる（これからの公演は幅 360 px、終わった公演は幅 240 px の粗め）。入れてある分も縮め直す
sources:
  - cloudflare/scripts/deliver_posters.py
  - cloudflare/scripts/free_tier.py
  - cloudflare/test/test_free_tier.py
  - tools/taguri/deploy/github-actions/catalog.yml
links:
  - depends_on: crawler-run-1014
  - answers: q-r2-poster-growth
  - supports: dec-free-tier-only
  - affects: dec-posters-r2
---
起案者の指示（2026-10-14）「ポスターはちょっと画質落としてから入れて。過去の公演はちょっと粗めでもよい」。
- 原因: 取得の機械（GitHub Actions）に Pillow が入っていなかったので、取得のときに幅 360 px に縮める処理（posters.shrink）が何もしておらず、1 枚 約 440 KB のまま R2 に入っていた（crawler-run-1014）
- 直したこと: Catalog のジョブで Pillow を入れる。deliver_posters.py が入れる前に WebP にする ── これからの公演は幅 360 px・画質 72、会期が終わった公演（candidates.jsonl と past/stages.jsonl の会期から判断）は幅 240 px・画質 55。画面のポスターは幅 84〜104 px なので、高精細の画面でも足りる。縮めたほうが大きくなる・読めない画像は元のまま入れる
- 入れてある分: 1 回に 500 枚まで、R2 から取り出して（Class B、取得の側でも数える）縮め、新しい名前（.webp）で入れ直し、古いものを消す（消すのは無料の操作）。D1 の poster 表の名前も入れ替える。約 4 日で 2,000 枚が終わる
- 見込み: 1 枚 約 440 KB → 数十 KB になるので、R2 の 8 GB の上限まで数十年分の余裕になる（実際の大きさは次の実行の表で確かめる）
