---
id: dec-reminder-catalogue-fill
type: decision
status: adopted
date: 2026-10-14
title: 開幕リマインドは、推薦の索引（rec_stage）に無い今週・来週の初日を、毎日入れている公演一覧（catalogue）で補う。/api/health に 14 日以内の初日の件数を出す
sources:
  - cloudflare/src/screens/reminder.js
  - cloudflare/src/worker.js
  - cloudflare/test/lists-screen.test.js
  - https://github.com/island-6848/taguri-crawler/actions/runs/38486187595
links:
  - depends_on: dec-reminder-worker
  - affects: dec-free-tier-only
---
起案者の問い（2026-10-14）「開幕リマインドは推薦がなくても表示されるはずだけど、出ないのなんで？」。
- 画面の組み立ては推薦と関係しない（記録 0 件の新しい利用者でも、rec_stage に今週の初日があれば出ることを手元で確かめた）。材料は rec_stage の今の版だけだった
- rec_stage は deliver_catalogue.py が「書き込みが今日の予算に収まる日だけ」版ごと入れ替える（収まらない日は skipped）。入れ替えが止まると、古い版にはこれからの初日が無くなり、画面が空になる。catalogue は変わった行だけを毎日書くので新しい。どちらも同じ candidates.jsonl から作る
- 本番でどちらだったかは確かめられていない。この環境から本番（app.taguri.workers.dev）にも取得のログの全文にも届かない。2026-10-13 23:45 UTC の取得は、公演一覧を入れる段は成功、過去の公演を入れる段が SQLITE_TOOBIG で失敗（文の大きさを文字で数えていた。バイトで数えるように直し済み）
- 直し: rec_stage に無い stage_id は catalogue（date が今日〜13 日後）から足す。catalogue には都道府県が無いので、県で絞ったときは出ない。読みは date の索引で窓の中の行だけ
- /api/health の catalog に opening_14d（index・catalogue の件数）と index_version を足した（件数だけ。利用者のことは出さない）。次に空になったら、どちらが 0 かで原因が分かる
