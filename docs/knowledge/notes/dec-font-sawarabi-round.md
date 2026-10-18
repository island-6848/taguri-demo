---
id: dec-font-sawarabi-round
type: decision
status: superseded
date: 2026-10-18
title: 押すもの・丸の中の字（両端が半円の押し口と札）・ロゴはさわらびゴシック、公演名とほかは Zen角ゴシック New
sources:
  - https://fonts.google.com/specimen/Sawarabi+Gothic
  - https://fonts.googleapis.com/css2?family=Sawarabi+Gothic&display=swap
  - https://github.com/google/fonts/blob/main/ofl/sawarabigothic/OFL.txt
  - https://github.com/google/fonts/blob/main/ofl/sawarabigothic/METADATA.pb
  - https://github.com/google/fonts/blob/main/ofl/zenmarugothic/ZenMaruGothic-Medium.ttf
  - web/fonts.css
  - web/round-text.js
  - docs/design/logo/make_type.py
  - cloudflare/test/fonts.test.js
links:
  - supersedes: dec-font-action-maru
---
起案者の指示（2026-10-18）「丸ゴシックのところ さわらびゴシックにできる？公演名に使う字体もこれにして」、続けて「丸のなかの文字だけ丸ゴシックにできる？」。どれが「丸のなか」かを聞き、「角が丸い押し口」「角が丸い札」「ロゴの丸」を選んだ（評価の判子は選ばなかった）。

確かめたこと（一次情報・取得元から直接取得）:
- さわらびゴシックは SIL OFL 1.1（google/fonts の OFL.txt・METADATA.pb の license: "OFL"、designer: "mshio"）。Google Fonts の CSS が返すのは 400 だけで、文字の範囲ごとの woff2 が 121 ファイル（計約 1.3 MB）。太字は無い
- サイトの CSP（default-src 'self'）が外のフォントを読まないので、woff2 を web/assets/fonts/sawarabi-gothic/ に置いて配る。ライセンスの本文は assets/fonts/OFL-SawarabiGothic.txt。静的なファイルは Workers の無料枠の数に入らない〔workers-static-assets-free〕

決めたこと（web/fonts.css）:
- `--font-action`（さわらびゴシック）: ボタン・ボタンの形のリンク・タブ・select・送信。`--font-title`（さわらびゴシック）: 公演名。どちらも 400 のまま組み、font-synthesis:none で作り太りを止める（日本語の字の作り太りはつぶれるため）。前は押すものを丸ゴシックの太字にしていたので、押す字は細くなった
- `--font-round`（Zen丸ゴシック 700）: 両端が半円の押し口と札の中の字。web/round-text.js が、描かれた形（border-radius が高さの半分以上で、枠線か地の色があるもの）を見て data-round を付ける。丸さは部品ごと・画面の幅ごとに CSS が決め、theme.css が四角に上書きしている部品もあるので、クラスの名前を並べると漏れる。読んでから書く順にして組み直しを抑え、画面の書き換え（MutationObserver）と幅の変化で付け直す。評価の判子（.rb・.stamp）と図（svg、制覇マップのマス・ログインの図の丸）は外す。app.js を読まないログイン・規約の頁でも同じファイルを読む
- ロゴの丸（紋章）と、電話の幅の帯の横組みの「たぐり」を Zen丸ゴシック Medium の字形にした（docs/design/logo/make_type.py。字ごとの寸法を FONTS にまとめ、LOGO_FONT=hina で前のひな明朝に戻せる）。濁点の星・「り」の払いの先の糸・字の墨の真ん中を丸の中心に合わせる決まりは前のまま。字のファイルは gf/ に置き、リポジトリには入れない（.gitignore）。案 2・案 3（type2・type3）はひな明朝の案のまま残した

確かめたこと: e2e-walk 41 段（wrangler dev と Chromium）。画面の写しで、両端が丸い「戻る」「取り消す」「任意」「確認できず」「使い方」・ログインの丸い押し口が丸ゴシック、四角に近い「公式サイト」「回答を直す」「追加」・並べ替えの select がさわらびゴシック、公演名がさわらびゴシック、ロゴが丸ゴシック。test/fonts.test.js（どの頁も fonts.css と round-text.js を読む・@font-face の指すファイルが全部ある・丸の決まりが押すものの決まりより後ろ）。

分かっていないこと: ログインの画面の上の帯の「たぐり」（auth.css の .brand、明朝の文字）は丸の中ではないので変えていない。

追記（2026-10-18）: 起案者「やっぱごめん丸ゴシックはさわらびゴシックでいいや。ロゴのフォントもさわらびゴシックでつくってほしい」。
- 丸の中の字（--font-round）もさわらびゴシック（400、作り太りなし）。round-text.js の印付けは残す（押すものではない丸い札も、角ゴシックではなくさわらびゴシックになる）。Zen丸ゴシックはどこにも使わなくなったので、字のファイル（122 個）と @font-face を外した
- ロゴ（紋章と、電話の幅の帯の横組み）の「たぐり」を、さわらびゴシック Regular の字形で作り直した（make_type.py の FONTS['sawarabi']: 濁点は輪郭 0・1、字の墨の真ん中 390、大きさ 49。字のファイルは google/fonts の SawarabiGothic-Regular.ttf を取得元から直接取った）。LOGO_FONT=maru・hina で前の字に戻せる
- 確かめたこと: JS 389 件、e2e-walk 41 段、画面の写し（ボタン・丸い札・公演名・ロゴがさわらびゴシック）

追記（2026-10-18、その 2）: 起案者「『り』の払いの先から繋がる糸、『り』くらい太いところからしたの水平に繋がるまでの間で、だんだん細くなるように」。
- 糸の始まりを「り」の払いの切り口の真ん中（字の単位で 403, -17）にし、太さを払いの線の太さ（77 単位、紋章で約 3.8）から、床の水平の線と繋がるところで床の線と同じ 1.4 まで、線に沿った長さに比例して細くした（make_type.py の taper_curve。始まりは平ら、終わりは丸く閉じる）。床の線はそこから左へ 1.4 のまま
- 字と糸の継ぎ目に隙間が見えたので、糸の始まりを払いの線の中へ 1.5 だけ差し込んだ（ri_in の向き）
- 寸法の無い字（ひな明朝・Zen丸ゴシック）は、前と同じ細い線のまま引く

追記（2026-10-18、その 3）: 起案者「繋ぎ目がたがたしてる。平滑化して曲線でつなぎ」（電話の画面の写しで、払いの切り口で糸が折れて段になっていた）。
- 原因: 糸の出だしの向き（左下へ急に下がる）が、払いの線の向き（左へ、少し下がる）と違い、切り口で折れていた。切り口も線の向きに直角ではない
- 直したこと: 糸の 1 つ目の曲線の始まりの向きを、払いの線の向き（ri_in の逆）に合わせた。払いの線の太さを測り直し（82 単位。外の縁が少し曲がるので 86 で取る）、糸の始まりを同じ太さ・同じ向きで線の中へ 2 だけ差し込んだので、切り口の角も糸の帯の中に入る。後ろの曲線どうしの継ぎ目も、前の終わりの向きと次の始まりの向きがそろっている
- 確かめたこと: 紋章を 20 倍に拡大した写しで、継ぎ目に折れも段も無い

追記（2026-10-18、その 4）: 起案者「やっぱタイトルの表示だけ前のzen角ゴシック？のやつに戻して」。公演名（--font-title）を Zen角ゴシック New に戻し、太さも各画面の指定（半券・評価の行は太字）に戻した。ボタン・丸の中の字・ロゴはさわらびゴシックのまま。各画面の題字・見出しはもともと Zen角ゴシック New で変えていない。e2e-walk 41 段と画面の写しで確かめた。
