---
id: fix-interest-contrast-after-split
type: decision
status: adopted
date: 2026-10-18
title: 興味なしとの比べ（興味ありの件数 /（興味あり＋興味なし））は、1 公演ぶんを割ったあとに掛ける。興味なしの分はその公演の重さから引くだけで、ほかの人・種類には回さない（#109）
sources:
  - https://github.com/island-6848/taguri-demo/issues/109
  - cloudflare/src/recommend.js
  - cloudflare/test/recommend-interest.test.js
links:
  - affects: impl-interest-split
---
issue #109（2026-10-18）: interestShares は比べの倍率を掛けてから人の半分・種類の半分それぞれを合計 1 に割り直していたので、興味なしにも同じ割合でいる人・種類しか無い公演（人 1 人と形式 1 つ、など）では倍率が割り直しで消え、同じ人・形式の興味なしを 20 件足しても値が変わらなかった（issue の Node 実行で 0.1979486637 のまま）。
- 決めたこと: 仕様は〔impl-interest-split〕に書いたとおり「興味なしにもいるものは弱める」ほう。倍率は割り直しのあとに掛ける。そのため、興味なしにもいる人・種類の分はこの公演の重さ（合計 1）から引かれ、合計は 1 未満になる。前は引いた分が興味ありだけの人・種類へ回っていたが、それはしない
- 試験: 人 1・形式 1 の公演で、興味なし 0 → 1 → 20 件と値が下がる（20 件で 1/10 未満）、片方だけ共通する場合は共通する方だけ下がり、もう片方は変わらない、1 キーの公演も下がる
- 画面の控えは screen-v23
- 分からないこと: 実利用で順位が良くなるかは測っていない（〔reco-accuracy-unverified〕）。興味なしを負の証拠（値を下げる）として使うかは別の問い
