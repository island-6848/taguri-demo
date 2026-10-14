---
id: dec-scale-workers
type: decision
status: superseded
date: 2026-10-13
title: 1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる
sources:
  - docs/service-roadmap.md
links:
  - affects: q-direction
  - depends_on: q-real-catalog-stats
  - depends_on: q-crawler-host
verifies:
  - S12
---
勧めとして出した（起案者は未決定）。理由: 費用は小さいうちは 0 円、1000 人でも月 5 ドルで足りる。サーバーの OS 更新・バックアップ・回収の心配を自分で抱えずに済み、7〜30 日前まで戻せる。無料の VM は 1000 人でも 0 円で動くが、1 台が止まると全員の記録に届かず、回収・障害・保守の負担をすべて運営者が負う。1000 人の記録を預ける前提では、月 750 円ほどを払って任せる方が安全と判断した。取得処理は別の機械が要る（q-crawler-host）。
（2026-10-13、起案者が Workers＋D1 に寄せると決めた）採用。
2026-10-13、起案者の指示「必ず無料の範囲内にして。絶対超えないで」で、有料プランに上げる部分を取り消した（dec-free-tier-only）。Workers＋D1 に寄せることは変わらない。
