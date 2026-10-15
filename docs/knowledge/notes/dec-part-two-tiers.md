---
id: dec-part-two-tiers
type: decision
status: adopted
date: 2026-10-15
title: 興味ありの配り方の役の格は 2 段だけ（主な役・中心の作り手は 1、アンサンブル・そのほかのスタッフは 0.3）。書かれた順・トメは使わない
sources:
  - cloudflare/src/recommend.js
  - cloudflare/test/recommend-interest.test.js
links:
  - supersedes: dec-part-tiers-tome
  - answers: q-interest-why-unknown
  - raises: q-part-tier-until-when
---
起案者の指摘と決定（2026-10-15）「別に主演が気になるから興味あるわけじゃないからなあ」「なるほど。いつまで使うかは要検証だけどBがいいね」。役の格は「公演の中でどれだけ大きいか」で、「なぜ気になったか」ではない。押した数が少ないうちに、大人数の公演でアンサンブル全員に同じだけ配られるのを抑える弱い歯止めとしてだけ使う。
- 出演: 主な役（役名つき。役名が 1 人も無ければ「アンサンブル」の見出しより前、見出しも無ければ全員）は 1、それ以外は 0.3
- 作り手: 演出・脚本・原作・作曲・構成・音楽・振付・翻訳・潤色・作詞は 1、そのほか（照明・音響・舞台監督など）は 0.3
- 「なぜ」は、何件にも共通するもの・本人の好み・興味なしとの比べ・理由の名前が推し量る（impl-interest-split）
- ◎ の評価やおすすめ候補の点数に役の格を使う案は、同じ理由（◎ も主役が良かったからとは限らない）で取り下げた
