---
id: d1-writes-undercounted
type: finding
status: confirmed
date: 2026-10-15
title: 取得の D1 の書き込みの見積もりが、主キーの索引への書き込みを数えておらず、実際（D1 の rows_written）より 1.5〜2 倍少なかった。見積もりを直した。毎日の索引の全入れ替えは、索引が大きいと無料枠を越える
sources:
  - https://github.com/island-6848/taguri-crawler/actions/runs/38646724578/job/116135281670
  - cloudflare/scripts/deliver_catalogue.py
  - cloudflare/scripts/deliver_past.py
links:
  - depends_on: d1-meta-size-after
  - affects: dec-free-tier-only
  - raises: q-index-incremental
---
Catalog #5 のログ: 過去の公演 10,001 行の投入で D1 の rows_written は 30,000。見積もりは 1 行 2（行と tkey の索引）で 20,000 と控えていた。D1 は索引への書き込みも rows_written に数え（d1-meta-size-after）、たぐりの表はどれも TEXT や複数列の主キーなので SQLite が主キーを別の索引に持つ。1 行の書き込みは「行＋主キーの索引＋ほかの索引」。ポスター（poster 表、ほかの索引なし）は 2,500 行で 5,000 と見積もりどおりだった。
- 直したこと（2026-10-15）: 過去の公演 1 行 3、公演一覧 1 行 3（catalogue_date の索引）、venue_pref・rec_meta 1 行 2、索引・題名・カードは 1 行 2（行と主キー）＋ rec_stage_start の分。前の版を消す分は、前の版があるときだけ 2 倍（初回の索引は消す分が無い）
- 影響: 見積もりが少なかったので、控えの 8 万の手前で止める歯止めが、実際には 12〜16 万まで書かせる恐れがあった（D1 の無料枠は 1 日 10 万行。越えると請求ではなく、その日の書き込みが失敗する ── 利用者の記録も保存できなくなる）。実際にこれまで越えたかは、Cloudflare のダッシュボードの D1 の数で確かめていない
- 分かっていないこと: 推薦の索引の行数。初回は 2×行数で入る見込みだが、毎日の版の入れ替え（入れる＋前の版を消す＝4×行数）は、行数が 2 万を越えると 8 万の控えに収まらず「skipped」になり、索引が古いまま残る（q-index-incremental）
