---
id: dec-system-test-design
type: decision
status: proposed
date: 2026-10-20
title: システムテストは 116 ケース（必須 99）。本番・Cloudflare・実機は起案者が流し、Claude は手順と記録を用意する。Time Travel・migration の失敗は試験用の別の D1（taguri-st）で試す
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/docs/system-test-spec.md
  - https://github.com/island-6848/taguri-demo/blob/master/docs/system-test-procedure.md
  - https://github.com/island-6848/taguri-demo/blob/master/docs/backup-restore.md
links:
  - depends_on: dec-system-test-plan
  - depends_on: dec-free-tier-only
  - affects: q-d1-migration-failure
  - affects: q-workers-cpu-real
  - affects: q-passkey-real-devices
  - affects: q-safari-cookies
  - affects: q-firebase-user-deletion
---
仕様書 `docs/system-test-spec.md` と手順書 `docs/system-test-procedure.md` で決めたこと:

- ケースは計画書の項目 ID に連番を付ける（例: FN-01-02）。116 ケース、うち必須 99。Claude が流すのは 75、起案者・ベータ参加者が 41
- 判定は OK・NG・保留・対象外の 4 つ。証拠が無ければ OK にしない。ローカルの OK は本番のケースに数えない。不具合は致命・重い・軽いの 3 段
- 全体の合格: 必須 100% OK、任意 8 割以上 OK（NG・保留は理由つき）、致命・重いの未解決 0、最後の回帰で新しい重い以上 0、消失・混在 0、無料枠 8 割未満・請求 0 円、S11・S25 済み
- **担当の分け方:** Claude の作業環境からは本番の Worker に届かない（2026-10-20、`curl https://app.taguri.workers.dev/api/health` がプロキシの 403）。Cloudflare の口座の鍵も、非公開の taguri-crawler も無い。だから本番・`wrangler --remote`・taguri-crawler・実機は起案者が流し、Claude は手順・SQL・記録の下書きを用意して結果を判定の案にする。公開リポジトリの Actions（Service watch・Catalog age の手動実行）は Claude が動かせる
- **Time Travel は戻す先を選べず、その D1 自身が戻る**（`docs/backup-restore.md` の「本番の D1 がその時点に丸ごと戻る」）。だから S07 の試験は本番では行わず、試験用の `taguri-st` に記録を入れて戻す。migration の途中の失敗〔q-d1-migration-failure〕も `taguri-st` で試す。書き込みは 1 回 100 行以内（口座の 1 日の枠を本番と分け合う）
- 見張りをわざと鳴らす: Service watch は存在しない URL、Catalog age は `max_days=-1`（今日のカタログでも 0 > -1 で失敗する。`check_catalog_age.py` の `age > max_days`）
- 書き足す試験・道具: `st-escape.test.js`・`st-headers.test.js`・`st-owner-only.test.js`・`st-log-marker.js`・`st_seed_users.mjs`・`st_measure_screens.mjs`（おすすめ以外の画面の CPU を測る道具は今は無い）

分かっていないこと: D1 の数の上限など、試験用の D1 を作ることの無料枠の条件は公式の料金表でまだ確かめていない（作ったら試験のあと消す）。起案者がこの分け方を認めるか。
