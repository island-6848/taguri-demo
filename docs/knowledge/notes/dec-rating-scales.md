---
id: dec-rating-scales
type: decision
status: adopted
date: 2026-10-14
title: 評価の付け方を設定で選べるようにした（図形：○×・○△×・◎○△×／星：5 段階・0.5 きざみ）
sources:
  - cloudflare/src/screens/grade.js
  - cloudflare/test/grade.test.js
links:
  - depends_on: dec-star-default
  - depends_on: dec-user-scale-range
  - depends_on: eval-douban-scales
  - affects: comp-recommender
---
起案者の指示（2026-10-14）は「オーソドックスなのだけ実用化してほしい。2段階（単純に○×）、3段階（○×△）、と11段階（星0.5きざみ）。星にするか図形にするかは自分で選べるようにして」。

選べる形と、保存の形は次のとおり（設定の「評価の付け方」、app_setting の rating_scale）。
- 図形：○×（"2/2"・"1/2"）、○△×（"3/3"〜"1/3"）、◎○△×（"◎" など。前からの形）。
- 星：5 段階（"n/5"）、0.5 きざみ（"n/11"。★ ＝ (n−1)/2 で、★0〜★5）。
- 設定が無ければ、◎○△× で付けたことのある人は ◎○△×、ほかは星 5 段階。

扱いは次のとおり。
- 形を変えても、付けた評価は付けたときの形のまま残し、その形で表示する。推薦は、同じ段階の評価どうしで本人の中での位置 z を出す（recommend.gradeOf が 2〜11 段階を受け付ける）。変換して混ぜるより同じか良かった（eval-douban-scales）。
- 色・並び・「最上位」・分布の帯は、段階の中の位置 f（最低 0〜最高 1）で決める。最上位は f ＝ 1、真ん中（f ＝ 0.5）はどちらの側にも入れない。
- 0.5 きざみの星は、0 の札と、左右の半分ずつ押せる星 5 つ。押した所までを塗り、半分は左半分だけ塗る。

確かめたこと：grade.test.js と、手元の Worker と Chromium。設定で 0.5 きざみを選んで ★2.5 を付けると、判子が ★2.5 になった。○× に変えて ○ を付けると、前の ★2.5 はそのまま残った。
