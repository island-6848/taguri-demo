---
id: dec-venue-pref
type: decision
status: adopted
date: 2026-10-15
title: 一覧（catalogue）の公演の都道府県を、劇場名 → 都道府県の表（venue_pref）で付ける
sources:
  - cloudflare/migrations/0024.sql
  - cloudflare/scripts/deliver_catalogue.py
  - cloudflare/src/screens/fallback.js
  - cloudflare/src/screens/reminder.js
links:
  - depends_on: index-never-delivered
  - affects: comp-d1
---
起案者の指摘（2026-10-15）は次の 3 つ。
- 「場所絞ったら公演カレンダー0件になる」
- 「場所絞ったら開幕リマインド0件になる」
- 「都道府県がわからない作品しかない」

原因は次の 2 つ。
- 推薦の索引が本番に一度も入っておらず（index-never-delivered）、公演はすべて一覧から出ていた。
- 一覧には都道府県が無い。取得した候補（candidates.jsonl）は pref を持っているが、convert_catalogue.public_candidate が metadata に残すのは group・fields・synopsis・words だけだった。

決めたことは次のとおり。
- 一覧の行に pref を足すと、全行の中身が変わって 1 回すべて書き直しになる。それは同じ日の索引の投入と書き込みの予算（WRITE_BUDGET）を取り合う。
- そこで、劇場ごとに 1 行の表 venue_pref（数百行）を別に持ち、deliver_catalogue.py が変わった行だけを書く。
- 同じ劇場名で都道府県が 2 つ以上あるもの（「市民会館」など）は、入れない。
- 画面（fallback.stageInfo・reminder.openingCandidates）は、catalogue.venue で LEFT JOIN して都道府県を埋める。

それでも都道府県が分からない公演の扱いは次のとおり。
- 公演カレンダーは、件数を言う。
- 開幕リマインドは、絞った一覧の下に別にまとめて出す（見逃しを防ぐ画面なので隠さない）。
