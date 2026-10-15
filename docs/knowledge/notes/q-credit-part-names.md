---
id: q-credit-part-names
type: question
status: open
date: 2026-10-15
title: 出演欄の「役名：名前」「アンサンブル：名前」を、役名ごと 1 人の名前として読んでしまう（credits の parseCredits・measure_nets._names）。直すか
sources:
  - cloudflare/src/screens/credits.js
  - tools/review/measure_nets.py
links:
  - affects: impl-interest-split
  - affects: impl-person-ordinal-v3
---
2026-10-15、役柄の重さを入れるときに手元で試して分かった。parseCredits({出演: 'ジャン・バルジャン：福井晶一／吉原光夫'}) が ['出演', 'ジャン・バルジャン:福井晶一'] と ['出演', '吉原光夫'] を返す。「アンサンブル：田中」も 'アンサンブル:田中' になる。こう書く公演では、その人の別の公演と名前が合わず、推薦にも理由にも効かない。Python（measure_nets）と Worker（credits.js）は一致試験で同じ結果を保っているので、直すなら両方と試験を同時に直す。実際の公演一覧でこの書き方がどれだけあるかは数えていない。
