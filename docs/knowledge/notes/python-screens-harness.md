---
id: python-screens-harness
type: finding
status: confirmed
date: 2026-10-13
title: Python の画面は一時保存先・固定日付・通信なしで、テストの中から動かせる
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/test/screens/python_screens.py
links:
  - supports: dec-render-full-migration
---
コードを一時フォルダに写して data/ を架空カタログにし、service 版の公開モードで要求を流す。1 回 1 秒ほど。これを正解にして Worker 版と比べる。
