---
id: dec-auto-link-past
type: decision
status: adopted
date: 2026-10-13
title: 過去の公演の一覧（2019 年以降）を毎日 6,000 枚ずつ作り、記録を自動で結び付ける
sources:
  - tools/review/fetch_past_stages.py
  - cloudflare/scripts/deliver_past.py
  - cloudflare/migrations/0012.sql
  - cloudflare/src/screens/autolink.js
  - tools/taguri/deploy/github-actions/past-stages.yml
links:
  - answers: q-auto-link-past
  - depends_on: auto-link-current-state
---
起案者の指示（2026-10-13）「2019年以降、1日6000件で進めて」（q-auto-link-past の範囲と件数。外へは配らず照合に使う、という条件ごと進めてよいと受け取った）。
作ったもの:
- 取得（tools/review/fetch_past_stages.py）: サイトマップの公演ページの番号を新しいほうから 1 回 6,000 枚まで読み、題名・会期（初日・千秋楽）・劇場・団体・都道府県・出演と作り手の欄だけを data/past/stages.jsonl に足す。HTML は残さない。会期の終わりが 2019-01-01 より前のページが 300 枚続いたら読み終わり。続きは data/past/progress.json の cursor から。取得の作法は polite_http（1.1 秒間隔）。毎日の Catalog が読む公演（candidates.jsonl）は読まない
- 定期実行（taguri-crawler の .github/workflows/past-stages.yml、写しは tools/taguri/deploy/github-actions/past-stages.yml）: 毎日 22:47 JST。Catalog と同じ concurrency（catalog）で順番に走り、同じ state ブランチに書き戻す。135 分で止めて、読んだ分は残す
- D1（migration 0012）: past_stage 表（stage_id・題名・tkey・初日・千秋楽・劇場・団体・都道府県・people）と、works に stage_auto（自動で結び付けた）・stage_off（利用者が外した）を足した。cloudflare/scripts/deliver_past.py が前回からの新しい行だけを入れる（1 日 2 万書き込みまで）
- 結び付け（cloudflare/src/screens/autolink.js）: 題名の鍵（rate_performances.title_key）が同じで、観た日がその会期の中にある公演が past_stage と今の一覧（rec_stage）を合わせて **ちょうど 1 つ** のときだけ結び付ける。2 つ以上なら結び付けない（同じ題名の別の座組を取り違えると、知らない人が名簿に入る）。日記帳・評価一覧を開いたとき（1 回 200 件まで）と、記録を足した・直したときに動く。手で外した記録（stage_off）には二度と結び付けない。自動で付けた結び付けは編集欄に「自動で結び付けました」と出る
- 過去の公演の出演・作り手は、日記帳の名簿（peopleByKey）とおすすめの名簿（recommend.js の peopleFor）に入り、編集欄の「題名／劇場／初日」の表示（stageLabels）にも使う。手で結び付けるときも past_stage の公演を選べる
- ついでに直した不具合: link_works.py が利用者を区別せずに works を書いていた（user_id の条件を足した）
**まだ利用者の目には見えない:** 今の本番の画面（デモ版・サービス版）は Render の Python が組んでいて、Worker の画面（NATIVE_UI）は本番ではまだ使っていない（dec-migration-branch-wip）。結び付けは Worker の画面に移ったときに効く。過去の公演の一覧は、その前から毎日たまっていく。
確かめたこと: 取得の試験 4 件（新しいほうから読む・続きから読む・古い公演が続いたら止まる・読めないページと一覧にある公演を飛ばす）、D1 へ入れる試験（前回からの分だけ・予算で止める・入れ損ねたら翌日入れ直す）、結び付けの試験 4 件（日付で会期を選ぶ・外した記録と他の利用者に触らない・候補が 2 つなら結び付けない）、Worker の試験 58 件（Python との画面の一致を含む）、runtime-smoke。ここからは CoRich に繋がらない（robots.txt を読めない）ので、本物のページの読み取りは初回の実行の記録で確かめる。
