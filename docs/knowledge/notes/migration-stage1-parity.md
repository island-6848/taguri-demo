---
id: migration-stage1-parity
type: finding
status: confirmed
date: 2026-10-13
title: 段 1（記録と評価）の画面 4 枚と書き込み 11 種が、Python と同じ応答を返すようになった
sources:
  - https://github.com/island-6848/taguri-demo/tree/wip-screens-port/cloudflare/test/screens/scenarios.json
  - https://github.com/island-6848/taguri-demo/commit/84a4e59
links:
  - affects: dec-render-full-migration
  - depends_on: dec-migration-branch-wip
verifies:
  - S34
---
wip-screens-port で、評価一覧・未評価・感想・日記帳の 4 画面と、add_work・rate・note・fix_work・merge_work・drop_work・restore_work・purge_work・hand_credits・link_stage・visit_note を Worker に移した。test/screens.test.js が 4 つの手順（計 150 段ほど）を Python（Render と同じ service 版・一時 DB・日付固定）と Worker で流し、状態コードと応答（body_html を含む）がすべて一致した。出演者の読み取り（measure_nets.parse_credits）は 10 通りの書き方で Python と直接比べた。
Python と意図して違う所: ポスターは Worker に無いので出さない（Python 側の試験環境にも無いので一致する）。日記帳のあらすじは持ち主の記録の控え（themes.jsonl の学習側）なので出さない。回ごとのメモは、メールから来た記録（公開版の利用者には無い）でしか出ない。
まだ確かめていないこと: 本物のカタログの量での CPU 時間と D1 の読み取り行数、2 人の利用者での分離の手順。本番では NATIVE_UI を設定するまで使われない。
