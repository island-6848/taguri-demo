---
id: f-link-card-x-ok
type: finding
status: confirmed
date: 2026-10-20
title: X（Twitter）にリンクのカードが出るようになった（起案者が確認）
sources:
  - cloudflare/public/robots.txt
  - cloudflare/src/link-card.js
links:
  - answers: q-link-card-x
  - depends_on: dec-link-card
---
起案者の確認（2026-10-20）「Twitterのカード出た」。robots.txt を置いたあと（コミット 6122f9e）に確かめた。出なかった原因が robots.txt だったのか、配信の遅れや X の控えだったのかは、切り分けていない。
