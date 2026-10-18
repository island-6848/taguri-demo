---
id: free-tier-audit-1018
type: finding
status: confirmed
date: 2026-10-18
title: 使う側を全部足しても、R2 は保存 8.5 GB・Class A 約 30 万回・Class B 約 330 万回で無料枠に収まる。D1 の書き込みは取得・管理・予行・定期実行で 1 日 約 9.35 万行、残りが利用者の分
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/docs/free-tier-audit-2026-10-18.md
  - https://github.com/island-6848/taguri-crawler/actions/runs/39084288296
  - https://github.com/island-6848/taguri-demo/issues/139
links:
  - supports: dec-free-tier-only
  - raises: q-r2-ledger-reconcile
  - raises: q-d1-user-writes-uncapped
  - raises: q-workers-builds-minutes
  - affects: q-d1-reads-real
---
issue #139 の点検。リポジトリのコードの読み合わせと、本番の取得（taguri-crawler の Catalog #12、2026-10-18 04:09 UTC）の Free-tier check の表から数えた。一次情報（コードと実行の記録）だけで確かめたので confirmed。合算の表と使う側ごとの表は `docs/free-tier-audit-2026-10-18.md`。

本番の今の量（Catalog #12）: Actions 直近 31 日 886／1,500 分（59%）、D1 の取得の書き込み 47,547／80,000 行（59%）、R2 の保存 367 MB／8 GB、Class A 6,653／30 万回、Class B 1,822／300 万回。8 割を越えたものは無い。名前の索引は 256 ファイル（69 MB）をその日すべて送った。D1 の大きさは 48.6 MB（meta.size_after）。

分かったこと:
- 共通の控えを見ずに使っていたもの: 修正依頼の片付け（上限なし、最悪の日 約 8,000 行）・ポスターのやり直し（上限の 1 回手前から 3 回まで送れた）・控えの入れ物の確かめ（lifecycle の PUT などを数えていない）・戻す予行（新しい D1 への書き込みと Actions の分を数えていない）。dec-free-tier-audit-fixes-1018 で直した
- 管理画面の控えは取得の控えと別のファイルで、取得の R2 の保存を知らない。別の上限（0.5 GB）で合計を 8.5 GB に抑えた
- 取得のジョブは state ブランチを取り出せないと初回として続け、空の控えで R2 に入れ、最後に空の控えで state を上書きしていた（R2 にある分を数えなくなり、請求の恐れ）。雛形で止めるようにした
- Actions は過去の公演とポスターの読み取りが残りを使う作りなので、続けると直近 31 日が上限の 8 割（1,200 分）を越えて通知が出る見込み。上限を越えたわけではない
- 数えていないもの: D1 の読み出し・Worker の D1 の書き込みの全体・Workers の要求・Workers Builds の分。どれも越えると止まる側（請求なし）

分からないこと: 控え（台帳）の数と、Cloudflare・GitHub の画面の数の差（突き合わせていない）。利用者が 1 日に書く・読む行数の実測。
