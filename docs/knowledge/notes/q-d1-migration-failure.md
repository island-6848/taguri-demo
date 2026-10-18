---
id: q-d1-migration-failure
type: question
status: open
date: 2026-10-18
title: D1 で migration の 1 ファイルが途中で失敗したとき、前半は巻き戻るか。再実行・コードの巻き戻しで記録は保てるか
sources:
  - https://github.com/island-6848/taguri-demo/issues/137
  - https://developers.cloudflare.com/d1/reference/migrations/
links:
  - affects: comp-d1
---
ローカルの試験（records-survive-1018）は SQLite で、migration が行のある DB で失敗しないこと・値を変えないことまでを確かめた。D1 の側の振る舞い（1 ファイルが 1 つのトランザクションか、失敗したファイルは d1_migrations に記録されず次の配備で再び当たるか、外部キーの扱い）は、公式の文書を開けず（作業環境から developers.cloudflare.com の名前を引けなかった、2026-10-18）確かめていない。

次に調べること: 公式の migrations・外部キーの文書。隔離した D1（無料枠の範囲の別のデータベース）に 0001〜N を当てて人工の利用者を入れ、残りを当てる・わざと失敗する migration を当てる・古い Worker で読む、を試す。
