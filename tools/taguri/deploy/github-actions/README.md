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

## D1 に入れる段

取り直しのあと、`cloudflare/scripts/deliver_catalogue.py` が**前回から変わった公演の行だけ**を SQL にし、
`wrangler d1 execute taguri-demo --remote` で本番の D1 に入れる（dec-d1-catalogue-delivery）。

- 入れるのは終わっていない公演の公開の欄と、一度だけ読んだあらすじ・内容の要素（`themes.jsonl`）。消さずに上書きだけする
- 何を入れたかは `data/d1/delivered.json`（`state` ブランチ）に、wrangler が成功したあとで書く。失敗した分は次回まるごと入れ直す
- 1 日の書き込みが 6 万行を超えるなら止める（無料枠は 10 万行。残りは利用者の操作のため）
- 推薦の索引（`build_recommend_index.py`）は、版が変わり、枠に収まるときだけ入れる
- 秘密 `CLOUDFLARE_API_TOKEN`・`CLOUDFLARE_ACCOUNT_ID` が無ければこの段は飛ばす。鍵はこの段にだけ渡す
- `rec_meta` に取り直した日・入れた時刻・これからの公演の数を書き、Worker の公開の `/api/health` が返す
  （`.github/workflows/catalog-age.yml` が毎日見る。変数 `TAGURI_HEALTH_URL` を入れると動く）

## まだ足りないもの

- 実際のカタログで、初回と毎日の書き込み行数・索引の大きさを測る（q-real-catalog-stats）
- Worker の `/api/catalogue` は 1,000 件までしか返さない（q-catalogue-api-limit）
- 定期実行は遅れたり飛ばされたりすることがある（gha-schedule-unreliable）
