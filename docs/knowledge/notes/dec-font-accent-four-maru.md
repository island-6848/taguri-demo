---
id: dec-font-accent-four-maru
type: decision
status: adopted
date: 2026-10-18
title: おすすめ理由の丸枠の「人物」「形式」だけ Zen丸ゴシック 700。さわらびゴシックはほかの 4 か所（公式サイト・発売の状況・お気に入りの名前の札・評価しない）
sources:
  - web/fonts.css
  - web/assets/fonts/zen-maru-gothic/
  - web/assets/fonts/OFL-ZenMaruGothic.txt
  - cloudflare/scripts/sync_public_ui.py
  - cloudflare/test/fonts.test.js
  - cloudflare/test/e2e-walk.js
links:
  - supersedes: dec-font-accent-five
---
起案者の指示（2026-10-18）「おすすめ理由に出てくる丸枠のなかに入ってる『人物』とか『種類』の文字だけ丸ゴシックにして」。ここでの丸ゴシックは Zen丸ゴシック（親の作業の指示で確かめた）。

決めたこと:
- `.rs .net`（おすすめ理由の札）だけを `--font-maru`（"Zen Maru Gothic"）の 700 にした。ほかの 4 か所（`.sitebtn`・`.sale .pill`・`.ftag`・`.rb button.nograde`）はさわらびゴシック（`--font-accent`）のまま
- 字のファイルは、同じ日にいったん外したもの（コミット 4f2c641 の親）から、web/assets/fonts/zen-maru-gothic/*.woff2（122 個、約 2.3 MB、文字の範囲ごと）と OFL-ZenMaruGothic.txt を戻し、@font-face も同じ親の web/fonts.css から戻した。sync_public_ui.py の写す一覧にも戻した。ライセンスは SIL OFL 1.1（ファイルは前に取得元から取ったものと同じ）
- 札の表示名「種類」は「形式」にした〔dec-reason-two-works〕

無料枠: 静的なファイルは Workers の要求の数に入らない〔workers-static-assets-free〕。cloudflare/public のファイルは 405 → 528 個。静的なファイルの数の上限は 1 版あたり 20,000 個と覚えているが、この作業では公式の文書を開いて確かめていない（未確認。確かめるまでは数が 1 桁以上少ないことだけを根拠にする）。ブラウザは画面に出た字（「人物」「形式」「感想」）の範囲のファイルだけを読む。

確かめたこと: test/fonts.test.js（@font-face の書体が 3 つ・指すファイルが全部ある・さわらびゴシックは 4 か所だけ・Zen丸ゴシックは .rs .net だけで 700）。e2e-walk の段「今週のおすすめ: カードの見た目」で、札の計算された字が "Zen Maru Gothic"・太さ 700 であること、写し（PC・電話の幅）で丸い字になっていること。
