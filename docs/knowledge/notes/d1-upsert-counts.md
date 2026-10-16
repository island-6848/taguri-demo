---
id: d1-upsert-counts
type: finding
status: confirmed
date: 2026-10-16
title: D1 は upsert が既にある行に当たると 1 行 1（主キーの索引は書かない）、新しい行は 2 と数える。見積もりは全部を新しい行として数えるので、送り直しのときは約 2 倍多い。7009 で失敗と出た Catalog #7 の import は、実は D1 に入っていた
sources:
  - https://developers.cloudflare.com/d1/platform/pricing/
  - https://developers.cloudflare.com/d1/best-practices/use-indexes/
  - https://github.com/island-6848/taguri-crawler/actions/runs/38851892982
  - https://github.com/island-6848/taguri-crawler/actions/runs/38853274508
  - https://github.com/island-6848/taguri-crawler/actions/runs/38856122652
links:
  - depends_on: d1-writes-undercounted
  - affects: index-only-run-1016
---
起案者「3から進めて」（2026-10-16、書き込みの見積もりの見直し）。

- 公式（検索結果の引用で見た。ページそのものは開いていない）: INSERT・UPDATE・DELETE で触れた行ごとに数え、索引のある列を書くときは索引の分も 1 行足す（Use indexes）。upsert の数え方そのものは書かれていない
- 取得の実行のログ（一次情報）: Catalog #8 は 12,034 行（うち rec_stage 3,510）を送り、D1 の rows_written は 15,548 ≒ 12,034 ＋ 3,510。Catalog #9 は 2,841 行（rec_stage 145）で 2,998 ≒ 2,841 ＋ 145（＋消した 1 行の分）。どちらも「1 行 1 ＋ rec_stage の開始日の索引 1」で、新しい行なら 2 のはずの主キーの索引の分が無い。#8 の 1 つ目のファイルは last_row_id 0（新しい行が無い）
- つまり #8・#9 が送った行は、ほとんどが D1 に既にあった。#7（04:41 UTC）は wrangler が 60 秒で "Upstream service unavailable [code: 7009]" を返したが、import は D1 の側で終わっていた。#7 の 20,000 行（公演 3,897 件）の中に、#8・#9 の行がすべて入る。index-only-run-1016 の「D1 には入っていないはず」は誤り
- 今日（UTC 10-16）の D1 の実際の書き込み（取得の分）は、#7 約 43,897（新しい行として。数は読めていない）＋ #8 15,548 ＋ #9 2,998 ≒ 62,400。控えは 77,302 で、差の 1.5 万は #8・#9 の見積もり（全部を新しい行として数えた分）
- 見積もり（1 行 2 ＋ rec_stage 1）は新しい行には合っている（初回の残り 3.9 万行はすべて新しい行）。多めになるのは、既にある行を送り直すとき（毎日の差分で値だけ変わった行、失敗と出たのに入っていた分の送り直し）

分からないこと: wrangler の 7009 のあと、import が終わったかどうかを確かめる方法（終わっていれば送り直しは 1 行 1 で済むが、終わっていなければ 2）。UPDATE で値が変わらない列の索引を D1 が書くか（rec_stage の start は毎回 1 足されているように見える）。
