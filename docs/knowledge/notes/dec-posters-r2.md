---
id: dec-posters-r2
type: decision
status: adopted
date: 2026-10-13
title: ポスターは R2 に置き、Worker の画面にも出す。R2 に入れた分は取得の作業データから外す
sources:
  - cloudflare/scripts/deliver_posters.py
  - cloudflare/migrations/0013.sql
  - cloudflare/src/worker.js
  - cloudflare/src/screens/rate.js
  - tools/taguri/posters.py
  - tools/taguri/crawler_state.py
  - tools/taguri/deploy/github-actions/catalog.yml
links:
  - answers: q-crawler-state-size
  - answers: q-worker-posters
---
起案者の指示（2026-10-13）「ポスターは R2 など別の置き場に移す（Worker にポスターを出す件と一緒に決める）」（q-crawler-state-size の案 2 を選んだ）。
作ったもの:
- 取得（毎日の Catalog の「Upload posters to R2」の段）: cloudflare/scripts/deliver_posters.py が、取り込んだポスターのうちまだ R2 に無いものを Cloudflare の REST API（PUT /accounts/<id>/r2/buckets/taguri-posters/objects/<file>）で入れ、D1 の poster 表（stage_id, file、migration 0013）に載せ、data/r2/posters.json に控える。鍵に R2 の権限が無い・バケットが無いときは何も変えずに先へ進む（ポスターは今までどおり作業データに残る）
- 作業データ: crawler_state.py は R2 に入れ終えたポスター（data/r2/posters.json にあるもの）を state ブランチに入れない。posters.py は R2 にあるものを取り直さない
- Worker: GET /img/<file> を R2（POSTERS）から返す（ログインした人だけ。R2 に無ければ今までどおり Render へ）。Worker の画面（評価一覧・未評価・日記帳）は、結び付いた公演のポスターが poster 表にあれば Python と同じ <img class="poster" src="/img/<file>"> を出す。手で入れたポスターは公開版では元から使えない。持ち主の「観た日からの推測」（posters.match）は移していない
**起案者がすること（これが済むまで R2 には入らない）:**
1. Cloudflare のダッシュボードの R2 で、バケット taguri-posters を作る（R2 を初めて使うときは、R2 の有効化と支払い方法の登録を求められる。無料枠は 10 GB・月 100 万回の書き込み・1,000 万回の読み出し）
2. taguri-crawler の GitHub Secrets にある CLOUDFLARE_API_TOKEN の権限に「Workers R2 Storage: Edit」を足す（ダッシュボードの「API トークン」で、そのトークンを編集）
3. 1 と 2 が済んだら知らせてもらう → wrangler.jsonc に r2_buckets（binding POSTERS、bucket_name taguri-posters）を足す。**バケットより先に足すと、本番の配信（Workers Builds）が失敗する**ので、それまでは足さない
確かめたこと: Worker の試験 64 件（R2 から返す・R2 に無ければ Render へ・未ログインは 401・日記帳に結び付いた公演のポスターが出る）、deliver_posters の試験（新しい分だけ・403 では何も変えない）、crawler_state の試験（R2 に入れた分は state に入れない）、migration 0013 の適用、runtime-smoke。
2026-10-13 追記: 起案者がバケット taguri-posters を作り、鍵に「Workers R2 Storage: Edit」を足した。wrangler.jsonc に r2_buckets（POSTERS）を足した。R2 は無料枠を越えると請求が来るので、保存 8 GB・Class A 月 30 万回・Class B 月 300 万回の上限を付けた（dec-free-tier-only）。1 回に入れるのは 2,000 枚まで。
