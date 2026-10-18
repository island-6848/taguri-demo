---
id: q-search-request-crawl
type: question
status: open
date: 2026-10-14
title: 本番の「次の更新で探してもらう」依頼（D1 の search_request）を、取得が読んで CoRich で探す段をどう作るか
links:
  - raises: dec-search-worker
  - affects: dec-free-tier-only
---
Worker の「探す」と「手で足す」は、見つからない題名を D1 の search_request に控える（dec-search-worker）。Python 版は aggregate_search_requests で全利用者の依頼を利用者が分からない形にまとめ、毎日の更新で探していた。取得（taguri-crawler の Catalog）が D1 からこの集計を読む段がまだ無い。
決めること: 読む頻度と件数の上限（Actions の分数・CoRich への 1 秒 1 回の作法）、見つかった公演を picked.jsonl に入れて翌日のカードに載せる流れ、古い依頼を消す期限。

追記（2026-10-18, issue #101）: まだ答えは出ていない。コードで確かめた: Worker に /api/catalog/search-requests は無く（Python の serve.py にだけある）、taguri-crawler の .github/workflows/catalog.yml は TAGURI_NAMES_URL・TAGURI_NAMES_TOKEN を渡さないので、run.py の fetch_requests.py は「依頼を読む先が未設定なので飛ばす」。D1 の search_request は依頼した日（created_at）しか持たず、探したか・見つからなかったか・失敗したかの記録も無い。画面は〔search-request-not-read〕のとおり、この段ができるまで「次回の更新で探します」と約束しない。
