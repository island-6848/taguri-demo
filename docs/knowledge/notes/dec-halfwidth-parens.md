---
id: dec-halfwidth-parens
type: decision
status: adopted
date: 2026-10-18
title: 画面に出す全角のカッコ（ ）は、表示する直前に半角の ( ) にそろえる（web/halfwidth.js。どの頁も読む）
sources:
  - web/halfwidth.js
  - cloudflare/src/stage-search.js
  - cloudflare/src/client/import-parse.js
  - cloudflare/test/fonts.test.js
  - cloudflare/test/e2e-walk.js
links:
  - affects: dec-font-accent-five
---
起案者の指示（2026-10-18）「サイト全体で全角のカッコを使ってるところは、半角に変えて」。

調べたこと（リポジトリのコード）: 全角のカッコは cloudflare/src に約 1 万 1600 字、web/app.js に約 5500 字、作り置きのカードを作る Python（tools/review/render_recommend.py など）にも多い。多くはコメントだが、公演名をゆるく比べる正規表現（stage-search.js の CROWN・DROP）や予約メールを読む正規表現（import-parse.js）は、全角と半角の両方に当たるよう全角のカッコを使っている。取得した公演名・会場名（データ）にも全角のカッコがある。ソースを一括で置き換えると読み取りが壊れ、Python 版との突き合わせの試験も大量に直すことになる。

決めたこと:
- web/halfwidth.js を新しく置き、index.html とログイン・規約・プライバシーポリシー・カレンダー連携の頁が読む（cloudflare/public に写す）。画面の文字（テキストの節）と title・aria-label・placeholder・alt の全角のカッコを半角にする。app.js が後から描く画面やログインの案内の文にも、MutationObserver で当てる
- 変えないもの: 文字を書く欄（input・textarea）、本人が書いた感想・メモの表示（.int・.wnt・.nnv）、script・style・code・pre
- サーバーが返す HTML とソースの文言は全角のまま（試験と Python 版の突き合わせを保つ）。表示だけが半角になる
- 確かめたこと: fonts.test.js（どの頁も halfwidth.js を読む）、e2e-walk に「全角のカッコが画面に残らない（主な画面）」の段を足した（おすすめ・開幕リマインド・評価一覧・日記帳・購入済み・設定・アカウント）。49 段すべて OK。ログイン画面とおすすめのカードの写しで半角になっていることを見た

分かっていないこと: 公演名に入っている全角のカッコ（取得したデータ）も表示では半角になる。本人の感想以外で、変えたくない文字があるかは起案者に確かめていない。
