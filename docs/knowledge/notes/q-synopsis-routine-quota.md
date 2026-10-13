---
id: q-synopsis-routine-quota
type: question
status: open
date: 2026-10-13
title: あらすじを Claude の定期実行で読むと、1 日にどれだけ読め、起案者の使用枠をどれだけ使うか
links:
  - depends_on: dec-synopsis-reader-claude
---
初回はサイトマップで読んだ公演のうち、終わっていない分がまとめて待ちに入る（件数は初回の取得が終わってから数える）。
1 回の定期実行で何件読むか（いまの案は 40 件）、待ちが減る速さ、起案者の対話での使用に響かないかを、最初の数回で測る。
自分の Claude で作ったデータを公開サイトに出すことが利用規約上問題ないかは、まだ一次情報で確かめていない。

追記（2026-10-13 21:11 UTC）: 予定していた確認。今夜 19:17 UTC の Catalog の定期実行は始まっていなかった（taguri-crawler の実行一覧の最新は 13:25 UTC の手動実行。ワークフローは active）。GitHub の schedule は遅れたり飛ばされたりする（とくに足したばかりのワークフロー）。午後の実行はあらすじの読み取り待ちを書き出す前のワークフロー（GEMINI_API_KEY を渡す古い版）で動いたので、state ブランチに credits/synopsis_queue.jsonl はまだ無い（0 件）。読み取り待ちの件数が分からないので、Claude の定期実行はまだ作っていない。次の Catalog の実行のあとで数えて作る。
