---
id: design-studio
type: component
status: current
date: 2026-10-13
title: 見た目の調整室（起案者が色・文字・ボタン・配置・文言を決めて保存し、Claude が読み取って実際の画面に反映する）
sources:
  - https://claude.ai/artifact/NH7Z8DGfij161BfkjEGg3q
links:
  - depends_on: dec-design-default-ito
  - affects: dec-theme-user-choice
---
起案者の依頼（2026-10-13）「全体のデザインを私が調整できるサイトつくってくれる？カラパレとかボタンの形とか位置とか文言とかの指定できるような」。
調整室は、色（地・文字・補足・線・差し色・差し色の上の文字、読みやすさの比も出す）、文字（題名と本文の書体・大きさ）、ボタン（回答 3 つの形: 切り取り札・別々の枠・丸い札・文字だけ／評価の形: 判子・一列・四角／選んだときの塗り・角の丸み・枠の太さ）、配置（タブを上か下か・半券の耳の左右・糸の有無・理由の位置・回答の並び・ゆとり）、文言（タブ・見出し・ボタンなど 16 か所）を変えると、今週のおすすめ・日記帳・メニューの見本が変わる。既定はたぐる糸（dec-design-default-ito）。
「保存する」で artifact の db の design/current に、「残す」で presets/<id> に入る。Claude は ArtifactData で design/current を読み、web/style.css の変数と画面の文言に反映する（まだ反映の手順は作っていない）。
