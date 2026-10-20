---
id: fix-conquest-record-venue
type: decision
status: adopted
date: 2026-10-20
title: 劇場制覇マップは、記録に書いた劇場を、結び付いた公演の劇場より先に見る（ツアーの別会場の公演に結び付いた記録で、観た劇場が塗られなかった）
sources:
  - cloudflare/src/screens/conquest.js
  - cloudflare/test/conquest.test.js
  - https://github.com/island-6848/taguri-crawler/blob/state/d1/delivered.json
links:
  - affects: comp-cf-worker
---
起案者の指摘（2026-10-20）「眺めるの行ったことある劇場のとこ、キャナルシティ劇場追加したのに福岡が塗られなかったのなぜ？修正」。

- データの側は揃っていた: 取得の行でキャナルシティ劇場は 122 件とも同じ書き方で福岡県（candidates 17・past 105）。配送済みの分母の表（venue_census）にも「キャナルシティ劇場 → 福岡県」がある
- 原因: visitedVenues が、記録が公演に結び付いていると公演の劇場（rec_stage.entry.theater・past_stage.venue）を先に使い、記録に書いた劇場（works.venue）を見ていなかった。ツアーの公演で別の会場（東京の劇場など）の番号に結び付いた記録は、観た劇場をキャナルシティ劇場にしても東京が塗られる。手元の試験で再現した
- 直し: 記録に劇場が書いてあればそれを使う。県は、公演の劇場と同じ名前のときだけ公演の県、違えば分母の表・劇場名の表で引く。記録に劇場が無ければ前のとおり公演の劇場
- 本番の起案者の記録がこの形だったかは、本番の D1 を見られないので確かめていない（同じ症状になる道はこれだけだった）
