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
