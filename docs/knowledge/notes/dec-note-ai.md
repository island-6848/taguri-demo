---
id: dec-note-ai
type: decision
status: adopted
date: 2026-10-21
title: 感想は、設定で同意した人の分だけ Claude Haiku 5.5 に送って特徴を読み取り、感想の好み（#104）に使う。答えは候補の番号と符号だけ・1 回 20 件・同じ感想は 1 度だけ・夜にまとめて
sources:
  - cloudflare/src/note-ai.js
  - cloudflare/src/impression.js
  - cloudflare/migrations/0045.sql
  - cloudflare/public/privacy.html
  - cloudflare/test/note-ai.test.js
  - https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers
links:
  - affects: impl-impression-worker
  - affects: q-impression-not-in-service
---
起案者の指示（2026-10-21）「apiの呼び出しが月100$無料らしいので、ユーザが書いた感想をclaudeのapiで分析して推薦に組み込むようにしたい。トークン消費を最小限にして」「感想を送信することにチェックした場合のみ可能（設定画面に同意非同意つくって）」「haikuにしたい」。

- **100 ドルの枠:** Max 5x の加入者が Console の組織を結び付けると、毎月 100 ドルの API の枠が付く（公式の文書）。支払い方法を登録しなければ、使い切った月は API が止まって請求されない。無料の約束（dec-free-tier-only）に収まる。Pro と Free には枠が無い
- **同意:** 既定は送らない。設定の「感想の AI 読み取り」で同意した人の感想だけを送る（app_setting の note_ai）。同意をやめると、読み取った結果（note_ai）とおすすめの控えを消す。プライバシーポリシー第 5 条は「感想を AI に送らない」だったので、同意した人に限る例外と送り先（Anthropic, PBC）を書き足した
- **送る中身:** 感想の本文（X のポストの出どころの行を除く）と、その公演に付いた種類の言葉（CONTENT_AXES の軸。impression.js が好みに使う言葉と同じ）だけ。名前・アカウント・公演名・作品の番号は送らない。出演者の名前も候補に入れない
- **言葉の数を減らす工夫:**
  1. 答えは「番号:候補番号と符号」だけにした。候補の中から選ばせるので、自由に書かせるより出る言葉が少ない
  2. 1 回の問い合わせに 20 件をまとめ、決まりの文（system）を 20 件で分け合う
  3. 同じ感想は 1 度だけ読む（文の印 note_hash）
  4. 候補の無い感想・8 字未満の感想は送らない
  5. 考える段を外し、手間は low にした
  6. JSON は使わない
- **送る時:** Worker の夜の定期実行（18:41 UTC）だけ。1 晩 10 回・200 件まで（無料の Worker の外への問い合わせは 1 回 50 まで）。GitHub Actions の分数は増やさない
- **上限:** 月 500 万トークン（NOTE_AI_TOKENS_CAP、Haiku 5.5 で約 0.6 ドル）を D1 の usage に数える
- **見込み:** 1 件あたり入力 約 200・出力 約 10 トークン（見積もり。本番の最初の夜に usage で確かめる）
- **推薦への入れ方:** impressionAdjust に結果を渡す。読み取った時と感想の文が同じ作品だけ、決まりで読む代わりに AI の読みを使い、書き直した直後は決まりで読む。部品外し（ablate.impression）はそのまま効く
- **AI が断ったとき・答えの形が崩れたとき:** その感想は refused・bad として残し、同じ文のあいだは読み直さない（費用が際限なく増えないように）
- **選ばなかったもの:**
  - Batch API（半額）は、結果が次の夜になり 2 段の手間が増える。費用は月数円なので使わなかった
  - 決まりで読めた感想を送らない前段のふるいも入れなかった。否定や言い換えは AI の方が読めるため。費用が問題になったら足す
- **まだのこと:** 起案者が Console の組織を枠に結び付け、鍵を Worker の秘密の値（ANTHROPIC_API_KEY）に入れるまで、夜の読み取りは何もしない。決まりの読みと比べて当たりが良くなるかは、再生（H1）で確かめる
