---
id: people-sincos-glibc
type: finding
status: confirmed
date: 2026-10-14
title: 相関図の初期配置の sin・cos は、V8 と CPython（glibc 2.39）で 3.4% の角度が 1 ulp ずれ、460 回の力学配置のあとで 30px 動く。JS は正しく丸めた値に glibc の丸めを表で合わせて一致させた
sources:
  - cloudflare/src/screens/people.js
  - cloudflare/test/people.test.js
  - cloudflare/test/screens/people_fixture.py
links:
  - affects: dec-records-worker
---
people.layout は名前の順に円周へ置く（math.cos/sin(τ·i/n)）。V8 の Math.cos/sin と glibc は、n < 512 の角度の約 3.4% で 1 ulp 違う。.1f に丸めても隠れない（力学配置で増える）。Python の sin・cos を JS に渡すと全件一致したので、原因はこれだけ。
glibc も正しく丸めてはいない（高精度の級数で確かめると、349 の角度で glibc の側がずれている）。JS は double-double（約 106 bit）で正しく丸めた値を出し、glibc が逆に丸める 349 件（n, i, Δsin, Δcos。どれも ±1 ulp）を表 GLIBC_FIX で合わせる。テストは n < 512 の 13 万の角度すべてを Python と比べる。
限り: 一致するのはこの機械の libm（glibc 2.39・FMA）の Python。macOS の CPython や別の glibc では配置が違いうる。n ≥ 512 は正しく丸めた値のままで、一致は保証しない。ブラウザでは Math.cos/sin を使わないので、どのブラウザでも同じ絵になる。
