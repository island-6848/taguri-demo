---
id: impl-d1-settle
type: decision
status: adopted
date: 2026-10-16
title: D1 に入れ終えたら、書く前に足した見積もりを D1 が返した rows_written に置き換える。見積もり自体は下げない
sources:
  - cloudflare/scripts/free_tier.py
  - cloudflare/scripts/deliver_catalogue.py
  - cloudflare/test/test_free_tier.py
  - cloudflare/test/test_deliver_catalogue.py
  - tools/taguri/deploy/github-actions/catalog.yml
  - https://github.com/island-6848/taguri-crawler/blob/main/.github/workflows/catalog.yml
links:
  - depends_on: d1-upsert-counts
  - depends_on: dec-free-tier-only
---
d1-upsert-counts から。見積もりを「既にある行は 1」に下げると、控えのハッシュと D1 の中身がずれたとき（D1 を戻した・表を消したなど）に少なく数える恐れがある（起案者「絶対超えないで」）。そこで見積もりは今のまま多めに足し、入れ終えたあとに D1 自身の数で控えを直す。
- deliver_catalogue.py build: 足した日と見積もりを out/spent.json に残す。commit: 送った全部のファイル（空でない catalogue.sql、index-upload-NN.sql、labels・cards）の wrangler の出力（<ファイル>.log）から rows_written を読み、全部そろったときだけ free_tier.d1_settle で「その日の控え − 見積もり ＋ 実際」にする。1 つでも読めなければ見積もりのまま（多めのまま）
- catalog.yml: 送る段で `set -o pipefail` と `wrangler … 2>&1 | tee <ファイル>.log`（tee を挟んでも wrangler の失敗で段が止まる）
- 効くこと: 同じ日のあとの実行（夜の定期実行・索引だけの実行）が使える予算が、実際の分だけ残る。今日の例では #8・#9 で 1.5 万が戻っていた。1 回の実行の中の上限（max_rows）は今のまま見積もりで決める
- 過去の公演（deliver_past.py）は見積もり（1 行 3）が実際と合っている（d1-writes-undercounted）ので今回は触らない
