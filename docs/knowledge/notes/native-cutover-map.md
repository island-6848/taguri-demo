---
id: native-cutover-map
type: finding
status: confirmed
date: 2026-10-13
title: 日記帳などを Worker の画面に切り替えるための今の状態（NATIVE_UI）
sources:
  - cloudflare/src/screens/index.js
  - cloudflare/src/worker.js
  - cloudflare/src/original-ui.js
  - docs/render-migration-plan.md
  - cloudflare/wrangler.jsonc
links:
  - raises: q-native-cutover
---
起案者の指示（2026-10-13）「日記帳などを Cloudflare 版の画面に切り替える段取りも進めて」を受けて、コードと計画書を読んで確かめた。
- 切り替えは環境変数 `NATIVE_UI`（"all"、または "screen:works,api:fix_work" のような一覧）。本番の wrangler.jsonc には無い（全部 Render へ中継）。名前ごとに切り替えられる仕組みはあるが、計画書（render-migration-plan.md 23 行）は「本番は最後に一度だけ切り替える」と決めている（文書は NATIVE_SCREENS と書いていたので NATIVE_UI に直した）
- **一部だけ切り替えると記録が分かれる。** 利用者の今の記録は Render の SQLite（tg_session の利用者）にあり、Worker の D1 の利用者（Firebase・復旧コード）とは結び付いていない（render-two-identities）。Render の記録は移さないと決めている（dec-no-render-data-migration・dec-service-starts-empty）。日記帳を Worker に切り替えた直後は 0 作品になり、おすすめ・眺める・探す・設定・登録など Render のままの画面とは別の記録を見ることになる。おすすめの画面の評価ボタン（Render の work_key）を Worker が受けると 400 になる
- 移した 4 画面（評価一覧・未評価・感想・日記帳）と 12 の書き込み（今回 unseen を足した）は Python と同じ HTML を返す（screens.test.js）。まだ Render に行くもの: suggest（結び付ける公演の候補）・suggest_web・import_status・hand_poster、react・favourite・decline など他の画面の書き込み
- D1 の材料: rec_stage・rec_people・stage_label・rec_meta は毎日の Catalog が入れる。まだ本番に 1 度も入っていない（dec-d1-catalogue-delivery）。past_stage は今日から。空だと出演者・公演名の表示・自動の結び付け・手での結び付けが効かない
- ポスターは Worker に無い（q-worker-posters）。CPU 時間（無料枠 10ms）と D1 の行数は本物の量で測っていない
- デモ版（GitHub Pages → Render）は NATIVE_UI では切り替わらない（q-demo-trial-design）
この日に足した試験（cloudflare/test/cutover.test.js）: 一部だけの一覧では書いた名前だけが Worker で答え、残りは Render へ行く／未設定なら全部 Render へ行く（今の本番）／2 人の利用者が Worker の画面で互いの記録を見られず、名指しでも書き換えられない。
