---
id: legacy-test-failures
type: finding
status: confirmed
date: 2026-10-12
title: test_digest と test_impressions は以前から失敗している
sources:
  - tools/taguri/test_digest.py
  - tools/taguri/test_impressions.py
---
変更の前後で同じ件数（1 件と 4 件）失敗する。CI には入っていない。
