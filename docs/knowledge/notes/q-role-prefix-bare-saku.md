---
id: q-role-prefix-bare-saku
type: question
status: open
date: 2026-10-16
title: クレジットの行頭の「作」「演出」を区切りなしでも剥がすので、「作間」「作田」のような本物の姓も 1 字欠けるのではないか
sources:
  - tools/review/measure_nets.py
  - cloudflare/src/screens/credits.js
  - cloudflare/test/credits.test.js
links:
  - affects: dec-credit-part-names
---
`_ROLE_PREFIX`（Python）と `ROLE_PREFIX`（Worker）は `^(脚色|翻訳|上演台本|原案|原作|作|演出|振付|訳)[\s　]*` で、後ろに空白が無くても剥がす。そのため「作り手14」→「り手14」、「演出家A」→「家A」になる（review-tests-stale-1016 で見つけた）。仮の名前だけの話ではなく、「作間」「作田」のように「作」で始まる姓の出演者も、名簿で 1 字欠けた別の人になるはず。一致試験（credits.test.js）は Python と Worker が同じに読むことしか見ないので、両方が同じに欠けても通る（例の「作：作家A」も「家A」と読んでいる）。

分からないこと: 実データで、区切りなしの「作山田太郎」のような書き方（剥がすのが正しいもの）と、「作」で始まる人名（剥がしてはいけないもの）がそれぞれ何件あるか。この作業環境には取得したクレジットが無いので数えていない。数えてから、区切り（空白・コロン・中黒）がある時だけ剥がすかを、Python と Worker で同時に決める。それまではコードを変えない。
