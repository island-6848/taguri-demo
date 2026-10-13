---
id: q-r2-poster-growth
type: question
status: open
date: 2026-10-13
title: ポスターが R2 の上限 8 GB に近づいたら、どれを消すか
links:
  - affects: dec-posters-r2
  - affects: dec-free-tier-only
---
deliver_posters.py は上限の手前で入れるのをやめる（入らなかったポスターは作業データに残り、state ブランチがまた膨らむ）。1 枚の大きさと 1 日に増える枚数はまだ測っていない（最初の R2 への取り込みのあと、Free-tier check の表で分かる）。案: 終わって 1 年を過ぎ、誰の記録にも結び付いていない公演のポスターを R2 から消す（消すのは Class A に数えない見込み。未確認）。
