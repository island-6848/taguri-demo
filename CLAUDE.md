# このリポジトリで作業するときの約束

## 調べたことは必ずナレッジグラフに記録する

起案者から毎回言われなくても、**調べたこと・今後調べること・決めたことは、すべて `docs/knowledge/notes/` に 1 件 1 ファイルで記録する。** 索引と図は `docs/knowledge/README.md`。

- 調べたら `type: finding`。出典 URL を `sources`、確かめた日を `date` に書く。分かったことと、分からなかったことの両方を書く
  - `confirmed` にしてよいのは一次情報だけ: 公式の文書・料金表、取得元そのもの、リポジトリのコード・実行結果。公式ページを検索結果の引用でしか見ていないときは、本文にそう書く
  - ブログ・集計サイト・推測・見積もりは `unverified`
- 分からないこと、次に調べることは `type: question`（`open`）。答えが出たら、答えの finding から `answers: <問いの id>` でつなぎ、問いを `answered` にする
- 決めたことは `type: decision`。取り消すときは消さずに `superseded` にし、新しい決定から `supersedes` でつなぐ。前提が揺らいだら `proposed` に戻して問いを立てる
- 古くなった事実は消さずに `outdated` にする
- 別のセッション・ブランチの作業で分かったことも記録する（出典はブランチのファイルの URL）
- 計画などの文書から項目を指すときは `〔id〕` と書く
- 書いたら `python3 tools/knowledge/build_graph.py`（CI が `--check` で確かめる）。形は `tools/knowledge/build_graph.py` の冒頭

### 自動で確かめる仕組み（`.claude/settings.json`）

- WebSearch・WebFetch の後: 調べたことを控え（`.claude/knowledge-inbox.jsonl`、リポジトリには入れない）に足し、記録を促す
- `docs/knowledge/notes/` を書き換えた後: 索引と図を作り直す
- 応答を終える前: 記録していない調べもの、古い索引、壊れた参照があれば止める。記録するまでもない調べものだったときは `python3 tools/knowledge/hook.py dismiss`

## 並行している作業に気を付ける

同じリポジトリを別のセッションが同時に触っていることがある（例: `cloudflare-d1-preview`・`cloudflare-complete-migration` ブランチ）。
方針に関わる作業を始める前に、`git fetch` してブランチと master の最近のコミットを確かめ、食い違う方針があればナレッジグラフに `question` として記録し、起案者に伝える。
