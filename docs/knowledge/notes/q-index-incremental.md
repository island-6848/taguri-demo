---
id: q-index-incremental
type: question
status: open
date: 2026-10-15
title: 推薦の索引を毎日まるごと入れ替える作りは、D1 の書き込みの無料枠（1 日 10 万行）に収まるか。公演ごとの差分だけ書く作りに変えるか
links:
  - depends_on: d1-writes-undercounted
---
いまは版（ver）ごとに rec_stage・rec_credit・rec_people・rec_gram を全部入れ、前の版を消す。書き込みは約 4 ×（行数）。行数がまだ分からない（初回の投入で index-stats の rows_written が分かる）。2 万行を越えるなら、変わった公演の行だけを書く差分の作りが要る。次の Catalog の報告の "index" を見て決める。

2026-10-15 追記（起案者の問い「なぜまるごと入れ直して前の版を消しているの？」）: 決めた記録（decision）は見つからない。コード（build_recommend_index.to_sql「Insert ver, switch to it, then drop other versions」）から読める理由:
- 切り替えを一度に済ませるため。新しい版を全部入れてから rec_meta の 'current' を 1 行書き換えるので、Worker は入れている途中の半端な索引を読まない。入れるのに失敗しても古い版が残る
- 推薦の控え（rec_cache）の印に版を入れているので、版が変われば全員の控えが自然に捨てられる
- 作りが単純（差分を数えなくてよい）。索引を Render から移す最初の段（step 1）で、行数が小さい前提だった
- 版は中身のハッシュなので、公演が 1 件増えても終わっても新しい版になり、ほぼ毎日入れ直しになる
差分にする案: 公演ごとに行のハッシュを控え（公演一覧の delivered.json と同じ形）、変わった公演の rec_stage・rec_credit・rec_people だけ書き、消えた公演の行を消す。版の 1 行は「索引の更新日」として残し控えを捨てる合図に使う。rec_gram（題名の 2 文字ごとの束）は 1 行に多くの公演が入るので、変わった束だけ書き直す。途中の半端な状態は、公演 1 件ずつの違いなので推薦の誤りは小さい。
