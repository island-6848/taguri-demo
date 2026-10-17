---
id: impl-terms-reagree
type: decision
status: adopted
date: 2026-10-18
title: 規約・プライバシーの説明を yomiyasu で書き直して版を 2026-10-18-2 に上げ、登録済みの人にも次に開いたときに同意し直してもらう
sources:
  - cloudflare/src/terms.js
  - cloudflare/src/worker.js
  - web/app.js
  - cloudflare/public/terms.html
  - cloudflare/public/privacy.html
  - cloudflare/test/terms-reagree.test.js
links:
  - depends_on: tool-yomiyasu
---
起案者の回答（2026-10-17）: 「規約も含める」（規約も yomiyasu で書き直し、版を上げて、登録済みの人にも同意し直してもらう）。
- 本文: 権利・義務・条件・例外・数値・期間・当事者・条の番号は変えず、読みやすさだけを直した（yomiyasu の検査は「決まり」の立場で meaning_risk=0）。意味が動きうる直しは 1 か所: 第 4 条「以前にこの規約に違反して利用を止めた人」→「利用を止められた人」（「違反して」と第 11 条から、止めたのは運営者と読んだ）。迷ったところ（第 16 条 3・第 17 条・第 12 条 1 など）は原文のまま
- 版: TERMS_VERSION を 2026-10-18-2 に上げ、login.html の #agree・terms.html と privacy.html の「版 …」と改定の履歴をそろえた（worker.test.js が 4 か所を比べる）
- 同意し直し: 画面の答え（/api/screen/*）に、users.terms_version が今の版でない人（NULL を含む）だけ terms_update を付ける（1 行読むだけ）。画面（app.js agreeAgain）が同意するまで上に出し続け、チェックして「同意して続ける」で POST /api/agree（terms.agreeAction が版を確かめて terms_version・terms_at を書く）。保存の上限でも通す（既にある行の書き換えだけ）。同意しない人のために、アカウントの画面（ログアウト・退会）へのリンクを置く
