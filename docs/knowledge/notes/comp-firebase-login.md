---
id: comp-firebase-login
type: component
status: current
date: 2026-10-13
title: ログイン：Firebase Authentication（Google・メールリンク）
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/src/firebase-auth.js
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/src/client/login.js
---
Worker が ID トークンを自前で検証（RS256・Google の公開鍵・aud/iss/sub/exp/auth_time）し、D1 のセッションを発行する。ブラウザ側は inMemoryPersistence。プロジェクト taguri-97959。
