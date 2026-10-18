---
id: q-privacy-ical-url
type: question
status: open
date: 2026-10-18
title: プライバシーポリシーに、Google カレンダーの非公開アドレスがたぐりのサーバーを通ることを書くか
sources:
  - cloudflare/public/privacy.html
  - cloudflare/src/screens/settings.js
  - cloudflare/test/register-text.test.js
---
規約・プライバシーポリシーの文体を直したとき（〔dec-legal-style-no-reagree〕）に気づいた食い違い。中身は変えない指示だったので本文は直していない。

- プライバシーポリシー第 5 条第 3 項第 4 号は「カレンダーをブラウザの中で読み取る」「本サービスに送るのは題名の候補と日付…カレンダーの本文は送らない」と書く。
- 一方、観劇記録を追加の画面（src/screens/settings.js、試験 register-text #91）は、非公開アドレス（iCal の URL）を貼ったときは「アドレスをたぐりのサーバーに送り、サーバーが Google からカレンダー全体を取ってきて、この端末に渡します（保存はしません）」と書いている。
- この読み方（サーバーを通る経路）がプライバシーポリシーに無い。書き足すなら中身の変更なので、版を上げて同意し直してもらうかも含めて起案者が決める。
