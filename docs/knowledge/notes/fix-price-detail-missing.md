---
id: fix-price-detail-missing
type: finding
status: confirmed
date: 2026-10-18
title: 値段の詳細が出ない公演の理由は 3 つ。公演ページに幅しか無い（これからの公演の 15%）、作り置きのカードの無い公演の札が料金を持っていなかった、一覧から拾った行の料金が幅だけ
sources:
  - tools/review/fetch_candidates.py
  - cloudflare/scripts/build_cards.py
  - cloudflare/src/screens/fallback.js
  - cloudflare/src/screens/override.js
  - cloudflare/src/screens/lists.js
  - web/app.js
  - cloudflare/test/cards.test.js
  - cloudflare/test/override.test.js
  - cloudflare/test/test_build_cards.py
---
起案者の質問（2026-10-18）「たまに値段の詳細取得できてない公演があるのはなぜ？」。

カードの料金の明細（app.js compactTickets の .lprice）は、カードの `.when .price` の文（取得した CoRich の「料金（1枚あたり）」の欄）を行に分けて作る。発売日などの行は除き、幅だけの行（「2,750円 ～ 7,150円」）も 1 行として出す。

分かったこと:
1. **公演ページそのものに幅しか書かれていない公演がある（直せない、データの側）。** 手元の data/review/candidates.jsonl（2026-10-18 08:02 の取得）で、これから・上演中の 1,314 件のうち 198 件（15%）は、料金の欄が「8,500円 ～ 12,000円」と【発売日】の行だけで、券種ごとの金額が無い（主催が CoRich に書いていない）。この公演は幅の 1 行だけが出る。同じ集計で、料金の欄に「N円 ～ N円」（同じ額の幅）を含む行は全体（終わった公演を含む）で 1,212 件あり、これが「12000円〜12000円」の出どころ。同じ額の幅は 1 つの額で書くようにした〔dec-rec-card-1018-layout〕
2. **作り置きのカード（rec_card）の無い公演のカードが料金を持っていなかった（直した）。** 興味あり・お気に入り・購入済みの一覧（lists.js）と探す（search.js）は、rec_card の無い公演（一覧 catalogue にだけある開幕リマインドの公演、カードの版がまだ届いていない公演など）を fallback.fallbackTemplate で組む。ここが料金の欄を出しておらず、公演ページの欄があっても「料金 不明」になり、金額の絞り込みの data-yen も無かった。料金の欄と data-yen を入れた
3. **検索の一覧から拾った行（fetch_candidates.listing）の料金は、一覧に出る幅だけ（直した）。** `price` は一覧の `<p class="price">`（幅だけ）で、公演ページの欄（fields の「料金（1枚あたり）」、明細あり）を読んでも `price` を書き換えていなかった。サイトマップから拾った行（stage_row）は欄そのものなので差は無い。いまの取得はすべてサイトマップから（上の 1,314 件の source がすべて sitemap）なので、いま画面に出ている差ではないが、一覧からの取得に戻すと全部が幅だけになる。build_cards.stage_dicts で欄を先に使うようにした
4. ついでに見つけた不具合（直した）: 手で入れた料金（stage_override、override.applyPrice）の金額の幅を読む priceRange が、正規表現の s 旗で【発売日】の行より後ろの文をすべて捨てていた（Python の render_recommend.price_range は改行をまたがない）。発売日の行より後ろに安い券種がある公演では、絞り込みの金額が違っていた。Python と同じにした

分からなかったこと: 本番の D1 の rec_card・catalogue を直接は見ていない（この作業環境から本番には繋がない）。本番のカードで 2・3 にあたる公演が何件あるかは数えていない。手元の取得の控えの数（1）は本番の取得と同じ処理の出力だが、日付がずれていることがある。

確かめたこと: cards.test.js（rec_card の無いカードに料金と data-yen）、override.test.js（発売日の行より後ろの金額も読む）、test_build_cards.py（一覧の幅より公演ページの欄を使う）。
