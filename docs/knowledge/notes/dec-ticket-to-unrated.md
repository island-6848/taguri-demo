---
id: dec-ticket-to-unrated
type: decision
status: adopted
date: 2026-10-18
title: 行く日（開演の時刻）が過ぎた券は、その回の記録（未評価）を自動で作る。消した回は券も消して作り直さない
sources:
  - cloudflare/src/screens/lists.js
  - cloudflare/src/screens/works.js
  - cloudflare/test/lists-screen.test.js
links:
  - answers: q-ticket-to-rating
  - affects: dec-native-cutover-now
---
起案者の指示（2026-10-18）「購入済みの公演で、行く日に過去の日を入れても『評価する記録』にするために、行く日が過ぎたら自動で未評価に入れるようにして。」で〔q-ticket-to-rating〕に答えが出た。

決めたこと（cloudflare/src/screens/lists.js の promoteTickets）:
- 行く日が今日より前、または今日で開演の時刻を過ぎた（日本時間）券は、その回の記録（works、評価なし）を作る。千穐楽を待たない。前は購入済みの公演は千穐楽を過ぎるまで何も起きなかった
- 同じ公演・同じ日の記録がもうあれば作らない（どちらかに時刻が無いか、時刻が同じとき）。同じ日の昼と夜は別の記録（work_key に `#時刻`）
- 観る前のメモは記録の「動機」に持っていく
- 未評価・評価一覧・お気に入り・開幕リマインドを開いたときに動く（その人の券と記録を数行読むだけで、書くのは新しい回の分だけ。無料枠の読み書きはほぼ増えない）
- 行かなかった回は、日記帳で外す → 完全に取り消す（または 30 日後の自動削除）と、works.deleteWork がその回の券も消すので、作り直さない

確かめたこと: test/lists-screen.test.js（会期途中の回・同じ日の 2 回・何度開いても増えない・消した回が戻らない・後の回も過ぎたら出る）、JS 382 件・Python 128 件・ローカル workerd のスモークが通った。

分かっていないこと: 外しただけ（取り消し待ちの 30 日）の間は記録が残るので作り直さないが、「元に戻す」をせずに券だけ残したい人がいるかは分からない。
