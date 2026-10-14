---
id: dec-free-tier-only
type: decision
status: adopted
date: 2026-10-13
title: たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる
sources:
  - docs/free-tier-budget.md
  - cloudflare/scripts/free_tier.py
  - cloudflare/src/free-tier.js
  - cloudflare/migrations/0014.sql
  - tools/taguri/deploy/github-actions/catalog.yml
links:
  - supersedes: dec-scale-workers
  - depends_on: r2-free-tier-billed
  - depends_on: gha-minutes-reset-budget
  - depends_on: d1-free-limits
  - depends_on: workers-free-cpu-10ms
  - affects: dec-auto-link-past
  - affects: dec-posters-r2
  - affects: q-native-cutover
  - raises: q-free-tier-account-settings
  - raises: q-r2-poster-growth
---
起案者の指示（2026-10-13）「必ず無料の範囲内にして。絶対超えないで。つねに警戒してチェックして。全資料に書き込んで、厳重に管理して。」
**有料のプラン・従量課金には上げない**（以前の勧め dec-scale-workers「上限に近づいたら月 5 ドルに上げる」は取り消し）。無料枠に収まらなくなったら、新規登録を止める（ALLOW_REGISTRATION=false）・取得を減らすなど、使う量を減らす側で対応し、起案者に知らせる。この方針を変えられるのは起案者だけ。
上限（数字は cloudflare/scripts/free_tier.py の CAPS と cloudflare/src/free-tier.js にだけ書く。一覧は docs/free-tier-budget.md）:
- GitHub Actions（非公開の taguri-crawler）: 無料 月 2,000 分 → **直近 31 日で 1,500 分**。Catalog のジョブの最初の段が GitHub の API で分数を数え、これからの 31 日のどの区切りでも収まるときだけ動かす（請求の月の区切りがどこでも越えない）。過去の公演はその残りで読む（1 日 0〜135 分）。読めなければ過去の公演は読まない
- D1 の書き込み: 無料 1 日 10 万行 → **取得の分は 1 日 8 万行**。書く前に作業データの控え（data/free_tier/usage.json）に足す
- R2（**越えると請求が来る**）: 保存 10 GB → **8 GB**、Class A 月 100 万回 → **30 万回**（PUT は送る前に数える）、Class B 月 1,000 万回 → **300 万回**（Worker が D1 の usage 表に抜き取りで数え、届いたら R2 を読まずに Render へ回す。D1 が読めないときも R2 を読まない）
- Workers・D1 の読み・Workers Builds・Render・GitHub Pages・Firebase は無料プランのまま（上限で止まるだけで請求されない）
見張り: Catalog のジョブの最後の段（Free-tier check）が、使った量と上限の表を実行の Summary に出し、上限の 8 割を越えたか読めなければ失敗する（GitHub から持ち主に通知）。Worker の /api/health も R2 の読み出しの数を返す。最後の歯止めは GitHub の支払いの上限 0 ドルと、Cloudflare の Budget alerts（知らせるだけ。cf-budget-alerts-not-cap）。
変えたこと: 過去の公演の読み取りを Catalog のジョブの中に移した（past-stages.yml をやめた。準備と書き戻しの 10 分を毎日省く）。起案者の「1 日 6,000 件」は、無料枠に収まる分だけにした（初めの数日は 1 日 約 7,000 枚まで読めるが、31 日の枠が埋まると 1 日 約 1,500 枚に下がる見込み。crawler-actions-minutes）。ポスターの 1 回の上限を 6,000 から 2,000 枚にした（D1 の 1 日の書き込みに収めるため）。
