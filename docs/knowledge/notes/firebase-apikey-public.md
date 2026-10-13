---
id: firebase-apikey-public
type: finding
status: unverified
date: 2026-10-13
title: Firebase の Web 用 API キーは秘密ではない（使える範囲は承認済みドメインとキーの制限で絞る）
sources:
  - https://firebase.google.com/docs/projects/api-keys
links:
  - raises: q-firebase-key-restriction
---
Firebase の説明に基づく理解。この環境からは公式文書を読み直せていない。キーの制限（Web サイト・Identity Toolkit / Token Service のみ）は起案者の側でまだ。
