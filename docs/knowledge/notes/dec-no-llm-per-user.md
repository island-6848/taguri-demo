---
id: dec-no-llm-per-user
type: decision
status: adopted
date: 2026-10-18
title: 利用者ごとに LLM を呼ばない。LLM が読むのは公演ごとに 1 回のあらすじだけ（運営者の Claude）。年表・相関図の読み・感想の好み・メールの判定は規則で作る
sources:
  - cloudflare/test/no-llm.test.js
  - tools/credits/extract_theme_llm.py
links:
  - depends_on: dec-synopsis-reader-claude
  - depends_on: eval-synopsis-blind-1018
---
起案者「持ち主だけの機能を claude にするなら、もしユーザーが莫大に増えたとき困るよね。できる限り claude に近いレベルで限界までルールベースで実装して、最小限 claude を呼ぶかたちで実装しないと困りませんか」「お願い。感想で書いた内容を推薦に反映させるところまで踏まえて」（2026-10-18）。

**守ること**
- Worker（利用者の要求ごとに動くもの）は LLM の API を呼ばない。`test/no-llm.test.js` が src の全ファイルで確かめる。
- LLM が読むのは、公演ごとに 1 回のあらすじだけ。読む数は公演の数で決まり、利用者の数では増えない。
  - 新しい公演は 1 日 30 件前後。定期実行の 1 日 240 件で足りる。
  - 本文が 400 字に満たないページは、読む前に規則で空にする（MIN_STORY_TEXT）。候補 1,353 件で数えると、42 件があらすじ 0・言葉あり 1 件だった。
- 年表の読み・相関図の読み・感想からの好み・メールの判定は、規則で作る。持ち主の手元の Gemini の呼び出しも、規則に置き換える。
