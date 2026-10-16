---
id: dec-past-name-index
type: decision
status: adopted
date: 2026-10-16
title: 過去の公演の「名前 → 公演」の索引を R2 に置き、ハッシュタグの画面は 1 回の読み出しで過去の公演を出す
sources:
  - cloudflare/scripts/deliver_past_index.py
  - cloudflare/src/screens/lists.js
  - cloudflare/test/test_deliver_past_index.py
links:
  - depends_on: dec-auto-link-past
  - depends_on: dec-posters-r2
  - affects: comp-frontend
---
起案者の指示（2026-10-15）は「ハッシュタグ絞り込みで、過去の公演はボタン押して調べるんじゃなくて自動的に表示して」。D1 の読み取りを守るため 1 日の回数に上限を付けたところ、「明日じゃ困る。すぐ表示できるための方法考えて」→ 4 案（A: R2 の名前索引、B: 登録した名前だけ先に調べる、C: その日の使い回し、D: 上限を上げる）から A を選んだ。

作りは次のとおり。
- 取得（taguri-crawler の Catalog、deliver_past の段の後）:
  - deliver_past_index.py が data/past/stages.jsonl の全行から「名前 → 公演」を作る。
  - 名前は出演・作り手（parse_credits）と団体で、正規化は lists.nz と同じ。
  - FNV-1a（32 bit）% 256 で分け、R2（taguri-posters）の pastidx/v1/<2 桁>.json に置く。
  - 中身が前回と同じファイルは送らない（data/r2/pastidx.json に SHA-256）。
  - R2 の保存と今月の書き込みは free_tier.py の控えで数え、上限の手前で止まる。
- 画面（lists.pastByName）:
  - その名前のファイルを 1 つだけ読む（R2 の読み出し 1 回。Worker の r2ReadAllowed で数える）。
  - 名前全体で一致し、D1 は読まない。
  - 索引がまだ無い・R2 が使えないときだけ、past_stage を全部読む代わりの検索をする（全体で 1 日 150 回まで）。
- 無料枠への影響:
  - R2 の書き込み: 1 日 256 回まで（月 7,680 回まで。上限 30 万回）。
  - 保存: 数 MB〜数十 MB。
  - 読み出し: 画面を開くたびに 1 回。
- 団体名は完全一致だけになる（前の D1 の検索は団体名を部分一致で探していた）。
