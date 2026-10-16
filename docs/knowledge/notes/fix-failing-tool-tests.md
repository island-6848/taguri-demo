---
id: fix-failing-tool-tests
type: finding
status: confirmed
date: 2026-10-16
title: 落ちていた道具の試験 6 本のうち、1 本は本物の不具合（名前の頭の「作」を役職として削っていた）、3 本は試験か環境の側、2 本は本人の記録が要るものだった。CI に 10 本足した
sources:
  - tools/review/measure_nets.py
  - cloudflare/src/screens/credits.js
  - tools/taguri/test_digest.py
  - tools/taguri/test_impressions.py
  - tools/taguri/test_state_backup.py
  - .github/workflows/recommendation-loop.yml
---
起案者「次は4（落ちてる試験）やって」（2026-10-16）。リポジトリのコードと実行結果から（一次情報）。
- **本物の不具合**（test_measure_nets・test_interest_roster）: `_ROLE_PREFIX` が役職の語（作・訳・演出 …）を、後ろに区切りが無くても名前の頭から削っていた。「作り手24」が「り手24」に、実在の名前なら「作間龍斗」が「間龍斗」になる。最初の版からあった（f663083）。区切り（空白・コロン・中黒・=・|）があるときだけ外すようにした（Python と credits.js の両方。一致の試験に例を足した）。作業データで比べると、旧は「作曲」を「曲」、「演出助手」を「助手」という名前にしていた。新は役職の語のまま残り、ROLE_VOCAB で名前から外れる。索引を次に作るとき、直った名前の分だけ差分が出る
- **試験が古い**（test_digest）: 日付の見出しは 2026-08-26 に h3 から `<details class="dgday">` に変えていた。試験を合わせた
- **試験が手元のデータに頼っていた**（test_impressions）: 会場の移し替えの確かめが、本人の記録の DB の行を前提にしていた。試験の中で 1 行足すようにした。「実データを読める」「引用を出せる作り手がいる」は本人の記録が無いと確かめられないので、無いときは「確かめない」と出す（あるときは今までどおり）
- **環境の差**（test_state_backup）: `with sqlite3.connect(...) as con:` は commit するだけで閉じない。Python 3.13 は閉じていない接続に ResourceWarning を出し、それが試験の読むログに混ざった。CI は 3.12 なので出ていなかった。試験の中の接続を closing で閉じた
- **本人の記録が要る**（test_rate_performances）: 買った回のデータ（メールから取り出す）を確かめる道具で、公開リポジトリには無い。直さない
- CI（recommendation-loop.yml）に入っていなかった 10 本を足した（test_rate_performances を除く）。CI の 33 本は、きれいに取り出したリポジトリで全部通ることを確かめた
