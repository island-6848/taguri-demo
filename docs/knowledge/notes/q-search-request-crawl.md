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

追記（2026-10-21、起案者の指示「Issue #101：検索リクエストが実際に処理される仕組みを検討する」）: 案を書いた。まだ作っていない（起案者が決める）。
- **前提の変化:** 〔dec-crawl-tiers〕で、CoRich に新しく載った公演は毎日サイトマップの差分で読むようになった。CoRich の検索ページは GitHub Actions からは断られる〔corich-search-waf-403〕。だから「頼まれた題名を探しに行く」より「毎日取った公演の中に、頼まれた題名があるかを照らす」ほうが、追加の通信も検索もいらない。
- **案:**
  1. 取得の毎日の更新の最後（D1 に入れる段のあと）で、D1 から依頼を題名ごとにまとめて読む（`SELECT qkey, query, count(*) FROM search_request GROUP BY qkey LIMIT 200`）。利用者は分からない形。
  2. 手元の候補・カレンダー・過去の公演の題名の鍵（title_key）と、頭の一致・含む一致で照らす。
  3. 結果を新しい表 `search_request_status(qkey, status, checked_at, found)` に書く。status は 照らした・見つかった・まだ。
  4. 探すの画面は、依頼の行に「次回は○月○日 4 時台」のほか、状態（受け付けた・照らしたが見つからない・見つかった）を出す。見つかったときは、その公演へのリンクを出す。
  5. 古い依頼（90 日）は消す。
- **費用の見込み:**
  - Actions は数秒（通信なし）。
  - D1 の読み出しは依頼の表の行数（利用者 × 最大 MAX_REQUESTS）で、今は数百行。書き込みは 1 日 最大 200 行で、取得の 8 万行の中。
  - 作るもの: migration 1 つ、Worker の探すの画面、取得の段 1 つ、試験。
- **決めること:** 作るかどうか。作るなら「見つかったら知らせる」（お知らせ・メールは無料枠の外の仕組みが要る）は入れず、画面に出すだけにするのがよい。
