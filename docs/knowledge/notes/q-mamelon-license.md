---
id: q-mamelon-license
type: question
status: open
date: 2026-10-18
title: マメロンを Web フォントとしてサイトに置いて配ってよいか（ライセンス）と、ファイルをどこから取るか
sources:
  - https://moji-waku.com/mamelon/
  - https://free-font.blog.jp/archives/8470502.html
links:
  - affects: font-trial
---
検索結果の引用でしか見ていない（unverified）: 配布元は「もじワク研究」、商用利用可とされる。2020 年に「マメロン Hi Regular」として作り直され、旧版は公開を終える予定とされていた。派生の「キウイ丸」は SIL OFL。
- 確かめること: 公式の配布ページ（moji-waku.com/mamelon/）の利用規約で、Web フォントとしての埋め込み・サーバーに置いての配信が許されているか。許されていれば、ファイルを web/assets/fonts/mamelon/ に置き、theme.css に @font-face を足す（woff2 にして、必要なら文字を絞る）
- このセッションからは配布元に接続できない。起案者がファイルを置くか、環境の許可するドメインに moji-waku.com を足す
- 許されていなければ、近い形の「キウイ丸」（OFL）を候補にする
