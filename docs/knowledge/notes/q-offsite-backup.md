---
id: q-offsite-backup
type: question
status: answered
date: 2026-10-13
title: D1 のバックアップを、Time Travel の期間より長くどこに残すか
links:
  - depends_on: q-r2-boto3
verifies:
  - S07
  - S10
---
VM の外（R2 など）に置く。認証の情報を含むので暗号化し、削除の依頼と保持期間に合わせて消す。
Workers＋D1 に寄せたので、対象は D1。Time Travel は無料で 7 日・有料で 30 日（d1-time-travel）。それより長く残すなら R2 などへ書き出す。q-d1-backup と合わせて決める。
