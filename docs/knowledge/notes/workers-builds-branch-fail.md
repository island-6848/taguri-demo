---
id: workers-builds-branch-fail
type: finding
status: confirmed
date: 2026-10-14
title: コミットの ✗（Workers Builds）は、master 以外のブランチの組み立てが失敗しているもの。master の組み立ては毎回成功している見込み
sources:
  - https://api.github.com/repos/island-6848/taguri-demo/commits/f212dc3/check-runs?filter=all
  - https://api.github.com/repos/island-6848/taguri-demo/commits/c06ae0b/check-runs?filter=all
  - https://api.github.com/repos/island-6848/taguri-demo/commits/736bcea/check-runs?filter=all
links:
  - affects: workers-builds-master-fail
  - raises: q-branch-builds-fail
---
推薦側のセッションから「736bcea のあと、master のすべてのコミットで Workers Builds が開始と同時に失敗し、本番が止まっている」と知らせがあったので、GitHub の check-runs（filter=all）を読んだ。
- 1 回の組み立てごとに check-run が 2 つ出る: 始まったときの in_progress（そのまま更新されない）と、終わったときの completed（started と completed が同じ時刻なので「0 秒」に見える）。組み立て自体は 20〜35 秒かかっている
- 同じコミットを master と作業ブランチ（claude/push-md67fv・claude/demo-records-setup-yqo65u など）に押すと、押した数だけ組み立てが走る。**どのコミットでも成功が 1 回あり、失敗はそれ以外**（736bcea も失敗 1・成功 1。f945c16 は失敗 2・成功 1、c06ae0b は成功 1・失敗 1、f212dc3 は失敗 2・成功 1）
- 押した順と時刻が合う: f212dc3 は作業ブランチ→master の順に押し、1 回目（01:35:41 開始）が失敗・2 回目（01:36:04 開始）が成功。c06ae0b は GitHub で master に合流した直後（01:28:52 開始）が成功
- GitHub の画面はいちばん後に終わった組み立ての結果をコミットの印にするので、ブランチの失敗が後に来ると ✗ になる
分からないこと: どの組み立てがどのブランチかは GitHub からは読めない（Cloudflare のダッシュボードの Builds の記録に出る）。本番の Worker の URL がリポジトリに書かれていないので、/api/health を外から確かめていない。ブランチの組み立てが失敗する理由（q-branch-builds-fail）。
