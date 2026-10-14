---
id: q-aspects-ui
type: question
status: open
date: 2026-10-13
title: 評価の画面に「気になった所」（任意・複数選択）のボタンを付けるか
links:
  - depends_on: reco-v2-index-compatible
  - affects: migration-stage1-parity
---
推薦側のセッション（PR #13）からの依頼（2026-10-13）: records と works に aspects 列（migrations/0012.sql、TEXT・既定 ''）を足した。値はコードのカンマ区切りで順序固定 ── story（話・脚本・構成）・direction（演出・見せ方）・acting（演技・出演）・music（歌・音楽）・dance（ダンス）・design（美術・衣裳）・price（値段に見合わない）・venue（会場・座席）。定義は user_recommender.ASPECTS・recommend.js ASPECTS・rate_performances.ASPECT_CODES / clean_aspects。計算は低い評価のときだけ使う。
依頼の中身: 評価の画面（app.py と cloudflare/src/screens/rate.js）の評価の近くに、任意で複数選べる「気になった所」のボタンを付け、works.aspects に保存する口を作る（Python と Worker の HTML の一致を保つ）。
未決: 起案者が付けるかどうか。PR #13 が master に入るのが前提。migrations の番号は、master は 0011 まで（2026-10-13 時点）なので 0012 は重ならない。
rec_people の「#」の行に「#値段」（料金の帯）が増えるが、日記帳は「#」の行を除いているので影響しない。rec_cache の印は person-ordinal-v3+fav1+asp1。
