---
id: dec-corich-sitemap
type: decision
status: adopted
date: 2026-10-13
title: GitHub Actions では CoRich の検索を使わず、サイトマップで新しい公演を見つけて公演ページを読む
sources:
  - tools/review/fetch_candidates.py
links:
  - depends_on: corich-search-waf-403
  - depends_on: corich-sitemap-stage-ids
  - affects: dec-crawler-gha-private
verifies:
  - S24
---
起案者の指示（2026-10-13、「それで進めて」）。データはすべて CoRich のまま、見つけ方だけを変える。
fetch_candidates.py に --source sitemap を足した（TAGURI_CORICH_SEARCH=off のときの既定）: サイトマップの公演 id のうち前回より新しいものだけ公演ページを読み、題名・団体・劇場・都道府県・期間・クレジットを 1 回の取得で作る。初回は新しいほうから 6,000 件（1.1 秒に 1 件で 2 時間弱の見込み）。
同じ設定のとき、名前で検索する機能（お気に入りの登録名・探してほしい題名）は検索ページを使うので止まる（代わりは未定、q-name-search-without-corich-search）。
