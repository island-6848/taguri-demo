---
id: dec-calendar-import-limits
type: decision
status: adopted
date: 2026-10-18
title: Google カレンダーの取り込みは、5 年前から今日までの予定を 5,000 件まで、新しい順に、カレンダーごとに公平に分けて読む。上限で落とした分は画面で知らせる。iCal の TZID は Intl.DateTimeFormat で日本時間にそろえる
sources:
  - cloudflare/src/client/calendar-google.js
  - cloudflare/src/client/import-parse.js
links:
  - affects: q-review-1015
---
issue #78〜#82・#89・#90・#98・#99（2026-10-18 の点検、master b8fb7c7）への対応。

- 前は古い順に集めて 5,000 件で止まり、2 つ目以降のカレンダーを読まなかった（#82）。いまは全カレンダーを読み、1 ページ（2,500 件）を越える重いカレンダーだけ今日から約半年ずつさかのぼって読み直す。合計が 5,000 件を越えたら各カレンダーに新しい分から公平に割り当て、小さいカレンダーが使わない分をほかに回す。落としたら `capped` と `since`（どの日より前を落としたか）を返し、画面に出す
- 呼び出しはふつう 1 カレンダー 1 回、重い試験でも 15 回未満。利用者の Google の枠で動き、たぐりの無料枠は使わない
- TZID は Intl.DateTimeFormat（ブラウザーと Workers の両方にある）で日本時間に直す。分からない時間帯は書かれた時刻のまま `tz_unknown` を付けて画面で知らせる（黙って日本時間にしない）。VTIMEZONE だけで定義された独自の時間帯は未対応
- 送る本文は件数（20）ではなく UTF-8 のバイト数（8,192）で分ける（#89）。1 件で越えるものは名前を出す
- 実在しない日付・時刻は、取り込みの経路でも /api/record と同じ規則（isDay・isTime、import-parse.js）で落とし、どの項目かを返す（#90）
- 繰り返し予定の個別の変更（RECURRENCE-ID）は、前と同じく繰り返しとして読み飛ばす
