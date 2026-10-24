---
id: q-impression-llm-credits
type: question
status: open
date: 2026-10-24
title: 利用者の感想を、Max 契約の毎月の API クレジットで LLM に読ませ、推薦に生かすか（dec-no-llm-per-user の見直し）
sources:
  - https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers
links:
  - depends_on: find-max-api-credits
  - affects: dec-no-llm-per-user
  - affects: impl-impression-worker
---
起案者（2026-10-24）「利用者の感想を推薦に活かしたい、Max契約してたら100ドルまで無料って聞いたけど」

**今の形:** 感想は規則で読んでいる（impl-impression-worker）。Worker は LLM を呼ばない（dec-no-llm-per-user、no-llm.test.js）。

**案（起案者が決めること）**
- Worker からは呼ばない。1 日 1 回のまとめ処理で、新しく書かれた・直された感想だけを Batch API（Haiku 5.5）に送る。返ってきた「好きな特徴・苦手な特徴」を D1 に置き、Worker は今の規則と同じように読むだけにする。
- 見積もり（unverified）: 感想 1 件を入力 1,500・出力 200 トークンとすると、Batch で約 0.000125 米ドル。100 米ドルで月 80 万件ほど。費用より、利用者の同意とクレジットが切れたときの備えが問題になる。
- 決めること:
  1. 利用者の同意: 感想の本文を外（Anthropic）に送ることになる。プライバシーポリシーの改定と、改めての同意が要る。前の決定にも「利用者の同意が要る」とある。
  2. クレジットが切れたとき・契約をやめたとき: 今の規則での読みに戻す（止まっても推薦は壊れない形にする）。
  3. どこで動かすか: GitHub Actions は分数が足りない。Cloudflare の Cron（Workers の無料枠）か、起案者のセッションの定期実行か。
  4. 支払い方法を Claude Platform に登録しない・自動の買い足しを入れない（越えたら止まる形を保つ）。
