---
id: synopsis-coverage-1016
type: finding
status: confirmed
date: 2026-10-18
title: 本番の取得（state ブランチ、2026-10-16 22:27 UTC）では、終わっていない候補 1,353 件すべてがあらすじの読み取り済み。あらすじあり 836 件（62%）、題材の語あり 1,109 件（82%）
sources:
  - https://github.com/island-6848/taguri-crawler/blob/state/credits/themes.jsonl
  - https://github.com/island-6848/taguri-crawler/blob/state/review/candidates.jsonl
links:
  - affects: q-synopsis-lit-gaps
  - affects: q-synopsis-routine-quota
  - affects: q-prompt-g2-base
---
taguri-crawler の state ブランチ（作業データ 2026-10-16T22:27Z daily）の credits/themes.jsonl を数えた（2026-10-18）。

- 行数 1,353。すべて side=candidate、model=claude-routine、prompt_version=g2、at=2026-10-16
- review/candidates.jsonl は 4,813 件、うち終わっていない（ended でない）1,353 件。**その全件に行がある**
- あらすじあり 836、題材の語あり 1,109、**語はあるがあらすじが空 273**（c6 から、あらすじが無くても語を残す。この 273 件の語は本文と照らす手立てが無い）
- 「本文に無い」で落ちた 31。読み取り待ち（synopsis_queue.jsonl）に 31 件残っている
- 1 行あたりの語の数: 0 が 244、上限の 8 が 272（20%）。異なる語 2,149
- 多い語: ミュージカル 138、恋愛 130、家族 90、コメディ・ファンタジー 67、バレエ 66、夢 56、落語 50

分かったこと: 10/13〜15 の「ほぼ空」は解消していて、**量は足りている。次は質（別の公演の混入・語の根拠）**。
分からないこと: D1（本番の画面）に何件届いているか（本番の URL にはこのセッションから届かない）。
1,353 件が同じ日付なのは、`at` が読んだ日ではなく書いた日（`to_row`・`--import-answers` で `datetime.date.today()`）だから（コードで確かめた）。相手のセッションによれば定期実行（trig_01Y7a7jwMQpEgcCiTdkwwVaK）は 1 回 60 件・1 日 4 回（最大 240 件/日）で、1,353 件を 1 日では読めない。まとめて読んで 10/16 に取り込んだと見られるが、誰がいつ読んだかは確かめられていない。
