---
id: font-trial
type: decision
status: adopted
date: 2026-10-18
title: 文字の形を試す。ボタンは Zen丸ゴシック Bold（手元に置いて配る）、本文はマメロン（ファイル未入手）。これまでの文字を「規定」として残し、設定で戻せる
sources:
  - https://fonts.google.com/specimen/Zen+Maru+Gothic
  - https://github.com/googlefonts/zen-marugothic/blob/main/OFL.txt
  - https://sankoufont.com/japanese-font/mamelon-3/
  - web/theme.css
  - web/app.js
links:
  - raises: q-mamelon-license
---
起案者「各ボタンはこのzen丸ゴシックのBoldを使用して。ほか本文はマメロン。あくまでこれお試しなので、現在のフォントを規定として。もしかしたら変更後に戻すかもしれないので」（2026-10-18）。
- サイトの CSP（default-src 'self'）が外のフォントを読まないので、Zen丸ゴシック Bold は Google Fonts の CSS が指す woff2（文字の範囲ごと 122 ファイル、計約 2 MB）を web/assets/fonts/zen-maru-gothic/ に置き、@font-face を theme.css に入れた。ブラウザは使う文字の範囲の分だけ読む。ライセンスは SIL OFL 1.1（公式リポジトリの OFL.txt を取得元から直接取得して assets/fonts/OFL-ZenMaruGothic.txt に置いた）。静的ファイルは Workers の無料枠で数えない〔workers-static-assets-free〕
- 切り替え: これまでの本文の文字を --font-body-default（規定）として残し、html[data-font="trial"] のときだけボタンを Zen丸ゴシック Bold、本文をマメロンにする。既定はお試し。設定の「文字の形（お試し）」で「規定の文字」に戻せる（この端末に覚える）
- マメロン: 配布元（moji-waku.com）にも sankoufont.com にもこのセッションから接続できず（ネットワークの設定で拒否）、ファイルもライセンスの本文も確かめていない。それまでは、端末に「マメロン」が入っていればそれ、無ければ規定の文字で出る〔q-mamelon-license〕
