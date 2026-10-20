---
id: f-deliver-past-reads
type: finding
status: confirmed
date: 2026-10-20
title: 過去の公演の送り直し（deliver_past の people・題名の UPDATE）が、取得の 1 回で D1 を 1,527,180 行読んでいた（1 日 500 万行の 3 割）。相関の副問い合わせを UPDATE … FROM に替え、150 行の文で 23,400 → 600 行にした
sources:
  - https://github.com/island-6848/taguri-crawler/actions/runs/39390407820
  - cloudflare/scripts/deliver_past.py
  - cloudflare/test/test_deliver_past.py
  - https://github.com/island-6848/taguri-demo/issues/242
links:
  - depends_on: d1-free-limits
  - affects: d1-reads-over-1020
  - affects: dec-past-title-backfill
---
issue #242 の点検の途中、取得のログで見つけた（2026-10-20）。

- **見たもの。** Catalog #17（2026-10-20 08:01 UTC、taguri-crawler）の「Deliver the new past stages to D1 (past_stage)」。wrangler が返した数は、文 69・`Rows read` 1,527,180・`Rows written` 10,000。書いたのは 1 万行なのに、読んだのは 150 万行だった。
- **原因。** 送り直しの文（_people_updates・_title_updates）の形が `WITH v(...) AS (VALUES …) UPDATE past_stage SET people=(SELECT p FROM v WHERE v.id=past_stage.stage_id) … WHERE stage_id IN (SELECT id FROM v)` だった。
  - SQLite はこれを、書き換える 1 行ごとに v を全部なめる形で動かす（EXPLAIN QUERY PLAN に CORRELATED SCALAR SUBQUERY が 2 つ）。1 文が約 150 行なので、1 文で 150 × 150 の読み出しになる。
  - 手元の D1（wrangler の getPlatformProxy、past_stage 2 万行）で 1 文を測った。前の形は rows_read 23,400・rows_written 150。`UPDATE past_stage SET people=v.p, synopsis=v.s FROM v WHERE past_stage.stage_id=v.id` は rows_read 600・rows_written 150。
  - 23,400 × 69 文 ≈ 160 万行で、ログの 152 万行とほぼ合う。
- **10-20 の上限越えとの関係。** 越えた日（UTC の 10-20）に、取得がこの 150 万行を読んでいた。〔d1-reads-over-1020〕が見つけた候補の全件読み（1 回 30,453 行）と合わせて、500 万行に届いた。どちらがどれだけ効いたかは、ダッシュボードの日ごとの数でしか分からない（確かめていない）。
- **直したこと。** 2 つの文を UPDATE … FROM にした。試験（UpdateReadsTest）は、どの文の EXPLAIN QUERY PLAN にも CORRELATED が無いこと、書き換えた中身が前と同じことを確かめる。前のコードでは落ちる。
- **まだ見ていないこと。** 無料枠の点検（free_tier.py check）の表には D1 の読み出しの行が無い。取得の段が読んだ数（wrangler の Rows read）を足して数えるかは、別に考える〔q-crawl-d1-reads-counted〕。
