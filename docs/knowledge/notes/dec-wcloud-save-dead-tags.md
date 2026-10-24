---
id: dec-wcloud-save-dead-tags
type: decision
status: adopted
date: 2026-10-24
title: ことばの雲に「画像を保存」（PNG）を付ける。これから観られる公演の無いハッシュタグは押せない札にする
sources:
  - web/app.js
  - web/theme.css
  - cloudflare/src/screens/tagged.js
  - cloudflare/src/screens/rowinfo.js
  - cloudflare/test/rowinfo.test.js
links:
  - affects: dec-word-cloud
---
起案者の指示（2026-10-24）「ことばの雲、画像ダウンロードボタンをつけて」「『いま、題材に「〇〇」が付いている、今後の公演はありません。』と出さないで、1件もないならリンク踏んでも飛べないようにしてください」。

- ことばの雲の下に「画像を保存」。雲の SVG の色・字の太さを 1 語ずつ写した複製を 2 倍の大きさで canvas に描き、地の色を敷いて PNG で保存する（taguri-kotoba-no-kumo.png）。ブラウザの中だけで作り、外へは送らない。画面の CSP は img-src が 'self' と data: だけなので、SVG は blob: でなく data: で読む（blob: では読めず、保存が始まらなかった）
- ハッシュタグの一覧（/recommend/tag）へ飛ぶ札のうち、これから観られる公演に 1 件も付いていない語は、押せない札（.dead、点線の枠・薄い字）にする。サーバーが rec_card のいまの版の終わっていない行の題材（手で入れた題材はそちら）から語の集まりを作り（tagged.liveTagKeys）、評価一覧・未評価・日記帳の行のタグに印を付ける。これから観られる公演のカードのタグは、そのカード自身が 1 件目なので必ず押せる
- 一覧の画面の「今後の公演はありません」の文は、URL を直に開いたときのために残す（押して飛ぶ道は無くなる）
- 1 回開くごとに rec_card の終わっていない行を 1 回なめる（いま約 1,350 行）。行にタグがあるときだけ。無料枠（1 日 500 万行）の中
