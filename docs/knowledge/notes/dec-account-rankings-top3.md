---
id: dec-account-rankings-top3
type: decision
status: adopted
date: 2026-10-21
title: アカウントの団体・劇場のランキングは 3 位まで。1 のもの（1 作品・1 回）は出さず、同じ数は 1 行に併記する
sources:
  - cloudflare/src/screens/account.js
  - web/theme.css
  - cloudflare/test/account-stats.test.js
links:
  - supersedes: dec-account-rankings
  - answers: q-account-rankings-look-1021
  - affects: dec-account-page
---
起案者の指示（2026-10-21）「1作品のものは端折ってよい。同率の場合は併記して。つまりそれぞれ3行以内に抑えてください」。

- 数が 1 の名前（団体・劇場の作品数が 1、劇場に行った回数が 1）は出さない
- 同じ数の名前は 1 行に「、」で区切って並べる（名前の順）。順位は上に何件あるかで付ける（1 位が 2 件なら次の行は 3 位）
- 3 位より下の行は出さないので、どの一覧も 3 行以内
- 劇場で片方の数え方だけ 2 以上が無いとき（1 作品を何回も観た、など）は、その欄に「2 作品以上の劇場はまだありません」のように一言だけ出す。記録はあるがどちらにも出るものが無いときは「2 作品以上観た団体や劇場ができると、ここに出ます」
- 前の決定（dec-account-rankings）の残りの部分（順位の札・棒・作品数は題名の鍵で数える・行った回数は times と merged を足す・radio と CSS だけで切り替える）はそのまま
- 電話の幅（390px）と広い幅で写しを撮って確かめた
