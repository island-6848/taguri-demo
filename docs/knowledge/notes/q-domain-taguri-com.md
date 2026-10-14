---
id: q-domain-taguri-com
type: question
status: open
date: 2026-10-14
title: 本番の URL を taguri.com にするか（独自ドメインは年額がかかり、無料だけの約束と食い違う）
links:
  - depends_on: workers-dev-subdomain-rename
  - affects: dec-free-tier-only
  - affects: q-domain
---
起案者の希望（2026-10-14）「本番のurl、taguri.comにしたい」。ところが dec-free-tier-only（起案者の指示 2026-10-13「必ず無料の範囲内にして」）で、独自ドメインは使わないと決めている。.com は登録に年 10〜11 ドルかかる（無料枠は無い）。変えられるのは起案者だけなので、どちらにするかを聞く:
1. taguri.com を取る（年額を払う。無料だけの約束に「ドメインだけは例外」を足す。taguri.com が空いているかは起案者が登録事業者の画面で確かめる。パスキーはドメインに結び付くので、使い始める前に決めるのがよい〔passkey-rpid-domain〕）
2. 無料のまま workers.dev の名前を整える（例: アカウントの名前を taguri にし、Worker の名前を app にすると app.taguri.workers.dev。名前が空いていれば）
