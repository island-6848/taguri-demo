---
id: dec-sweep-recheck
type: decision
status: adopted
date: 2026-10-18
title: 記録の無いアカウントの片付けは、消す文ごとに「まだ空で、1 か月ログインしていない」を確かめ直す
sources:
  - cloudflare/src/cleanup.js
  - cloudflare/test/cleanup.test.js
  - https://github.com/island-6848/taguri-demo/issues/137
links:
  - depends_on: dec-signup-cap-atomic
  - affects: comp-d1
---
見つけたこと（コードで確認、2026-10-18）: sweepEmptyAccounts は、消す人を選ぶ SELECT と、1 人ずつの削除の batch が別だった。選んだ直後にその人がログインして記録を足すと、記録ごと消えるおそれがあった（間はごく短いが、「記録のあるアカウントは消さない」に反する）。

決めたこと: 削除の各文（ACCOUNT_TABLES と users）に、選ぶときと同じ条件を `EXISTS (SELECT 1 FROM users g WHERE g.id=?1 AND ...)` として足す。D1 の batch は 1 つのトランザクションとして順に実行される（dec-signup-cap-atomic と同じ前提）ので、条件が成り立てば全部消え、成り立たなければ何も消えない。消した数は users の削除の changes で数える。利用者が自分でアカウントを消すとき（deleteAccount）は条件を付けない。

無料枠: 確かめは主キーの索引で引く NOT EXISTS が 1 文に十数個、1 人 20 文ほど、1 日 50 人まで。読み出しは 1 日数万行にも届かず、D1 の無料枠に響かない。書き込みは変わらない。

試験: 選んだ直後に記録を足すと消えないこと（cleanup.test.js。条件を外すと落ちることも確かめた）。
