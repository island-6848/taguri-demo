---
id: font-trial
type: decision
status: superseded
date: 2026-10-18
title: 文字の形を試す。ボタンは Zen丸ゴシック Bold、本文は Zen角ゴシック New（どちらもサイトに置いて配る）。これまでの文字を「規定」として残し、設定で戻せる
sources:
  - https://fonts.google.com/specimen/Zen+Maru+Gothic
  - https://github.com/googlefonts/zen-marugothic/blob/main/OFL.txt
  - https://fonts.google.com/specimen/Zen+Kaku+Gothic+New
  - https://github.com/googlefonts/zen-kakugothic/blob/main/OFL.txt
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

追記（2026-10-18）: 起案者がマメロンの配布ファイル（mamelon_hireg.zip: Mamelon-3／3.5／4／5-Hi-Regular.otf と readme.txt）を渡した。
- readme.txt（配布元そのもの・confirmed）: 「フリーフォント（商用可）」「WEBフォントで使用する際はファイル名が長いので任意のものに変えてただいて構いません」「無断でのデータのアップロード・データの改変、改造・ニ次配布は、お控えいただくようご協力のほどお願い致します」。詳しい規約は https://moji-waku.com/mj_work_license/（このセッションから接続できず未読）
- 起案者の回答: 「R2 から配る」「太さは 3」。公開リポジトリ（GitHub）に入れると誰でも取れる＝二次配布に当たるおそれがあるため、リポジトリには入れず、変換もせず、名前だけ mamelon-3-hi-regular.otf に変えて R2 に置き、Worker の /img/（ログインした人だけ・1 週間ブラウザに残る）で配る。theme.css の @font-face がそれを読む。ログインの画面と、ファイルを入れるまでは規定の文字
- R2 に入れる: お手元で `python3 tools/admin/admin.py font Mamelon-3-Hi-Regular.otf`（CLOUDFLARE_ACCOUNT_ID・CLOUDFLARE_API_TOKEN が要る。R2 の上限の前に止まる）。約 3 MB で、R2 の保存 8 GB の上限と比べて小さい。読み出しは 1 人 1 週間に 1 回ほど
- 手元のファイルを読ませたブラウザで、本文がマメロン・ボタンが Zen丸ゴシックになることを確かめた

追記（2026-10-18、その 2）: 起案者「（Zen Kaku Gothic New）本文これにして」。本文のお試しをマメロンから Zen角ゴシック New に変えた。
- Google Fonts の Regular（400）と Bold（700）を文字の範囲ごとの woff2（242 ファイル、計約 2.7 MB）で web/assets/fonts/zen-kaku-gothic-new/ に置き、@font-face を theme.css に入れた。ライセンスは SIL OFL 1.1（公式リポジトリの OFL.txt を取得元から取って assets/fonts/OFL-ZenKakuGothicNew.txt に置いた）
- これまでの「規定」の文字の指定にも Zen Kaku Gothic New の名前はあったが、ファイルを置いていなかったので、端末に入っていなければヒラギノ・游ゴシックなどで出ていた。お試し（既定）ではサイトのファイルで必ず Zen角ゴシック New になる
- マメロンの @font-face は外した（R2 には入れていない）。admin.py の font（R2 に入れる命令）は残っているが、使わない
- ブラウザで、本文が Zen角ゴシック New・ボタンが Zen丸ゴシックで出ることを確かめた
