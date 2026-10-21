---
id: fix-replay-index-dates
type: decision
status: adopted
date: 2026-10-20
title: 再生（replay）は、公演が D1 に載った日と、お気に入りの名前ごとに足した時刻を控えて、日 t の索引とお気に入りに近づける（#72）
sources:
  - https://github.com/island-6848/taguri-demo/issues/72
  - cloudflare/scripts/build_recommend_index.py
  - tools/review/replay_eval.py
  - cloudflare/scripts/replay_job.py
  - cloudflare/src/screens/lists.js
  - cloudflare/test/test_replay_eval.py
  - cloudflare/test/test_recommend_index.py
  - cloudflare/test/fav-roles.test.js
links:
  - affects: impl-replay-eval
  - depends_on: q-replay-history-restore
---
起案者「issuesまだ47個あるから古い順に対応してください」（2026-10-20）。issue #72 は impl-replay-eval の限界の 1 つ目と 2 つ目。

issue の 2 つの案のうち、**「載った日」を控える案**にした。R2 に索引の差分を置く案は、R2 の保存と書き込みの回数を無料枠から使う。こちらは取得の作業データ（state ブランチ）のファイルが少し大きくなるだけで、D1・R2 の無料枠を使わない。

- **公演の載った日。**
  - 索引を差分で入れるとき（build_recommend_index.diff_sql に today を渡したとき）、前回のハッシュの控え `d1/index-hashes.json` に `_seen`（公演ごとに [初めて入れた日, 中身を最後に変えた日, 中身のハッシュ]）と `_seen_since`（控えを始めた日）を足す。
  - 中身は rec_stage と rec_people の行のハッシュ。題名・日付・出演者が変わると「変えた日」が進む。
  - 1 日の上限で入れきれずに次の日へ残した公演は、まだ載っていないとみなす。
  - 控えはその日の取得が D1 に入れたとき（deliver_catalogue.commit）だけ保存される。
- **再生での使い方。**
  - replay_job は `data/d1/index-hashes.json` を読み、replay_eval.replay に `seen` として渡す。手元では `--seen`。
  - 区切りの日 t ごとに、t より後に初めて載った公演と、控えに無い公演（作業データにはあるが、まだ D1 に無い）を、写しの rec_stage・rec_people・rec_credit・rec_affil から消す。
  - t より後に中身が変わった公演は、消さずに数だけ出す（per_origin の index_changed）。
- **お気に入り。**
  - お気に入りは今は favourites の表ではなく、app_setting の `declared`（JSON 1 行）に入っている（account.js の注記）。前の再生は、t より後にこの行を書き換えると、お気に入りが全部消えた写しで測っていた。
  - lists.favouriteAction が、名前を足すたびに `declared_at`（'種類\t名前' → 時刻）に控え、外すと控えから消す。D1 の書き込みは、お気に入りを足す・外すときに 1 行だけ増える。
  - 再生の cut_copy は、t より後に書き換えた declared を、t までに足した名前と時刻の無い名前（控えを始める前に足した名前）だけに戻す。
- **まだ残る限界。**
  - 控えを始めた日より前の t では、控え始めに載っていた公演がいつ載ったかは分からない。Summary にそう出す。state ブランチは履歴を持たないので、さかのぼっては作れない。
  - あとから足された出演者・あらすじは、今の中身のまま測る（数は出す）。
  - t より後に外したお気に入りの名前は戻せない。評価の履歴の問題（q-replay-history-restore、#113）と同じ。
