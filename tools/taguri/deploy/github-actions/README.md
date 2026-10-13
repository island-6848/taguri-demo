# 公演カタログの毎日の取得を GitHub Actions で動かす

EC2 は無い（docs/knowledge の no-ec2）。毎日の取得は、**非公開リポジトリ `island-6848/taguri-crawler`** の
GitHub Actions で動かす（dec-crawler-gha-private）。コードは公開リポジトリ `taguri-demo` の master を毎回取り出して使う。

## 置くもの

- `catalog.yml` → 非公開リポジトリの `.github/workflows/catalog.yml`

## 非公開リポジトリに入れる秘密（Settings → Secrets and variables → Actions）

| 名前 | 中身 |
| --- | --- |
| `AWS_ACCESS_KEY_ID`・`AWS_SECRET_ACCESS_KEY` | `stage-catalog/` だけに書き込める IAM ユーザーの鍵（下の権限） |
| `STAGE_CATALOG_BUCKET` | カタログを置いている S3 のバケット名 |
| `GEMINI_API_KEY` | あらすじから題材を読む段で使う（無ければその段は飛ばされる） |

IAM の権限（`<bucket>` を置き換える）:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
     "Resource": "arn:aws:s3:::<bucket>/stage-catalog/*"},
    {"Effect": "Allow", "Action": "s3:ListBucket", "Resource": "arn:aws:s3:::<bucket>",
     "Condition": {"StringLike": {"s3:prefix": "stage-catalog/*"}}}
  ]
}
```

## 動き

1. `crawler_state.py restore`: 前回の作業データ（`stage-catalog/crawler-state.tar.gz`）を戻す。初回は公開カタログを種にする
2. `publish_catalog.py --mode daily|weekly`: 取り直し、検査し、`stage-catalog/data.tar.gz` に載せる（前のものは `history/` に控える）
3. `crawler_state.py save`: 作業データを置く（失敗しても置く）

月〜土は毎日の更新、日曜は候補・クレジットまで取り直す。手動でも起動できる（Actions → Catalog → Run workflow）。
カタログが古くなったら、公開リポジトリの `Catalog age` が知らせる。

## まだ足りないもの

- Cloudflare 版が使う推薦の索引（`cloudflare/scripts/build_recommend_index.py`）を D1 に入れる段。Cloudflare の API トークンが要る
- 定期実行は遅れたり飛ばされたりすることがある（gha-schedule-unreliable）。`Catalog age` で気付く
