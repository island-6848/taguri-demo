---
id: dec-demo-seed-fictional
type: decision
status: proposed
date: 2026-10-18
title: 公開デモの見本 96 件を架空の題名・日付・会場に入れ替え、日報メールの宛先と差出人を手元の設定へ移す（今の版だけ。履歴は起案者が決める）
sources:
  - https://github.com/island-6848/taguri-demo/issues/122
  - tools/taguri/demo_purchase_works.json
  - tools/mail/send_daily_report.py
  - docs/demo-seed-ratings.md
links:
  - depends_on: sec-audit-1017
  - affects: demo-seed-link-rate
  - raises: q-pii-git-history
---
issue #122（〔sec-audit-1017〕の「起案者に決めてもらうもの」の 2 件）への対応。

## したこと
- `tools/taguri/demo_purchase_works.json` の 96 件を、すべて架空のものにした。題名は「見本：」で始め、会場は「架空劇場A」など。日付は 2021〜2025 年の作った日付で、未評価の 3 件は 2030 年。評価の数（◎28・○38・△18・×9・未評価3）と形は前と同じ。
- 実在の観劇の一覧になっていた `docs/demo-story-notes.md` の参照表と、`docs/demo-seed-ratings.md` の観劇予定の日付を外した。`tools/taguri/test_seed_demo.py` の、実在の公演の日時と会場を使った検査も架空の値に替えた。
- `tools/mail/send_daily_report.py` の宛先（第三者のメールアドレス 2 件）と差出人の名前を消した。`~/.config/nau-mail/report.json`（または環境変数 `DAILY_REPORT_TO`・`DAILY_REPORT_SENDER`）から読む。設定が無く `--to` も無いときは、送らずに止まる。

## 起案者に確かめてほしいこと（だから proposed）
- **デモの推薦が弱くなる。** 見本の題名と日付が出演者の控えと一致しなくなったので、`demo_seed_links` で結び付く記録が無い。見本の評価は「今週のおすすめ」の人物の点に効かない。戻すなら、実在の観劇日を使わない別の結び付け方（公開情報だけの公演 id に架空の評価を付けるなど）を決める。
- **持ち主のパソコンの設定が要る。** 日報を送るには、いままでの宛先を `~/.config/nau-mail/report.json` に一度書く。
- **過去の履歴には残っている。** 〔q-pii-git-history〕。

使う量は増えない（同じ件数の JSON を差し替えただけ。無料枠の数え方に変わりは無い）。
