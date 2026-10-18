---
id: q-region-before-keep
type: question
status: open
date: 2026-10-18
title: 今週のおすすめは全国で並べて上位 400 件（KEEP）に切ってから都道府県で絞るので、全国 401 位より下の県の候補は出せず「その県のおすすめはありません」になりうる。並べ直し（spreadLeads）も絞る前（#118、起案者の判断）
sources:
  - https://github.com/island-6848/taguri-demo/issues/118
  - cloudflare/src/screens/recommend.js
links:
  - affects: dec-recommend-filter-tiers
---
コードで確かめたこと（2026-10-18）: rankedGroups が sameProduction のあと groups.slice(0, KEEP) にし、会場（都道府県）を読むのは残した分だけ。recommendScreen の filtered がそのあとで県を絞る。
- 案 1: 控えに入れる前に、県ごとに上位 TOP（15）件を必ず残す（全国 400 件＋県ごとの不足分）。会場を読むのが残す分より増え、控え（rec_cache の body）も大きくなる。D1 の読み取り・CPU の見積もりが要る
- 案 2: 選んだ県があるときだけ、その県の会場を先に絞ってから並べる（控えを県ごとに分ける。控えの行が増える）
- 案 3: いまのまま、0 件のときの説明を「全国の上位に入っていない」と分けて書く
- 推し: 案 1。ただし本物の索引で、400 件の外にどれだけ県の候補があるか（県ごとの件数）を先に数える。並べ直しを県ごとにするのは案 1 のあと
