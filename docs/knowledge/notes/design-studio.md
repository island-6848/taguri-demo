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
「保存する」で artifact の db の design/current に、「残す」で presets/<id> に入る。Claude は ArtifactData で design/current を読み、web/style.css の変数と画面の文言に反映する。
2026-10-13 反映（起案者の指示「調整室の内容を反映して」）: design/current（保存 2026-10-13T14:44:20Z）を web/design.json に写し、web/theme.css を style.css の後に重ねた（cloudflare/public にも同期）。反映したのは、色の語（--plane・--surf・--ink・--ink2・--mute・--ring・--acc・--curtain）、書体の並び、半券の角と影、ゆとり、回答 3 つの切り取り札と並び（興味あり・興味なし・持っている、CSS の order で並べ替え、HTML は変えない）、評価の判子、理由の見出し「おすすめ理由」、日記帳の見出し「日記帳」。暗い表示は元のまま。
反映していないもの（web/design.json の not_applied）: タブを上に 5 つ並べる作り替え（いまは左の縦帯に 14 項目）、半券に糸を通す飾り、評価の問いかけの行、外部の書体（下の q-webfont-local）。
同じ日の起案者の指摘「白地と半券の色一緒すぎる。背景はうっすいグレー」を受けて、調整室に「地（画面の背景）」を「紙（半券・記録）」と分けて足し、地を #f0f0ee にした（design/current にも足した）。
