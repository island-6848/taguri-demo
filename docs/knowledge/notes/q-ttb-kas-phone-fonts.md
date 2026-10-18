---
id: q-ttb-kas-phone-fonts
type: question
status: open
date: 2026-10-18
title: 暦の貸切の回「(貸)17:00」は、実際の電話（iPhone・Android の字）でも升の中で 1 行に収まるか
sources:
  - cloudflare/test/e2e-walk.js
  - web/theme.css
links:
  - affects: dec-rec-card-1018-layout-b
---
e2e-walk（Chromium・幅 390px）では、電話の幅の升 35px に「(貸)17:00」がちょうど 35px で収まった（余りが無い）。字の幅は端末の字（ヒラギノ・Noto など）で変わるので、実際の電話で折り返したりはみ出したりしないかは確かめていない。はみ出すなら、升の間（border-spacing）や暦の左の字下げを詰めて升を広げるか、「(貸)」を時刻の上の行に回すかを起案者と決める。
