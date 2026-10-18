---
id: q-pii-git-history
type: question
status: open
date: 2026-10-18
title: 公開リポジトリの過去の履歴に残る観劇記録と第三者の連絡先を、履歴から消すか（force push と、複製・フォークへの影響を含めて起案者が決める）
sources:
  - https://github.com/island-6848/taguri-demo/issues/122
links:
  - depends_on: dec-demo-seed-fictional
---
〔dec-demo-seed-fictional〕で今の版からは消したが、過去のコミットには残っている。履歴は書き換えていない。

過去の版に残っているもの（値はここに書かない）:
- `tools/taguri/demo_purchase_works.json`：持ち主の観劇の記録 96 件（題名・日付・開演時刻・劇場）。2026 年 10〜11 月の予定を含む。
- `docs/demo-seed-ratings.md`：未評価 3 件の題名と観劇予定日。
- `docs/demo-story-notes.md`：見本の位置ごとの作品名の表（観た作品の一覧）。
- `tools/taguri/test_seed_demo.py`：1 件の公演の日付・劇場・開演時刻。
- `tools/mail/send_daily_report.py`：第三者 2 人の勤め先のメールアドレスと、その 2 人の姓（`--to` の説明）、差出人の姓。

決めること:
- 履歴から消すか（`git filter-repo` などで書き換え、force push。ほかのブランチ・作業中のセッション・フォークや複製には残る）。
- GitHub のキャッシュ（古いコミットの URL）を消す依頼をするか。
- 第三者 2 人に知らせるか。
