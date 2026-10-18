---
id: dec-font-action-maru
type: decision
status: adopted
date: 2026-10-18
title: 書体は基本すべて Zen角ゴシック New、利用者が起こすアクション（ボタン・ボタン形のリンク・タブ・選ぶ欄）だけ Zen丸ゴシック
sources:
  - web/fonts.css
  - web/app.js
  - web/theme.css
links:
  - supersedes: dec-font-roles
---
起案者の指示（2026-10-18）「基本的に全てzen角ゴシックで、ユーザが起こすアクションだけ丸ゴシックにしたい」。同じ日の〔dec-font-roles〕（見出しを丸ゴシック、ボタンを角ゴシック）を置き換える。

決めたこと（web/fonts.css）:
- 角ゴシック: 本文・見出し（各画面の題字も）・公演名・表・札・数字・文字を書く欄・本人が書いた文・状態の一言・空のときの一言・ふつうのリンク
- 丸ゴシック（700）: button、select、type=button/submit/reset、role="button"、ボタンの形のリンク（a.btn・.sitebtn・.loadbtn）、絞り込みのタブ（.ftab）。押し口ごとに `font:inherit` と書いた所が多いので `!important`
- 外すもの: 評価の判子（.rb の中・.stamp。押せる判子も判子の字）、制覇マップの SVG のマス（中の字は地図のラベル）、ロゴ、封蝋、☆、等幅のコード
- ふつうのリンクは移動で、アクションではないとして角ゴシックにした。畳んだ欄の見出し（summary）も角ゴシック
- 設定の「規定の文字」はこれまでの字に戻る（ボタン・入れ口は規定の側でも角ゴシック）

確かめたこと: 部品を並べた頁とログインの頁で、Chromium の計算後の書体が上のとおり（見出し・本文・入れ口は角ゴシック、ボタン・タブ・select・送信は丸ゴシック、判子は明朝のまま）。

分かっていないこと: リンクや summary も「押すもの」として丸ゴシックにしたいかは起案者に確かめていない。
