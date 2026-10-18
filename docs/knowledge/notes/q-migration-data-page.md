---
id: q-migration-data-page
type: question
status: open
date: 2026-10-18
title: アカウントの画面から行く /migration-data/ が、移行前の記録の画面のまま
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/public/migration-data/index.html
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/src/screens/account.js
links:
  - affects: dec-account-page
  - affects: comp-passkeys
---
アカウントの画面の「パスキーを追加・削除する」「復旧コードを作り直す」は /migration-data/ へ行く。通し検証〔e2e-walk-1018〕では、パスキーの欄は使えたが、同じページに「観劇記録 0件」（日記帳には 8 件）・「観劇記録を追加」・「お気に入り」・「移行用JSONを取り込む」・「ログアウト」が並んでいた。これらは移行前の表（records・favourites）を読み書きし、サービス版の画面には出ない。

パスキーと復旧コードの欄をアカウントの画面へ移すか、/migration-data/ から古い欄を外すかを決める。外すときは、移行前の表に残っている人の記録を移す手順も要るかを確かめる。
