---
id: cross-origin-cookies
type: finding
status: confirmed
date: 2026-10-13
title: Pages と Render は別サイトなので、Cookie が別サイトの扱いになる
sources:
  - tools/taguri/serve.py
  - web/app.js
links:
  - supports: dec-own-domain
  - raises: q-safari-cookies
  - affects: comp-frontend
verifies:
  - S04
---
github.io の画面から onrender.com の API を呼ぶため、Cookie に SameSite=None; Secure を付けている。別サイトの Cookie はブラウザに弾かれることがある。
