# 利用者の記録の控えと戻し方（サービス版・D1）

2026-10-14。検証項目 S07・S31・S26 の手順書。決めたことの根拠は `docs/knowledge/notes/dec-d1-backup.md`。

## 控えは 2 段

| | 何が | どこに | どれだけ | 戻せる細かさ |
| --- | --- | --- | --- | --- |
| Time Travel | D1 全体 | Cloudflare（自動・無料） | 7 日 | 分単位のどの時点でも |
| 毎日の書き出し | 利用者の記録の表だけ（`backup_d1.py` の `DERIVED` 以外のすべて） | R2 `taguri-backup`（控え専用。Worker からは見えない）の `backup/d1/YYYY-MM-DD.sql.gpg`（gpg・AES-256 で暗号化） | 30 日 | 1 日に 1 回（取得のジョブの終わり） |

公演カタログ・推薦の索引は控えに入れない（毎日の取得で作り直す）。ログインのセッションも入れないので、戻したあとは利用者に入り直してもらう。

## 起案者が一度だけすること

1. 合言葉を作る（例: パスワード管理のアプリで 32 文字以上をランダムに）。**別の場所にも控える。無くすと控えは二度と開けない。**
2. 非公開の taguri-crawler の Settings → Secrets and variables → Actions に `BACKUP_PASSPHRASE` として入れる
3. 次の毎日の取得のあと、ログの「Back up the user records」に `"key": "backup/d1/…"` が出ていることを見る
4. taguri-crawler の Actions で「Restore drill」を手動で動かし、`"ok": true` と、かかった時間を下の記録に書く（S31）

## 戻し方

### 7 日以内の、ある時点に戻す（Time Travel）

```sh
cd cloudflare
npx wrangler d1 time-travel info taguri-demo --timestamp=2026-10-14T10:00:00+09:00   # その時点の印（bookmark）
npx wrangler d1 time-travel restore taguri-demo --bookmark=<印>
```

本番の D1 がその時点に丸ごと戻る（戻したあとに付いた記録は消える）。戻す前の印も表示されるので控えておけば、やり直しも戻せる。

### 7 日より前に戻す（毎日の書き出し）

```sh
cd cloudflare
W=$(mktemp -d)                                          # 平文はリポジトリの外に置く（公開リポジトリに入れない）
npx wrangler r2 object get taguri-backup/backup/d1/2026-10-01.sql.gpg --remote --file "$W/backup.sql.gpg"
gpg --decrypt -o "$W/backup.sql" "$W/backup.sql.gpg"   # 合言葉を聞かれる
npx wrangler d1 create taguri-restored                 # 新しい D1 に入れて中身を確かめる
npx wrangler d1 execute taguri-restored --remote --yes --file "$W/backup.sql"
npx wrangler d1 migrations apply taguri-restored --remote   # 控えのあとに足された表を作る
```

そのあと、毎日作り直す表（カタログ・索引）を取得のジョブで入れ直し、`wrangler.jsonc` の `database_id` を新しい D1 に向けて master に入れる。確かめ終わったら `rm -rf "$W"` で消す（暗号化されていない）。`*.sql` は `.gitignore` で除外してあるが、リポジトリの中には置かない。

**注意: 控えの日付より後に「完全削除」した人の記録も戻ってしまう。** 戻したら、その間に届いた削除の依頼をもう一度実行する（いまは削除した人の一覧を残していない〔q-restore-redelete〕）。

## 戻したあとに確かめること（issue #74 の追加の条件）

行の数がそろうだけでは足りない。戻した D1 で次を確かめ、結果を下の「予行の記録」に書く。平文・秘密の値・利用者ごとの中身は、公開のログや issue に出さない（数と合否だけを書く）。

1. **中身と結び付き:** 作り物の利用者 A・B（予行の前に本番ではなく予行用の D1 に作る）の、記録・評価・感想・お気に入り・答え（興味あり等）・券の日時・設定・手入力の作り手を、控えを取る前の値と 1 件ずつ比べる。A の行が B に混ざっていないこと
2. **ログインし直して読める:** セッションは戻さない作りなので、ログインし直して本人の画面から記録が読めること。パスキーは RP ID が合う隔離の環境でだけ確かめる（本番のドメインで試さない）
3. **作り直す表を入れてから使える:** カタログと索引を取得のジョブで入れ直したあと、記録の追加・評価・おすすめ・探すが通ること
4. **古い形の控えから戻す順:** 控えの後に足された migration がある場合、`d1 execute`（控え）→ `d1 migrations apply`（足りない表）の順で通ること
5. **削除の依頼のやり直し:** 控えの日付より後に完全削除した人がいれば、その人の行が戻っていないことを確かめ、戻っていれば消す（いまは削除した人の一覧を残していないので、手順は〔q-restore-redelete〕が決まるまで手作業）
6. **数字:** 戻せた時点、失いうる期間（控えの日付から戻した時点まで）、戻すのにかかった時間

## 予行の記録

| 日付 | 方法 | 控え | 結果 | 開く | 入れる |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Restore drill（手動） | `backup/d1/2026-10-18.sql.gpg`（25 表・4,726 行。Catalog #13 が作った最初の控え） | **動かなかった**。無料枠の見積もり（`free_tier.py plan --mode drill`）が、直近 31 日の Actions 1,124 分＋見込み 1,484 分で上限 1,500 分に届くとして止めた | | |
