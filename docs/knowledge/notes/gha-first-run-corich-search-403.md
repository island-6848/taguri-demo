---
id: gha-first-run-corich-search-403
type: finding
status: confirmed
date: 2026-10-13
title: GitHub Actions からは CoRich の公演一覧の検索（/stage/search）が 403 で断られた
sources:
  - https://github.com/island-6848/taguri-crawler/actions/runs/38402020387（非公開）
links:
  - affects: q-crawler-repo
  - raises: q-corich-search-refusal
  - affects: dec-polite-crawling
verifies:
  - S24
---
初回（weekly）の実行で、候補の一覧を取る fetch_candidates.py が CoRich の /stage/search を 2 回目の要求（robots.txt の次）で 403 Forbidden を受けて止まった。同じ実行の中で、ステイジーズカレンダーの取り込みは通り（998 件を読み、楽日が今日以降 823 件、公式サイトからクレジットが取れたのは 406 件・2 分）、そのときの CoRich への 41 件の要求は断られていない。検索のページだけが断られる理由（robots.txt・名乗り・データセンターの接続元のどれか）は未確認。取得の作法として、断られたものを名乗りや接続元を変えてすり抜けることはしない。候補が 0 件だったので publish_catalog.py の検査（100 件未満は載せない）で失敗し、作業データ（656 ファイル）は state ブランチに書き戻した。
