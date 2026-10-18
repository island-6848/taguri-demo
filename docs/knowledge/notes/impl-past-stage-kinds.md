---
id: impl-past-stage-kinds
type: decision
status: adopted
date: 2026-10-18
title: 過去の公演（past_stage）にも種類の言葉（形式・原作・翻訳・ジャンル）を入れ、過去の記録からも好みを学べるようにした
sources:
  - cloudflare/scripts/deliver_past.py
  - cloudflare/scripts/replay_job.py
  - tools/review/replay_eval.py
  - cloudflare/test/test_deliver_past.py
links:
  - affects: impl-impression-worker
  - affects: q-auto-link-past
---
起案者の指摘（2026-10-18）「30 件くらい過去の記録とか追加したのに、全然おすすめに反映されてる感じがしない。過去の公演はあらすじとか取得できてない？」。
- 再生（Actions の Replay）に出した内訳（数だけ）: 記録 32 件・評価あり 28 件。全部が公演につながっていたが、27 件は過去の公演で、種類の言葉があるのは 1 件、感想 2 件のうち種類の言葉もあるのは 0 件。過去の公演は出演者・作り手の名前しか持っていなかった
- そのため過去の記録からは人物の好みだけを学び、形式・原作・ジャンルの好みも、感想の好み（#104）も学べなかった。過去の記録の人物が、これからの公演に出ていなければ、おすすめは動かない
- 手当て: deliver_past の people に、索引と同じ規則の種類の言葉（user_recommender.stage_tags。題名・劇場・クレジット・原作の書き方から決める）を足した。手元の 24,816 件で 21,486 件（87%）に付く。LLM は使わない
- 送り済みの行は PEOPLE_REV 2 で people の列だけを UPDATE で送り直す（INSERT OR REPLACE は消す分も数えられて倍かかる）。1 行 2 書き込みと見積もり、毎日の上限（20,000）の中で 3 日ほどかかる
- 表示（出演者・作り手）と「観たのに記録がない」の取り込みは、'#' の行を除いて読む
- まだのこと: 過去の公演のページにはあらすじが無いので #題材 は付かない（題材の好みと、題材を書いた感想は、過去の記録からはまだ学べない）
