---
id: synopsis-llm-history
type: finding
status: confirmed
date: 2026-10-13
title: あらすじの読み取りは Gemini API。以前の claude CLI 呼び出しは起案者の判断でやめている
sources:
  - tools/credits/extract_theme_llm.py
links:
  - affects: q-synopsis-reader
---
extract_theme_llm.py は Gemini API（tools/llm_gemini.py）であらすじと題材を抜き出し、data/credits/themes.jsonl にモデルと指示の版つきで確定させる。
2026-08-27 までは claude CLI をサブプロセスで呼んでいたが、「対話用セッションと同じ枠・同じログイン状態にバッチの認証まで乗せるのは、費用と安全の両面でまずい」という起案者の指摘で切り離した。
利用者の感想からの好みの読み取りは、サーバー内の規則処理で、外部の AI には送っていない（service-privacy-draft.md）。
