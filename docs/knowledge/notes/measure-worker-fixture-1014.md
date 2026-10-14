---
id: measure-worker-fixture-1014
type: finding
status: confirmed
date: 2026-10-14
title: 試験用の小さな索引（84 公演）でも、Worker のおすすめの計算は CPU 中央値 2〜9 ms・最も遅い回 50 ms。無料の 10 ms に近いので、本物の索引で測る
sources:
  - cloudflare/scripts/measure_worker.mjs
  - tools/taguri/deploy/github-actions/catalog.yml
links:
  - affects: q-workers-cpu-real
  - affects: q-real-catalog-stats
  - depends_on: dec-free-tier-only
---
measure_worker.mjs: 索引を手元の SQLite に入れ、評価 0〜300 件の作り物の利用者（星 1〜5 を乱数、固定の種）にお気に入り 2 件を付けて、Worker と同じ recommendFor を呼ぶ。SQLite の中の時間を引いた JavaScript の CPU 時間（Workers では D1 を待つ時間は CPU に数えない）と、読んだ行数を出す。最初の 1 人は V8 の翻訳を数えないための空回し。
試験用の索引（parity_fixture の最大、84 公演・795 クレジット）で、この作業環境（共有の機械）では 9 回の中央値 2.4〜9.0 ms、最も遅い回 5〜51 ms（GC の止まりを含む）、読む行数 846〜1,360。
読み方: 本物の索引は公演が桁違いに多いので、無料の 10 ms を越える見込みが高い。ただし、おすすめは利用者ごと・日ごとに rec_cache に置くので、計算は 1 日 1 回と評価を付けた直後だけ。越えた回は Workers が 1102 のエラーを返す。本物の数字は毎日の取得のジョブ（Measure the Worker's recommendation …）のログで見る。越えるなら、重い部分を取得の側（夜のバッチ）に移す・候補を絞るなどを考える（有料にはしない）。
