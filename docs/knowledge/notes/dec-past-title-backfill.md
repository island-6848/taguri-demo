---
id: dec-past-title-backfill
type: decision
status: adopted
date: 2026-10-20
title: 前に取った過去の公演（30,414 件）の題名も、公演ページを読み直して冠名・サブタイトル込みにする。あらすじの 2 周目で読むページはそのついでに直し、2 周目が通り過ぎた行だけを過去の公演の時間の 3 割で読み直す
sources:
  - tools/review/fetch_past_stages.py
  - cloudflare/scripts/deliver_past.py
  - tools/review/test_past_stages.py
  - cloudflare/test/test_deliver_past.py
  - https://github.com/island-6848/taguri-crawler/blob/state/past/progress.json
links:
  - answers: q-past-title-backfill
  - depends_on: dec-title-crown-subtitle
---
起案者の指示（2026-10-20）「過去の公演もお願いします…」。

- 本番の控え（2026-10-20 09:41 UTC の state）: 過去の公演 30,414 行、title_main のある行 0。あらすじの 2 周目は 4,231 行目まで
- 2 周目（stories → _story）はもともと公演ページを読むので、そのページから題名も直す（titles_of → apply_titles）。取得は増えない
- 2 周目が通り過ぎた行（あらすじ済みで読まずに飛ばした行を含む）は retitle が読み直す。時間の決まった実行（毎日の取得・stories.yml）で、past_minutes と枚数の RETITLE_SHARE（0.3）を使う。読み直す行が無くなれば 0。読み取り待ちが一杯で 2 周目が止まっている間は、先の行も読む
- 読めなかったページはもとの題名をタイトルとして控え、読み直さない。一覧（stages.jsonl）は行の順と数を変えずに書き換える（配送は行の数で送った所を数える）
- 配送（deliver_past）: 送り済みの行で題名が変わったものだけ、title の列を UPDATE（鍵 tkey は変えない）。送った印は past_delivered.json の titles_sent
- 無料枠: Actions の分数は増えない（past_minutes の中の配分）。CoRich への要求の間隔も同じ（polite_http）。D1 は題名が変わる行 1 件 2 書き込み（WRITES_PER_UPDATE）を、配送の 1 日の枠（BUDGET 2 万）の中で
- 見込み: 2 周目が通り過ぎた約 4,200 行は 1 枚 1.1 秒で約 80 分ぶん、残りの約 2.6 万行は 2 周目が進むにつれて直る
