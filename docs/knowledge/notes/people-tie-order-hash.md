---
id: people-tie-order-hash
type: finding
status: confirmed
date: 2026-10-14
title: people.timeline は同じ回数の人を集合の順で並べており、Python の実行ごと（PYTHONHASHSEED）に相関図の時間のつまみの順が変わっていた
sources:
  - tools/taguri/people.py
  - cloudflare/test/screens/people_fixture.py
links:
  - affects: dec-records-worker
---
`sorted(set(...), key=lambda p: -cnt[p])` が 2 か所（段ごとに増えた人と、残りの段）。同じ回数の人は文字列のハッシュの順になり、プロセスごとに変わる（実際のデータで `data-pnet-time` の並びが変わる）。キーに名前を足した（`(-cnt[p], p)`）。JS も名前の順で並べる。直したあと、重い記録とランダムな重い記録 3 つで JS と Python が一致した。フィクスチャは同じ回数が出ないように作り、3 つの PYTHONHASHSEED で出力が変わらないことを確かめる。
