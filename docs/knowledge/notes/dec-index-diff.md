---
id: dec-index-diff
type: decision
status: adopted
date: 2026-10-15
title: 推薦の索引を、版ごとの全入れ替えから「変わった行だけ書き、無くなった行だけ消す」差分に変えた（行は版 'live' のまま、中身の変化は rec_meta 'index_rev'）
sources:
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/scripts/deliver_catalogue.py
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/worker.js
  - cloudflare/test/test_recommend_index.py
  - cloudflare/test/test_deliver_catalogue.py
links:
  - answers: q-index-incremental
  - depends_on: d1-writes-undercounted
  - affects: comp-rec-index
---
起案者の指示（2026-10-15）「お願い」（索引の行数を待たずに差分に変える）。
- build_recommend_index.py --hashes-out（と --prev-hashes）: 表ごとに主キー → 行のハッシュ（12 桁）を控え、前回と違う行を INSERT … ON CONFLICT DO UPDATE、前回あって今回無い行を DELETE（鍵の値で選ぶ）。最初に、古い版の作り（ver が 'live' 以外）の行を消す。rec_meta は current='live'（Worker の読み方は変えない）、index_rev=中身のハッシュ、onboarding
- deliver_catalogue.py: data/d1/index-hashes.json を前回分として渡し、書き込みは 2 ×（変えた行＋消した行）＋ rec_stage の分。変わった行が 0 なら "unchanged"。予算を越えるなら "skipped" にしてハッシュを保存しない（次回また同じ差分を送る）。送った分のハッシュは commit のときだけ控えに移す（wrangler が失敗すれば移らない）
- Worker: 推薦の控え（rec_cache）の印に index_rev を足した（screens/recommend.js・worker.js recommendFor）。版の値は 'live' で変わらないため
- 試験: 差分を順に当てた表が、毎回まるごと入れた表と同じ中身になる（減る・戻る・何も変わらない、古い版の掃除）。送らなかった差分のハッシュは控えに残らない
- 引き換え: 入れている途中は、新旧の行が混ざった状態を読むことがある（公演 1 件ずつの違いなので推薦の誤りは小さい）。控え（index-hashes.json）が失われたら、次回は全部を書き直す（ON CONFLICT なので壊れない。消すべき行は残りうる）
- 初回（本番に索引がまだ無い）: 全行を書く。書き込みは約 2 × 行数
