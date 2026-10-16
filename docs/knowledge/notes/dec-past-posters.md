---
id: dec-past-posters
type: decision
status: adopted
date: 2026-10-16
title: 過去の公演（2019 年以降）のポスターも、毎日の取得で少しずつ取り込む（無料枠の残りの 3 分の 1、1 日 60 分まで）
sources:
  - tools/taguri/posters.py
  - tools/review/fetch_past_stages.py
  - cloudflare/scripts/free_tier.py
  - taguri-crawler .github/workflows/catalog.yml
links:
  - depends_on: dec-posters-r2
  - affects: comp-crawler
---
起案者の質問と指示（2026-10-16）:
- 「自分から登録した公演のポスターが一個もでないのはなぜ？」
- 「過去の公演の全てのポスターデータも欲しい」

原因:
- ポスターを取っていたのは、これからの公演と終わって 180 日以内の公演（candidates.jsonl、ポスター 4,386 枚）だけだった。
- 過去の公演の一覧（data/past/stages.jsonl、17,802 件）はページの HTML を残さないので、画像の URL が無く、1 枚も無かった。
- 自分で登録した記録は、たいてい過去の公演に結び付くので、ポスターが出なかった。

作り:
- fetch_past_stages.row_from_html: これから読むページは、行に `poster`（画像の URL、無ければ空）を残す。追加の取得は要らない。
- posters.fetch_past（`posters.py --past --max-minutes N`）: 過去の公演を上演の新しい順に見る。
  - 行に `poster` が無いもの（これまでに読んだ行）は、ページを 1 回だけ読み直して URL を data/past/poster_urls.json に控える。
  - 画像を取り、縮めて data/review/img に置く。
  - 同じ画像（ツアーの各会場など）は 1 回だけ取り、ほかの公演には写しを置く。
  - R2 に入れ終えたもの・手元にあるものは飛ばすので、止まっても次の回は続きから。
- 公演ページ（stage.corich.jp）と画像（stage-image.corich.jp）は別のホストなので、polite_http の「同じホストへ 1.1 秒に 1 回」を守ったまま交互に読める（1 公演およそ 1.2 秒）。
- 403 などで断られたら、その回は手を引く（polite_http.Skipped）。回避はしない。

無料枠:
- GitHub Actions: free_tier.plan が、過去の公演の読み取りと同じ残りから 3 分の 1（1 日 POSTER_MAX_MINUTES = 60 分まで）を `poster_minutes` として渡す。残りが少ない日は 0 分にして取らない。31 日の窓が上限を越えないことを試験で確かめている。
- R2・D1 へは、これまでどおり deliver_posters.py が控えを見て、入れられる分だけ入れる（1 回 2,000 枚まで、1 枚 約 18 KB）。
- 1 日 60 分なら 約 3,000 公演。今ある 17,802 件は、Actions の残りしだいで 1〜3 週間ほど。過去の公演の読み取りが進むと件数は増える。
