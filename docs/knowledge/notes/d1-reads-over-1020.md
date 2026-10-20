---
id: d1-reads-over-1020
type: finding
status: confirmed
date: 2026-10-20
title: 2026-10-20 の D1 の 1 日の読み出しの上限（500 万行）越えは、題名の先頭一致を 21 本の範囲の OR で引いて past_stage を毎回全部読んでいたため。範囲ごとに 1 本を batch で送り、1 回 30,453 → 61 行にした
sources:
  - cloudflare/src/stage-search.js
  - cloudflare/src/screens/suggest.js
  - cloudflare/src/screens/search.js
  - cloudflare/src/recommend.js
  - cloudflare/test/title-leads.test.js
links:
  - depends_on: d1-free-limits
  - depends_on: d1-index-measure-193
  - affects: dec-affil-reco
---
起案者の電話で Error 1101 の画面が出て、Cloudflare から「D1 row read requests are temporarily blocked」（1 日 5,000,000 行。2026-10-21 00:00 UTC に戻る）のメールが届いた。

測り方は d1-index-measure-193 と同じ（wrangler の getPlatformProxy の D1 が返す meta.rows_read）。本番の大きさの索引（rec_stage 5,099・rec_credit 36,039・past_stage 30,414・rec_affil 23,050・rec_gram 14,415 行）と、記録 20 件・興味あり 10 件の利用者 1 人で、画面を 1 回ずつ開いた。

| 文 | 前 → 後（rows_read） |
|---|---|
| 候補（/api/suggest。探す・観劇記録を追加・行けばよかったで、打つたびに呼ぶ） | 30,453 → 61 |
| 探すの画面（過去の公演の題名の分） | 30,414 → 範囲ごとに当たった行だけ |
| おすすめの計算し直し（所属の表を人から引く文が 3 回） | 83,927 → 15,366 |

- **原因:** 2026-10-19 に、題名の頭の語（「舞台」「ミュージカル」など 19 語）を付けた形でも引くようにした（titlePrefixes）。引き方は `(tkey>=? AND tkey<?) OR …` を 21 本並べた 1 つの文で、D1 は tkey の索引を使わずに past_stage を全部読んでいた。候補は打つたびに呼ぶので、約 165 回で 500 万行に届く。前日に入れた変更で、当日に越えた
- **直し方:** 範囲ごとに 1 本の文にして（それぞれ tkey の索引で読む）、1 回の batch でまとめて送る（stage-search.pastByPrefix）。UNION ALL で 1 つにまとめる案は捨てた。D1 は compound SELECT の項の数に上限があり（backup_d1.py で当たった）、頭の語を足すと届きうる
- **試験:** 候補と探すの画面で過去の公演を引く文が、どれも `USING INDEX past_stage_tkey` で読むことを EXPLAIN QUERY PLAN で確かめる（title-leads.test.js）。直す前のコードでは落ちる
- **所属の表（dec-affil-reco）:** `ver=? AND person IN (…)` は主キー（ver, affil, …）が選ばれ、その版の所属の行を全部読んでいた。人の索引（0041 の rec_affil_person）を INDEXED BY で名指しした。本番の所属の表はまだ約 860 行で、10-20 の越えの原因ではないが、全部入ると計算し直しのたびに 69,000 行になる
- **残り（今回は直さない）:** 探すの画面の、これからの公演を全部読む文（rec_stage と rec_card、1 回 約 10,000 行）、眺める（約 6,000 行）、おすすめの計算し直しの劇団名の instr（約 5,000 行）。どれも打つたびではなく画面を開いたときだけで、1 日 500 万行には 500 回以上かかる。急ぎの越えを止めるのが先と判断した
