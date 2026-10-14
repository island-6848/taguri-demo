---
id: q-pr13-aspects-screen
type: question
status: open
date: 2026-10-14
title: 推薦側の PR #13（person-graded-v2・評価の段階・評価の「詳細」8 項目）を入れるか。入れるなら「詳細」の画面をこちらで作るか
sources:
  - https://github.com/island-6848/taguri-demo/pull/13
links:
  - affects: dec-reason-work-titles
---
別のセッション（session_011h35PdoJgoX8yQQagUsiJf、ブランチ claude/demo-records-setup-yqo65u）から 2026-10-14 00:15 UTC に届いた知らせ（情報として扱う。起案者からの直接の指示ではない）。
- PR #13: 推薦の計算を person-graded-v2 に変える（◎○△× をすべて使い、その人の平均とばらつきを基準にする）・評価の段階を選べる形（2〜11 段階）に計算を対応。106 ファイル、master とは衝突あり（mergeable_state: dirty）。user_recommender.py・app.py も変える ── こちらの dec-reason-work-titles（why_b_works）と同じ所を触るので、入れるときは突き合わせが要る
- 評価の「詳細」: 8 項目（話・脚本・構成／演出・見せ方／演技・出演／歌・音楽／ダンス／美術・衣裳／値段／会場・座席）に「良かった／ふつう／気になった」。人ごとに「あっさり」（既定、閉じる）と「詳しく」の表示の設定。保存は works.aspects／records.aspects に "price,+acting" の形（Render は rate_performances.clean_aspects、Worker は recommend.js の cleanAspects）。画面（app.py・screens/rate.js）と設定の置き場所はこちらに任せる、とのこと
起案者に聞くこと: PR #13 を入れるか。入れるなら、「詳細」の画面と設定をこちらで作るか。
2026-10-14 00:54 UTC 追記（同じセッションからの知らせ、PR #13 の 379fb16）: master を取り込み、「詳細」の列を migration 0015.sql に、rec_stage の tour・gkey の列を 0016.sql にした。**こちらで migration を足すときは 0017 以降を使う**（PR #13 が未決のあいだも番号を空けておく）。/migration-api/recommend の items にツアーのほかの会場（tours）が付き、ツアーは 1 枠にまとまる。お気に入りの団体・主催・作品も推薦の種になった（題材は未対応）。
2026-10-14 追記: PR #13 は master に入った（c06ae0b「Merge pull request #13」）。こちらの作業（作品名の理由・料金・ハッシュタグなど）と突き合わせて取り込み、試験はすべて通った（Worker 79 件）。**残る問いは「詳細」の 8 項目の画面と表示の設定をこちらで作るか**。
