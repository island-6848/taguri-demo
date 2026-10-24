---
id: dec-missed-cancel-btn-base
type: decision
status: adopted
date: 2026-10-24
title: 行けばよかったは 1 件ずつ取り消せる（取り消した題名は hidden で残す）。回答の押し口の下の台を、押し口と同じ幅に収める
sources:
  - cloudflare/migrations/0047.sql
  - cloudflare/src/screens/settings.js
  - web/app.js
  - web/theme.css
  - cloudflare/test/cantgo.test.js
links:
  - affects: comp-cf-worker
---
起案者の指示（2026-10-24）「行けばよかった、各公演取り消せるようにして」「ボタンの下側のあみかけの箇所が枠線よりはみ出ているのを修整して」。同じ時の「サイト内のすべてのボタン、同じの二度クリックしたら選択なしになるようして」は、回答の押し口（興味あり・興味なし・購入済・星）では前から 2 度目で選択を外すので、どのボタンで外れなかったかを起案者に聞いている。

- 行けばよかったの各行（興味ありのまま終わって自動で入った分も、題名で足した分も）に「取り消す」。押すと missed の行を hidden=1 にする（migrations/0047）。行を消すと、自動で入る分は次に開いたときにまた出てしまうため（自動の分は、missed に同じ題名があると出さない）。もう一度足すと hidden=0 に戻る
- 押し口の下のしま模様の台（.btns button::after）が、押し口より左右に 2px ずつはみ出していた。*{box-sizing:border-box} は ::after に効かず、台の幅（押し口の外の枠の端まで）に台自身の枠 2px が外へ足されていた。台も枠込みの寸法にした（高さは前と同じ見え方の 16px）。手元のブラウザーで、押し口と台の幅が同じ（120.27px）になるのを測った
