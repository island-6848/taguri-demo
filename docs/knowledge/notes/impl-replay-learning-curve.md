---
id: impl-replay-learning-curve
type: decision
status: adopted
date: 2026-10-20
title: 再生に学習曲線（--curve）を足した。同じ区切り・同じ後の答え・同じ索引のまま、日 t までの評価を古いほうから k 件（1・2・5・10・20・全部）だけ残して測る（#103）
sources:
  - https://github.com/island-6848/taguri-demo/issues/103
  - tools/review/replay_eval.py
  - cloudflare/scripts/replay_job.py
  - cloudflare/test/test_replay_eval.py
links:
  - affects: impl-replay-eval
  - depends_on: fix-replay-index-dates
---
起案者「issuesまだ47個あるから古い順に対応してください」（2026-10-20）。issue #103 は「評価が増えるほど当たりやすくなる」を、今の Worker の計算で確かめる求め。

- **測り方。** `replay_eval.py replay --curve`、Actions では `replay_job.py --curve`。
  - 区切りの日 t ごとに、いつもの写し（日 t までの記録・日 t の索引〔fix-replay-index-dates〕）を作る。そこから、利用者ごとに評価を古いほう（評価した時刻 rated_at の順）から k 件だけ残した写しを、k = 1・2・5・10・20 と全部で作る。
  - 同じ後の答え（t より後 1 週間）を、Worker と同じ rankedGroups の順位で当てる。区切りごとに索引は変えないので、カタログの更新による変化と、評価の数による変化を切り分けられる。
  - k 件以上の評価がある人だけを、その k に数える（足りない人は全部の評価と同じになるため）。
  - 評価の無い記録（観ただけの記録の種）・お気に入り・興味ありは、どの k でも同じに残す。
- **出すもの**（k ごと）。人数、AUC の中央値、後で答えた公演がおすすめに入っていた割合（候補のカバー率）、k=1 より良くなった人・悪くなった人、その符号検定の p。全員がいつも良くなるとは決めつけない。
- **費用。** 計算は Actions の中の node だけで、D1・R2 は読まない。区切りごとに Worker の計算を 6 回多く動かすので、Replay の分（REPLAY_MINUTES 20 分）の中で収まるかは、初めて動かしたときに確かめる。既定では動かさない（--curve を付けたときだけ）。雛形の replay.yml（tools/taguri/deploy/github-actions/）に入力 curve を足した。taguri-crawler の replay.yml にも同じ変更が要る（ジョブの上限は 20 分のまま）。
- **画面の言い方。** issue が挙げた TIPS の「評価が増えるほど…当たりやすくなります」は、今の画面（screens/recommend.js の TIPS）にはもう無い。
- **分からないこと。** 評価が 1 段階だけの人では、評価を増やしても人の値が 0 のままで、曲線は平らになる〔q-all-same-ratings-no-reco〕（#106）。
