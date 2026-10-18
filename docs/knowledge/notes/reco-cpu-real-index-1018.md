---
id: reco-cpu-real-index-1018
type: finding
status: confirmed
date: 2026-10-18
title: 本番の大きさの索引で、推薦の計算は Workers Free の 10 ms を大きく越えていた（評価 0 件で 24 ms、50 件で 98 ms、300 件で 483 ms）。理由の作品名の絞り込みなど 4 か所を直して 14／24／110 ms になった。評価が 20 件を越える利用者はまだ越える
sources:
  - cloudflare/scripts/measure_worker_replay.mjs
  - cloudflare/scripts/measure_worker.mjs
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/recommend.js
links:
  - affects: fix-cpu-same-production
  - raises: q-reco-cpu-structure
---
#138（2026-10-18）。taguri-crawler の state ブランチ（10-18 04:09Z）の review/candidates.jsonl・recommend2.json・credits/themes.jsonl から build_recommend_index.py で索引を作った（公演 4,769・出演と作り手 32,746 行。本番の報告 4,812・32,827 とほぼ同じ）。
測り方: measure_worker.mjs は SQLite の時間を壁時計で引くので同じ索引で ±50% 揺れた。新しい measure_worker_replay.mjs は D1 の答えを 1 度記録して JSON.parse で返し直し、JavaScript の CPU だけを数える（このマシン: Xeon 2.1 GHz。Cloudflare の機械との比は分からない）。

| 評価の数 | 直す前 | 直した後 | D1 から受け取る JSON（0 件） |
|---:|---:|---:|---|
| 0 | 24 ms | 14 ms | 1.56 MB → 0.46 MB |
| 20 | 49 ms | 17 ms | |
| 50 | 98 ms | 24 ms | |
| 100 | 193 ms | 39 ms | |
| 300 | 483 ms | 110 ms | |

直したこと（screen-v29）:
1. 控えに残す作品名（titles）を、全件 × 残す束 400 で比べていた → 理由に出す鍵の Set を先に作る（評価の多い人ほど効いた。いちばん大きい）
2. 会場の県を rec_stage.entry の JSON をまるごと読んで JSON.parse していた → D1 の json_extract(entry,'$.pref')
3. 控え（rec_cache）に全員分の理由を残していた → 画面が使う人 4 人・種類 3 つだけ（書くときの stringify と読むたびの parse が軽くなる）
4. D1 の行を列名つきの物で受け取っていた → .raw()（列の並びの配列。試験の代わりの SQLite では all() から同じ並びに直す）

まだ越えるところ: 0 件でも約 14 ms で、重いところが 1 つに偏っていない（D1 の答えの読み解き約 3 ms、点数付け約 3 ms、束ね約 1.5 ms、GC 約 1.5 ms…）。評価の数に比例して増えるのは、点数を付ける人の数（0 件で約 50 人、50 件で約 1,000 人、300 件で約 4,400 人）と、その人たちの出演・作り手の行。控えがあれば計算しないが、評価・興味ありを押すたびに控えは捨てられる。
Cloudflare の機械でどれだけ速いかは分からない（このマシンより速い見込みだが、何倍かは確かめていない）。〔q-reco-cpu-structure〕
