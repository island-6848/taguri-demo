---
id: dec-csp-script-self
type: decision
status: adopted
date: 2026-10-20
title: 画面の CSP を script-src 'self' にした（'unsafe-inline'・'unsafe-eval' を外す）。index.html の先読みと「眺める」の storyline をファイルに出し、HTML の onload・onerror・onsubmit・onchange を app.js の委譲に移した（#155）
sources:
  - https://github.com/island-6848/taguri-demo/issues/155
  - cloudflare/public/_headers
  - web/app.js
  - web/prefetch.js
  - web/storyline-draw.js
  - cloudflare/src/screens/cards.js
  - cloudflare/scripts/sync_public_ui.py
links:
  - answers: q-original-ui-csp
  - affects: sec-audit-1017
---
起案者「issuesまだ47個あるから古い順に対応してください」（2026-10-20）。issue #155。

- **変えた CSP**（cloudflare/public/_headers の /*）。`script-src 'self' 'unsafe-inline' 'unsafe-eval'` を `script-src 'self'` にした。
  - style-src の 'unsafe-inline' は残した。画面の HTML に style="…" が多く、外すには別の作業が要る。
  - /login と /oauth-calendar は、Worker が前から別の CSP を付けている（worker.js の loginPage・calendarCallbackPage）。
- **ファイルに出したスクリプト**
  - index.html の先読み（最初の画面の API を CSS より先に取りに行く）→ web/prefetch.js。
  - 「眺める」の storyline の図。前は app.js の中の文字列（SL_SCRIPT）を <script> に入れて動かしていた → web/storyline-draw.js。画面に #sl-data が来るたびに <script src> を足し直して動かす。中身は cloudflare/src/screens/storyline_js.js の STORYLINE_JS と同じ。
  - sync_public_ui.py が、両方を cloudflare/public に写す。
- **委譲に移したもの**（web/app.js）
  - ポスターの img の onload・onerror → `img[data-poster]` の load・error を document の捕まえる側で聞く。load・error は泡立たないため。
  - 設定の絞り込みの form の onsubmit="return false" → `form[data-nosubmit]`。
  - 並べ替えの select の onchange → `select[data-autosubmit]`。
  - service worker のつながらないときの画面の onclick="location.reload()" → `<form><button>`。同じ URL を GET で送り直すので、読み込み直しになる。
- **そのまま残したもの**
  - 画面の本文に入っている <script>（カレンダー・観劇の年表・storyline）。innerHTML で入れるので、前から動いていない。同じ働きは app.js にある。
  - d3 の中の Function(…)。CSV を読む部品にだけあり、たぐりは使わない。
  - Python 版（tools/taguri/app.py）の HTML の onload など。デモの GitHub Pages には CSP が無い。
- **確かめたこと。** cloudflare の node の試験 530 件。本物の Worker と Chromium で主な操作を通す e2e-walk（CSP の違反はコンソールのエラーとして拾う）。
- **HSTS。** issue のとおり、独自ドメインを持つまでは足さない。独自ドメインは使わない（CLAUDE.md）ので、今は足さない。
