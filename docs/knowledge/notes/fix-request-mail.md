---
id: fix-request-mail
type: finding
status: unverified
date: 2026-10-17
title: Worker から Gmail の SMTP（465・TLS）で自分宛てにメールを送れる見込み（Workers の TCP ソケット・Gmail のアプリ パスワード・1 日 500 通）
sources:
  - https://developers.cloudflare.com/workers/runtime-apis/tcp-sockets/
  - https://support.google.com/mail/answer/22839
  - https://support.google.com/accounts/answer/185833
links:
  - affects: impl-fix-request
---
このセッションは developers.cloudflare.com などに通信できない（ネットワークの設定で拒否）ため、公式のページを今回は読めていない。以下は手持ちの知識で、確かめていない。
- Cloudflare Workers の TCP ソケット（`connect()`、`secureTransport: "on"`）で外の SMTP に TLS でつなげる。25 番は塞がれているが 465/587 は使える。無料プランでも使える見込み
- Gmail は 2 段階認証を有効にすると「アプリ パスワード」を作れ、SMTP の AUTH PLAIN に使える。個人の Gmail の送信は 1 日 500 通まで（越えると一時的に送れなくなる。請求はない）
- 分からないこと: 無料プランでの TCP ソケットの扱いと、Gmail がアプリ パスワードを今後も受け付けるか。本番で 1 通送れたら confirmed にする
