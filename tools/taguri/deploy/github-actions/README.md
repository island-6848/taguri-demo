# 公演カタログの毎日の取得を GitHub Actions で動かす

EC2 も AWS も使っていない（docs/knowledge の no-ec2・no-aws）。毎日の取得は、**非公開リポジトリ
`island-6848/taguri-crawler`** の GitHub Actions で動かす（dec-crawler-gha-private）。
コードは公開リポジトリ `taguri-demo` の master を毎回取り出して使う。

## 無料枠（いちばん大事な約束）

**有料のものは 1 つも使わない。無料枠を越えそうなら、使う前に止める**
（起案者の指示 2026-10-13「必ず無料の範囲内にして。絶対超えないで。つねに警戒してチェックして」。
上限の一覧は `docs/free-tier-budget.md`、数字は `cloudflare/scripts/free_tier.py` の `CAPS` にだけ書く）。

- 非公開リポジトリの Actions は **月 2,000 分まで無料**。ジョブの最初の段（Plan within the free tier）が
  直近 31 日のジョブの分数を数え、**1,500 分**に収まるときだけ動かす。届く見込みなら失敗して何もしない
- 過去の公演を読む分数は、その残りから毎日決める（1 日 0〜135 分）。起案者の「1 日 6,000 件」は、
  無料枠に収まらない日は減らす（6,000 件は 1 日 約 120 分で、毎日だと月 3,600 分になる）
- D1 の書き込みは 1 日 8 万行まで（無料は 10 万行）、R2 は保存 8 GB・書き込み月 30 万回まで（無料は 10 GB・100 万回。
  **R2 は越えると請求が来る**）。どの段も上限の手前で止まる
- 最後の段（Free-tier check）が使った量を表にし（実行の Summary に出る）、上限の 8 割を越えたか読めなければ失敗する。
  失敗すると GitHub から持ち主に通知が届く
- 最後の歯止めは GitHub 側の支払いの上限 0 ドル（既定）。**変えないこと**

## 置くもの

- `catalog.yml` → 非公開リポジトリの `.github/workflows/catalog.yml`
- `replay.yml` → 非公開リポジトリの `.github/workflows/replay.yml`（推薦の再生。手で動かすだけ。下の「推薦の再生」）
- `restore-drill.yml` → 非公開リポジトリの `.github/workflows/restore-drill.yml`（控えから戻す予行）

**雛形と本番は同じ中身にしておく。** 2026-10-18 に本番だけにある段（あらすじの読み取り待ち・過去の公演のポスター・
名前の索引）と、雛形だけにある段（Worker の CPU・D1 の行数の測定、毎日の控え）がずれていた（#70）。
本番の `catalog.yml` をそのまま写して合わせた。段を足す・変えるときは、**本番を直したら同じ日にこの雛形へ写す**
（逆も同じ）。確かめるには、両方を取り出して `diff` が空であること:

    diff tools/taguri/deploy/github-actions/catalog.yml ../taguri-crawler/.github/workflows/catalog.yml

Worker の推薦の CPU・D1 の行数の測定（`cloudflare/scripts/measure_worker.mjs`、S20・S21）は、本番の段から外れていた。
毎日の Actions の分を使わないよう、段には戻さず、測りたいときに取得の環境か手元で
`node cloudflare/scripts/measure_worker.mjs --index <索引の SQL>` を動かす。

## 設定

- 秘密は要らない（作業データは同じリポジトリの `state` ブランチに書き戻すので、`GITHUB_TOKEN` だけで足りる）
- LLM の鍵は渡さない。あらすじは LLM を呼ばずに読み取り待ち（`data/credits/synopsis_queue.jsonl`）に書き出し、
  起案者の Claude の定期実行が読む（dec-synopsis-reader-claude。下の「あらすじの読み取り」）
- 初回は Actions → Catalog → Run workflow を mode=weekly で手動で動かす（前回の作業データが無いので、候補から取り直す）

## 動き

1. 公開リポジトリのコードを取り出し、`state` ブランチ（前回の作業データ）を `state/` に取り出す
2. `crawler_state.py restore --from state`: 作業データを `data/` に戻す（`state` が無ければ週 1 の取り直しで始める）
3. `free_tier.py plan`: 無料枠の残りを見て、動かすか・週 1 か毎日か・過去の公演を何分読むかを決める
4. `publish_catalog.py --mode daily|weekly --dry-run --out catalog.tar.gz`: 取り直して検査する（S3 には載せない）
5. D1 に入れる（下）・ポスターを R2 に入れる（`deliver_posters.py`）
6. 過去の公演のページを読み（`fetch_past_stages.py`、q-auto-link-past）、D1 の `past_stage` に入れる（`deliver_past.py`）
7. `free_tier.py check`: 使った量の表。上限の 8 割を越えたら失敗する
8. `crawler_state.py save --to state` と `git push -f`: 作業データを `state` ブランチに 1 コミットで置き換える（失敗しても置く）

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
- 1 日の書き込みが 6 万行を超えるなら止める。さらに、その日（UTC）の取得の書き込みの合計が 8 万行を越えないように、
  書く前に `data/free_tier/usage.json` に足す（無料枠は 10 万行。残りは利用者の操作のため）
- 推薦の索引（`build_recommend_index.py`）は、版が変わり、枠に収まるときだけ入れる
- 秘密 `CLOUDFLARE_API_TOKEN`・`CLOUDFLARE_ACCOUNT_ID` が無ければこの段は飛ばす。鍵はこの段にだけ渡す
- `rec_meta` に取り直した日・入れた時刻・これからの公演の数を書き、Worker の公開の `/api/health` が返す
  （`.github/workflows/catalog-age.yml` が毎日見る。変数 `TAGURI_HEALTH_URL` を入れると動く）

## まだ足りないもの

- 実際のカタログで、初回と毎日の書き込み行数・索引の大きさを測る（q-real-catalog-stats）
- Worker の `/api/catalogue` は 1,000 件までしか返さない（q-catalogue-api-limit）
- 定期実行は遅れたり飛ばされたりすることがある（gha-schedule-unreliable）

## 推薦の再生（replay.yml）

推薦が当たっているかを、本番の利用者の記録で測る（`docs/research/real-data-eval-plan.md` の §3・H5、`impl-replay-eval`）。
パソコンが無くても、スマートフォンの GitHub アプリかブラウザで動かせる（起案者の指示 2026-10-18）。

1. taguri-crawler の Actions → **Replay** → Run workflow（持ち主の user_id は任意）
2. 終わったら、その実行の **Summary** に表が出る（AUC・部品を外したときの差・p 値。集計だけ）

- 最初の段が Actions の分数を数え、毎日の取得の分を取っておいて 20 分が残るときだけ動かす（`free_tier.py plan --mode replay`）
- 利用者の記録は D1 から読むだけ（毎日の控えと同じ表。数千行で、D1 の 1 日の読み出しの無料枠 500 万行のわずか）。
  索引と過去の公演は作業データから作る。読んだ記録は一時ディレクトリに置き、終わったら消す
- 秘密は Catalog と同じ `CLOUDFLARE_API_TOKEN`・`CLOUDFLARE_ACCOUNT_ID`
