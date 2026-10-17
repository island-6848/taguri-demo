---
id: dec-recommend-filter-tiers
type: decision
status: adopted
date: 2026-10-17
title: おすすめ画面の道具を「おすすめの選び方」（効かせ方・出さない語）と「表示の絞り込み」（場所・料金）の 2 段に分け、「おすすめに出てこない公演を探す」を外した
sources:
  - cloudflare/src/screens/recommend.js
  - web/app.js
  - web/theme.css
  - cloudflare/test/search-uncarded.test.js
links:
  - supersedes: impl-recommend-find
  - affects: dec-page-pref-filter
---
起案者「今週のおすすめで『場所』『料金』は単なる結果のしぼりこみ、『効かせ方』『出さない語』はおすすめに直接関係する要素、でそれら４つを並列並べるのはおかしい。『おすすめに出てこない公演を探す』は消して」（2026-10-17）。
- それまで: 4 つの札（場所・効かせ方・出さない語・料金）を 1 列に同じ扱いで並べていた（filterRow が .fil2 の中の details を札にする）
- いま: 見出し付きの 2 段
  - 「おすすめの選び方 ── 好みの計算そのものを変えます（どの公演が選ばれるかが変わります）」: 効かせ方・出さない語（.fil2.tune）
  - 「表示の絞り込み ── 選ばれたおすすめのうち、見る分だけに絞ります（順位は変わりません）」: 場所・料金（.fil2.narrow。料金の札は app.js priceFilter がこの段に足す）
  - 選び方を上、絞り込みをカードのすぐ上に置いた（計算 → 絞り込み → 結果、の順）
- filterRow は .fil2 ごとに札を作り、札の数で列を決める（2 段とも 2 列）
- 「おすすめに出てこない公演を探す」の欄を外した（recommend.findBox と test/recommend-find.test.js を削除）。ワンポイント・答え終えたときの案内・興味ありの空の一覧の文は「探す」画面へのリンクに替えた。/recommend?find= は無視する
- ブラウザ（幅 390・1100）で 2 段と札を確かめた
