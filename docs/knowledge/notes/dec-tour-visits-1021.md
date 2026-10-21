---
id: dec-tour-visits-1021
type: decision
status: adopted
date: 2026-10-21
title: まとめた記録は観た回ごとの日付・劇場・開演を残して出し、回数と劇場は回ごとに数え、1 回ずつ分けられるようにする。ツアーを続けて足すときの劇場名・日付の範囲・探すの一覧も直す
sources:
  - cloudflare/src/screens/works.js
  - cloudflare/src/screens/row.js
  - cloudflare/src/screens/diary.js
  - cloudflare/src/screens/account.js
  - cloudflare/src/screens/search.js
  - cloudflare/src/screens/suggest.js
  - cloudflare/src/screens/rate.js
  - cloudflare/src/screens/timetable.js
  - web/app.js
  - web/theme.css
  - cloudflare/test/visits.test.js
links:
  - depends_on: ux-tour-repeat-merge-1021
  - affects: dec-account-rankings-top3
  - affects: fix-past-tour-venue-by-date
  - affects: dec-register-detail-repeat
---
起案者の指示（2026-10-21）: ux-tour-repeat-merge-1021 で挙げた問題を直す（「お願い」）。

- loadWorks（works.js）: まとめた記録の回も、観た日・最後の日・回数・劇場・開演・公演を残す。記録ごとに visits（回の一覧）・seen_times（回数の合計）・seen_last（いちばん後に観た日）を付け、日記帳の並びは seen_last で
- 回数（seenTimes）を、日記帳・評価・感想待ち・眺める（年輪・時間割）・アカウントでそろえる。アカウントの劇場は回ごとにその劇場で数える
- 行（row.js）: 劇場は「劇場A ほか 2 会場」（venueLine。劇場で絞る鍵 venueKey は前のまま）。1 回だけの記録には開演の時刻を添える。まとめた記録には「観た N 回の日付と劇場」を開ける一覧を出し、日記帳ではまとめた回ごとに「分ける」
- 「すべて表示」: まとめた記録を回ごとの行に開く。評価・感想は共有し、直す欄は残した回の行にだけ
- 分ける（merge_work の one）: 1 回だけ分けられる。分けた回に評価が無ければ、まとめていた記録の評価を写す（感想は写さない）。「まとめた N 件を戻す」は「すべて分ける」にし、こちらも評価を写す
- 足すとき: 劇場の欄が、選んでいた公演の劇場の名前のままなら、観た日から結び付け直した劇場の名前で保存し、画面の欄も直す。観劇記録の追加で過去のツアーの公演を選んだら、観た日はツアー全体の期間から選べる。探すの「追加した回」に劇場を添える
- 探すの過去の公演: もう記録した公演も消さずに出し、「記録あり N 回」と添える（ツアーの劇場の選択欄にも）。ボタンは「観た（もう 1 回追加）」
- 観劇記録の追加の候補（記録の行）に、劇場と開演を出す
- Python と比べる試験（screens.test.js）では、サービス版だけの形（開演・まとめた回を足した回数・回の一覧）を外して比べる。形は visits.test.js

無料枠: 読む・書く問い合わせは増やしていない（回の情報は前から読んでいた works の行から作る。探すのツアーの期間は、すでに読んだ行から作る）。分けるときの書き込みは 1 回あたり 2〜3 行。

確かめたこと: npm test（539 件）が通る。ローカルの Worker と Chromium で、旅の芝居を 7 回足して日記帳・探す・アカウント・分ける・追加を通した。回の一覧と「記録あり」を電話の幅で写した。

残したこと: 分けたあと新しく足した回は、また残した記録にまとまる（今は一覧に出るので見える）。まとめた記録を「取り消す」と、まとめた回も一緒に見えなくなる。確認の文はまだそれを知らせない。
