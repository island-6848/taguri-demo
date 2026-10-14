---
id: dec-account-cap-counted
type: decision
status: adopted
date: 2026-10-14
title: 利用者の上限は数えて決めた：300 人まで・新規は 1 日 30 人まで。D1 の大きさを Worker が見て 4 GB で書き込みと登録を止め、上限の無かった 5 つの表に 1 人あたりの件数の上限を付ける
sources:
  - cloudflare/src/free-tier.js
  - cloudflare/src/rate-limit.js
  - cloudflare/src/worker.js
  - cloudflare/migrations/0021.sql
  - cloudflare/test/free-tier-d1.test.js
links:
  - answers: q-account-limit-100
  - depends_on: d1-free-limits
  - depends_on: dec-free-tier-only
  - affects: dec-login-hardening
---
起案者の指示（2026-10-14）「数えてから決めて」（100 人の上限を外したままにするか）。
- **保存（5 GB）は人数では守れない。** ふつうの人は 0.7 MB だが、長い文字で埋めると 1 人 218 MB 以上〔user-storage-measured〕で、20 人ほどで尽きる。そこで (1) D1 が返す大きさ（meta.size_after）〔d1-meta-size-after〕を Worker が 1 分に 1 回見て、4 GB（8 割）に達したら、増える書き込みと新規登録を 503 で止める（見ること・消すことは続けられる）。(2) 0021 で、件数の上限が無かった visit_note・hand_credits・excluded・merges（各 2,000）と search_request（200）に上限を付けた
- **読み（1 日 500 万行）が人数を決める。** よく使う人 1 人で 1 日約 3.5 万行（1 画面 300〜600 行×30 回＋推薦の計算し直し約 1 万行×2）と見積もり、8 割の 400 万行で約 110 人。3 人に 1 人が毎日使うとして **300 人**にした。見積もりなので実測で見直す〔q-d1-reads-real〕
- **書き込み（1 日 10 万行、取得が 8 万）**: 利用者の分は 2 万行。新規を 1 日 30 人にして、登録が集中した日に書き込みを使い切らないようにした（以前は 200 人）
- D1 の無料枠は越えても請求されず、その日は止まるだけ（R2 と違う）。なので大きさが読めないときは止めない（サービスを落とさない）。数字は free-tier.js（D1_BYTES_CAP・MAX_ACCOUNTS・NEW_ACCOUNTS_PER_DAY）にだけ書く。/api/health の free_tier に d1_bytes・accounts と上限を出す
- PR #17（dec-login-hardening）の「100 人の上限を外す」は、0001 のトリガーを外したまま、Worker 側の 300 人に置き換えた
