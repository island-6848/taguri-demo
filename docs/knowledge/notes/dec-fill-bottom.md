---
id: dec-fill-bottom
type: decision
status: adopted
date: 2026-10-24
title: おすすめで答えたときの入れ替わりの 1 枚は、一覧のいちばん下に足す（押したカードのすぐ下はやめる）
sources:
  - web/app.js
links:
  - supersedes: dec-fill-below
  - affects: comp-cf-worker
---
起案者の指示（2026-10-24）「おすすめ画面で回答したら、次に候補が出てくるのは、一番下でよい」。

- 10-20 の「押したカードのすぐ下に出す」（dec-fill-below）を撤回。押したところに割り込むより、一覧の終わりに足すほうがよいと起案者が判断した
- 三択・✕ のどちらで答えても、足した 1 枚は一覧のいちばん下。点の高い順も崩れない
- 画面全体を読み込み直さない動きと、ふわっと出るアニメーションはそのまま
