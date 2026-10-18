---
id: fix-interest-note-names
type: decision
status: adopted
date: 2026-10-18
title: 興味ありの「なぜ気になったか」に名前があっても、打ち消し・苦手の語がある区切り、「○○より」「○○と比べ」の名前、長い名前の一部は多めに配らない（分からないときは等分のまま）。LLM は使わない（#111）
sources:
  - https://github.com/island-6848/taguri-demo/issues/111
  - cloudflare/src/recommend.js
  - cloudflare/test/recommend-interest.test.js
links:
  - affects: impl-interest-split
  - depends_on: q-interest-why-unknown
---
issue #111（2026-10-18）: interestShares は note.includes(名前) だけで、その人へ 5 倍（INTEREST_NOTE_BOOST）配っていた。「俳優Aが理由ではない」でも A／B が 0.5／0.5 → 0.833／0.167 に変わり、比べるため・苦手と書くための名前が好みとして増えた。
- 直したこと（recommend.noteNames）: 文を句点・読点・逆接（けど・けれど・のに・ものの・しかし・でも・だが）で区切り、名前のある区切りに打ち消し・苦手の語（ない・無い・なく・ません・ではな・じゃな・苦手・嫌・きらい・微妙・いまいち・以外・抜き）が無く、名前のすぐ後ろが「より」「と比べ」「に比べ」「と比較」（敬称を挟んでも）でないときだけ 5 倍にする。長い名前の所は伏せてから短い名前を探す（「山田花子」の中の「山田」は数えない）。1 文字の名前は前と同じく数えない
- 方針: 確かな肯定だけを使い、否定・不明なら補正しない（issue の完了条件）。取りこぼし（「見たことないから気になる」「少ない出番でも」も打ち消しとして等分になる）は、多めに配らないだけで害は小さい側に倒した
- 画面の控えは screen-v25
- 分からないこと: 実際のメモでどれだけ当たるか（取りこぼし・誤り）は測っていない。明示的に人を選ばせる画面にするかは起案者の判断（〔q-interest-why-unknown〕）
