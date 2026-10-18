---
id: search-request-not-read
type: finding
status: confirmed
date: 2026-10-18
title: 「次の更新で探してもらう」の依頼は D1 に控えるだけで、毎日の更新はまだ読んでいない。画面は探すと約束せず、更新の日時は crawl-time.js の 1 つの決まりから出す（#101）
sources:
  - cloudflare/src/crawl-time.js
  - cloudflare/src/screens/search.js
  - cloudflare/src/screens/settings.js
  - tools/taguri/fetch_requests.py
  - tools/taguri/run.py
  - tools/taguri/deploy/github-actions/catalog.yml
  - https://github.com/island-6848/taguri-crawler/blob/17cf15f9bbf7ca2c456de1935e34d2e244cbb83b/.github/workflows/catalog.yml
links:
  - affects: q-search-request-crawl
  - affects: dec-search-worker
---
issue #101（master b8fb7c7 の見直し, 2026-10-18）: 探すの「依頼済み」が「次の更新（毎日4時台）」「見つかれば翌日」とだけ書き、日付も時間帯も無く、依頼した・探して見つからなかった・失敗したを分けていなかった。

確かめたこと（コード）:
- 毎日の更新（taguri-crawler の Catalog）は cron '17 19 * * 0-5' と '17 19 * * 6'（UTC）＝日本時間 4:17。GitHub の定期実行は約 3 時間遅れたことがある〔dec-index-first-load〕
- 依頼を読む段は動いていない: Worker に /api/catalog/search-requests が無く、取得のワークフローは TAGURI_NAMES_URL を渡さないので fetch_requests.py は飛ばす〔q-search-request-crawl〕
- D1 の search_request に残るのは依頼した日（created_at）だけ。探した結果の状態は記録していない

したこと: 更新の時刻を cloudflare/src/crawl-time.js（CRAWL_UTC_HOUR・CRAWL_UTC_MINUTE、遅れの余裕 CRAWL_LATE_HOURS = 6）にだけ書き、「次回は○月○日 4時台（日本時間）」をそこから作る。test/crawl-time.test.js が tools/taguri/deploy/github-actions/catalog.yml の cron と同じかを確かめる。依頼を読む段ができるまで（crawlSearch.requests = false）、画面は「依頼を控えました。探す段はまだ準備中で、まだ探していません」と書く。段ができて true にすると、依頼のあとの更新の回数で「次回は○月○日の更新で探します」と「更新が n 回あったが、まだ公演一覧に無い（見つからなかったのか、順番が来ていないのか、失敗したのかは記録が無いので分からない）」を分けて出す。

分からないこと: 取得の側で依頼を読む段を作るか（Worker に依頼を利用者が分からない形で返す口を足す・取得に URL と合言葉を渡す）は起案者の判断。新しい定期実行や保存は足していない。
