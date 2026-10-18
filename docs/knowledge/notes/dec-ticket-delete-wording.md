---
id: dec-ticket-delete-wording
type: decision
status: adopted
date: 2026-10-18
title: 「観劇日を追加する」の入れてある日の消す口を「この日時を削除」にし、直し方と、消したあとに言う文（data-done）をサーバーの HTML に持たせる
sources:
  - cloudflare/src/screens/calendar.js
  - tools/taguri/stage_calendar.py
  - cloudflare/test/calendar.test.js
  - cloudflare/src/screens/lists.js
  - https://github.com/island-6848/taguri-demo/issues/100
links:
  - affects: dec-calendar-worker
---
issue #100（master b8fb7c7 の見直し、2026-10-18）: 公演カレンダーの「観劇日を追加する」の中の「入れてある日」で、確定前の券は「違う」、確定した券は「取り消す」を押すと data-del で消していた。消えるのが行く日だけなのか、興味あり・購入済みの登録まで消えるのかが分からなかった。

確かめたこと（リポジトリのコード）: `/api/ticket` の action=del（cloudflare/src/screens/lists.js の ticketAction）は ticket の 1 行（利用者・会場・日付・時刻）を消すだけで、購入済み・興味あり・お気に入りの記録には触らない。日時を書き換える口は無い（直すには消して入れ直す）。

決めたこと:
- 押し口の字は確定前・確定後とも「この日時を削除」（確定前は「確定」を先に出すのはそのまま）。title に「この行く日（10/15 13:00）だけを消します。購入済み・興味あり・お気に入りの登録は消えません」
- 「入れてある日」の見出しに直し方を添える:「日時を直すときは『この日時を削除』で消して、下の『行く日』から入れ直してください」
- 押し口に `data-done`「10/15 13:00 の行く日を削除しました。公演の登録（購入済み・興味あり・お気に入り）は変わりません。入れてある日は、あと N 件です」（最後の 1 つなら「もうありません」）を持たせる
- Worker（calendar.js）と Python（stage_calendar.py）を同じ形にした（calendar.test.js が突き合わせる）

残っていること: 消したあとの一言は画面の JS（web/app.js と stage_calendar.JS → cloudflare/src/screens/calendar_js.js）が出していて、いまは「取り消しました」と書いたあと 0.5 秒で読み直す。`b.dataset.done` を読んで出し、読めるだけの間を置くように JS を直す必要がある（この変更では JS に触っていない）。
