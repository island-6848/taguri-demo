---
id: dec-title-crown-subtitle
type: decision
status: adopted
date: 2026-10-20
title: 公演の題名は 冠名・タイトル・サブタイトルを空白でつなげたものにする。照合に使う題名の鍵（tkey）・ツアーのまとめ・名前の索引の鍵はタイトルだけ（title_main）から作る
sources:
  - tools/credits/fetch_credits.py
  - tools/review/fetch_candidates.py
  - tools/review/fetch_past_stages.py
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/scripts/deliver_past.py
  - cloudflare/scripts/deliver_past_index.py
  - tools/review/test_past_stages.py
  - cloudflare/test/test_deliver_past.py
links:
  - depends_on: f-corich-title-parts
  - raises: q-past-title-backfill
---
起案者の指示（2026-10-20）「冠名とサブタイトルもタイトルに含めてほしい」。

- fetch_credits.heading が見出しの 3 つを読み、full_title がつなげる。タイトルの中に既にある冠名・サブタイトルは重ねない。取得の行は title（つなげたもの、NFKC）と title_main（<title> のタイトルだけ）を持つ
- 鍵をタイトルだけにするのは、題名の鍵で照合している所があるため: 記録を過去の公演に自動で結び付ける（autolink、題名の鍵の一致）、過去の公演の候補（打った言葉で鍵が始まる）、同じ公演のまとめ（sameProduction・tour_key）。冠名を鍵に入れると「もう、それにしか見えない」と打っても「喜劇結社バキュン！ズ第６回公演 もう、それにしか見えない」に当たらなくなる
- 形式の札（form_of）は題名全体から見る（冠名に「朗読劇」「舞台」などがあることが多い）
- これからの公演: 公演ページは取得の控えにあるので、次の取得で取り直さずに入れ替わる（使い回しの行も控えのページを読み直す）
- 過去の公演: ページを残していないので、これから取る公演からつながった題名になる。前に取った約 1.8 万件は〔q-past-title-backfill〕
- 無料枠: 取得の回数は増えない。題名が変わる行の書き換え（差分で書く）だけ
