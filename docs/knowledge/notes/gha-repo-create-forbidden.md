---
id: gha-repo-create-forbidden
type: finding
status: confirmed
date: 2026-10-13
title: この作業環境の GitHub 連携では、新しいリポジトリを作れない
sources:
  - https://claude.ai/code/session_015xXsQ9C4423EMquRbg7m3U（create_repository が 403 Resource not accessible by integration）
links:
  - affects: dec-crawler-gha-private
  - raises: q-crawler-repo
---
非公開リポジトリ taguri-crawler を作ろうとしたが、GitHub の連携の権限が足りず 403 になった。起案者が GitHub の画面で作る必要がある。作ったあと、このセッションに追加すれば中身を入れられる。
