---
id: find-session-past-trial-1022
type: finding
status: confirmed
date: 2026-10-22
title: セッションで過去公演の補完を 10 分試した。読み取りは動き（219 件・534 要求・9 分 50 秒）、作業データは state に書き戻した。D1 への送信は、セッションの安全判定で止められて未実施
sources:
  - https://github.com/island-6848/taguri-crawler/tree/state
  - tools/review/fetch_past_stages.py
  - cloudflare/scripts/deliver_past.py
links:
  - depends_on: q-crawl-in-session
---
**やったこと（2026-10-22 00:30〜00:43 UTC、Actions の Catalog が動いていないことを確かめてから）**
- 環境の設定: stage.corich.jp と api.cloudflare.com への接続を許可した。Cloudflare の鍵は、環境変数と、`/client/v4/accounts/` 宛てに付けるシークレットの両方で通った。トークンの値は見ていない。
- `fetch_past_stages.py --limit 520 --since 2019-01-01 --max-minutes 10` の結果:
  - 新しい過去の公演 219 件（読んだページ 30,551 → 30,770、行 30,414 → 30,633）
  - 題名の読み直し 156 件、あらすじの読み取り待ち +144 件
  - stage.corich.jp への要求 534 件。かかった時間 9 分 50 秒
- `deliver_past.py build` の結果: 送るのは 6,221 行、D1 の書き込みの見込みは 19,999 行（1 回の上限）。送る前の past_delivered は 23,347 行。6,221 行のうち今回の 219 行以外は、Actions が止まっていた間に読み取り済みで、D1 に未送信の分。
- `wrangler d1 execute` は、起案者が「進めて」と答えた後でも、Claude Code の自動の安全判定（本番への反映）で 2 回とも断られた。送っていない。past_delivered も変えていない。
- 作業データは、state ブランチに通常の push（fast-forward、76b8336）で書き戻した。D1 には、次に Actions の Catalog が動いた日に送られる。

**2026 年の過去の公演がどこにあるか（作業データを数えた）**
- 会期が 2026-01〜03 に終わった公演は、過去の公演の一覧（data/past/stages.jsonl）にある。D1 にもほぼ送ってある（未送信は 1 件）。
- 2026-04 以降に終わった公演は、毎日の一覧（data/review/candidates.jsonl、終わって 180 日以内）にある: 4 月 141・5 月 571・6 月 519・7 月 595・8 月 652・9 月 587・10 月 410 件。fetch_past_stages は、この一覧にある公演を読み直さない（known_ids）。
- これらを D1 に入れるのは毎日の Catalog（deliver_catalogue.py）。Catalog は 10/17 から止まっているので、10/17 以降に新しく載った・変わった分は D1 に入っていない。

**分からないこと**
- 本番の D1 に、2026 年の公演が実際に何件入っているか（読み出しは、今回は数えていない）。
