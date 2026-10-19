---
id: dec-font-maru-500
type: decision
status: adopted
date: 2026-10-19
title: 公式サイトの押し口と発売の札は Zen丸ゴシック 500（字のファイルを足した）。おすすめ理由の「人物」「形式」は 700 のまま。✕（候補から消す）は取り消せなくてよい
sources:
  - web/fonts.css
  - web/assets/fonts/zen-maru-gothic/
  - cloudflare/test/fonts.test.js
  - cloudflare/test/e2e-walk.js
  - https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@500&display=swap
links:
  - depends_on: dec-font-accent-four-maru
  - depends_on: dec-card-dismiss
---
起案者の答え（2026-10-19）「戻せなくてよい。データ消えるわけじゃないし。ファイル追加して。」

- ✕（候補から消す）の取り消しは作らない。答えは reaction に残っている（interest=3・4）。
- Zen丸ゴシックは 700 しか配っていなかったので、公式サイトの押し口・発売の札が太字に見えていた。Google Fonts の CSS（上の URL、2026-10-19 に取得）が指す 500 の woff2 を、文字の範囲ごとに 122 個（約 2.5 MB）web/assets/fonts/zen-maru-gothic/zmg500-*.woff2 に置き、@font-face を足した。ライセンスは同じ SIL OFL 1.1（OFL-ZenMaruGothic.txt）。
- `.sitebtn`・`.sitelink`・`.sale .pill` は 500、`.rs .net` は 700 のまま。
- 確かめたこと: fonts.test.js（使い分けと 500・700 の @font-face）。e2e で計算された太さが 500 で、500 の字が読み込めること（document.fonts.check）を確かめ、写しを見た。
- 無料枠: 静的なファイルは Workers の要求の数に入らない〔workers-static-assets-free〕。cloudflare/public のファイルが 122 個増える。ブラウザは画面に出た文字の範囲のファイルだけを読む。
