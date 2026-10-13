# 公演カタログの毎日の取得を GitHub Actions で動かす

EC2 も AWS も使っていない（docs/knowledge の no-ec2・no-aws）。毎日の取得は、**非公開リポジトリ
`island-6848/taguri-crawler`** の GitHub Actions で動かす（dec-crawler-gha-private）。
コードは公開リポジトリ `taguri-demo` の master を毎回取り出して使う。

## 置くもの

- `catalog.yml` → 非公開リポジトリの `.github/workflows/catalog.yml`

## 設定

- 秘密は要らない（作業データは同じリポジトリの `state` ブランチに書き戻すので、`GITHUB_TOKEN` だけで足りる）
- `GEMINI_API_KEY` は渡さない。あらすじは LLM を呼ばずに読み取り待ち（`data/credits/synopsis_queue.jsonl`）に書き出し、
  起案者の Claude の定期実行が読む（dec-synopsis-reader-claude。下の「あらすじの読み取り」）
- 初回は Actions → Catalog → Run workflow を mode=weekly で手動で動かす（前回の作業データが無いので、候補から取り直す）

## 動き

1. 公開リポジトリのコードを取り出し、`state` ブランチ（前回の作業データ）を `state/` に取り出す
2. `crawler_state.py restore --from state`: 作業データを `data/` に戻す（`state` が無ければ週 1 の取り直しで始める）
3. `publish_catalog.py --mode daily|weekly --dry-run --out catalog.tar.gz`: 取り直して検査する（S3 には載せない）
4. `crawler_state.py save --to state` と `git push -f`: 作業データを `state` ブランチに 1 コミットで置き換える（失敗しても置く）

利用者の記録・認証・持ち主の購入の記録は、作業データに入れない。

## あらすじの読み取り（起案者の Claude）

`state` ブランチの `credits/synopsis_queue.jsonl` が読み取り待ち。定期実行は次をする:

1. `taguri-demo`（master）と `taguri-crawler` の `state` ブランチを取り出し、`crawler_state.py restore --from state`
2. `python3 tools/credits/extract_theme_llm.py --print-queue 40` の指示どおりに読み、答えの JSON 配列を `answers.json` に書く
3. `python3 tools/credits/extract_theme_llm.py --import-answers answers.json`（本文に実在しないあらすじは落ちる）
4. `crawler_state.py save --to state` してコミットし、`state` に push（取得処理の実行中は避ける）

## まだ足りないもの

- **できたカタログを Cloudflare 版（D1）に届ける段**（q-catalog-to-worker）。推薦の索引
  （`cloudflare/scripts/build_recommend_index.py`）を作り、`wrangler d1 execute` で入れる。Cloudflare の API トークンが要る。
  D1 の無料枠は 1 日 10 万行の書き込みなので、索引の入れ替えの行数を先に測る（q-real-catalog-stats）
- 定期実行は遅れたり飛ばされたりすることがある（gha-schedule-unreliable）
