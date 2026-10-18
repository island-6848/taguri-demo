---
id: dec-font-roles
type: decision
status: adopted
date: 2026-10-18
title: 書体の役割を決める。見出しは Zen丸ゴシック、本文・ボタン・入れ口・表・札・数字・公演名は Zen角ゴシック New。指定は web/fonts.css だけに置く
sources:
  - web/fonts.css
  - web/theme.css
  - web/index.html
  - web/app.js
  - cloudflare/public/login.html
  - cloudflare/public/_headers
  - cloudflare/src/worker.js
  - cloudflare/test/gate.test.js
links:
  - supersedes: font-trial
  - affects: dec-design-default-ito
---
起案者の指示（2026-10-18）: Zen角ゴシックを主な書体（本文・ボタン・入力・表・ナビ・バッジ・数値やラベル）、Zen丸ゴシックを差し色の書体（h1/h2 などの見出し、カードやモーダルの見出し、空状態・成功の一言）として使い分けを統一し、CSS・設定・各部品を見直すこと。

決めたこと:
- 書体の指定を新しい web/fonts.css にまとめた（@font-face・`--font-sans`・`--font-maru`・役割ごとの規則）。theme.css からは @font-face とお試しの規則（ボタンを丸ゴシックにしていた）を外した。index.html とログイン・規約・プライバシー・カレンダー連携の頁が fonts.css を読む（前はログインなどの頁は端末の字と明朝の見出しだった）
- 丸ゴシック: h1〜h6（各画面の題字を含む）、畳んだ札の見出し（.card>summary）、アカウントの名前、答え終えたときのお礼、`.empty`
- 角ゴシック: 本文、ボタン・入れ口（判子以外）、`.said`（成功と失敗の両方を出すので UI の文字として扱う）、公演名（半券の h3・評価の行・日記帳でそろえる）、本人が書いた文、カレンダーの月と年表の年（表の見出し・数字）、見出しの中の `small`、おすすめ理由の「人物」「種類」の札
- 決まりの外に残す: ロゴ、評価 ◎○△× の判子と封蝋（「評価はハンコのまま」）、☆ の段階、等幅のコード
- 設定の「規定の文字」（html[data-font="default"]）を選ぶと、これまでの字（明朝の見出し・Taguri Title の題字）に戻る。ボタン・入れ口はどちらでも角ゴシック（前は規定の側でブラウザの既定の字 Arial になっていた）

前の起案者の指示と変わったところ（どれも fonts.css の 1 行で戻せる）:
- ボタンを Zen丸ゴシック Bold にしていた（font-trial、2026-10-18）→ 角ゴシック
- 本人が書いた文を明朝にして画面の字と分けていた（2026-10-15「ユーザーが自分で入力したものはちょっとフォント変えて」）→ 本文の決まりで角ゴシック
- おすすめ理由の札を丸ゴシックにしていた（2026-10-18）→ 札の決まりで角ゴシック

読み込み（確かめたこと・リポジトリのコード）: サイトの CSP は `default-src 'self'`・`style-src 'self'`（cloudflare/public/_headers、worker.js）で、Google Fonts の CSS も字のファイルも外からは読めない。そのため Google Fonts の woff2 を unicode-range ごとにサイトに置いている（角ゴシック 400・700 各 121 ファイル、丸ゴシック 700 の 122 ファイル）。ブラウザは画面に出た文字の範囲のファイルだけを読み、font-display:swap。丸ゴシックは見出しにしか使わないので 700 だけで、500 などは足していない。どのファイルが要るかは文字で決まるので preload はしない（外れたファイルを先に読むと無駄になる）。静的なファイルは Workers の無料枠の数に入らない〔workers-static-assets-free〕。

確かめたこと: ログインの頁と部品を並べた頁で、Chromium の計算後の書体が上のとおり（丸ゴシックは見出しだけ、読み込まれたのは角ゴシック 400・700 と丸ゴシック 700 だけ）。e2e-walk（wrangler dev と Chromium）41 段が通った。

分かっていないこと: 丸ゴシックは 700 しか置いていないので、`.empty` の長めの一言が太く見える。重ければ 500 を足すか、`.empty` を外す。
