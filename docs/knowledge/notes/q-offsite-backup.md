---
id: q-offsite-backup
type: question
status: open
date: 2026-10-13
title: バックアップをどこに、どう暗号化して、いつまで置くか
links:
  - depends_on: q-r2-boto3
verifies:
  - S07
  - S10
---
VM の外（R2 など）に置く。認証の情報を含むので暗号化し、削除の依頼と保持期間に合わせて消す。
