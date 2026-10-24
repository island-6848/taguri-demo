---
id: find-max-api-credits
type: finding
status: confirmed
date: 2026-10-24
title: Claude の Max・Team 契約には、毎月の API クレジットが付く（Max 5x は 100 米ドル・Max 20x は 200 米ドル）。使い切ると API は止まり、支払い方法も自動の買い足しも無ければ請求されない
sources:
  - https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers
  - https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans
  - https://platform.claude.com/docs/en/about-claude/pricing
links:
  - affects: dec-no-llm-per-user
  - raises: q-impression-llm-credits
---
公式の文書（Claude Platform Docs・ヘルプセンター）で確かめた（2026-10-24）。

**分かったこと**
- 対象: Max 5x（毎月 100 米ドル）・Max 20x（200 米ドル）・Team（席ごと、合わせて 500 米ドルまで）。Free・Pro・Enterprise は対象外。契約から 7 日たつと受け取れる。
- 受け取り方: claude.ai の Settings > Billing で、Claude Console の組織を 1 つ結び付ける。結び付けた組織は自分では変えられない（変えるにはサポートに連絡）。
- 使える先: Claude API・Message Batches・Managed Agents・Agent SDK・Playground。Claude Code（定期実行を含む）と、アプリの追加利用には使えない。
- 期限: 毎月の請求の区切りで消え、繰り越さない。
- **使い切ったとき:** 買ったクレジットも自動の買い足し（auto-reload）も無ければ、API の要求は次の月のクレジットまで止まる（"Your credit balance is too low"）。Claude の契約には請求されない。Claude Platform に支払い方法を登録する必要は無い。営業経由の請求書払いの組織だけは、越えた分が請求される。
- 使い過ぎの歯止め: ワークスペースごとに使う上限（spend limit）を置ける。
- 料金（2026-10-24 の料金表）: Claude Haiku 5.5 は入力 0.10・出力 0.50 米ドル／百万トークン。Batch API は半額（入力 0.05・出力 0.25）。

**無料枠の決まりとの関係**
- 「越えたら止まるか請求されるか」は、**止まる**（支払い方法・買ったクレジット・自動の買い足しが無い限り）。CLAUDE.md の「越えると請求されるものは使わない」には当たらない形で使える。
- ただし、起案者の Max 契約が続いていることが前提になる。契約が終わると、クレジットも止まる。

**分からないこと**
- 起案者の契約が Max 5x か 20x か。
- クレジットの規約（https://www.anthropic.com/legal/credit-terms）の、ほかの利用者に向けたサービスで使うことの扱い。本文はまだ読んでいない。
