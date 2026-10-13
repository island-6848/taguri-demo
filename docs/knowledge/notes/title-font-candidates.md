---
id: title-font-candidates
type: finding
status: confirmed
date: 2026-10-13
title: 題字の書体の候補（明朝と本文ゴシックの間）── どれも SIL OFL
sources:
  - https://raw.githubusercontent.com/google/fonts/main/ofl/zenkakugothicantique/OFL.txt
  - https://raw.githubusercontent.com/google/fonts/main/ofl/shipporiantiqueb1/OFL.txt
  - https://raw.githubusercontent.com/google/fonts/main/ofl/shipporiantique/OFL.txt
  - https://raw.githubusercontent.com/google/fonts/main/ofl/kleeone/OFL.txt
  - https://raw.githubusercontent.com/google/fonts/main/ofl/zenmarugothic/OFL.txt
  - https://raw.githubusercontent.com/google/fonts/main/ofl/kiwimaru/OFL.txt
  - https://claude.ai/artifact/4o7QY23vNLcZF7wcrqVQg9
links:
  - supports: ofl-japanese-fonts
  - affects: dec-design-adopted
---
起案者の指摘（2026-10-13）「各ページのタイトル題字、フォントが明朝すぎるかも。明朝と、今の本文との間くらいのいい感じのフォントない？」。
google/fonts の ofl/ に下の 6 書体の OFL.txt があることを確かめた（すべて SIL Open Font License 1.1、商用無料）。
- Zen Kaku Gothic Antique ── 本文の Zen Kaku Gothic New と同じ家族で、筆のはらい・ふところが明朝寄りに残る。題字の第一候補にしてデザイン案（キャンバス）に当てた
- Shippori Antique B1 / Shippori Antique ── 明朝の骨格にゴシックの線。いちばん明朝寄り
- Klee One ── 楷書の手書き。やわらかいが画面全体の題字には個性が強い
- Zen Maru Gothic・Kiwi Maru ── 丸み。やさしいが「スタイリッシュに」という方針からは外れる
デザイン案キャンバスに「題字の書体くらべ」の画板を足し、いまの Zen Old Mincho と並べた。
分からないこと: Zen Kaku Gothic Antique を JIS 第 1 水準に絞ったときの重さはまだ測っていない（Zen Kaku Gothic New と同程度の 0.45 MB 前後と見込むが見積もり）。

追記（2026-10-13）: 題字に Zen Kaku Gothic Antique Bold を当てて本番に反映した。各画面の題字に使う字（app.py などの layout()・<h1> から拾った漢字 75 字と、かな・英数・記号）だけに pyftsubset で絞った woff2 が 43,904 バイト。web/assets/fonts/zkga-title.woff2（OFL の本文を OFL-ZenKakuGothicAntique.txt として同じ場所に置いた）を自分のサイトから配る。外部から読み込まない守りは保つ。絞った字に無い字は端末の書体で出る。
