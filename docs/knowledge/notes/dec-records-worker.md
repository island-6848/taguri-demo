---
id: dec-records-worker
type: decision
status: adopted
date: 2026-10-14
title: 眺めるを Worker に移す。重い 2 枚（人の流れ・相関図）はブラウザで組み立て、地図と題材の偏りは出さない
sources:
  - cloudflare/src/screens/records.js
  - cloudflare/src/screens/charts.js
  - cloudflare/src/screens/compare.js
  - cloudflare/src/screens/storyline.js
  - cloudflare/src/screens/people.js
  - cloudflare/src/screens/figs.js
  - cloudflare/scripts/sync_figs.py
  - web/app.js
links:
  - depends_on: dec-chronicle-worker
  - depends_on: workers-free-cpu-10ms
  - depends_on: dec-free-tier-only
  - affects: comp-native-screens
---
起案者の指示（2026-10-14）「残りの画面も順に移して」の最後の 1 枚。これで元の画面（ORIGINAL_SCREENS）はすべて Worker が答える（cutover.test.js）。
- app._records_body の訪問者の形（owner=False）を移した。年輪（charts.spiral_panel）・よく行く劇場（venue_panel）・人の流れ（storyline.panel）・相関図（people.panel(owner=False)）・比べる相手は何か（compare.pop_note）・作りの型（compare.panel）。どれも手で作った記録で Python と一字一句同じ（charts・compare・storyline・people の test）
- **人の流れと相関図は Worker で組まない。** 重い記録で温まっても 12 ミリ秒・19〜29 ミリ秒、最初の 1 回は 70〜90 ミリ秒かかり、無料の CPU 10 ミリ秒を越える〔storyline-cpu-over-10ms〕〔people-cpu-over-10ms〕。Worker は評価した作品と作り手を `#figs-src` に入れて置き場所 `[data-fig]` だけを返し、ブラウザが /figs/figs.js（同じ組み立てを sync_figs.py が public/figs/ へ写したもの）で埋める。静的ファイルは要求数にも CPU にも数えない〔workers-static-assets-free〕。Chromium の中でも Python と同じ HTML になることを確かめた
- 「比べる」の相手（rec_stage の今の版の件数・初日の範囲・作りの型ごとの公演数・catalogue の件数）は数え直すと数千行読むので、rec_meta 'compare_pop' に版と日付で 1 日 1 回だけ書いて使い回す（読み 2 回・書き 1 日 1 行）
- 作りの型は、Python がクレジットの欄（翻訳・作曲・原作・振付）で見ていたのを、同じ欄から読んだ役職名で見る（公開の版に残っているのは役職と名前の組だけ）
- 出さないもの: 行った劇場の地図（劇場の座標と輪郭が D1 に無い。Python も座標が無ければ出さない）、題材の偏り（題材のまとまりの表が D1 に無く、Python も訪問者の記録では自分の側が 0 件）、LLM の読み（持ち主だけ）
- Python 側の直し: people.timeline が同じ回数の人を集合の順（実行ごとに変わる）で並べていたので、名前の順を足した〔people-tie-order-hash〕
