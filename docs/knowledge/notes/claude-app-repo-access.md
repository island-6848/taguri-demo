---
id: claude-app-repo-access
type: finding
status: confirmed
date: 2026-10-13
title: Claude の GitHub アプリは taguri-crawler にまだ入っていない
sources:
  - https://claude.ai/code/session_015xXsQ9C4423EMquRbg7m3U（add_repo・list_repos の結果）
links:
  - affects: q-crawler-repo
---
起案者が非公開リポジトリ taguri-crawler を作ったが、このセッションからは見えない（add_repo が「見つからないか権限が無い」、リポジトリの一覧にも出ない）。Claude の GitHub アプリが taguri-demo だけに許可されているため。起案者が GitHub の設定でアプリの対象に taguri-crawler を足す必要がある。
