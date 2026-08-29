#!/usr/bin/env python3
"""「たぐり」の画面。**入口は 1 つで、上のナビゲーションで移動する。**

## 画面の割り方 ── 何を隣に置くかで決める

起案者の指示に従い、**「おすすめ」の直下に「今週のおすすめ」「興味あり」「お気に入り」を
置いた。**「今週のおすすめ」は順位を付けて 15 件に切る「答え」で、お気に入りは件数も条件も付けない「お知らせ」
である（企画書 1 章）── **性質が違うのに同じ場所に混ざっていた。** 同じページに縦に積むと、
読み手は上から順に同じ重みで読んでしまう。**親を 1 つ立てて子として並べると、「どれを
見に来たのか」を先に選べる。**

## 束の親は行き先ではない（2026-08-25）

起案者の指示 ──「『おすすめ』自体のボタンは押せなくして、『今週のおすすめ』ってページを
サブに置いてください。『おすすめ』自体のボタンを押すと、折りたたみに使えるように」、
続けて ──「同様に、『観た公演の評価』も『評価一覧』を追加して、折りたためるような
仕組みにして」。さらに ──「『記録を見返す』も同様にページを増やして折りたためるようにして」。
**「おすすめ」「観た公演の評価」「記録を見返す」の 3 つが、この形になっている。**

**親が行き先も兼ねていたので、いま見ているのが子のうちどれなのかが名前として
画面に出ていなかった** ── 1 段目を開いているとき、左で濃くなるのは親だけで、
子の側には印が付かない。1 段目を「今週のおすすめ」「評価一覧」「眺める」という名前の
子に降ろすと、**現在地は必ず子のどれか 1 つになる。**

**空いた親は、束を畳む押し口にした。** 既定で開くのは**いま居る束だけ**なので、
帯は束の中に居るとき 10 行・束の外に居るとき 7 行になる（3 つとも開くと 16 行・約 740px
あり、縦の短い画面では送りが出る）。畳んだかどうかは束ごとに端末に覚えるので、
**行き先を押すたびに既定の形に戻ることはない**（`NAV_FOLD_JS`）。
**畳んでいるあいだは親のほうを紙の色で抜く** ── そうしないと、畳んだとたんに
現在地が画面から消える。

**「記録を見返す」も同じ形にした**（起案者の指示 ──「『記録を見返す』も同様にページを
増やして折りたためるようにして」）。1 段目の「眺める」を子として立てると親は画面で
なくなるので、**押すと飛ぶ押し口と押すと畳む押し口が 1 つの部品に同居しない。**
**帯の 3 つの束は、これですべて同じ形である。**

## 「おすすめ」の中は横並びではなくフローである（2026-08-24）

起案者の指示 ──「ナビゲーションバーをフローで左から右に流れるように。推薦 → 興味あり
→ お気に入りの順」（1 段目はのちに「今週のおすすめ」と名前を付けた）。**丸い札を 3 つ横に置いた形では、どれも対等な行き先に見えていた。**
実際には**前の段の操作が次の段を作る。**

**推薦の 1 枚をもぎる（「興味あり」を押す）と 2 段目に入り、2 段目で「なぜ気になったか」を
書くと、その文に出てきた名前が 3 段目の登録候補として出てくる**（`tools/taguri/reasons.py`）。
段の番号と矢印を出したのは、この繋がりが画面に無かったからである。

**「興味あり」は畳んだ束から画面に出した。** 買い忘れを防ぐための一覧なのに `<details>` の
中で題名と日程だけの行になっていて、開くまで見えなかった（`RR.tracking_html`）。

**4 段目は「評価一覧」である**（起案者の指示 ──「独立してつくっていいけど、おすすめの
4 段目からも飛べるように」）。**輪はここで閉じる** ── 今週のおすすめ → 興味あり →
お気に入り → 評価一覧 → 次のおすすめが変わる。左の帯では別の束（観た公演の評価）の
1 段目として置き、**同時におすすめのフローの 4 段目としても出す**
（`/rate` はどちらから入っても同じ画面である）。

**公演情報の登録は独立させた。** これは**入力の画面**であって、読む画面ではない。
週 3 分で一覧を読む動作の中に「メールを取り込む」「手で 1 件足す」を混ぜると、
読みに来たのか書きに来たのか分からなくなる。

**評価は、その登録の画面からさらに独立させた**（2026-08-24）。1 度はここに置いていたが、
**「入力どうしをまとめる」は作り手側の軸だった** ── 本人の側から見ると開く時期が違う。
取り込みと追加は一覧を更新するときの作業で、**評価は観た帰りに付けるもの**である。
しかもこれは**この仕組みでいちばん効く入力**で（名簿は「◎ を付けた公演の作り手」しか
材料に持てない）、別の名前のページの 3 番目に埋まっていた結果、**上演が終わって未評価の
ものが 28 件溜まっていた。**

| 道 | 画面 | 役割 |
|---|---|---|
| `/start` | **はじめる** | 何も入っていないときの入口。名前の登録から順に 3 段を出す |
| `/recommend` | **おすすめ ▸ 今週のおすすめ** | 答え。順位を付けた 15 件と、もう追いかけない束 |
| `/recommend/reminder` | **おすすめ ▸ 開幕リマインド** | 答えていない候補・興味あり・お気に入りのうち初日が近いもの。券がある公演の直近予定 |
| `/recommend/interest` | **おすすめ ▸ 興味あり** | 追いかける。もぎった公演と、書いた理由 |
| `/recommend/favourites` | **おすすめ ▸ お気に入り** | お知らせ。登録した名前の新着と、登録・解除 |
| `/rate` | **観た公演の評価 ▸ 評価一覧** | 輪を閉じる。付けた評価を ◎○△× ごとに見る |
| `/register` | **公演情報の登録** | 入力。メールの取り込みと、手での登録 |
| `/records` | **記録を見返す ▸ 眺める** | 図で全体の形を見る（束の 1 段目）。これから上演される公演との差（もとの「比べる」）も同じ画面に含む |
| `/records/chronicle` | **記録を見返す ▸ 観劇史年表** | 記録を年の順に並べ、その年に何が始まったかを見る |
| `/records/works` | **記録を見返す ▸ 日記帳** | 1 公演ごとの記録を読み、直す |
| `/search` | **探す** | 引く。名前・題材・題名で過去の記録を辿る |
| `/settings` | **設定** | 決めごとと、たまにしか押さない道具（書き出す・別の端末に記録を移す） |

**答えを出すのは推薦だけ**という線は動かしていない（企画書 1 章）。他の画面は、
推薦の順位を付けるために内部で持っている量と、観た事実を出しているだけである。

## ポスターを出す

**画像は端末内から出す**（`/img/<stage_id>`）。外部の URL を `<img src>` に書くと、
一覧を開くたびにブラウザが外部へ要求を出すことになり、**画面から外部サイトを叩かない**
という守り（企画書 5 章の 5）を画像 1 枚で破る。取り込みは更新の段で行う
（`tools/taguri/posters.py`）。
"""

from __future__ import annotations

import html
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
sys.path.insert(0, str(ROOT / "tools" / "review"))
# **値を URL に載せる形へ直すために使う。** ◎ や △ は ASCII の外にあるので、
# 生のまま置くと押した先で何が来るかがブラウザ任せになる
from urllib.parse import quote                                     # noqa: E402

import charts as CH
import chronicle as CR2
import compare as CP
import digest as DG
import storyline as SL
import trace as TR                                                    # noqa: E402
import venues as VE                                                  # noqa: E402
import icons as IC                                                 # noqa: E402
import logo as LG                                                  # noqa: E402
import impressions as IM                                           # noqa: E402
import people as PE                                               # noqa: E402
import posters as PO                                               # noqa: E402
import prefmap as PM                                               # noqa: E402
import reasons as RE                                               # noqa: E402
import recommend as RC                                             # noqa: E402
import render_recommend as RR                                      # noqa: E402
import stage_calendar as SC                                        # noqa: E402

DB = ROOT / "data" / "review" / "ratings.db"
E = RR.E


def R_NORM(s: str) -> str:
    """団体名を比べるための正規化。全角・空白・括弧・中黒のゆれを落とす。

    **団体名は表記が揺れる**（「座・高円寺」と「座・高円寺レパートリー」は別だが、
    「ふぉ〜ゆ〜」と「ふぉ～ゆ～」は同じ）。作品の親を組む鍵に使うので、
    **落とすのは記号と幅の違いだけにする** ── 語そのものを削ると別の団体が同じ鍵になる。
    """
    import re as _re
    import unicodedata as _u
    return _re.sub(r"[（）()『』「」・\s　]", "", _u.normalize("NFKC", s or "")).lower()

# 4 つ目は行き先ごとの子で、**「おすすめ」の中の段をそのまま左に出す**
# （起案者の指示・2026-08-24 ──「左のナビゲーションバーからもそれぞれのページに
# 飛べるようにして」）。**フローの札からしか行けない画面を作らない** ── 段の途中の
# 画面（興味あり・お気に入り）は、フローを 1 段目から辿らないと開けなかった。
#
# **「おすすめ」は行き先ではなく、束ねている名前である**（起案者の指示・2026-08-25 ──
# 「『おすすめ』自体のボタンは押せなくして、『今週のおすすめ』ってページをサブに置いて
# ください。『おすすめ』自体のボタンを押すと、折りたたみに使えるように」）。
# 1 段目の画面は「今週のおすすめ」という名前の子として置き、**親の押し口は開閉だけを
# する**（`path` が `None` の行がそれで、`layout` が `<details>` で組む）。
#
# **親が行き先も兼ねていたので、押した先が子のどれなのかが画面から分からなかった。**
# 「おすすめ」を押すと 1 段目に飛ぶが、左には「おすすめ」しか濃くならず、
# **いま見ているのが 3 つの子のうちどれなのかが名前として出ていない。**
# 子を 3 つに揃えると、現在地は必ず子のどれか 1 つになる。
#
# **「観た公演の評価」も同じ形にした**（起案者の指示・2026-08-25 ──「同様に、
# 『観た公演の評価』も『評価一覧』を追加して、折りたためるような仕組みにして」）。
# 1 度は「フローの 4 段目でありながら独立した行き先でもあるので上の階層に残す」と
# していたが、**残した結果、親が行き先も兼ねる形がここにも残っていた** ── 付けた評価を
# 見ているとき、左で濃くなるのは「観た公演の評価」だけで、**3 つの子のうちどれを
# 読んでいるのかが名前として出ていない。** 1 段目を「評価一覧」という子に降ろした。
NAV = ((None, "おすすめ", "ticket",
        (("/recommend", "今週のおすすめ", "ticket"),
         ("/recommend/reminder", "開幕リマインド", "inbox"),
         ("/recommend/interest", "興味あり", "flag"),
         ("/recommend/favourites", "お気に入り", "star"))),
       # **暦は「おすすめ」の子にしない。** 3 つの束（券がある・興味あり・お気に入り）を
       # まとめて見る画面なので、どれか 1 つの段の下に置くと嘘になる（起案者の指示・
       # 2026-08-24 で独立した行き先として立てた）。
       ("/calendar", "公演カレンダー", "calendar", ()),
       # **「購入済み公演」も独立した行き先にした**（起案者の指摘・2026-08-25 ──
       # 「もうチケットを買っていてこれから観に行く公演についてまとめられているページが
       # ない」）。**「すでに持っている」の束は、それまで 2 か所に分かれていた** ──
       # 公演カレンダーで束を「すでに持っている」だけに絞る、または「おすすめ」の
       # いちばん下で「もう追いかけない公演（興味なしと答えた分）」と同じ見出しの下に
       # 畳んである一覧。**どちらも「これから観に行く」ことを主役にした画面ではなかった。**
       # 対応の向きを確認したところ、独立した画面を作る案を選んだ（新しいページを作る
       # ／暦の絞り込みを直す／おすすめ下部の見出しを分けるの 3 案から）。
       #
       # **名前は「もう観に行く公演」→「持っているチケット」→「購入済み公演」と
       # 2 度直した**（起案者の指摘・2026-08-25 ──「『もう観に行く』って日本語変。
       # チケットをすでに買ってる公演ってことだよね？」、続けて「持っているチケット、を
       # 『購入済み公演』に変えて」）。**決まっているのは「券を買ったか」だけである。**
       #
       # **絵記号は「おすすめ」と同じ `ticket` を使う。** 意匠の絵記号は他の場所でも
       # 1 つの意味に固定していない（例＝`check` は「観た公演の評価」の親とボタンの
       # どちらにも使う）。ここでは**券そのものの形が、実際に手元にある券をいちばん
       # 正しく表す**ので、重なりよりも意味の正しさを取った。
       ("/tickets", "購入済み公演", "ticket", ()),
       # **「観た公演の評価」に子を 3 つ置く**（起案者の指示・2026-08-24 ──「『評価』って
       # ナビゲーションバーのボタンを押したら過去の自分の評価一覧が出てきて、サブページと
       # して未評価でページを分けてもいいのでは？」）。**それまでは 1 枚に 3 つの束が
       # 積まれており、表に出ていたのは 5 件だけで、付けた評価 98 件はこの画面のどこにも
       # 出ていなかった**（残りは畳んだ束の中）── 画面の名前と中身が合っていない
       (None, "観た公演の評価", "check",
        (("/rate", "評価一覧", "check"),
         ("/rate/unrated", "未評価", "clock"),
         ("/rate/notes", "感想", "pencil"))),
       ("/register", "公演情報の登録", "inbox", ()),
       # **「記録を見返す」の中は 3 つの画面だった**（起案者の指示・2026-08-24）。
       # 開く理由が違う ── 図は全体の形、比べるは自分の偏り、日記帳は 1 本の公演。
       # 1 枚に積むと、日記帳に用がある人が毎回 8 枚の図を通り過ぎることになる。
       # **「眺める」と「比べる」は、そのあと 1 つに統合した**（起案者の指示・
       # 2026-08-26 ──「比べると眺めるを統合して」）。「自分の記録の確認」と「これから
       # の公演との差」の距離は、日記帳ほど離れていなかった（`page_records` の docstring
       # 参照）。**ここも束の親にした**（起案者の指示・2026-08-25 ──「『記録を見返す』も
       # 同様にページを増やして折りたためるようにして」）。1 段目の「眺める」を子として
       # 立てることで親が画面でなくなり、**押すと飛ぶ／押すと畳むが 1 つの部品に同居しない。**
       (None, "記録を見返す", "chart",
        (("/records", "眺める", "chart"),
         # **「たどる」は 1 本を選んで深く見る画面である**（起案者の指示・2026-08-25）。
         # もとは「作り手の再会」が一望・こちらが 1 本という分担だったが、「作り手の
         # 再会」は 2026-08-26 の指示で外した（`page_records` の docstring 参照）──
         # 1 人ずつ深く追う道は「たどる」が引き続き持つ
         ("/records/trace", "たどる", "user"),
         # **「相関図」を独立画面から「眺める」へ戻した**（起案者の指示・2026-08-27
         # ──「独立した『相関図』のページを消して、眺めるに移動して」）。2026-08-25 に
         # 8 枚の中の 1 枚では狭いという理由で独立させた判断（下の `page_records` の
         # docstring に残す）を、ここで撤回する ── 独立させたこと自体が誤りだったの
         # ではなく、指示によって元へ戻すことになった。中身（`people.py` の `panel()`）
         # は変えていない。この行はもう無い（`page_network` も削除した）
         # **「観劇の年表」を「眺める」から独立させた**（起案者の指示・2026-08-26 ──
         # 「『観劇の年表』を独立した『観劇史年表』というページにして独立させて、
         # 『記録を見返す』の下において」）。「相関図」を独立させたのと同じ判断で、
         # もとは「眺める」の図の 1 枚（`chronicle.py` の `panel()`）だったが、
         # 専用の画面がほしいという指示なので外した。中身は変えていない
         ("/records/chronicle", "観劇史年表", "calendar"),
         ("/records/works", "日記帳", "book"))),
       ("/search", "探す", "search", ()),
       # **「設定」は最後に置く**（起案者の指示・2026-08-26 ──「一括の設定画面を
       # つくってほしい」）。内容を読みに来る画面ではなく、決めごとを直しに来る画面
       # なので、他の画面と並べるとどれも「まず見るところ」に見えてしまう。
       #
       # **「書き出す」は独立の道から外し、この画面の中の 1 枚の札にした**（起案者の
       # 指示・2026-08-26 ──「とりあえず書き出し機能はあまり使わないので設定に移動
       # してしまって」）。持ち出し（JSON）も、別の端末に記録を丸ごと移す道具も、
       # どちらも「たまにしか押さない道具」という点で「都道府県の既定」と役目が近い
       # ── 週次で見る画面には要らない
       ("/settings", "設定", "gear", ()))
# **「おすすめ」の中はフローである** ── 実際にデータが繋がっている（推薦の 1 枚を
# もぎると興味ありに入り、興味ありに書いた理由の文から名前を拾ってお気に入りの登録候補が
# 出る。`tools/taguri/reasons.py`）。この並びとラベルは `test_design.py` が直接検査して
# いるのでデータとしては残すが、**画面には帯として出していない**（起案者の指摘・
# 2026-08-25 で段の帯を全廃した ── 戻るボタンと道のり（パンくずリスト）が役目を引き継いだ）。
SUB_RECOMMEND = (
    ("/recommend", "今週のおすすめ", "ticket", "今週の分から選びます"),
    ("/recommend/reminder", "開幕リマインド", "inbox", "答えていない候補の初日が近づくと知らせます"),
    ("/recommend/interest", "興味あり", "flag", "「興味あり」を押した公演を追いかけます"),
    ("/recommend/favourites", "お気に入り", "star", "登録した名前の新着が届きます"),
    ("/rate", "評価一覧", "check", "観たあとに ◎ を付けます"),
)


# ---------------------------------------------------------------- ポスター
def _poster(stage_id) -> str:
    """端末内に取り込んだポスター。**無ければ何も出さない**（枠だけ置かない）。

    **読み込んでいる間は文字を出す**（起案者の指摘・2026-08-25 ──「『興味ありなし』を
    押した後、新しく出てくる公演のポスターが画像表示エラーのようになってしまっている」）。
    **原因そのものは `serve.py._json` で直した**（鍵を埋めずに配っていた）。それでも
    ここに文字を足すのは、**壊れたのではなく読み込み中である場面が他にも起こりうる**
    ためである ── 失敗したときにブラウザの既定のアイコンが出ると、直っていても
    直る前と同じ見え方になり、また同じ勘違いを招く。`onerror` で文言を差し替えて
    絵そのものを隠すので、**本当に読み込めなかったときも「エラーのような」表示にはならない。**
    """
    f = PO.have().get(str(stage_id))
    if not f:
        return ""
    return (f'<span class="pwrap"><img class="poster" src="/img/{E(f)}?t=__TAGURI_TOKEN__"'
            f' alt="" loading="lazy"'
            f' onload="this.parentElement.classList.add(\'ld\')"'
            f' onerror="this.parentElement.classList.add(\'pe\');'
            f'this.nextElementSibling.textContent=\'読み込めませんでした\'">'
            f'<span class="pmsg">読み込み中…</span></span>')


RR.POSTER = _poster            # カードと行に差し込む（既定は何も出さない）
DG.POSTER = _poster             # 開幕リマインドの行にも同じものを差し込む


def _load_notes_by_person() -> None:
    """自分が書いた感想を、推薦の理由に差し込めるようにする。

    **1 度だけ読む。** `measure_nets.load_rated()` は購入の記録とクレジットを突き合わせる
    ので、チケット 1 枚ごとに呼ぶと画面が開かない。**取れなかったら空のままにする** ──
    引用は理由の欄の添え物なので、これで画面が落ちてはいけない。
    """
    try:
        RR.NOTES_BY_PERSON = IM.by_person()
    except Exception:                                               # noqa: BLE001
        RR.NOTES_BY_PERSON = {}


_load_notes_by_person()


# ---------------------------------------------------------------- 共通の外枠
SCRIPT = """
const T = "__TAGURI_TOKEN__";
const live = !T.startsWith("__TAGURI");
if (!live) document.querySelectorAll(
    ".btns,.rb,.fav-add,.miss-add,.imp,.add-work,.ed-btns,.sug,.mergeq,.drop-row,"
    + ".ed-link,.ns-body,.wbox,.addtk,.chfoot")
    .forEach(g => g.classList.add("dead"));
const dn = document.querySelector(".dead-note");
if (dn) dn.hidden = live;

// **あらすじが 3 行に収まっているときは「続きを読む」を出さない**（起案者の指示・
// 2026-08-26 ──「あらすじで隠れているものがない場合は『続きを読む』を表示しないで」）。
// **CSS の `line-clamp` だけでは、実際にあふれているかを判定できない**（あふれて
// いるかを問う疑似クラスは無い）ので、描いたあとの高さで判定する ── 畳んだ高さ
// （`clientHeight`）と、全部表示したときの高さ（`scrollHeight`）が同じなら、
// 畳んでも隠れている行は無い。`.cast`（出演者の「ほか N 名」）は件数で出し分けて
// いるので対象にしない ── `.syn .mrb` に絞る。
document.querySelectorAll(".syn .mrb").forEach(b => {
  const t = b.closest(".syn")?.querySelector(".txt");
  // **`hidden` 属性ではなく、直接 `style.display` を触る。** `.syn .mrb{display:block}`
  // という決まりのほうが `[hidden]` の既定より詳しさが強く、`hidden` を付けただけでは
  // 見た目が変わらなかった（実測）
  if (t && t.scrollHeight <= t.clientHeight + 1) b.style.display = "none";
});

async function post(path, body, group, done) {
  const said = group ? group.querySelector(".said") : null;
  try {
    const r = await fetch(path, {method: "POST",
      headers: {"X-Taguri-Token": T, "Content-Type": "application/json"},
      body: JSON.stringify(body)});
    const d = await r.json();
    if (!r.ok) { if (said) said.textContent = "できなかった: " + (d.error || r.status); return null; }
    if (said && done !== null) said.textContent = done || "記録した";
    return d;
  } catch (e) { if (said) said.textContent = "できなかった: " + e; return null; }
}

// 段の名前と札。**画面に出す言葉は 1 か所（WEIGHT_STEPS）から取る** ──
// 画面の側にも書くと、つまみの位置と札の言葉がずれる
const WSTEPS = __TAGURI_WSTEPS__, WLABEL = __TAGURI_WLABEL__;

// **貼った本文からのタグの読み取りは、別スレッドで数十秒かかる。** 押した直後の
// 応答にはまだタグが無いので、届くまで数秒おきに確かめ、届いた枠だけ差し替える ──
// 開き直さないとタグが出ない、という手待ちを無くすためである（起案者の指示・2026-08-26）。
function pollHandTheme(sid, el, tries) {
  if (tries >= 10 || !el.isConnected) return;          // 約 40 秒で諦める
  setTimeout(() => {
    post("/api/hand_theme_refresh", {stage_id: sid}, null, null).then(d => {
      if (!d) return;
      const w = document.createElement("div");
      w.innerHTML = d.html;
      const fresh = w.firstElementChild;
      if (fresh && fresh.querySelector(".tags")) { el.replaceWith(fresh); return; }
      pollHandTheme(sid, el, tries + 1);
    });
  }, 4000);
}

// **つまみを動かしても保存しない。** 変わったのは画面の上だけであることを、
// 札と確定の押し口の色で言う ── 動かしただけで効いたと読まれないためである
document.addEventListener("input", ev => {
  const sl = ev.target.closest && ev.target.closest(".wsl");
  if (!sl) return;
  const row = sl.closest(".wrow"), box = sl.closest(".wbox");
  const step = WSTEPS[+sl.value];
  row.querySelector(".wv").textContent = WLABEL[step];
  row.classList.toggle("off", step === "off");
  box.classList.add("dirty");
  const said = box.querySelector(".wsaid");
  if (said) said.textContent = "まだ確定していません";
});

document.addEventListener("click", ev => {
  if (!live) return;
  const b = ev.target.closest("button");
  if (!b) return;
  if (b.dataset.v) {
    const g = b.closest(".btns,.rb");
    const path = g.dataset.stage ? "/api/react" : "/api/rate";
    const body = g.dataset.stage ? {stage_id: g.dataset.stage, value: b.dataset.v}
                                 : {work_key: g.dataset.work, verdict: b.dataset.v};
    // **答えた枠を次の候補で埋めるために、いま出している分を送る**（起案者の指示・
    // 2026-08-24 ──「三択のボタンを押したら、まだ在庫があるなら別の候補に入れ替えて
    // 表示すべきだね」）。**在庫は画面の側にしか無い** ── 何を出しているかを知って
    // いるのは画面だけなので、除く分を送らないと、いま並んでいる 1 枚がもう 1 枚増える。
    // **推薦の枠だけが対象である** ── 興味あり・お気に入りは順位で切った枠ではないので、
    // 埋める先が無い
    const slot = b.closest(".ticket.recommend");
    if (slot) body.shown = [...document.querySelectorAll(".ticket.recommend")]
                             .map(a => a.dataset.stage).filter(Boolean);
    // **もぎれる。** 押した結果が形で分かる（記録できなかったら元に戻す）。
    // **評価待ちの行は ◎○△× を押したときに外れる**（起案者の指示・2026-08-24）──
    // 半券がもぎられるのは劇場に入るときなので、観終わった 1 枚が外れる形にする。
    // 「まだ判断できない」では外さない ── 評価し終わっていない
    const tk = b.closest(".ticket");
    const wt = b.closest(".wait");
    const row = tk || wt;
    const tear = (tk && b.dataset.v === "interest")
              || (wt && "◎○△×".indexOf(b.dataset.v) >= 0);
    if (tear) row.classList.add("torn");
    post(path, body, g).then(d => {
      if (!d) { if (tear) row.classList.remove("torn"); return; }
      g.classList.add("done");
      // **押した評価を、その場で余白に押す**（起案者の指示 ──「一個操作したら適宜
      // リロードしてほしい」の趣旨。ここは読み込み直さずに済む）。**判子が出ないと、
      // 押したのに何も起きていないように見える** ── 以前は評価の字が出るのは次に
      // 開いたときだった。**感想の欄も同時に開く** ── 観た帰りに ◎ を押す瞬間が、
      // いちばん言葉の出てくる瞬間である（焦点を移すのは ◎ のときだけ）
      const rr = b.closest(".rec-row");
      if (rr && rr.querySelector("[data-stamp]")) {
        const st = rr.querySelector("[data-stamp]");
        st.className = "stamp" + (b.dataset.v.length > 1 ? " hold" : "");
        st.textContent = b.dataset.v;
        st.removeAttribute("aria-label");
        const box = rr.querySelector(".inote");
        if (box && !rr.querySelector(".inr")) {
          box.hidden = false;
          if (b.dataset.v === "\u25ce") box.querySelector("textarea").focus();
        }
      }
      if (tk && b.dataset.v === "interest") {
        const wn = tk.querySelector(".why-note");
        if (wn) { wn.hidden = false; wn.querySelector("textarea").focus(); }
      }
      // **評価を押した直後に、感想の欄を開く。** 観た帰りに ◎ を押す瞬間が、いちばん
      // 言葉が出てくる瞬間である。**焦点を移すのは ◎ のときだけ** ── 引用が返るのは
      // ◎ の作品だけなので、× や △ で書くよう促すと返りの無い入力になる
      const wn2 = g.parentElement && g.parentElement.querySelector(".wnote");
      if (wn2) {
        wn2.hidden = false;
        if (b.dataset.v === "◎") wn2.querySelector("textarea").focus();
      }
      // **答えた枠を、次の候補で埋める**（起案者の指示・2026-08-24）。
      //
      // **「すでに持っている」で画面を読み込み直すのをやめた。** 前は 900ms 後に
      // `location.reload()` していた（同日の指示「一個操作したら適宜リロードして
      // ほしい」による）。**撤回の理由は 2 つある** ── ① 読み込み直すと読んでいた
      // 場所を失う。15 枚を上から見ている途中に先頭へ戻される。② 埋めるだけなら
      // 作り直す必要が無い。**「操作した結果がすぐ出る」という元の趣旨は、押した
      // 1 枚に印が付き、入れ替わりの 1 枚がその場で増えることで満たしている。**
      //
      // **押した 1 枚は消さずに残す。** 興味あり・興味なしは直後に理由の欄が開くので、
      // 消すと書いている途中の欄ごと消える。**足す先は一覧のいちばん下** ── 上から
      // 下へ読む画面なので、読み進む先に現れる。点の高い順という並びも壊れない。
      if (d.fill) {
        const said = g.querySelector(".said");
        if (d.fill.said && said) said.textContent = d.fill.said;
        if (d.fill.html) {
          const all = document.querySelectorAll(".ticket.recommend");
          const box = document.createElement("div");
          box.innerHTML = d.fill.html;
          const fresh = box.firstElementChild;
          if (fresh && all.length) {
            fresh.classList.add("filled");
            all[all.length - 1].after(fresh);
            bindNotes(fresh);          // 足した 1 枚の入力欄にも動きを付ける
          }
        }
      }
      // **見送った理由は出すだけで、開かない。** 書く頻度が低い入力なので、
      // 焦点まで移すと「書かないと進めない」ように見える
      if (b.dataset.v === "nointerest") {
        const row = b.closest(".ticket, .fav");
        const nn = row && row.querySelector(".nn");
        if (nn) nn.hidden = false;
      }
    });
  } else if (b.dataset.fav === "add") {
    const g = b.closest(".fav-add"), i = g.querySelector("#fav-name");
    if (!i.value.trim()) return;
    post("/api/favourite", {action: "add", kind: g.querySelector("#fav-kind").value,
      name: i.value.trim()}, g, "登録しました")
      .then(d => { if (d) { i.value = ""; waitJob(g, true); } });
  } else if (b.dataset.fav === "promote") {
    const r = b.closest(".prom");
    post("/api/favourite", {action: "add", kind: b.dataset.kind, name: b.dataset.name}, r,
      "登録しました（この名前の公演は、件数の制限なしに新着に出ます）")
      .then(d => { if (d) { r.classList.add("done"); b.disabled = true; waitJob(r, true); } });
  } else if (b.dataset.fav === "remove") {
    const t = b.closest(".tag");
    post("/api/favourite", {action: "remove", kind: t.dataset.kind, name: t.dataset.name},
      t.parentElement).then(d => { if (d) { t.remove(); waitJob(t.parentElement, true); } });
  } else if (b.dataset.dec === "add") {
    // **出さない語を確定する。** 候補の札から押す道と、自分で打つ道の 2 つがある
    const r = b.closest(".prom"), box = b.closest(".pbox");
    const w = b.dataset.word || (box.querySelector("#dec-word") || {}).value || "";
    if (!w.trim()) return;
    post("/api/decline", {action: "add", word: w.trim()}, r || b.parentElement,
      "出さないことにしました")
      .then(d => { if (d) { if (r) { r.classList.add("done"); b.disabled = true; }
                            waitJob(r || b.parentElement, true); } });
  } else if (b.dataset.dec === "remove") {
    const t = b.closest(".tag");
    post("/api/decline", {action: "remove", word: t.dataset.word}, t.parentElement,
      "戻しました")
      .then(d => { if (d) { t.remove(); waitJob(t.parentElement, true); } });
  } else if (b.classList.contains("rsx")) {
    // **「なぜ出てきたか」の 1 行を消す。**（起案者の指示・2026-08-26 ──
    // 「『なぜ出てきたか』は各項目に×ボタンをつけて不要な推薦は今後消せるように
    // してほしい」）。網 a（申告）は登録を外し、網 b・c（人物・内容）は
    // 「出さない語」に足す ── どちらも既存の口をそのまま呼ぶ。
    // **押した行をその場で消す。** 組み直しは数秒かかるので、消えるまで待たせない
    const li = b.closest("li.rs");
    b.disabled = true;
    const req = b.dataset.kind
      ? post("/api/favourite", {action: "remove", kind: b.dataset.kind, name: b.dataset.name},
             null, null)
      : post("/api/decline", {action: "add", word: b.dataset.word}, null, null);
    req.then(d => { if (d) { li.remove(); waitJob(null, true); } else { b.disabled = false; } });
  } else if (b.dataset.miss) {
    const g = b.closest(".miss-add"), i = g.querySelector("#miss-title");
    if (!i.value.trim()) return;
    // **登録した直後に演者とあらすじを調べに行く。** 終わるまで `waitJob` が
    // 進み具合を見に行き、終わったら読み込み直す ── 押した本人からは、
    // 調べ終わるまで何も起きなかったように見えないようにする。
    // **打っている途中の入力は無い**（欄はここで空にする）ので、読み込み直して困らない
    post("/api/missed", {title: i.value.trim()}, g,
         "登録しました ── 演者とあらすじを調べています…")
      .then(d => { if (d) { i.value = ""; waitJob(g, true); } });
  } else if (b.dataset.imp) {
    const g = b.closest(".imp");
    b.disabled = true;
    // **押した瞬間に帯を出す。** 返事は数百ミリ秒で返るが、そこまで何も動かないと
    // 押せたのかどうかが分からない ── 待ちの形は押した時点から出す
    IMP_T0 = Date.now();
    prog({running: true, step: 1, total: 0, n: 0, name: "購入確認メールを探しています"});
    post("/api/import_mail", {}, g, "取り込みを始めました").then(d => {
      if (!d) { b.disabled = false; return; }
      poll(g, b);
    });
  } else if (b.dataset.reload) {
    // **終わってから、本人が押したときだけ読み込み直す。** 待つ間にこの画面の下で
    // 手入力を書いていることがあるので、勝手に入れ替えない
    b.disabled = true;
    location.reload();
  } else if (b.dataset.addWork) {
    const g = b.closest(".add-work");
    const t = g.querySelector("#w-title"), dt = g.querySelector("#w-date");
    if (!t.value.trim()) return;
    post("/api/add_work", {title: t.value.trim(), date: dt.value,
      venue: g.querySelector("#w-venue").value,
      time: g.querySelector("#w-time").value,
      stage_id: g.querySelector("#w-stage").value}, g, "登録しました（評価待ちに並びます）")
      .then(d => {
        if (!d) return;
        t.value = ""; g.querySelector("#w-stage").value = "";
        document.getElementById("sug").replaceChildren();
        if (askMerge(g.parentElement, d.work_key, d.similar)) return;
        // **材料を取り終えてから作り直す。** すぐ読み込み直すと、取りに行っている
        // 最中の画面（ポスターの無い行）が出て、押した結果が見えない
        waitJob(g, true);
      });
  } else if (b.dataset.addFound) {
    // **探して見つけた、終わった公演を、その場で観た記録として登録する。**
    // 経路は「公演情報の登録」②（手で足す）と同じ /api/add_work（`RR.register_button`）
    const g = b.closest(".act") || b.parentElement;
    b.disabled = true;
    post("/api/add_work", {title: b.dataset.title, date: b.dataset.date,
      venue: b.dataset.venue, stage_id: b.dataset.addFound}, g,
      "登録しました（評価待ちに並びます）")
      .then(d => { if (d) waitJob(g, true); else b.disabled = false; });
  } else if (b.dataset.sugWeb) {
    sugWeb();
  } else if (b.dataset.pick) {
    // **候補を選んだら、そのまま欄に入れる。** 打ち直させない
    const r = b.closest(".sug-row"), g = document.querySelector(".add-work");
    g.querySelector("#w-title").value = r.dataset.title;
    g.querySelector("#w-date").value = r.dataset.date || "";
    g.querySelector("#w-venue").value = r.dataset.venue || "";
    g.querySelector("#w-stage").value = r.dataset.stage || "";
    document.getElementById("sug").replaceChildren();
    g.querySelector(".said").textContent = "候補から入れました。内容を確かめて登録してください";
  } else if (b.dataset.merge) {
    const g = b.closest(".mergeq");
    post("/api/merge_work", {work_key: b.dataset.mergeWork, other: b.dataset.merge}, g,
      null).then(d => {
      if (!d) return;
      g.querySelector(".said").textContent =
        "「" + d.kept_title + "」にまとめました"
        + (d.moved.length ? "（" + d.moved.join("と") + "も移しました）" : "")
        + " ── 画面を読み込み直します";
      setTimeout(() => location.reload(), 1400);
    });
  } else if (b.dataset.mergeNo) {
    const g = b.closest(".mergeq");
    g.querySelector(".said").textContent = "別の公演として、そのままにします";
    g.querySelectorAll("button").forEach(x => x.disabled = true);
    setTimeout(() => location.reload(), 1200);
  } else if (b.dataset.unmerge) {
    const g = b.closest(".ed-btns") || b.parentElement;
    post("/api/merge_work", {work_key: b.dataset.unmerge, unmerge: true}, g,
      "まとめを取り消しました ── 画面を読み込み直します")
      .then(d => { if (d) setTimeout(() => location.reload(), 1000); });
  } else if (b.dataset.wsave) {
    // **確定を押したときに 1 回だけ書き、そこで読み込み直す**（起案者の指示・2026-08-24）。
    // つまみを動かすたびに書く形をやめた ── 7 つを続けて動かしたいのに、1 つ動かす
    // ごとに画面が入れ替わってしまう
    const box = b.closest(".wbox"), w = {};
    box.querySelectorAll(".wsl").forEach(sl => {
      w[sl.dataset.weight] = WSTEPS[+sl.value];
    });
    post("/api/weight", {weights: w}, null, null).then(d => {
      const said = box.querySelector(".wsaid");
      if (!d) { if (said) said.textContent = "できなかった"; return; }
      box.classList.remove("dirty");
      if (said) said.textContent = "この効かせ方で読み込み直します…";
      // **押した直後だけは開いたまま戻る。** 「推薦に出なくなった公演が N 件」の
      // 知らせはこの欄の中にあるので、畳んで戻すと押した結果が見えない
      location.hash = "weights";
      setTimeout(() => location.reload(), 500);
    });
  } else if (b.dataset.wreset) {
    const box = b.closest(".wbox"), w = {};
    box.querySelectorAll(".wsl").forEach(sl => { w[sl.dataset.weight] = "mid"; });
    post("/api/weight", {weights: w}, null, null).then(d => {
      if (!d) return;
      location.hash = "weights";
      setTimeout(() => location.reload(), 400);
    });
  } else if (b.dataset.setPref || b.dataset.setPrefAll) {
    // **設定は「押したときに 1 回だけ書く」**（効かせ方と同じ規約）。チェックの
    // 並びは `.pfil` の form が持っているので、そこから読む ── 別の場所に状態を
    // 二重に持たない
    const card = b.closest("#pref-setting");
    const prefs = b.dataset.setPrefAll ? [] :
      [...card.querySelectorAll('input[name="pref"]:checked')].map(i => i.value);
    post("/api/pref_setting", {prefs}, card,
      "保存しました ── 次に開いたときから効きます").then(d => {
      if (d) setTimeout(() => location.reload(), 700);
    });
  } else if (b.dataset.unseen) {
    // **押したら一覧から外れる**（起案者の指示・2026-08-24）。評価待ちを開くたびに
    // 作り直すようにしたので、読み込み直せば実際に消える。**書く欄は開かない操作なので、
    // ここで読み込み直しても入力が消えることはない**
    const g = b.closest(".ns-body") || b.parentElement;
    post("/api/unseen", {work_key: b.dataset.unseen, unseen: true}, g,
      "行かなかったと記録しました ── 一覧から外します")
      .then(d => {
        if (!d) return;
        g.classList.add("done");
        const row = b.closest(".wait, .rec-row");
        if (row) row.classList.add("skipped");
        setTimeout(() => location.reload(), 900);
      });
  } else if (b.dataset.seen) {
    const g = b.closest(".rb") || b.parentElement;
    post("/api/unseen", {work_key: b.dataset.seen, unseen: false}, g,
      "観た公演に戻しました ── 画面を読み込み直します")
      .then(d => { if (d) setTimeout(() => location.reload(), 900); });
  } else if (b.dataset.drop) {
    // **2 回押させる。** 取り消しは戻せるが、押し間違いに気づく機会は要る
    const g = b.closest(".ed-btns") || b.parentElement;
    if (b.dataset.armed !== "1") {
      b.dataset.armed = "1";
      b.textContent = "本当に取り消す（あとで戻せます）";
      return;
    }
    post("/api/drop_work", {work_key: b.dataset.drop}, g,
      "取り消しました ── 「取り消した記録」から戻せます")
      .then(d => { if (d) setTimeout(() => location.reload(), 1200); });
  } else if (b.dataset.handtheme) {
    // **入れた内容は、押したときに 1 回だけ送る。** 打っている途中で送ると、
    // 打ち終わる前の断片が推薦の材料に入る
    const g = b.closest(".syn"), v = s => (g.querySelector(s) || {}).value || "";
    const sid = b.dataset.handtheme;
    // **出演者・作り手は役職ごとの欄をまとめて 1 つの fields にする。**
    // 日記帳の「手で入れる」（`data-handSave`）と同じ集め方
    const fields = {};
    g.querySelectorAll(".ht-cast[data-hand]").forEach(t => { fields[t.dataset.hand] = t.value; });
    b.disabled = true; b.textContent = "保存しています…";
    post("/api/hand_theme", {stage_id: sid, words: v(".ht-w"),
                             synopsis: v(".ht-s"), url: v(".ht-u"), fields}, null, null).then(d => {
      if (!d) { b.disabled = false; b.textContent = "保存する"; return; }
      // **押した結果をその場で出す。** あらすじの枠ごと差し替える（`syn_block`）
      const w = document.createElement("div");
      w.innerHTML = d.html;
      const el = w.firstElementChild;
      if (el) {
        if (d.said) {
          const n = document.createElement("p");
          n.className = "hsaid"; n.textContent = d.said;
          el.appendChild(n);
        }
        g.replaceWith(el);
        // **読み取り中なら、開き直させずに自分で拾いに行く。**
        if (d.read) pollHandTheme(sid, el, 0);
      }
    });
  } else if (b.dataset.handSave) {
    // **書いた内容を、押したときに 1 回だけ書く。** 打っている途中で送ると、
    // 名前を打ち終わる前の断片が名簿に入る
    const g = b.closest(".hand"), f = {};
    g.querySelectorAll("[data-hand]").forEach(t => { f[t.dataset.hand] = t.value; });
    post("/api/hand_credits", {work_key: g.dataset.work, fields: f},
         b.closest(".pfoot"), null).then(d => {
      if (!d) return;
      const said = b.closest(".pfoot").querySelector(".said");
      if (said) said.textContent = d.said || "保存しました";
      // **畳んだ見出しの人数も直す。** 開いたまま数だけ古いと、
      // 入ったのがいくつなのか読めない
      const sm = g.querySelector("summary");
      if (sm) sm.textContent = "ポスター・クレジットを手入力する"
        + (d.n ? "（出演者 " + d.n + " 名を入れてあります）" : "");
    });
  } else if (b.dataset.handOff) {
    const g = b.closest(".hand");
    post("/api/hand_poster", {work_key: b.dataset.handOff, drop: true}, g,
      "手で入れたポスターを外しました ── 画面を読み込み直します")
      .then(d => { if (d) setTimeout(() => location.reload(), 1000); });
  } else if (b.dataset.lkWeb) {
    // **付け替える欄からも外の公演情報を探せるようにする**（起案者の報告・2026-08-24
    // ──「どれだけ試してもポスターが違ったり、出演者が取得できなかったりした」）。
    // **手元にしか無い公演しか選べなかったので、直せない記録があった** ── 実測で
    // 「ナディラ」「明日、泣けない女 昨日、甘えた男」は候補が 0 件で、外す以外に
    // 押せる口が無かった。**打っている最中には行かない**（押したときだけ・守り 5）
    const i = b.closest(".ed-link").querySelector("[data-lk-q]");
    if (i) lkSearch(i, true, b);
  } else if (b.dataset.link) {
    const g = b.closest(".ed-link");
    post("/api/link_stage", {work_key: g.dataset.work, stage_id: b.dataset.link}, g,
      "結び付けました ── 材料を取りに行きます")
      .then(d => { if (d) waitJob(g, true); });
  } else if (b.dataset.unlink) {
    const g = b.closest(".ed-link");
    post("/api/link_stage", {work_key: b.dataset.unlink, stage_id: ""}, g,
      "結び付けを外しました").then(d => { if (d) setTimeout(() => location.reload(), 1000); });
  } else if (b.dataset.restore) {
    const g = b.parentElement;
    post("/api/restore_work", {key: b.dataset.restore}, g, "戻しました")
      .then(d => { if (d) setTimeout(() => location.reload(), 900); });
  } else if (b.dataset.purge) {
    // **2 回押させる。** 除外そのものは動かないが、「取り消した記録」からは
    // 戻す口ごと消える ── 押し間違いに気づく機会は要る
    const g = b.parentElement;
    if (b.dataset.armed !== "1") {
      b.dataset.armed = "1";
      b.textContent = "本当に完全に取り消す（一覧から消えます）";
      return;
    }
    post("/api/purge_work", {key: b.dataset.purge}, g,
      "完全に取り消しました ── この一覧から消えます")
      .then(d => { if (d) setTimeout(() => location.reload(), 900); });
  } else if (b.dataset.fix) {
    // 公演詳細の直し。**題名は作品ごと、上演日・開演時刻・劇場は回ごとに送る**
    const g = b.closest(".editor");
    const t = g.querySelector("[data-ed-title]");
    const shows = [...g.querySelectorAll(".ed-show")].map(r => ({
      uid: r.dataset.uid || "",
      date: r.querySelector("[data-ed-date]").value,
      time: (r.querySelector("[data-ed-time]") || {}).value,
      venue: (r.querySelector("[data-ed-venue]") || {}).value}));
    b.disabled = true;
    post("/api/fix_work", {work_key: b.dataset.fix, title: t.value, shows},
         g.querySelector(".ed-btns"), null).then(d => {
      b.disabled = false;
      if (!d) return;
      const said = g.querySelector(".ed-btns .said");
      said.textContent = d.n
        ? (d.gone ? "直しました ── この題名は演劇でないものとして候補から外れます"
                  : (d.moved ? "直しました（評価と感想も新しい題名へ引き継ぎました）"
                             : "直しました"))
        : "変わったところはありませんでした";
      // **近い記録があれば、読み込み直す前に聞く。** 読み込み直すと質問ごと消える
      if (askMerge(g, d.work_key || b.dataset.fix, d.similar)) return;
      if (d.n) setTimeout(() => location.reload(), 1200);
    });
  } else if (b.dataset.unfix) {
    const g = b.closest(".editor");
    post("/api/fix_work", {work_key: b.dataset.unfix, clear: true},
         g.querySelector(".ed-btns"), "抽出結果に戻した ── 画面を読み込み直す").then(d => {
      if (d) setTimeout(() => location.reload(), 900);
    });
  } else if (b.dataset.mail) {
    // **メールの中身は押したときに読む。** 一覧を開くだけで 195 通を読むのは無駄で、
    // 本文はどこにも保存しない（企画書 2 章）
    const g = b.closest(".editor"), box = g.querySelector(".ed-mail");
    box.hidden = !box.hidden;
    if (!box.hidden) box.querySelectorAll("[data-hints]").forEach(hints);
  } else if (b.dataset.why) {
    // **追いかけている一覧で、理由を書く／書き直す。** 入力欄を並べない代わりの押し口
    const w = b.closest(".wnw"), wn = w.querySelector(".why-note"), r = w.querySelector(".wnr");
    if (r) r.hidden = true; else b.hidden = true;
    wn.hidden = false;
    wn.querySelector("textarea").focus();
  } else if (b.dataset.noteOpen) {
    // **感想は押してから開く。** 107 行に入力欄を並べると、読みに来た画面が入力用紙になる
    // **押し口は `.inw` の外にも出る。** まだ何も書いていない記録では「感想を書く」が
    // 押し口の列（`.tools`）に並ぶので、行そのものから欄を探す
    const w = b.closest(".inw") || b.closest(".rec-row") || b.closest(".wait");
    const box = w.querySelector(".inote"), r = w.querySelector(".inr");
    if (r) r.hidden = true; else b.hidden = true;
    box.hidden = false;
    box.querySelector("textarea").focus();
  } else if (b.dataset.vnoteOpen) {
    // **「この回のメモ」も、感想と同じ「押してから開く」形にそろえる**（`data-note-open`
    // と同じ判断）
    const w = b.closest(".vnw") || b.closest(".rec-row");
    const box = w.querySelector(".vnote"), r = w.querySelector(".vnr");
    if (r) r.hidden = true; else b.hidden = true;
    box.hidden = false;
    box.querySelector("textarea").focus();
  } else if (b.dataset.rateOpen) {
    // **押してから開く。** 感想の欄と同じ形（`data-note-open`）にそろえてある
    const row = b.closest(".rec-row"), g = row.querySelector(".rb");
    if (g) { g.hidden = false; b.hidden = true; }
  } else if (b.dataset.btnsOpen) {
    // **「興味あり」の三択も、押してから開く**（「評価を押し直す」と同じ形）
    const row = b.closest(".ticket"), g = row.querySelector(".btns");
    if (g) { g.hidden = false; b.hidden = true; }
  } else if (b.dataset.mtAdd) {
    // **カードの中で行く日を追加する**（起案者の指示・2026-08-26 ──「『観劇日を
    // 追加する』のボタンを消して、各公演ごとに観劇日を追加できる欄を設けて
    // ください」）。押し口はこのカードの stage_id を使う ── 別の会場に付けたいときは
    // その会場のカードから入れる
    const box = b.closest(".mytix"), dd = box.querySelector(".mt-d").value,
          tt = box.querySelector(".mt-t").value, said = box.querySelector(".said");
    if (!dd) { said.textContent = "行く日を入れてください"; return; }
    post("/api/ticket", {stage_id: b.dataset.mtAdd, date: dd, time: tt}, box, "記録しました")
      .then(r => { if (r) setTimeout(() => location.reload(), 500); });
  } else if (b.dataset.mtDel || b.dataset.mtOk) {
    // **すでに入れてある行く日の「確定する」「取り消す」。** 押し口自身が持つ
    // stage_id を使う ── 券はカードの代表会場とは違う会場に付いていることがある
    const box = b.closest(".mytix");
    const sid = b.dataset.mtDel || b.dataset.mtOk;
    const body = {stage_id: sid, date: b.dataset.date, time: b.dataset.time,
                  action: b.dataset.mtOk ? "confirm" : "del"};
    post("/api/ticket", body, box,
         body.action === "confirm" ? "確定しました" : "取り消しました")
      .then(r => { if (r) setTimeout(() => location.reload(), 500); });
  } else if (b.dataset.more) {
    // あらすじの続きと、出演者の残り。**同じ押し口で開く**
    (b.closest(".syn") || b.closest(".cast")).classList.toggle("open");
  } else if (b.dataset.close) {
    fetch("/api/close", {method: "POST", headers: {"X-Taguri-Token": T}, keepalive: true});
    b.textContent = "閉じてよい";
  }
});

// **同じ公演かどうかは、機械が決めずに聞く。**
// 題名が近いだけでは同じ公演とは限らない ── 同じ戯曲の別の上演は題名が完全に一致する。
function askMerge(where, workKey, similar) {
  if (!similar || !similar.length) return false;
  const box = document.createElement("div");
  box.className = "mergeq";
  const h = document.createElement("p");
  // **引用符は単引用符で書く。** この JavaScript は Python の三重引用符の中にあるので、
  // 逆斜線で二重引用符を逃がすと Python 側で逆斜線が外れ、JavaScript が壊れる
  h.innerHTML = '<b>題名の近い記録が ' + similar.length
    + ' 件あります。これと同じ公演ですか？</b><br>'
    + '<span class="mq-note">同じ公演なら、回・評価・感想を 1 つの記録にまとめます。'
    + '別の公演なら、そのままにします（同じ戯曲の別の上演は、題名が同じでも別の公演です）。</span>';
  box.append(h);
  similar.forEach(x => {
    const r = document.createElement("div");
    r.className = "mq-row";
    const d = [x.first_date || "日付不明",
               x.times > 1 ? x.times + " 回観た" : "",
               x.verdict ? "評価 " + x.verdict : "評価はまだ",
               x.mails ? "メール " + x.mails + " 通" : "手で足した記録"]
              .filter(Boolean).join("・");
    r.innerHTML = '<span class="mq-t"></span><span class="mq-m"></span>';
    r.querySelector(".mq-t").textContent = x.title;
    r.querySelector(".mq-m").textContent = d;
    const yes = document.createElement("button");
    yes.textContent = "同じ公演です（まとめる）";
    yes.dataset.merge = x.work_key;
    yes.dataset.mergeWork = workKey;
    r.append(yes);
    box.append(r);
  });
  const foot = document.createElement("div");
  foot.className = "mq-foot";
  const no = document.createElement("button");
  no.textContent = "どれとも別の公演です";
  no.dataset.mergeNo = "1";
  foot.append(no);
  const said = document.createElement("span");
  said.className = "said";
  foot.append(said);
  box.append(foot);
  where.querySelectorAll(".mergeq").forEach(x => x.remove());
  where.append(box);
  box.scrollIntoView({block: "nearest", behavior: "smooth"});
  return true;
}

// **結び付ける公演を探す欄。** 手で足す欄と同じ候補を使う（探し方を 2 通り作らない）。
//
// **引き出しは 2 つある。** 打っている最中は手元だけを引き、「外の公演情報から探す」を
// 押したときだけ外へ行く（守り 5 ── 一覧を眺める操作で外へ要求は出さない）。
// **並べ方は 1 つにまとめてある** ── 同じ題名で手元と外の結果が違う形で出ると、
// どちらが正しいのか確かめようがない。
function lkSay(box, msg) {
  const p = document.createElement("p");
  p.className = "sug-head";
  p.textContent = msg;
  box.append(p);
}

async function lkSearch(i, web, btn) {
  const box = i.parentElement.querySelector(".lk-sug");
  const q = i.value.trim();
  // **後から来た返事で、先の結果を消させない。** 手元の検索（打っている最中・0.2 秒）と
  // 外の検索（押したとき・最大 8 秒）は同じ欄に書くので、**打ってすぐ押すと、遅れて
  // 届いた手元の返事が外の結果を消していた**（実測 ── 見つかった 2 件が
  // 「手元のデータに見つかりませんでした」で上書きされた）。番号を振って、
  // **いちばん新しい検索の返事だけを書く。**
  clearTimeout(i._t);
  const my = i._seq = (i._seq || 0) + 1;
  const fresh = () => i._seq === my;
  if (q.length < 2) {
    box.replaceChildren();
    if (web) lkSay(box, "題名を 2 文字以上入れてから押してください");
    return;
  }
  if (web) {
    box.replaceChildren();
    lkSay(box, "CoRichの公演情報を探しています… 8 秒ほどかかります");
    if (btn) btn.disabled = true;
  }
  let d;
  try {
    const r = await fetch((web ? "/api/suggest_web?t=" : "/api/suggest?t=")
      + encodeURIComponent(T) + "&q=" + encodeURIComponent(q),
      {headers: {"X-Taguri-Token": T}});
    d = await r.json();
  } catch (e) { d = null; }
  if (btn) btn.disabled = false;
  if (!fresh()) return;
  box.replaceChildren();
  if (!d) { lkSay(box, "探せませんでした"); return; }
  if (d.error) { lkSay(box, d.error); return; }
  const rows = (d.rows || []).filter(x => x.kind === "stage");
  if (!rows.length) {
    // **見つからなかったときに、次に押す口を書く。** 手元に無いことと、公演そのものが
    // 無いことは別である ── 前は「古い公演は入っていません」で終わっていたので、
    // **読んだ人にできることが残っていなかった**
    lkSay(box, web
      ? "「" + q + "」に当たる公演は見つかりませんでした ── 副題や団体名を外して"
        + "短くすると当たることがあります"
      : "手元のデータに見つかりませんでした ── 「CoRichの公演情報から探す」を押してください"
        + "（月 1 回の取り寄せに入っていない公演や、古い公演は手元にありません）");
    return;
  }
  if (web) lkSay(box, "CoRichの公演情報から " + rows.length
    + " 件見つかりました ── 観たものを選んでください。見つからない場合は下の"
    + "「ポスター・クレジットを手入力する」から追加してください。");
  lkRender(box, rows);
}

document.addEventListener("input", ev => {
  const i = ev.target.closest("[data-lk-q]");
  if (!i || !live) return;
  clearTimeout(i._t);
  i._t = setTimeout(() => lkSearch(i, false, null), 220);
});

// **「たどる」の、名前で絞り込む欄。** サーバーには何も送らない ── 85 枚の札は
// すでに手元にあるので、打った文字でその場で出し分けるだけでよい（起案者の指摘・
// 2026-08-26 ──「85名の名前を羅列するってセンスない」への答え）
document.addEventListener("input", ev => {
  const i = ev.target.closest("[data-pk-filter]");
  if (!i) return;
  const q = i.value.trim();
  let shown = 0;
  document.querySelectorAll(".picks .pk").forEach(a => {
    const hit = !q || a.querySelector(".pk-n").textContent.includes(q);
    a.closest("li").hidden = !hit;
    if (hit) shown++;
  });
  const none = document.querySelector(".pk-none");
  if (none) none.hidden = shown > 0;
});

function lkRender(box, rows) {
    // **作品を親、会場ごとの上演を子として並べる**（起案者のイメージ・2026-08-24 ──
    // 「作品ページは親として必ず一個でその下に各地方ごとの子ノード、さらにその下に
    // 観にいった情報の子ノード」）。**取得元は作品の id を持っていない**（会場ごとの
    // 上演に 1 ページ）ので、親はこちらで組んでいる（`work_group`）。
    //
    // **子は畳まない。** 会場ごとに出演者も座組も違いうるので、**どの上演かは本人しか
    // 知らない** ── 親を 1 行にして、その下で会場と日程を選んでもらう。
    const stageRow = (x) => {
      const r = document.createElement("div");
      r.className = "sug-row stage";
      // **手で足す欄と同じ形にする。** ここは「どの公演か」を選ぶ欄なので、
      // **選ぶ手がかりは同じでなければならない** ── 絵が片方にしか無いと、
      // 同じ題名が並んだときに片方でだけ選び分けられることになる
      r.innerHTML = '<span class="sg-p"></span><span class="sg-b">'
        + '<span class="sg-t"></span><span class="sg-m"></span></span>';
      const ph = r.querySelector(".sg-p");
      if (x.poster) {
        const im = document.createElement("img");
        im.src = "/img/" + encodeURIComponent(x.poster) + "?t=" + encodeURIComponent(T);
        im.alt = "";
        im.loading = "lazy";
        ph.append(im);
      } else {
        ph.classList.add("none");
      }
      r.querySelector(".sg-t").textContent = x.title;
      // **観に行った回の数を添える**（木の 3 段目）。すでに記録がある上演は、
      // 「自分が行ったのはこれだ」と分かるいちばん強い手がかりである
      r.querySelector(".sg-m").textContent =
        [x.date, x.venue, x.note].filter(Boolean).join("・")
        + (x.mine ? "／この公演の記録が " + x.mine + " 回あります" : "");
      if (x.mine) r.classList.add("mine");
      const pick = document.createElement("button");
      pick.textContent = "この公演にする";
      pick.dataset.link = x.stage_id;
      r.append(pick);
      return r;
    };
    const order = [], at = {};
    rows.forEach(x => {
      const k = x.wk || x.title;
      if (!(k in at)) { at[k] = []; order.push(k); }
      at[k].push(x);
    });
    order.forEach(k => {
      const xs = at[k];
      if (xs.length === 1) { box.append(stageRow(xs[0])); return; }
      const d = document.createElement("details");
      d.className = "sug-work";
      const sm = document.createElement("summary");
      const mine = xs.reduce((a, x) => a + (x.mine || 0), 0);
      sm.textContent = xs[0].title + "（" + xs.length + " 会場の上演）"
        + (mine ? "── うち " + mine + " 回の記録があります" : "");
      d.append(sm);
      const p = document.createElement("p");
      p.className = "sug-head";
      p.textContent = "観に行った会場と日程を選んでください ──"
        + " 会場ごとに出演者や座組が違うことがあるので、"
        + "別の上演を選ぶと、観ていない公演の作り手が名簿に入ります。";
      d.append(p);
      xs.forEach(x => d.append(stageRow(x)));
      if (mine) d.open = true;
      box.append(d);
    });
}

// **手で足す欄の候補。** すでにある情報を、打っている最中に出す
let sugTimer = null;
function sugWatch() {
  const t = document.getElementById("w-title"), box = document.getElementById("sug");
  if (!t || !box) return;
  t.addEventListener("input", () => {
    document.getElementById("w-stage").value = "";   // 打ち直したら結び付きを外す
    clearTimeout(sugTimer);
    sugTimer = setTimeout(() => sugFetch(t.value, box), 220);
  });
}

async function sugFetch(q, box) {
  if (q.trim().length < 2) { box.replaceChildren(); return; }
  let d;
  try {
    const r = await fetch("/api/suggest?t=" + encodeURIComponent(T)
      + "&q=" + encodeURIComponent(q), {headers: {"X-Taguri-Token": T}});
    d = await r.json();
  } catch (e) { return; }
  sugRender(box, d.rows, "すでにある情報から選べます（"
    + ((d.rows || []).length) + " 件）");
}

// **手元に無い公演を、押したときだけ外の公演情報から探す。**（起案者の指示・2026-08-24）
//
// **打っている最中には行かない。** 1 つの相手には 1.1 秒に 1 回までを守るので、1 回の
// 検索に 8 秒ほどかかる。文字を打つたびに走らせると打ち直すたびにやり直しになり、
// **待っているのか壊れているのか本人には分からない。** 押した人が待っていると分かる形に
// する（探しているあいだ文を出し、ボタンを押せなくする）。
async function sugWeb() {
  const t = document.getElementById("w-title"), box = document.getElementById("sug");
  const btn = document.querySelector("[data-sug-web]");
  if (!t || !box) return;
  const q = t.value.trim();
  if (q.length < 2) { sugSay(box, "題名を 2 文字以上入れてから押してください", true); return; }
  sugSay(box, "CoRichの公演情報を探しています… 8 秒ほどかかります", true);
  if (btn) btn.disabled = true;
  let d = null;
  try {
    const r = await fetch("/api/suggest_web?t=" + encodeURIComponent(T)
      + "&q=" + encodeURIComponent(q), {headers: {"X-Taguri-Token": T}});
    d = await r.json();
  } catch (e) { d = null; }
  if (btn) btn.disabled = false;
  if (!d) {
    sugSay(box, "探せませんでした。お手数ですが、手で入れてください", true);
    return;
  }
  if (d.error) { sugSay(box, d.error, true); return; }
  if (!d.rows || !d.rows.length) {
    // **見つからなかったことを、次に何をすればよいかと一緒に出す。**
    // 「0 件」だけでは、打ち間違いなのか無い公演なのか分からない
    sugSay(box, "「" + q + "」に当たる公演は見つかりませんでした ── 副題や団体名を外して"
      + "短くすると当たることがあります。見つからないときは、そのまま手で入れてください", true);
    return;
  }
  sugRender(box, d.rows,
    "CoRichの公演情報から " + d.rows.length + " 件見つかりました ── 観たものを選んでください");
}

function sugSay(box, msg, clear) {
  if (clear) box.replaceChildren();
  const p = document.createElement("p");
  p.className = "sug-head";
  p.textContent = msg;
  box.append(p);
}

// **手元の候補と外の候補を、同じ見た目で並べる。** 選んだあとの動きが同じなので、
// 描き方を 2 通り作ると片方だけ直す事故が起きる
function sugRender(box, rows, headText) {
  box.replaceChildren();
  if (!rows || !rows.length) return;
  sugSay(box, headText, false);
  rows.forEach(x => {
    const r = document.createElement("div");
    r.className = "sug-row " + x.kind;
    r.dataset.title = x.title;
    r.dataset.date = x.date || "";
    r.dataset.venue = x.venue || "";
    r.dataset.stage = x.kind === "stage" ? (x.stage_id || "") : "";
    r.innerHTML = '<span class="sg-p"></span><span class="sg-b">'
      + '<span class="sg-k"></span><span class="sg-t"></span>'
      + '<span class="sg-m"></span></span>';
    // **ポスターは端末内の道からしか出さない。** 手元に無い公演（外から探した分）は
    // 枠だけを置く ── 行の高さが揃わないと、並んだ候補を上から読めない
    const ph = r.querySelector(".sg-p");
    if (x.poster) {
      const im = document.createElement("img");
      im.src = "/img/" + encodeURIComponent(x.poster) + "?t=" + encodeURIComponent(T);
      im.alt = "";
      im.loading = "lazy";
      ph.append(im);
    } else {
      ph.classList.add("none");
    }
    r.querySelector(".sg-k").textContent = x.kind === "record" ? "記録あり" : "公演";
    r.querySelector(".sg-t").textContent = x.title;
    r.querySelector(".sg-m").textContent =
      [x.date, x.venue, x.note].filter(Boolean).join("・");
    if (x.cast) {
      const c = document.createElement("span");
      c.className = "sg-c";
      c.textContent = "出演 " + x.cast;
      r.append(c);
    }
    if (x.kind === "record") {
      const w = document.createElement("span");
      w.className = "sg-dup";
      w.textContent = "すでに記録にあります";
      r.append(w);
    } else {
      const pick = document.createElement("button");
      pick.textContent = "これを使う";
      pick.dataset.pick = "1";
      r.append(pick);
    }
    box.append(r);
  });
}

// 直すための手がかり。**抽出が切った題名の続きは、ほぼ本文に書いてある**
async function hints(box) {
  if (box.dataset.done) return;
  box.dataset.done = "1";
  box.textContent = "メールを読んでいます…";
  try {
    const r = await fetch("/api/mail_hints?t=" + encodeURIComponent(T)
      + "&uid=" + encodeURIComponent(box.dataset.hints), {headers: {"X-Taguri-Token": T}});
    const d = await r.json();
    box.textContent = "";
    (d.hints || []).forEach(h => {
      const p = document.createElement("div");
      p.textContent = "・" + h;
      box.append(p);
    });
    if (!(d.hints || []).length) box.textContent = "本文に手がかりは見つかりませんでした。";
  } catch (e) {
    box.dataset.done = "";
    box.textContent = "メール本文を読めませんでした（" + e + "）。";
  }
}

// **押した直後に走る取得を、終わるまで見に行く。**
// 起案者の指示（2026-08-24）で、公演を足した・結び付けた・お気に入りに登録した直後に
// 材料を取りに行くようにした。**取ってきたものは、画面を作り直さないと出ない** ──
// 押した本人からは「何も起きなかった」ように見えるので、終わってから読み込み直す。
function waitJob(g, reload) {
  const said = g && g.querySelector(".said");
  const tick = async () => {
    try {
      const r = await fetch("/api/import_status?t=" + encodeURIComponent(T),
                            {headers: {"X-Taguri-Token": T}});
      const d = await r.json();
      if (said && d.line) said.textContent = d.line;
      if (d.running) { setTimeout(tick, 1200); return; }
      if (reload) {
        // **開いていた道具は、読み込み直しても開いたままにする。** 名前を 1 つ登録する
        // たびに枠が畳まると、2 つめを足すのに毎回開き直すことになる
        const op = document.querySelector("details.pbox[open]");
        if (op && op.id) location.hash = op.id;
        setTimeout(() => location.reload(), 700);
      }
    } catch (e) { if (reload) location.reload(); }
  };
  setTimeout(tick, 400);
}

// 断片で指された道具を開く。**`<details>` は自分では開かない**ので、こちらで開ける
if (location.hash.length > 1) {
  const t = document.getElementById(location.hash.slice(1));
  if (t && t.tagName === "DETAILS") t.open = true;
}

// **押した後に何も動かないのは、効かなかったのと見分けが付かない。**
// 取り込みは数分から数十分かかる（起案者の指示・2026-08-25「経過がわかるバーがほしい」）。
// 出すのは 3 つ ── いま何をしているか、何通のうち何通目か、あとどれくらいか。
//
// **残り時間は、実際に進んだ速さから出す。** 決め打ちの秒数は初回（数千通）と
// 差分（数通）で桁が違うので、当たらない数字を出すことになる。
// **進み始めてすぐは出さない**（数パーセントぶんの速さで割ると何時間にも見える）。
let IMP_T0 = 0;

function impMin(sec) {
  if (sec < 60) return "残り 1 分もかかりません";
  const m = Math.round(sec / 60);
  return m < 60 ? "残り およそ " + m + " 分" : "残り およそ " + Math.round(m / 6) / 10 + " 時間";
}

function prog(d) {
  const bar = document.querySelector("[data-ibar]");
  if (!bar) return;
  bar.hidden = false;
  const done = !d.running, total = +d.total || 0, n = +d.n || 0;
  // **どこまで伸ばすかは、取り込みを見ている側が 3 つの段を通して出している**
  // （`serve._pct`）── 段ごとに数え直すと、段が変わるたびに帯が戻る
  const pct = done ? 100 : Math.max(0, Math.min(99, +d.pct || 0));
  const seek = !done && !total;         // 何通あるかが分かる前
  bar.classList.toggle("iwait", seek);
  bar.classList.toggle("done", done);
  // **探している間は幅を書かない。** 直に書いた指定は規則より強いので、置いたままだと
  // 流れる帯が幅 0 のまま動かない ── 分かった時点で消して、規則に返す
  const fill = bar.querySelector(".ifill");
  if (seek) fill.style.removeProperty("width");
  else fill.style.width = pct + "%";
  bar.setAttribute("aria-valuenow", pct);
  bar.querySelector(".istep").textContent =
    done ? "取り込みが終わりました" : (d.name || "取り込んでいます");
  bar.querySelector(".inum").textContent =
    done ? "" : (total ? n + " / " + total + " 通" : "");
  // **残りは帯の伸びから出す。** 通数から出すと段が変わるたびに分母が変わり、
  // **段の変わり目で残り時間が跳ねる**（段 3 の 1 通目で「残り 40 分」になる）
  const rest = bar.querySelector(".irest");
  if (done || pct < 5 || !IMP_T0) rest.textContent = "";
  else rest.textContent = impMin((Date.now() - IMP_T0) / 1000 / pct * (100 - pct));
  // **終わった段は緑で埋める。** どこまで通ったのかが、止まったときにも残る
  const s = done ? 4 : (+d.step || 1);
  bar.querySelectorAll(".isteps li").forEach((li, i) => {
    li.classList.toggle("on", !done && i + 1 === s);
    li.classList.toggle("fin", i + 1 < s);
  });
}

function poll(g, b) {
  const said = g.querySelector(".said");
  IMP_T0 = IMP_T0 || Date.now();
  const tick = async () => {
    try {
      const r = await fetch("/api/import_status?t=" + encodeURIComponent(T),
                            {headers: {"X-Taguri-Token": T}});
      const d = await r.json();
      prog(d);
      said.textContent = d.line || "…";
      if (d.running) { setTimeout(tick, 1000); return; }
      b.disabled = false;
      IMP_T0 = 0;
      said.textContent = d.line || "終わりました";
    } catch (e) {
      // **聞きに行けなくても、走っているものは走っている。** 諦めずにもう一度聞く
      setTimeout(tick, 3000);
    }
  };
  tick();
}

// 走っている最中に開き直したときは、そのまま続きから見せる（`app._import_bar`）
{
  const bar = live && document.querySelector("[data-ibar][data-run]");
  if (bar) {
    const g = document.querySelector(".imp");
    if (g) poll(g, g.querySelector("button"));
  }
}

// **入力欄の動きは、後から足した 1 枚にも付ける。**
//
// ボタンは `document` で受けているので足した 1 枚でも効くが、**入力欄は読み込みのときに
// 1 度だけ結んでいた** ── 入れ替わりに差し込んだカードの欄は、書けるのに保存されない
// 欄になる。**2 度結ばないように印を付ける**（同じ blur で 2 回送ることになる）。
function bindNotes(root) {
// 「興味あり」に添えた理由。**離れたときに保存する**（書いている途中で送らない）
root.querySelectorAll(".why-note textarea").forEach(t => {
  if (t.dataset.bound) return;
  t.dataset.bound = "1";
  t.dataset.was = t.value;
  t.addEventListener("blur", () => {
    const g = t.closest(".why-note");
    if (!live || t.value === t.dataset.was) return;
    t.dataset.was = t.value;
    post("/api/react", {stage_id: g.dataset.stage, note: t.value}, g,
         "理由を保存した（お気に入りの昇格候補に出る）");
  });
});

// 「興味なし」に添えた見送った理由。**離れたときに保存する**
root.querySelectorAll("textarea[data-nono]").forEach(t => {
  if (t.dataset.bound) return;
  t.dataset.bound = "1";
  t.dataset.was = t.value;
  t.addEventListener("blur", () => {
    const g = t.closest(".nn");
    if (!live || t.value === t.dataset.was) return;
    t.dataset.was = t.value;
    post("/api/react", {stage_id: g.dataset.stage, note_no: t.value}, g,
         "理由を保存した").then(d => {
      if (!d || !t.value.trim()) return;
      // **畳んだ見出しに書いた文を出す。** 閉じても読めることが、この欄の返りである
      const s = g.querySelector("summary");
      s.textContent = "見送った理由";
      const v = document.createElement("span");
      v.className = "nnv";
      v.textContent = t.value;
      s.append(v);
    });
  });
});

root.querySelectorAll("textarea[data-note]").forEach(t => {
  if (t.dataset.bound) return;
  t.dataset.bound = "1";
  t.dataset.was = t.value;
  t.addEventListener("blur", () => {
    if (!live || t.value === t.dataset.was) return;
    t.dataset.was = t.value;
    // **保存できたことを、書いた欄のそばに出す。** `.rec-row` しか見ていなかったため、
    // 評価待ちの行と溜まった分の束に置いた欄では**保存の合図がどこにも出なかった**
    // （消えたのか保存されたのか分からない入力になる）
    post("/api/note", {work_key: t.dataset.note, note_impression: t.value},
         t.closest(".inote, .wnote, .wait, .rec-row"), "感想を保存した");
  });
});

// **「この回のメモ」も、離れたときに保存する**（感想と同じ形）。推薦には使わない
// 欄なので、送り先も別の口（`/api/visit_note`）にする
root.querySelectorAll("textarea[data-vnote]").forEach(t => {
  if (t.dataset.bound) return;
  t.dataset.bound = "1";
  t.dataset.was = t.value;
  t.addEventListener("blur", () => {
    if (!live || t.value === t.dataset.was) return;
    t.dataset.was = t.value;
    post("/api/visit_note", {uid: t.dataset.vnote, note: t.value},
         t.closest(".vnote, .rec-row"), "メモを保存した");
  });
});
}

bindNotes(document);

// **選んだ画像を、その場で端末内に写す。**（起案者の指示・2026-08-24）
// **外へは 1 バイトも出さない** ── 読むのはブラウザが開いたファイルで、送り先は
// 同じ端末で動いているこちらのプロセスだけである（企画書 5 章の守り 5 はそのまま）。
// **押した結果をその場に出す** ── 絵が入れ替わらないと、写せたのかが分からない。
document.addEventListener("change", ev => {
  const i = ev.target.closest("[data-hand-img]");
  if (!i || !live || !i.files || !i.files[0]) return;
  const g = i.closest(".hand"), said = g.querySelector(".hand-p .said");
  const f = i.files[0];
  if (said) said.textContent = "写しています…";
  const rd = new FileReader();
  rd.onerror = () => { if (said) said.textContent = "画像を読めませんでした"; };
  rd.onload = () => {
    post("/api/hand_poster", {work_key: g.dataset.work, image: rd.result}, null, null)
      .then(d => {
        if (!d) { if (said) said.textContent = "入れられませんでした"; return; }
        if (said) said.textContent = d.said || "入れ替えました";
        // **この欄の絵と、記録の側の絵の両方を差し替える**（同じ 1 枚を 2 か所に出している）
        // **名前は中身から作られているので、入れ替えれば URL が変わる**
        // （同じ URL のままだとブラウザが古い絵を出し続ける）
        const url = "/img/" + encodeURIComponent(d.poster) + "?t=" + encodeURIComponent(T);
        g.querySelectorAll(".ed-pv").forEach(pv => {
          pv.replaceChildren();
          const im = document.createElement("img");
          im.src = url;
          im.alt = "";
          pv.append(im);
        });
        setTimeout(() => location.reload(), 1200);
      });
  };
  rd.readAsDataURL(f);
  i.value = "";
});

// **効かせ方の欄は、開いたときは畳んでおく**（起案者の指示・2026-08-24 ──
// 「表示したとき常に開いているので、初期は閉じているようにしてください」）。
// **開くのは、確定か「ふつうに戻す」を押した直後だけである** ── その知らせ
// （推薦から外れた件数）はこの欄の中にしか無いので、畳んで戻すと結果が見えない。
{
  const wb = document.getElementById("weights");
  if (wb && location.hash === "#weights") wb.open = true;
}

// **画面を閉じたら自動で終了する仕組みは撤回した**（起案者の指示・2026-08-27）。
// 「記録を見返す」のような画面を長時間開いたままにする使い方と噛み合わなかった
// （タブを裏に回すとブラウザが定期送信を間引き、まだ見ているのに落ちることがあった）。
// 閉じるのはフッターの「終わる」ボタン（`/api/close`）と `Ctrl-C` に一本化した。
if (live) sugWatch();
"""

APP_CSS = """
/* ---- 2 カラム。ナビゲーションは常に左に出したままにする -------------------
   起案者の指示（2026-08-24）──「上にナビゲーションバーじゃなくて 2 カラムにして
   常に左にバーを出していてほしい」。

   **横並びの札を上に置くと、下にスクロールした時点で行き先が画面から消えていた。**
   この画面は 1 件ずつ押して進める使い方（評価を付ける・興味ありをもぎる）なので、
   縦に長い。左に貼り付けておけば、どこまで下がっても現在地と行き先が見えている。
   **縦に並べる利点はもう 1 つある** ── 項目名を省略せずに置ける。横並びでは
   「観た公演の評価」「公演情報の登録」が折り返して 2 段になっていた。            */
body{padding:0}
.shell{display:flex;align-items:flex-start;min-height:100vh}
/* ---- 左の帯は幕の色で塗る ---------------------------------------------------
   **帯と本文が同じ色だったので、境目が線 1 本しか無かった。** 画面が 1 枚の平らな面に
   見えて、どこが行き先でどこが読むところなのかが形で分からない ── **色を変えれば、
   線を足さずに分かれる。** えんじは `.curtain` の意匠にすでに入っている色なので、
   新しい色を持ち込んではいない。
   **現在地は紙の色で抜く。** 帯の中で 1 か所だけ紙が出ている形になるので、
   「いまこの紙を読んでいる」がそのまま出る。                                   */
/* **行の高さは、縦 15 行が入る前提で決める。** 起案者の指摘（2026-08-25）──
   「サイドバーが長すぎてスクロールバーがでちゃってる。スクロールバー出るのはダサい」。
   **束を 2 つ作った時点で、全部開くと帯は 15 行になっていた**（親 7 行と子 8 行）──
   1 行 43px・上下の余白 42px で約 700px あり、**縦 700px に満たない画面では必ず
   スクロールバーが出る。** 既定でいま居る束だけを開く手当て（`layout._group`）と
   合わせて、1 行あたりの高さも詰めた ── 詰めたのは余白だけで、**文字の大きさは
   変えていない**（読みにくくして行数を稼ぐことになる）。                        */
.side{position:sticky;top:0;flex:none;width:228px;height:100vh;overflow-y:auto;
 display:flex;flex-direction:column;gap:2px;padding:16px 14px 16px;
 background:var(--curtain);color:var(--curtain-w);border-right:1px solid var(--curtain);
 /* **それでも溢れる高さの画面はある。** 切り取るのではなく送るが、**太い灰色の棒が
    えんじの帯に載るのは避ける** ── 細くして、帯の中の色で塗る                  */
 scrollbar-width:thin;
 scrollbar-color:color-mix(in srgb,var(--curtain-w) 34%,transparent) transparent}
.side::-webkit-scrollbar{width:6px}
.side::-webkit-scrollbar-thumb{border-radius:99px;
 background:color-mix(in srgb,var(--curtain-w) 34%,transparent)}
.side::-webkit-scrollbar-track{background:transparent}
.side .brand{font-family:var(--mincho);font-size:19px;font-weight:600;letter-spacing:.14em;
 color:var(--curtain-w);padding:0 12px 12px}
/* **「たぐり」の下に検索窓を置く**（起案者の指示・2026-08-26）。宛先は既にある
   「探す」（`/search`）と同じ ── 新しい探し方は作らない。帯のどこからでも 1 打で
   探せるようにする窓なので、押し口ではなく Enter で送る単発の入力欄にする */
.side .search{position:relative;margin:0 0 10px;padding:0 12px}
.side .search svg{position:absolute;left:22px;top:50%;transform:translateY(-50%);
 opacity:.6;pointer-events:none}
.side .search input{width:100%;box-sizing:border-box;font:inherit;font-size:13.5px;
 padding:7px 10px 7px 32px;border-radius:10px;
 border:1px solid color-mix(in srgb,var(--curtain-w) 24%,transparent);
 background:color-mix(in srgb,var(--curtain-w) 10%,transparent);color:var(--curtain-w)}
.side .search input::placeholder{color:color-mix(in srgb,var(--curtain-w) 55%,transparent)}
.side .search input:focus{outline:2px solid var(--curtain-w);outline-offset:1px}
.side a{font-size:14.5px;text-decoration:none;padding:8px 12px;line-height:1.4;
 color:color-mix(in srgb,var(--curtain-w) 76%,transparent);
 border:1px solid transparent;border-radius:10px}
.side a:hover{color:var(--curtain-w);
 background:color-mix(in srgb,var(--curtain-w) 12%,transparent)}
.side a.on{color:var(--curtain);font-weight:700;background:var(--surf);border-color:var(--surf)}
/* **公演カレンダーと購入済み公演の間に隙間を入れる。** どちらも独立した行き先だが、
   「これから観に行く公演」を扱う 2 つが地続きに詰まって見えていた（起案者の指示・
   2026-08-26）。隙間は `href` で狙う ── 束を持たない単独行なので `NAV` 側に印を
   増やすほどではない */
.side a[href^="/tickets"]{margin-top:10px}
/* **段の途中の画面は、親の下に一段下げて置く。** 同じ高さに並べると 8 つの対等な
   行き先に見えて、「おすすめ」の中の段であることが画面から消える */
.side a.kid{margin-left:16px;font-size:13.5px;padding:5px 12px;gap:7px}
/* ---- 行き先を持たない親（「おすすめ」）------------------------------------
   起案者の指示（2026-08-25）── 押すと畳む／開くだけの押し口にした。
   **見た目は隣の行き先と同じ寸法にそろえる**（同じ働きの部品を作ったのではなく、
   同じ帯に並ぶ 1 行なので、行の高さと余白がずれると帯が段違いに見える）。
   **違いは山形 1 つで出す** ── 右を向いていれば畳んである、下を向いていれば開いている。
   文字を「＋／−」にはしない。押した結果は形で出し、名前の欄には名前だけを置く。   */
.side .grp{display:flex;flex-direction:column;gap:2px}
.side .grp>summary{display:flex;align-items:center;gap:9px;cursor:pointer;
 list-style:none;font-size:14.5px;padding:8px 12px;line-height:1.4;
 border:1px solid transparent;border-radius:10px;
 color:color-mix(in srgb,var(--curtain-w) 76%,transparent)}
.side .grp>summary::-webkit-details-marker{display:none}
.side .grp>summary:hover{color:var(--curtain-w);
 background:color-mix(in srgb,var(--curtain-w) 12%,transparent)}
.side .grp .gl{flex:1 1 auto;min-width:0}
.side .grp .cv{flex:none;opacity:.7;transition:transform .15s ease}
.side .grp[open]>summary .cv{transform:rotate(90deg)}
@media(prefers-reduced-motion:reduce){.side .grp .cv{transition:none}}
/* **畳んだときだけ、親が現在地の紙になる。** 開いているあいだは子のほうが現在地なので
   親は薄く光るだけにする（親子が両方濃いと、どちらが現在地か分からない）── しかし
   畳むと子が画面から消えるので、**そのままでは現在地がどこにも無くなる。**       */
.side .grp[open]>summary.sec{color:var(--curtain-w);
 background:color-mix(in srgb,var(--curtain-w) 16%,transparent)}
.side .grp:not([open])>summary.sec{color:var(--curtain);font-weight:700;
 background:var(--surf);border-color:var(--surf)}
/* **開いている節の親は、薄く光らせる。** 子が現在地のときに親まで濃く光ると、
   どちらが現在地なのか分からない */
.side a.sec{color:var(--curtain-w);
 background:color-mix(in srgb,var(--curtain-w) 16%,transparent)}
/* **`.main` は名前がぶつかっている。** チケットの本文の列も `.main` を名乗るので
   （`render_recommend.py` の `ticket`）、素の `.main` に余白を書くと**カード 1 枚ずつの
   中にも同じ余白が入る。** 実測で 1 枚あたり下に 72px・左右に 20px の使われない帯が
   でき、推薦の 15 枚では 1,080px（画面 1 枚ぶん）を占めていた。**帯の直下の列だけを
   指す。** 名前を変えるほうは採らない ── チケットの側は 3 つの画面で使われており、
   意匠を作業中の側に触ることになる。                                          */
.shell>.main{flex:1 1 auto;min-width:0;padding:0 20px 72px}
/* **狭い画面では 1 カラムに戻す。** 幅 228px を削ると本文が読めなくなるので、
   左に貼るのをやめて上に横並びで置く（元の形に近い）。                          */
@media(max-width:820px){
 .shell{flex-direction:column}
 .side{position:static;width:100%;height:auto;flex-direction:row;flex-wrap:wrap;gap:4px;
  padding:12px 14px;border-right:0;border-bottom:1px solid var(--curtain)}
 .side .brand{width:100%;padding:0 4px 6px}
 .side .search{width:100%;padding:0 4px 6px}
 /* **横並びに戻る幅では、束も 1 行として横に流す。** 縦積みのまま残すと、
    束の中だけが段違いになって帯が 2 段の高さになる                            */
 .side .grp{width:100%;flex-direction:row;flex-wrap:wrap;align-items:center;gap:4px}
 .side .grp .gl{flex:0 0 auto}
 .side .grp>summary{padding:8px 12px}
 .side a.kid{margin-left:0}
 .shell>.main{width:100%;padding:0 14px 72px}
 /* **横に折り返す帯なので、1行に入る数を増やして段数を減らす**（起案者の指摘・
    2026-08-29「ナビゲーションバーが長い」）。並び方は変えず、文字・余白・アイコンを
    詰めるだけにした ── 縦積みの帯からハンバーガーメニューに変える案もあったが、
    起案者の指示で「今の形のまま、並び方をもっとこまめる」を選んだ。 */
 .side a,.side .grp>summary{font-size:12.5px;padding:5px 9px;gap:5px}
 .side a.kid{font-size:11.5px;padding:4px 8px;gap:5px}
 .side svg.ico{width:13px;height:13px}
 .side .brand svg.tgm{width:19px;height:19px}}
/* ---- 段の帯（フローチャート）は撤去した ------------------------------------
   起案者の指摘「おすすめと評価のリンクを外して」→「これ自体消してほしい」→
   「記録を見返すのも消してよい」の 3 段階で、`.sub` の帯を全画面から消した
   （2026-08-25）。戻るボタンと道のり（`.crumbbar`）が役目を引き継いだ ── CSS も
   `flow_nav()` と一緒に削った。 */
/* ---- 戻るボタンとパンくずリスト ---------------------------------------------
   **どの画面にも同じ 1 行を置く**（起案者の指示・2026-08-25）。左に戻る、右に道のり
   ── 戻るは「直前の状態」、パンくずは「いまどの束の中か」で役目を分けている。       */
.crumbbar{max-width:1000px;margin:16px auto 0;padding:0 4px;display:flex;
 align-items:center;gap:14px;flex-wrap:wrap}
.backbtn{flex:none;font:inherit;font-size:12.5px;color:var(--ink2);background:none;
 border:1px solid var(--ring);border-radius:99px;padding:5px 13px;cursor:pointer}
.backbtn:hover{color:var(--ink);border-color:var(--base)}
.crumb{font-size:12.5px;color:var(--mute);display:flex;flex-wrap:wrap;
 align-items:center;gap:4px;min-width:0}
.crumb a{color:var(--acc);text-decoration:none}
.crumb a:hover{text-decoration:underline}
.crumb span[aria-current]{color:var(--ink2);font-weight:600}
.crumbsep{color:var(--base)}
.wrap{max-width:1000px}
/* `ch` を `em` に直した（起案者の指摘 2026-08-26）── 理由は render_recommend.py の `.lead` にある */
.lede{color:var(--ink2);margin:0 0 22px;font-size:14px;max-width:70em}
.poster{width:104px;height:146px;object-fit:cover;border-radius:6px;display:block;
 background:var(--grid);border:1px solid var(--ring)}
/* ---- 読み込み中の文字（起案者の指摘・2026-08-25）---------------------------
   **枠は `.poster` と同じ寸法にする** ── サイズを持つのは枠（`.pwrap`）で、
   絵はその中を埋めるだけにする。読み込む前と失敗したときは絵を透明にし、
   文字だけを重ねて出す。**遅いのではなく壊れているように見えるのを防ぐのが目的**
   なので、絵が来た瞬間に文字を消す（読み込み中の一瞬より長く出さない）。          */
.pwrap{position:relative;display:inline-block;border-radius:6px;overflow:hidden}
/* **絵は枠いっぱいに合わせる。** `.poster` 単体の固定寸法（104×146）は他の一覧行
   （評価一覧・日記帳など、`.pwrap` を使わない箇所）向けのままにしてあるので、
   ここで上書きしないと枠が 132×186 でも絵は 104×146 のまま隅に残る */
.pwrap .poster{width:100%;height:100%;border-radius:0;border:0;opacity:0;
 transition:opacity .12s}
.pwrap.ld .poster{opacity:1}
.pwrap.pe .poster{display:none}
.pwrap .pmsg{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
 padding:6px;text-align:center;font-size:10.5px;line-height:1.35;color:var(--mute)}
.pwrap.ld .pmsg{display:none}
@media(prefers-reduced-motion:reduce){.pwrap .poster{transition:none}}
.fav .pwrap{width:64px;height:90px;flex:none}
/* ---- 舞台の意匠 ------------------------------------------------------------
   **飾りだが、役割はある。** どの画面に居るのかを一目で分かるようにするための地であって、
   数字や理由の読み取りを邪魔しない位置（見出しの背後と、ページの上端）にだけ置く。 */
.curtain{height:22px;margin:0 0 20px;border-radius:0 0 12px 12px;
 background:repeating-linear-gradient(90deg,#7d1f2c 0 13px,#5c1220 13px 26px);
 box-shadow:inset 0 -7px 14px rgba(0,0,0,.38)}
.spot{position:relative}
.spot>h1{position:relative}
.spot::before{content:"";position:absolute;left:-24px;right:-24px;top:-34px;height:130px;
 background:radial-gradient(ellipse 60% 100% at 16% 0%,rgba(237,161,0,.16),transparent 66%);
 pointer-events:none}
@media (prefers-reduced-motion:no-preference){
 .ticket{animation:rise .34s cubic-bezier(.2,.8,.3,1) both}
 @keyframes rise{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}}
/* **半券の寸法を決める規則は `.rec-row .pin>*` の 1 本だけにする。**
   ここに `.rec-row .pin .poster{height:100%}` を足していたため、**「公演詳細を直す」を
   開いた行では半券が縦に伸びていた** ── `.pin` は `.rec-row`（`align-items:stretch`）の
   子なので高さが行いっぱいに確定しており、`height:100%` がその高さを拾っていた。
   **寸法を 2 か所で決めると、片方が勝ったことに気づけない。** */
.bundle{background:var(--surf);border:1px solid var(--ring);border-radius:12px;
 padding:12px 18px;margin:0 0 10px}
.bundle summary{cursor:pointer;font-size:14px;font-weight:600}
.bundle .lead{margin:10px 0 12px}
.tags{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0 0}
.tag{font-size:12.5px;border:1px solid var(--ring);border-radius:99px;padding:3px 8px 3px 5px;
 display:inline-flex;gap:8px;align-items:center;color:var(--ink2);background:var(--surf)}
.tag .tgn{min-width:0}
.tag button{font:inherit;font-size:11px;border:0;background:transparent;color:var(--mute);cursor:pointer}
.tag button:hover{color:#e34948}
.fav-add,.miss-add,.imp,.add-work{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0 0}
/* ---- 公演詳細を直す欄 -----------------------------------------------------
   **読む画面の中に置く入力なので、畳んだ状態を既定にする。** 開いた行だけが
   入力の場になり、読んでいる最中の行は読むための形のまま残る。 */
/* **先に確かめてほしい記録は、余白の側で言う。** 本文の枠を変えると、読む面の
   見た目が記録ごとに変わる */
.rec-row.check .marg{border-right-width:3px}
.rec-row.check .dt .md{color:var(--warn)}
.editor{margin:8px 0 0;font-size:13px}
.editor>summary{cursor:pointer;color:var(--acc);font-size:12.5px}
.editor[open]{border:1px dashed var(--ring);border-radius:10px;padding:10px 12px}
/* `ch`→`em`（render_recommend.py の `.lead` と同じ理由） */
.ed-lead{color:var(--ink2);font-size:12.5px;margin:8px 0 10px;max-width:64em}
.ed-t{display:block;font-size:12.5px;color:var(--mute);margin:0 0 8px}
.ed-t input{display:block;width:100%;max-width:44em;margin:3px 0 0}
/* **入力欄と、そのすぐ後ろの文字を離す**（起案者の指摘・2026-08-26 ── 日付・劇場・
   時刻の欄が近くなりすぎて見える）。`gap:8px` は同じ列にある「入力欄どうし」には
   足りていたが、**枠を持つ入力欄と、枠の無い文字（`.ed-m`）が並ぶと、枠の分だけ
   さらに近く見える。** 12px でも測ってみたが、まだ詰まって見えたので 16px にした
   （`.isteps` などで既に使っている値にそろえた）。 */
.ed-show{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin:0 0 6px}
.ed-m{color:var(--mute);font-size:11.5px}
.ed-btns{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:10px 0 0}
.ed-btns button{font:inherit;font-size:12.5px;padding:6px 16px;border-radius:99px;
 border:1px solid var(--ring);background:var(--surf);color:var(--ink2);cursor:pointer}
.ed-btns button:first-child{border-color:var(--acc);color:var(--acc);font-weight:600}
.ed-mail{margin:10px 0 0;border-top:1px solid var(--grid);padding:8px 0 0}
.ed-src{margin:0 0 8px;font-size:12px;color:var(--ink2);display:flex;
 flex-direction:column;gap:2px}
.ed-hints{color:var(--mute);font-size:11.5px;white-space:pre-wrap}
select,input[type=text],input[type=date],input[type=time]{font:inherit;font-size:13px;
 padding:6px 10px;border:1px solid var(--ring);border-radius:8px;background:var(--plane);
 color:var(--ink)}
.card button,.fav-add button,.miss-add button,.imp button,.add-work button{
 font:inherit;font-size:13px;padding:7px 18px;border-radius:99px;
 border:1px solid var(--ring);background:var(--surf);color:var(--ink2);cursor:pointer}
.imp button{border-color:var(--acc);color:var(--acc);font-weight:600}
/* ---- 取り込みの進み具合 -----------------------------------------------------
   起案者の指示（2026-08-25）──「経過がわかるバーがほしい。進行状況を一目で」。

   **動きで出すのは 2 つだけである** ── どこまで来たか（帯の長さ）と、いま何をして
   いるか（点）。数字は帯の上に置く。**帯の色は藍のまま**（押した結果として動いて
   いるもの）で、終わったら値の緑に変わる ── `.said` の「できました」と同じ色である。 */
.ibar{margin:14px 0 0;max-width:46em}
.ibar[hidden]{display:none}
/* **狭い画面では折り返す。** 3 つを 1 行に詰めると、段の名前が 2 行に割れた横で
   「137 / 402 通」も割れて、どの数字がどれなのか読めなくなる ── 数字のほうは
   割らずに次の行へ送る（起案者の指摘・2026-08-25） */
.ist{display:flex;gap:4px 10px;align-items:baseline;flex-wrap:wrap;
 font-size:12.5px;color:var(--ink2)}
.ist .istep{font-weight:600}
.ist .inum,.ist .irest{color:var(--mute);font-size:11.5px;white-space:nowrap;
 font-variant-numeric:tabular-nums}
.ist .irest{margin-left:auto;flex:none}
.itrack{position:relative;height:9px;margin:7px 0 0;border-radius:99px;
 background:var(--grid);overflow:hidden}
.ifill{height:100%;border-radius:99px;background:var(--acc);transition:width .5s ease}
.ibar.done .ifill{background:var(--good)}
/* **何通あるかが分かるまでは伸ばさない。** 0 パーセントの帯を出すと止まって見えるので、
   短い帯を流して「数えている最中である」ことを形で出す。
   **状態の名前に `wait` は使えない** ── 評価待ちの 1 行が同じ名前を使っており
   （`.wait{display:flex;border-left:3px …}`）、**帯がその行の形になって崩れていた**
   （起案者の指摘・2026-08-25）。部品の中だけで通じる名前を付ける。 */
.ibar.iwait .ifill{width:32%;transition:none;animation:isweep 1.6s ease-in-out infinite}
@keyframes isweep{from{transform:translateX(-110%)}to{transform:translateX(320%)}}
.isteps{list-style:none;display:flex;gap:16px;flex-wrap:wrap;margin:9px 0 0;padding:0;
 font-size:11.5px;color:var(--mute)}
.isteps li{display:flex;gap:6px;align-items:center}
.isteps li::before{content:"";width:7px;height:7px;border-radius:99px;flex:none;
 border:1px solid var(--base)}
.isteps li.on{color:var(--acc);font-weight:600}
.isteps li.on::before{border-color:var(--acc);background:var(--acc);
 animation:ipulse 1.3s ease-in-out infinite}
.isteps li.fin{color:var(--ink2)}
.isteps li.fin::before{border-color:var(--good);background:var(--good)}
.ibar.done .isteps li{color:var(--ink2)}
.ibar.done .isteps li::before{border-color:var(--good);background:var(--good);animation:none}
@keyframes ipulse{50%{opacity:.3}}
/* ---- 読み込み直す押し口は、終わってから出す -------------------------------
   **小さく置く**（起案者の指示・2026-08-25）。この画面で先に押すのは「取り込みを
   始める」であって、これはその後始末である ── 同じ寸法で並ぶと、2 つの入口が
   あるように見える。**役は同じなので形は変えない**（丸い縁・藍）。 */
.idone{display:none;margin:10px 0 0}
.ibar.done .idone{display:block}
.idone button{font:inherit;font-size:11.5px;padding:3px 11px;border-radius:99px;
 border:1px solid var(--ring);background:var(--surf);color:var(--acc);cursor:pointer}
.idone button:hover{border-color:var(--acc)}
/* ---- 今回入った公演の題名 ---------------------------------------------------
   **並べるだけである。** 日付も会場も付けない ── ここは入ったことを確かめる場所で、
   記録を読む場所ではない。**区切りは読点ではなく「／」** ── 題名の中に読点が入る
   ことがあり、どこまでが 1 つの題名なのかが読めなくなる。 */
.impgot{margin:12px 0 0;padding:11px 14px;border-radius:10px;
 border:1px solid var(--ring);background:var(--plane);font-size:13px;line-height:1.9}
.impgot b{font-size:11.5px;color:var(--mute);font-weight:600;display:block;margin:0 0 2px}
.impgot-l{color:var(--ink)}
/* **動きを減らす設定の端末では流さない。** 長さと点の色だけで同じことが読める */
@media (prefers-reduced-motion:reduce){
 .ibar.iwait .ifill,.isteps li.on::before{animation:none}
 .ifill{transition:none}}
button:disabled{opacity:.45;cursor:default}
.dead{opacity:.4;pointer-events:none}
/* ---- 1 件の記録を、1 日ぶんの帳面として組む ---------------------------------
   起案者の指示（2026-08-24）──「記録を観るページは日記帳っぽいとなおいい」。

   **枠で囲むのをやめた。** 108 件が同じ角丸の箱で縦に並ぶと、どれも同じ重さに見えて
   1 件 1 件が思い出であるという前提が形に出ていない。**左の余白と本文の境に線を
   1 本引くだけで 1 件が切れる**ので、箱が 108 個並ばない。

   行送りを 30px に固定して、その間隔で薄い横罫を敷く ── **題名・劇場・感想がすべて
   同じ罫に乗るので、あとから書き足した感想が同じ帳面の続きとして読める。**       */
.rec-row{display:flex;align-items:stretch;background:var(--surf);
 border:1px solid var(--grid);border-top:0;margin:0}
.rec-row:first-of-type{border-top:1px solid var(--grid);border-radius:0 4px 0 0}
.rec-row:last-of-type{border-radius:0 0 4px 4px}
/* ---- 左の余白。日付と印だけを置く ------------------------------------------
   **境の縦線は幕の色にする。** 帳面の朱の罫と同じ位置に来るので、意匠としても
   「余白と本文の境」という役割としても同じものになる。                          */
.rec-row .marg{flex:none;width:112px;padding:20px 14px 18px;
 display:flex;flex-direction:column;align-items:flex-end;gap:11px;text-align:right;
 border-right:1px solid color-mix(in srgb,var(--curtain) 36%,transparent)}
.rec-row .dt{font-family:var(--mincho);line-height:1.2;display:block}
.rec-row .dt .y{display:block;font-size:11.5px;color:var(--mute);letter-spacing:.09em;
 font-variant-numeric:tabular-nums}
.rec-row .dt .md{display:block;font-size:27px;font-weight:600;color:var(--ink);
 font-variant-numeric:tabular-nums;letter-spacing:.02em}
.rec-row .dt .wd{display:block;font-size:11px;color:var(--mute)}
.rec-row .dt.no{font-size:11.5px;color:var(--mute);line-height:1.5;font-family:inherit}
/* ---- 罫を敷いた面 ----------------------------------------------------------
   罫は背景なので、開いた入力欄の下にも走る（帳面の上で書いているので、それでよい）。
   **入力欄と押し口の側を不透明にする** ── 罫が文字と重なると読めない。          */
.rec-row .page{flex:1;min-width:0;padding:20px 22px 18px;
 background-image:repeating-linear-gradient(to bottom,
  transparent 0 29px,var(--grid) 29px 30px);
 background-position:0 20px}
.rec-row .ttl{font-family:var(--mincho);font-size:18px;font-weight:600;line-height:30px}
.rec-row .where{font-size:12.5px;color:var(--ink2);line-height:30px;
 display:flex;gap:0;flex-wrap:wrap}
.rec-row .where span+span::before{content:"／";color:var(--mute);padding:0 8px}
/* **押し口の列は、罫 1 行ぶんの高さに収める。** ここだけ高さが変わると、
   下の行から罫と文字がずれる */
.rec-row .tools{display:flex;gap:10px;align-items:center;flex-wrap:wrap;
 min-height:30px;margin:0}
/* **押し口は画面をまたいで同じ形にする**（`.rb button` は `render_recommend` の
   `.btns button` と同じ指定を共有している）。ここで別の形を作らない */
.rec-row .rb{display:inline-flex;gap:6px;align-items:center;flex-wrap:wrap}
/* **`display` を書いたら `[hidden]` を書き直す。** `[hidden]` の display:none は
   ブラウザの既定なので、こちらで display を書くと押す前から開いた状態で出てしまう
   （`.inote[hidden]` と同じ落とし穴） */
.rec-row .rb[hidden]{display:none}
.rec-row .rb button{min-width:38px;text-align:center}
.rec-row textarea{width:100%;margin:6px 0 0;font:inherit;font-size:13px;padding:8px 11px;
 border:1px solid var(--base);border-radius:8px;background:var(--surf);color:var(--ink);
 min-height:44px;resize:vertical}
/* ---- 右に貼った半券 --------------------------------------------------------
   **白い縁を付けてわずかに傾け、上端にテープを 1 枚。**
   **出せなかった分も枠を残す** ── 行によって高さが変わると、上から順に読めない。  */
.rec-row .pin{flex:none;align-self:flex-start;width:126px;padding:22px 20px 18px 6px;
 display:flex;align-items:flex-start;justify-content:center}
.rec-row .pin>*{position:relative;width:84px;height:118px;flex:none;
 object-fit:cover;background:var(--plane);
 border:5px solid var(--surf);border-radius:1px;transform:rotate(-1.1deg);
 box-shadow:0 1px 3px rgba(0,0,0,.2),0 7px 16px -10px rgba(0,0,0,.3)}
.rec-row:nth-of-type(2n) .pin>*{transform:rotate(1.3deg)}
.rec-row .pin>*::after{content:"";position:absolute;top:-11px;left:50%;width:46px;height:15px;
 transform:translateX(-50%) rotate(-2.5deg);
 background:color-mix(in srgb,var(--ink) 8%,transparent);
 box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--ink) 5%,transparent)}
.rec-row .noposter{background:repeating-linear-gradient(135deg,
 var(--plane) 0 6px,var(--surf) 6px 12px)}
/* ---- 評価の判子 ------------------------------------------------------------
   起案者の指示（2026-08-24）──「評価の◎とかのハンコがもっとスタンプで押したっぽい
   デザインだったらよりリアル」。

   **輪郭を歪めているのは `feTurbulence` の 1 枚のフィルタである**（`layout` が
   1 か所だけ置く）。円と字を同じフィルタに通すので、**輪と字が同じゴム版で押された
   ように崩れる** ── 円だけを歪めると、きれいな字が汚れた輪の中に浮いて貼り絵に見える。

   **紙に染む重ね方にする**（`--stamp-blend`）。明るい地では `multiply` で紙の色を
   通し、暗い地では `screen` で抜く。**上から不透明な色を置くとシールに見える。**

   **インクの抜けを 4 か所置く。** 判子は全面が均一に付かない ── 抜けは紙の色の点で
   作るので、`multiply` を通すと紙がそのまま出る（塗り足しではなく抜きである）。   */
.rec-row .stamp{--rot:0deg;position:relative;flex:none;width:46px;height:46px;
 display:grid;place-items:center;border:2.5px solid var(--curtain);border-radius:50%;
 font-family:var(--mincho);font-size:21px;font-weight:600;color:var(--curtain);
 background:radial-gradient(circle at 34% 28%,
  color-mix(in srgb,var(--curtain) 9%,transparent),transparent 68%);
 transform:rotate(var(--rot));opacity:var(--stamp-ink);
 mix-blend-mode:var(--stamp-blend);filter:url(#tg-ink)}
.rec-row .stamp::after{content:"";position:absolute;inset:-3px;border-radius:50%;
 pointer-events:none;background-image:
  radial-gradient(circle at 21% 33%,var(--surf) 0 1.7px,transparent 1.8px),
  radial-gradient(circle at 71% 17%,var(--surf) 0 1.1px,transparent 1.2px),
  radial-gradient(circle at 82% 70%,var(--surf) 0 2px,transparent 2.1px),
  radial-gradient(circle at 33% 81%,var(--surf) 0 1.3px,transparent 1.4px)}
/* **「まだ判断できない」は金にして字を落とす。** えんじで押すと、評価が付いた記録と
   見分けが付かない（7 文字なので円にも入らない） */
.rec-row .stamp.hold{border-color:var(--warn);color:var(--warn);
 font-family:inherit;font-size:10px;font-weight:700;line-height:1.25;text-align:center;
 letter-spacing:0;padding:0 3px;background:none}
/* **まだ押していない枠は、歪めない。** 判子はまだ押されていないので、
   押した跡の意匠を先に出さない */
.rec-row .stamp.none{border-style:dashed;border-width:1.5px;border-color:var(--base);
 background:none;filter:none;mix-blend-mode:normal;opacity:1;transform:none}
@media (prefers-reduced-motion:reduce){.rec-row .stamp{transform:none}}
/* ---- 狭い画面では、半券を本文の下に回す ------------------------------------
   **余白は残す。** 日付と印は 1 件を切る役なので、幅が狭くても縦に並べない。      */
@media(max-width:700px){
 .rec-row{flex-wrap:wrap}
 .rec-row .marg{width:86px;padding:16px 10px 14px}
 .rec-row .dt .md{font-size:22px}
 .rec-row .page{padding:16px 16px 14px}
 .rec-row .pin{width:100%;padding:0 16px 16px 86px;justify-content:flex-start}
 .rec-row .pin>*{transform:none}
 .rec-row .pin>*::after{display:none}}
/* ---- 感想は押してから開く ---------------------------------------------------
   **書いてあるものは文として出す**（`.inr`）。読み返すために入力欄の中をなぞらせない。
   **`display` を書いたら `[hidden]` を書き直す** ── `[hidden]` の display:none は
   ブラウザの既定なので、こちらで display を書くと押す前から開いた状態で出てしまう。   */
.inw{margin:6px 0 0}
.inote[hidden]{display:none}
/* **書いてある感想は、罫の上の文としてそのまま置く。** 枠に入れて左に色の帯を付けると
   「引用された誰かの文」に見える ── ここに並ぶのは本人が書いた文である。
   **明朝で組み、行送りを罫に合わせる。**
   **クレジット（出演・演出・脚本）とフォントの太さ・大きさしか違わず、パッと見分けが
   付かなかった**（起案者の指摘・2026-08-26）。**箱・帯は付けない**という上の判断は
   保ったまま、字を斜体にし、札の色を「なぜ出てきたか」の見出しと同じ `--curtain`
   にした ── クレジットは事実の一覧、感想は本人の声、という違いを色と字形の両方
   で言う。                                                                    */
.inr{display:flex;gap:11px;align-items:baseline;flex-wrap:wrap;font-size:15px;
 font-family:var(--mincho);line-height:30px}
.inl{flex:none;font-size:11px;color:var(--curtain);font-weight:700;font-family:inherit}
.int{color:var(--ink);min-width:0;flex:1;font-style:italic}
.int::before{content:"「";color:var(--mute);font-style:normal}
.int::after{content:"」";color:var(--mute);font-style:normal}
.inr .wnb{margin-left:auto;border:0;padding:0;font-size:11.5px}
.inr .wnb:hover{text-decoration:underline}
/* ---- 「すべて表示」だけの、回ごとのメモ ---------------------------------------
   **感想（`.inr`）とは色も字形も変える。** 感想は推薦の材料であることを
   `--curtain` と明朝の斜体で言っている ── この欄はその逆（推薦に使わない）なので、
   同じ色・同じ字形にすると「これも材料になる」と誤読される。地の色（`--mute`）の
   ゴシックで、事務的な覚え書きに見える形にした。                                */
.vnw{margin:6px 0 0}
.vnote[hidden]{display:none}
.vnr{display:flex;gap:11px;align-items:baseline;flex-wrap:wrap;font-size:13px;
 color:var(--mute);line-height:26px}
.vnl{flex:none;font-size:11px;color:var(--mute);font-weight:700}
.vnt{color:var(--ink2);min-width:0;flex:1}
.vnr .wnb{margin-left:auto;border:0;padding:0;font-size:11.5px}
.vnr .wnb:hover{text-decoration:underline}
/* ---- 1 件ごとの記録を、年で畳む ---------------------------------------------
   **中に何件あるかを見出しに出す。** 件数の分からない畳み方では、開くかどうかを
   決められない。いちばん新しい年（と、先に確かめてほしい分）だけ開いておく。      */
/* **年の見出しは、帳面の上に飛び出す索引の耳にする。** 押して開く見出しと押せない
   見出しで形を変えない ── どちらも「この年の束はここから始まる」を言う札である。   */
.yr{margin:0 0 18px}
.yr>h3,.yr>summary{display:inline-flex;gap:12px;align-items:baseline;
 background:var(--curtain);color:var(--curtain-w);font-size:13.5px;font-weight:700;
 letter-spacing:.05em;padding:6px 20px 5px;border-radius:4px 4px 0 0;margin:22px 0 0;
 list-style:none}
.yr>summary{cursor:pointer}
.yr>summary::-webkit-details-marker{display:none}
.yr>summary::after{content:"開く";font-weight:400;font-size:11.5px;
 color:color-mix(in srgb,var(--curtain-w) 72%,transparent)}
.yr[open]>summary::after{content:"閉じる"}
.yr>h3 .badge,.yr>summary .badge{font-weight:400;border:0;padding:0;
 color:color-mix(in srgb,var(--curtain-w) 78%,transparent)}
/* 耳のすぐ下から帳面が始まる。**上端だけ幕の色で止める** */
.yr>.rec-row:first-of-type{border-top:2px solid var(--curtain)}
.yr>h3+.rec-row,.yr>summary+.rec-row{border-top:2px solid var(--curtain)}
/* ---- 図を 2 列に並べる -------------------------------------------------------
   **縦に積むと、図だけで画面 8 枚ぶんになる**（実測）。半分の幅に入らない図
   （中に 2 列を持つ地図・人の網・表の広い節）は `wide` で幅いっぱいのままにする。   */
.figs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 16px;
 align-items:start;grid-auto-flow:dense}
.figs>.card,.figs>section{min-width:0}
.figs>.wide{grid-column:1 / -1}
@media(max-width:820px){.figs{grid-template-columns:1fr}}
/* ---- 探す ── 観た月のマス目 -------------------------------------------------
   **6 年ぶんを 1 画面に収める。** 日めくりの暦は 2,190 マス中 67 マスしか埋まらない
   （実測）ので、探す相手より空欄のほうが目に入る。**濃さだけで意味を運ばない** ──
   マスには本数をそのまま書く。空の月は押せない。                                */
.cal{margin:26px 0 0}
.cal-grid{display:grid;grid-template-columns:auto repeat(12,minmax(0,1fr));
 gap:4px;align-items:center;margin:0 0 12px;max-width:640px}
.cal .mh{font-size:10.5px;color:var(--mute);text-align:center}
.cal-y{font-size:11.5px;color:var(--mute);padding-right:8px;
 font-variant-numeric:tabular-nums}
.cal-c{display:flex;align-items:center;justify-content:center;aspect-ratio:1;
 border-radius:6px;font-size:11.5px;text-decoration:none;color:var(--ink);
 background:var(--plane);border:1px solid var(--ring);
 font-variant-numeric:tabular-nums}
.cal-c.off{background:none;border-style:dashed;border-color:var(--grid)}
.cal-c.l1{background:color-mix(in srgb,var(--acc) 16%,var(--surf))}
.cal-c.l2{background:color-mix(in srgb,var(--acc) 38%,var(--surf))}
/* **白い字にしない。** 明るい側でこの濃さに白を置くと 3.5:1 しか出ない（実測）。
   文字は `--ink` のままにすれば、明暗どちらでも 5:1 以上になる */
.cal-c.l3{background:color-mix(in srgb,var(--acc) 62%,var(--surf))}
.cal-c:hover{border-color:var(--acc)}
/* **選んだ月は、藍ではなくえんじで示す**（起案者の指摘・2026-08-25 ──
   「観た記録／これから観られる公演の耳がどちらを選んでいるか分かりにくい」）。
   直った先は耳ではなくここだった。マスの濃さ（本数）も、当たり判定の縁取りも
   `--acc`（藍）のままで、**「選んだ月」だけが同じ藍で塗られていた** ── この画面の
   上には「押せる耳は藍、開いている耳（現在地）はえんじ」という耳の規則が既にあり
   （`.idx .ix` の注記）、すぐ下のマス目だけがそれに反していた。**現在地は、
   このアプリのどこでも一貫してえんじである。** 色を揃えると、耳がどちらを
   選んでいても、選んだ月がどのマスなのかが同じ言葉で読めるようになる。 */
.cal-c.on{outline:2px solid var(--curtain);outline-offset:1px;font-weight:700}
.cal-none{display:inline-flex;gap:9px;align-items:baseline;text-decoration:none;
 border:1px solid var(--ring);border-radius:99px;padding:5px 14px;font-size:12.5px;
 color:var(--ink2);background:var(--surf)}
.cal-none:hover{border-color:var(--acc);color:var(--acc)}
.cal-none.on{border-color:var(--curtain);color:var(--curtain);font-weight:600}
.cal-none .mn{font-size:11.5px;color:var(--mute);font-variant-numeric:tabular-nums}
/* ---- 探す ── ヒットした箇所を、行の中に書く --------------------------------
   **どこに一致したのかで意味が違う**（出演なのか、演出なのか、題材の言葉なのか）。
   題名のすぐ下に置き、役割と名前を対にして出す。                                */
.hitwhy{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;margin:6px 0 2px;
 font-size:12px;color:var(--ink2)}
.hitwhy .hl{flex:none;font-size:11px;color:var(--mute)}
.hitwhy .hw{border:1px solid var(--ring);border-radius:99px;padding:1px 10px;
 background:var(--plane)}
.hitwhy .hw .k{color:var(--mute);margin-right:6px;font-size:11px}
.hit .why{color:var(--acc);font-size:12px;margin-left:10px}
.dl{display:inline-block;margin:14px 0 0;font-size:13.5px;padding:9px 20px;border-radius:99px;
 border:1px solid var(--ring);background:var(--surf);color:var(--acc);text-decoration:none}
/* ファイルの中での項目名。**控えの大きさで置く** ── 読むのは日本語の名前のほうで、
   これは「ほかの道具で開いたときにどの並びがどれか」を照らし合わせるためだけにある */
.xk{margin-left:9px;font-size:11px;color:var(--mute);font-family:ui-monospace,monospace}
.empty{color:var(--mute);font-size:13px}
.said{font-size:12px;color:var(--good)}
.card{background:var(--surf);border:1px solid var(--ring);border-radius:14px;
 padding:22px 24px 18px;margin:0 0 16px}
/* **「設定」の札は、既定で畳んでおく**（起案者の指示・2026-08-26 ──「設定の各項目は
   デフォルトで折りたたんで表示して」）。`<details class="card">` にするだけで、
   見出しより下（本文・フォーム）は全部そのまま隠れる ── 見出しの形（`h2`）は変えず、
   ここだけ `<summary>` に載せ替える。畳んだ状態でも、いま何が選ばれているか（右の
   バッジ）は見出しの行に出ているので、開かなくても現在の設定は読める。**開閉の印は
   ブラウザの既定の三角のままにする** ── 同じ「畳んである絞り込み」の `.pbox` と
   同じ規約（`render_recommend.py`）。 */
.card>summary{cursor:pointer;list-style:revert;display:flex;align-items:center;
 gap:9px;flex-wrap:wrap;font-family:var(--mincho);font-size:18.5px;font-weight:600;
 line-height:1.45}
details.card:not([open])>summary{margin:0}
.more{margin:14px 0 0}
.more summary{cursor:pointer;font-size:13px;color:var(--acc)}
.prom{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;padding:11px 0;
 border-bottom:1px solid var(--grid);font-size:13.5px}
.prom .w{font-weight:600}
.prom .k{font-size:11px;border:1px solid var(--ring);border-radius:99px;padding:1px 8px;
 color:var(--ink2)}
.prom .src{color:var(--mute);font-size:11.5px}
.prom .q{color:var(--ink2);font-size:12.5px;flex-basis:100%;margin:2px 0 0}
.prom button{margin-left:auto}
.prom.done{opacity:.45}
/* ---- すでにある情報から選ぶ -------------------------------------------------
   **入力欄のすぐ下に出す。** 別の場所に出すと、打っている手元から目を離すことになる。 */
.sug{margin:8px 0 0}
.sug-head{font-size:12px;color:var(--mute);margin:0 0 6px}
.sug-row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:13px;
 padding:8px 12px;border:1px solid var(--ring);border-radius:9px;background:var(--plane);
 margin:0 0 5px}
/* **ポスターを候補の先頭に置く。** 同じ題名の公演が並ぶことがあり（再演・ツアー）、
   文字だけだと日付と劇場を読み比べないと選べない ── **絵は 1 目で違いが分かる。**
   **無いときも枠を残す。** 行によって高さが変わると、上から順に読めない */
.sug-row .sg-p{flex:none;width:46px;height:65px;border-radius:4px;overflow:hidden;
 background:var(--plane);display:flex;align-items:center;justify-content:center}
.sug-row .sg-p img{width:100%;height:100%;object-fit:cover;display:block}
.sug-row .sg-p.none{border:1px dashed var(--ring)}
.sug-row .sg-b{flex:1;min-width:0;display:flex;gap:8px;align-items:baseline;
 flex-wrap:wrap}
/* ---- 直す欄のポスター。**いま何が出ているかを、直す場所の隣に置く** ---- */
.ed-pos{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:8px 0 0}
.ed-pos .ed-pv{flex:none;width:52px;height:73px;border-radius:4px;overflow:hidden;
 display:flex;align-items:center;justify-content:center}
.ed-pos .ed-pv img{width:100%;height:100%;object-fit:cover;display:block}
.ed-pos .ed-pn{width:100%;height:100%;border:1px dashed var(--ring);border-radius:4px}
.ed-pos .ed-m{flex:1;min-width:220px}
.sug-row .sg-k{font-size:11px;border:1px solid var(--ring);border-radius:99px;
 padding:1px 8px;color:var(--mute);flex:none}
.sug-row.record .sg-k{border-color:var(--warn);color:var(--warn)}
.sug-row .sg-t{font-weight:600}
.sug-row .sg-m{color:var(--mute);font-size:12px}
.sug-row .sg-dup{margin-left:auto;color:var(--warn);font-size:12px}
/* **出演は行を分けて置く。** 劇場と日程の行に続けると、どこまでが公演の情報なのか
   分からなくなる（同じ題名の公演を見分けるために出している） */
.sug-row .sg-c{flex-basis:100%;color:var(--mute);font-size:12px;line-height:1.6}
.sug-row button{margin-left:auto;font:inherit;font-size:12.5px;padding:4px 14px;
 border-radius:99px;border:1px solid var(--acc);background:var(--surf);color:var(--acc);
 cursor:pointer}
/* ---- 同じ公演かを確かめる ---------------------------------------------------
   **押した直後に、その場で出す。** 別の画面へ送ると、直した文脈が切れて答えられない。 */
.mergeq{margin:12px 0 0;padding:14px 16px;border:1px solid var(--acc);border-radius:11px;
 background:var(--surf)}
.mergeq p{margin:0 0 10px;font-size:13.5px}
.mq-note{color:var(--ink2);font-size:12.5px;font-weight:400}
.mq-row{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;font-size:13px;
 padding:8px 0;border-top:1px solid var(--grid)}
.mq-row .mq-t{font-weight:600}
.mq-row .mq-m{color:var(--mute);font-size:12px}
.mq-row button,.mq-foot button{margin-left:auto;font:inherit;font-size:12.5px;
 padding:5px 14px;border-radius:99px;border:1px solid var(--ring);background:var(--plane);
 color:var(--ink2);cursor:pointer}
.mq-row button{border-color:var(--acc);color:var(--acc);font-weight:600}
.mq-foot{display:flex;gap:12px;align-items:center;margin:10px 0 0;flex-wrap:wrap}
/* ---- 記録と公演の結び付け --------------------------------------------------- */
.ed-link{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:10px 0 0;
 padding:10px 12px;border:1px dashed var(--ring);border-radius:9px;background:var(--plane)}
.ed-lk{font-size:12px;color:var(--mute);flex:none}
.ed-lv{font-size:13px;font-weight:600}
/* **自動で結び付けた分は見た目を変える。** 確かめていないことが一目で分かる */
.ed-lv.auto{color:var(--warn)}
.ed-link:has(.ed-lv.auto){border-color:var(--warn)}
.ed-link .lk-sug{flex-basis:100%;margin:6px 0 0}
/* **外へ探しに行く口は、手で足す欄の「検索」と同じ見た目にする。** 同じ働きの口が
   2 か所にあるので、形が違うと別の機能に見える */
.ed-link button{font:inherit;font-size:12.5px;padding:6px 14px;border-radius:99px;
 border:1px solid var(--ring);background:var(--surf);color:var(--ink2);cursor:pointer}
.ed-link button[data-lk-web]{border-color:var(--acc);color:var(--acc);font-weight:600}
/* ---- ポスター・クレジットを手入力する欄 -------------------------------------
   **上の「推薦に使う公演」と見た目を分ける。** どちらも同じ「この記録を正しくする」
   作業だが、**片方は選ぶ操作で、こちらは書く操作である** ── 同じ枠で続けると、
   探して見つからなかった人が書く場所に辿り着けない。                            */
.hand{margin:10px 0 0;padding:10px 12px;border:1px dashed var(--ring);border-radius:9px;
 background:var(--plane)}
.hand>summary{cursor:pointer;font-size:13px;font-weight:600;color:var(--ink2)}
.hand[open]>summary{margin:0 0 8px}
.hand-p{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 12px}
.hand-p .ed-pv img{width:64px;height:90px;object-fit:cover;border-radius:5px;display:block}
/* **ファイルを選ぶ口は、ボタンの形にする。** 素の input はブラウザごとに姿が変わり、
   同じ画面の他の押し口と揃わない */
.hand-file{font:inherit;font-size:12.5px;padding:6px 14px;border-radius:99px;
 border:1px solid var(--acc);color:var(--acc);font-weight:600;cursor:pointer}
.hand-file input{display:none}
.hand-f{display:block;font-size:12.5px;color:var(--ink2);margin:0 0 10px}
.hand-f textarea{display:block;width:100%;margin:4px 0 0;font:inherit;font-size:13px;
 padding:6px 10px;border:1px solid var(--ring);border-radius:8px;
 background:var(--surf);color:var(--ink);resize:vertical}
.hand-h{display:block;font-size:11.5px;color:var(--mute);line-height:1.55;
 font-weight:400;flex-basis:100%}
.hand button{font:inherit;font-size:12.5px;padding:6px 14px;border-radius:99px;
 border:1px solid var(--ring);background:var(--surf);color:var(--ink2);cursor:pointer}
.hand .pfoot button{border-color:var(--acc);color:var(--acc);font-weight:600}
/* ---- 作品を親、会場ごとの上演を子として並べる -------------------------------
   **取得元は作品の id を持っていない**（会場ごとの上演に 1 ページ）ので、親はこちらで
   組んでいる。**子は畳まない** ── 会場ごとに出演者も座組も違いうるので、どの上演かは
   本人しか知らない。親を 1 行にして、その下で選んでもらう。                       */
details.sug-work{border:1px solid var(--ring);border-radius:10px;margin:5px 0;
 background:var(--plane)}
details.sug-work>summary{cursor:pointer;font-size:13px;font-weight:600;padding:9px 12px;
 color:var(--ink2)}
details.sug-work[open]>summary{color:var(--ink);border-bottom:1px solid var(--grid)}
details.sug-work .sug-row{margin:0;border:0;border-top:1px solid var(--grid);
 border-radius:0;background:transparent}
details.sug-work>.sug-head{margin:8px 12px 2px}
/* **すでに記録がある上演は目で分かるようにする。** 選ぶときのいちばん強い手がかりである */
.sug-row.mine{background:var(--surf);border-left:3px solid var(--acc)}
/* ---- 取り消した記録 --------------------------------------------------------- */
.drop-row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:13.5px;
 padding:9px 0;border-bottom:1px solid var(--grid)}
.drop-row .dt{font-weight:600}
.drop-row .dm{color:var(--mute);font-size:12px}
/* **押し口は 1 組にして、行の右端へまとめて寄せる。** 個々のボタンに margin-left:auto を
   持たせると、2 個目以降が余白を食い合って隙間が揃わない */
.drop-row .drop-btns{display:flex;gap:8px;align-items:center;margin-left:auto}
/* **取り消しの押し口は、色で他と分ける。** 押した結果が他のボタンと違う */
button.danger{border-color:var(--ring);color:var(--mute)}
button.danger:hover{border-color:#e34948;color:#e34948}
/* ---- 観ていない公演 ---------------------------------------------------------
   **畳んで置く。** 押す頻度の低い口なので、15 行すべてに開いた選択肢を並べると
   評価を付ける画面が「外す画面」に見える。閉じているのが既定である（`<details>` なので
   JavaScript を要さない）。 */
details.ns{flex-basis:100%;margin:2px 0 0;font-size:12.5px}
details.ns>summary{cursor:pointer;list-style:none;color:var(--mute);width:fit-content}
details.ns>summary::-webkit-details-marker{display:none}
details.ns>summary::before{content:"▸ "}
details.ns[open]>summary::before{content:"▾ "}
details.ns>summary:hover{color:var(--ink2)}
.ns-body{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0 2px;
 padding:9px 12px;border:1px dashed var(--ring);border-radius:9px;background:var(--plane)}
.ns-body p{margin:0 0 2px;flex-basis:100%;color:var(--ink2);line-height:1.7}
.ns-body button{font-size:12.5px}
.ns-body.done button{opacity:.35;pointer-events:none}
.ns-body.dead button{opacity:.4;pointer-events:none}
/* **行かなかった記録は、一覧の中で見た目を変える。** 観た記録と並べたまま印だけを
   付けないと、観た本数を目で数えたときに合わない */
.rec-row.skipped{opacity:.72}
.rb.notseen .nsm{font-size:12.5px;color:var(--mute);font-weight:600}
.rb.notseen button{font-size:12.5px;min-width:0}
.wait.skipped{opacity:.72}
/* ---- 推薦の効かせ方 ---------------------------------------------------------
   **枠は都道府県の絞り込みと同じ `.pbox` を使う。** 同じ「畳んである絞り込み」なので、
   別の見た目を作ると画面ごとに枠の意味を覚え直すことになる。
   **押し口も `.pfoot` / `.pall` と同じもの**（起案者の指示 ──「ボタンのデザインを
   他と統一して」）。 */
/* ---- 更新でできなかったこと。**一覧より前に置く** --------------------------
   **色で驚かせない。** 壊れたのではなく「今回はここが欠けている」という知らせなので、
   赤ではなく、注意の色の細い縦線だけを立てる（`.pnow` と同じ組み方）。 */
.runmiss{background:var(--surf);border:1px solid var(--ring);
 border-left:3px solid var(--warn);border-radius:0 12px 12px 0;
 padding:14px 20px;margin:0 0 20px;font-size:13.5px;line-height:1.9}
.runmiss p{margin:0}
.runmiss ul{margin:8px 0 0;padding-left:1.3em;color:var(--ink2)}
.runmiss li{margin:0 0 4px}
.runmiss .rm-f{margin:10px 0 0;color:var(--mute);font-size:12.5px}
.wfil{margin:0 0 22px}
/* ---- 絞り込みを 2 段組にする（起案者の指示・2026-08-24）--------------------
   **2 つの絞り込みは、別のことを決めている。** 場所は「どこなら観に行けるか」、
   効かせ方は「どの情報を順位に使うか」で、**片方を決めてからもう片方を決める順序は
   無い。** 縦に積むと上から順に読む形になり、下の 1 つは畳まれたまま気づかれにくい。
   **横に並べると、決めることが 2 つあることが 1 目で分かる。**
   **狭い画面では 1 列に戻す** ── 札が 47 個並ぶので、半分の幅では読めない。 */
.fil2{display:grid;grid-template-columns:1fr 1fr;gap:0 18px;align-items:start;
 margin:0 0 22px}
.fil2>.pfil,.fil2>.wfil{margin:0}
/* 畳んであるときは高さが揃うが、開くと片方だけ伸びる。**開いた側を下まで伸ばさない**
   ── `align-items:start` で上端を揃える（既定の stretch だと、閉じている側の枠が
   開いた側と同じ高さまで引き伸ばされて、空の箱に見える） */
@media(max-width:880px){.fil2{grid-template-columns:1fr;gap:0}
 .fil2>.pfil{margin:0 0 14px}
 .fil2>.pbox:not(:last-child){margin:0 0 14px}}
/* お気に入りの道具も同じ枠・同じ横並びを使う（`.pbox` を直に置く） */
.fil2>.pbox{margin:0}
/* ---- 帳面に挟んだ索引の耳で切り替える --------------------------------------
   起案者の指示（2026-08-24）──「札、デザインはさっきのままでメモ帳に付属している
   インデックスで切り替え、みたいなデザインにして」。

   **耳は紙に挟まっているものなので、押せる耳と開いている耳を「前後」で表す。**
   選んでいる耳だけが紙と同じ色で、下の 2px を塗りつぶして帳面とつながる ──
   ほかの耳は 1 段沈めて（`top`）、地の色で後ろに置く。

   **色の役割はそのまま。** 押せる耳の文字は藍（`--acc`）、開いている耳は現在地なので
   えんじ（`--curtain`）── 左の帯で現在地を紙の色で抜いているのと同じ規則である。

   **狭い画面では折り返す**（`flex-wrap`）。横に流して隠すと、5 つある耳のうち
   見えない分が「無い」ことになる ── 折り返せば全部見えたまま、下の段の耳が
   帳面とつながる形は保たれる。 */
.idx{display:flex;flex-wrap:wrap;align-items:flex-end;gap:3px;margin:0;padding:0 3px}
/* **耳が2段以上重なる画面（評価一覧の「評価」→「年」）だけに出す見出し。**
   `index_tabs`の`show_label`が真のときだけ描かれる（2026-08-29）。小さく・
   地味に置く ── 主役は耳そのものであって、見出しはどの軸かを示す添え書きである。 */
.idx-lab{display:block;font-size:11px;color:var(--mute);margin:.6em 0 .15em;padding:0 3px}
/* **押せる耳は紙の色**（起案者の指示・2026-08-24）。地（客席の壁の灰緑）の上に紙が
   挟まっている形になるので、耳が何枚あるかが地との差で読める。**文字は藍のまま** ──
   押せるものは藍という規則は動かさない。

   **縁取りはえんじで取る**（起案者の指示・2026-08-25）。灰色の線だと、白いままの耳が
   地に沈んで、そこに耳が挟まっていること自体が読めなかった。**耳の一列は、開いている
   ものも押せるものも同じえんじの線で描かれた 1 つの索引である** ── 塗りの有無だけが
   現在地を言う。色の役割は崩れない（線は形を描くもので、文字の藍が「押せる」を言う）。 */
.idx .ix{position:relative;top:2px;display:inline-flex;gap:8px;align-items:baseline;
 text-decoration:none;font-size:13px;line-height:1.5;padding:6px 14px 6px;
 background:var(--surf);color:var(--acc);
 border:1px solid var(--curtain);border-bottom:0;border-radius:7px 7px 0 0}
/* **重ねても縁取りはえんじのまま。** 押せることは文字の藍が言っているので、線の色を
   藍に振り替えると、指を乗せた耳だけ索引から外れて見える ── 紙にえんじを薄く敷く */
.idx .ix:hover{background:color-mix(in srgb,var(--curtain) 9%,var(--surf))}
.idx .ix .mn{font-size:11.5px;color:var(--mute);font-variant-numeric:tabular-nums}
/* **開いている耳はえんじを塗って白抜きにする**（起案者の指示・2026-08-24）。
   **帳面の上端の線と同じ色なので、耳と紙の境が消えて 1 枚につながる。**
   日記帳の年の耳も同じ塗りなので、これで 2 つの耳が同じ形になった。 */
.idx .ix.on{top:0;margin-bottom:-2px;padding:8px 16px;font-weight:700;
 background:var(--curtain);color:var(--curtain-w);
 border:2px solid var(--curtain);border-bottom:0}
.idx .ix.on .mn{color:color-mix(in srgb,var(--curtain-w) 76%,transparent)}
/* **色に頼らない印。** 耳が 2 枚しかない画面では、塗りつぶしと藍の文字のどちらが
   「選ばれている」側なのか、色の意味を知らないと読めない（起案者の指摘・2026-08-25）。
   check の印は開いている耳にしか出ないので、色を無視しても選択が読める */
.idx .ix .ixck{margin-right:-2px}
/* 耳が挟まっている帳面。**上端の線が耳と同じ色** ── 同じ 1 枚の紙である */
.idxsheet{background:var(--surf);border-top:2px solid var(--curtain);margin:0 0 4px}
.idxsheet>.mnow{margin:0;padding:13px 18px;border-bottom:1px solid var(--grid);
 border-left:1px solid var(--grid);border-right:1px solid var(--grid)}
/* 帳面の中の行は、上端の線を二重に引かない */
.idxsheet>.rec-row:first-of-type{border-top:0;border-radius:0}
/* **1 件が札で並ぶ画面の帳面。** 興味あり・お気に入り・探すは 1 件が券の札
   （`.ticket`）で、**札そのものが紙の色を持っている** ── 帳面まで紙で塗ると札が
   沈んで枠線しか残らない。**上端の線と、状態を書いた 1 枚だけを紙にし、札は地の上に
   置く。** 耳が受け止められる面（上端の 2px）は残るので、耳は浮かない。 */
.idxsheet.loose{background:none}
.idxsheet.loose>.mnow{background:var(--surf);border:1px solid var(--grid);border-top:0;
 border-radius:0 0 11px 11px;margin:0 0 18px}
/* **登録済みの札は、開いた中で高さを持たせすぎない。** 41 件あると 10 行になるので、
   畳んだ枠の中でもさらにスクロールできる形にする ── 枠の外の一覧まで押し下げない */
.pbox .tags{max-height:210px;overflow-y:auto;margin:12px 0 0}
/* 目盛りの意味は 1 か所にだけ書く。7 行それぞれに 5 つの言葉を並べない */
.wscale{display:flex;justify-content:space-between;align-items:baseline;
 font-size:11.5px;color:var(--mute);margin:12px 0 2px;padding:0 2px}
.wscale .wmid{color:var(--ink2)}
.wrow{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:9px 0;
 border-top:1px solid var(--grid);font-size:13px}
.wrow .wl{font-weight:600;flex:1 1 220px}
.wrow .wn{color:var(--mute);font-size:12px;flex:none;font-variant-numeric:tabular-nums}
/* **つまみ。** 段には弱い → 強いの順序があるので、位置そのものが強さを表す形にする
   （同じ大きさのボタンを 5 つ並べると「5 つの別の選択肢」に見える）。
   **見た目はブラウザのものに任せ、色だけを合わせる** ── つまみを自作すると、
   明暗のモードと OS ごとに崩れる箇所を自分で抱えることになる */
.wrow .wsl{flex:0 0 168px;accent-color:var(--acc);cursor:pointer;margin:0}
.wrow .wv{flex:0 0 118px;font-size:12.5px;color:var(--acc);font-weight:600}
/* **いちばん左に置いた行は薄くする。** 順位から消えていることを行の見た目で言う */
.wrow.off .wl{color:var(--mute);text-decoration:line-through}
.wrow.off .wv{color:var(--mute)}
/* **確定していないことを、押し口の側に出す。** 動かしただけで効いたと読まれないため */
.wbox.dirty .pfoot button[data-wsave]{border-color:var(--warn);color:var(--warn)}
.wsaid{font-size:12px;color:var(--mute)}
.wbox.dirty .wsaid{color:var(--warn)}
button.pall-btn{font:inherit;font-size:12.5px;color:var(--mute);background:none;
 border:0;padding:0;cursor:pointer;text-decoration:underline}
button.pall-btn:hover{color:var(--ink2)}
.wbox.dead .wsl{opacity:.4;pointer-events:none}
.wbox.dead .pfoot button{opacity:.4;pointer-events:none}
/* ---- 三択に答えた枠を埋めた 1 枚 -----------------------------------------
   **足したことが分かるように、1 度だけ動かす。** 一覧のいちばん下に差し込むので、
   静かに現れると増えたことに気づけない ── 押し口の側にも文で出しているが、
   **文と場所が離れているときは、動きのほうが先に目に入る。**
   動きを減らす設定は尊重する（増えたこと自体は文で分かる）。               */
.ticket.filled{animation:tgfill .45s ease-out}
@keyframes tgfill{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:none}}
@media(prefers-reduced-motion:reduce){.ticket.filled{animation:none}}
"""


# **畳んだかどうかを、画面をまたいで覚える。** ここは 1 枚ごとに読み込み直す作りなので、
# 覚えないと**行き先を押すたびに既定の形に戻る** ── 1 度畳めば畳んだままにならないと、
# 折りたたみとして使えない。
#
# **既定は「いま居る束だけ開く」である**（`layout._group`）。**押して決めたほうが勝つ** ──
# 畳んだ（`1`）なら居る束でも畳み、開いた（`0`）なら居ない束でも開く。既定を上書きする
# のが覚えた値の役目なので、**両方向に効かないと「開いておく」が保てない。**
#
# **帯のすぐ後ろに置いて、本文より先に走らせる。** 末尾の `SCRIPT` に混ぜると、
# 既定の形が 1 度描かれてから畳まる（ちらつく）。
#
# **端末の中にしか置かない。** 覚えるのは「畳んだか」の 1 文字だけで、記録には触らない。
# 読み書きに失敗しても既定のまま進む ── 帯が出ないほうが困る。
NAV_FOLD_JS = """
try{document.querySelectorAll(".side .grp").forEach(g=>{
  const v=localStorage.getItem("taguri.fold."+g.dataset.grp);
  if(v==="1")g.open=false; else if(v==="0")g.open=true;
  g.addEventListener("toggle",()=>{try{
    localStorage.setItem("taguri.fold."+g.dataset.grp,g.open?"0":"1");}catch(e){}});
});}catch(e){}
"""


def _crumbs(top: str, active_sub: str, title: str) -> list[tuple[str, str | None]]:
    """現在地までの道のり。**「たぐり」から必ず始まる。**

    起案者の指示（2026-08-25）──「どの画面にも戻るボタンをつけて、ぱんくずりすとを
    明記して」。

    返すのは (見出し, 道) の並びで、**道が `None` の行はいまの画面か、行き先を持たない
    親**なので、リンクにしない（親を押しても飛べる先が無い ── `_group` と同じ理由）。

    **最後の見出しは、いつも呼び出し側が渡す `title` にする。** NAV の子の名前を
    もう 1 度探して合わせるのではなく、画面がすでに持っている自分の名前をそのまま使う
    ── 探しても見つからない画面（NAV にまだ登録されていない道）でも、道のりの最後の
    1 段だけは必ず出る。
    """
    cur = active_sub or top
    for _p, label, _icon, kids in NAV:
        if any(cp == cur for cp, _cl, _ci in kids):
            return [("たぐり", "/"), (label, None), (title, None)]
    return [("たぐり", "/"), (title, None)]


def _crumb_bar(top: str, active_sub: str, title: str) -> str:
    """戻るボタンと、パンくずリスト。**画面のどこに居ても、この 1 行だけは必ず出る。**

    **戻るボタンは、ブラウザの「1 つ前」に戻る。** パンくずが担うのは「いま自分が
    どの束の中に居るか」（階層を上へ）、戻るボタンが担うのは「直前に何をしていたか」
    （時間を 1 つ前へ）── 月の絞り込みや都道府県の絞り込みなど、URL のパラメータで
    状態を持つ画面は、階層の親に飛ぶだけでは絞り込みが消える。**history を使えば、
    直前の絞り込みごと戻る。**

    **履歴が無いとき**（起動して最初に開いた画面）**は、「たぐり」の入口に戻す** ──
    戻る先が無いのに押せてしまう口を作らない。
    """
    crumbs = _crumbs(top, active_sub, title)
    parts = []
    for i, (label, href) in enumerate(crumbs):
        last = i == len(crumbs) - 1
        if href:
            parts.append(f'<a href="{href}?t=__TAGURI_TOKEN__">{E(label)}</a>')
        else:
            parts.append(f'<span{" aria-current=\"page\"" if last else ""}>{E(label)}</span>')
        if not last:
            parts.append('<span class="crumbsep" aria-hidden="true">›</span>')
    onclick = ("history.length>1?history.back():"
               "location.assign('/?t=__TAGURI_TOKEN__')")
    return (f'<div class="crumbbar">'
            f'<button type="button" class="backbtn" onclick="{E(onclick)}">'
            f'← 戻る</button>'
            f'<nav class="crumb" aria-label="現在地の道のり">{"".join(parts)}</nav></div>')


def layout(title: str, top: str, body: str, style: str, active_sub: str = "") -> str:
    """全画面に共通の外枠。**ナビゲーションはここ 1 か所にしか無い。**

    リンクにトークンを載せる ── 起動ごとの乱数を持たない要求は受け付けないので、
    画面の間を移動するときも同じ鍵を持ち回る（`__TAGURI_TOKEN__` は配る直前に置き換わる）。

    ## 段の帯（フローチャート）は撤去した（起案者の指摘・2026-08-25）

    以前は「おすすめ」「評価」「記録を見返す」の 3 か所に、段の並びを左から右へ流す帯
    （`flow_nav`）を置いていた。**「おすすめと評価のリンクを外して」→「これ自体消して
    ほしい」→「記録を見返すのも消してよい」の順に、3 段階で撤去した。** 最初はリンクだけ
    外し（`<a>` を `<span>` に）、次に帯そのものを消し、最後に残っていた「記録を見返す」
    の分も消した ── **戻るボタンと道のり（パンくずリスト）を全画面に置いた時点で、
    帯が担っていた役目（他の段の状態を見る・他の段へ移る）はどちらも別の場所に移って
    いた。** `flow_nav()` 自身は呼び出し元が無くなったので削った。
    """
    # **いま開いている画面に印を付ける。** 段の途中の画面（興味あり・お気に入り）は
    # `top` が「おすすめ」なので、子の印は `active_sub` で決める ── 親と子の両方が
    # 濃く光ると、どちらが現在地なのか分からない
    def _item(path: str, label: str, icon: str, kid: bool = False) -> str:
        # **段を持たない画面（はじめる）は `active_sub` を渡してこない。** そのときは
        # `top` を現在地として読む ── 渡ってこないことを「どの子でもない」と読むと、
        # 束の中に居るのに現在地がどこにも出ない
        on = ((active_sub == path) if active_sub else (top == path)) if kid \
            else (path == top and active_sub in ("", path))
        sec = (not kid) and path == top and not on
        cls = " ".join(c for c in ("kid" if kid else "", "on" if on else "",
                                   "sec" if sec else "") if c)
        return (f'<a href="{path}?t=__TAGURI_TOKEN__" class="{cls}">'
                f'{IC.ico(icon, 16 if kid else 18)}{E(label)}</a>')

    def _group(label: str, icon: str, kids: tuple) -> str:
        """**行き先を持たない親。** 押すと子の並びを畳む／開くだけである。

        起案者の指示（2026-08-25）── 押せる行き先ではなくなったので `<a>` をやめた。
        **`<details>` で組むのは、JavaScript が動かないときでも畳めるからである**
        （ファイルを直接開いた画面では押し口が軒並み死ぬ ── `.dead-note` 参照）。

        **畳んでも現在地は消さない。** 子が現在地のときは親に `sec` を付けておき、
        畳まれている間だけ親を紙の色で抜く（CSS の `.grp:not([open])`）── そうしないと、
        畳んだとたんに「いまどこを読んでいるのか」が画面から消える。

        **既定で開くのは、いま居る束だけである**（起案者の指摘・2026-08-25 ──
        「サイドバーが長すぎてスクロールバーがでちゃってる」）。全部を開いた形で出すと
        帯は 15 行・約 700px になり、**縦 700px に満たない画面では必ずスクロールバーが
        出る。** 居ない束を畳んでおけば 12 行に収まる ── **隠すのではなく、いま関係の
        あるものだけを開く。** 開いたままにすると本人が押して決めたときは、覚えた側が
        勝つ（`NAV_FOLD_JS`）。
        """
        here = any((active_sub == c[0]) if active_sub else (top == c[0]) for c in kids)
        return (f'<details class="grp" data-grp="{E(label)}"{" open" if here else ""}>'
                f'<summary class="{"sec" if here else ""}">'
                f'{IC.ico(icon, 18)}<span class="gl">{E(label)}</span>'
                f'{IC.ico("chevron", 14, "cv")}</summary>'
                f'{"".join(_item(*c, kid=True) for c in kids)}</details>')

    nav = "".join(_group(t, k, kids) if p is None else
                  _item(p, t, k) + "".join(_item(*c, kid=True) for c in kids)
                  for p, t, k, kids in NAV)
    # **「たぐり」の下の検索窓は、宛先が「探す」画面と同じ。** ここで新しく探す
    # 手段を作るのではなく、`/search` への近道を帯のいちばん上に置くだけである。
    search = (f'<form class="search" method="get" action="/search" role="search">'
              f'<input type="hidden" name="t" value="__TAGURI_TOKEN__">'
              f'{IC.ico("search", 15)}'
              f'<input type="search" name="q" placeholder="探す" aria-label="探す"></form>')
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>たぐり ── {E(title)}</title>{LG.favicon_tag()}
<style>{style}{APP_CSS}{CH.CSS}{PE.CSS}{VE.CSS}{IC.CSS}{LG.CSS}{PM.CSS}</style></head><body>
{RR.FILTERS}
<div class="shell">
<nav class="side" aria-label="画面の行き先">{LG.lockup(cls="brand")}{search}{nav}</nav>
<script>{NAV_FOLD_JS}</script>
<main class="main">
<div class="curtain" aria-hidden="true"></div>
{_crumb_bar(top, active_sub, title)}
<div class="wrap spot">
<div class="dead-note" hidden><b>このページのボタンは効かない。</b>
 ファイルを直接開いたため、押した内容を保存する先がありません。
 <code>python3 tools/taguri/run.py</code> から開いてください。</div>
{body}
<div class="foot"><button data-close="1">終わる（システムを閉じる）</button></div>
</div></main></div><script>{SCRIPT}{PE.JS}{PM.JS}</script></body></html>"""


# ------------------------------------------------- 開くたびに一覧を作り直す
#
# 起案者の指示（2026-08-24）──「一個操作したら適宜リロードしてほしい。たとえば公演じゃない
# ものを消したら、すぐ一覧からも消えてほしい」。
#
# ## リロードしても消えていなかった理由
#
# **押した内容は DB に入っていたが、画面が読んでいたのは起動のときに書き出した控えだった。**
# 評価待ちは `data/review/waiting.json`、推薦と束は `data/review/recommend2.json` で、
# **どちらも `run.py` を走らせたときにしか書き換わらない。** 取り消しはリロードまでしていた
# のに一覧から消えなかったのは、消えた先を読んでいなかったからである。
#
# **控えを消して、開くたびに DB から作る。** ただし**点の付け方はやり直さない** ── 順位は
# 週のあいだ動かない（同じ DB から同じ順位が出る）という性質を壊さずに、**どの束に入るかだけ
# を当て直す。** 反応は点を変えず、束の割り振りだけを決めているので、これで足りる
# （`recommend2.py` の割り振りと同じ規則を使う）。
#
# **`recommend` の 15 件は当て直さない。** これは週次の指標の分母（その週に全国で出した
# 15 件）で、画面に出す一覧は `ranked` から作る。**分母を動かすと、提示 → 興味あり → 購入の
# 連鎖を数えられなくなる。**
def waiting_rows(today: str = "") -> list[dict]:
    """評価待ち。**開くたびに数え直す。**

    控え（`waiting.json`）を読むのをやめた ── 取り消しても「行かなかった」を付けても、
    次に `run.py` を走らせるまで一覧から消えなかった。**控えは `run.py` が
    書き続ける**（画面を使わずに 1 枚だけ書き出す確認用の入口が読む）が、
    **画面はこの関数だけを見る。**
    """
    import datetime
    today = today or datetime.date.today().isoformat()
    _promote_owned_tickets(today)
    return [w for w in _works()
            if not w["verdict"] and w["bucket"] != "upcoming" and not w.get("unseen")
            and w["last_date"] and w["last_date"] <= today]


def _react_groups(react: dict) -> dict[str, list[str]]:
    """作品単位（`recommend2.work_key`）→ その作品の反応が乗っている stage_id の一覧。

    **行く日（`ticket`）は、「持っている」の反応が付く代表会場とは違う stage_id に
    付いていることがある。** ツアーの別会場は stage_id が違うので（フタマツヅキ・
    ミス・サイゴンが実際にそうである）、この作品のことだと分かっている stage_id を
    まとめて引けるようにしておく。**`react` 側に反応が付いた分だけを拾う** ──
    まだ反応の付いていない他会場は対象外（`_collapse_tracking_tours` と同じ理由）。
    """
    import recommend2 as RC2
    out: dict[str, list[str]] = {}
    for sid, v in react.items():
        if v.get("title"):
            out.setdefault(RC2.work_key(v["title"]), []).append(sid)
    return out


def _owned_done_date(stage_ids, c: dict, tickets: dict) -> str:
    """「持っている」券の、上演が終わったと言える日付。分からなければ空文字。

    **`stage_ids` は 1 つとは限らない。** 同じ作品がツアーで複数の会場に分かれ、
    stage_id が違うことがある（`sync_mail_tickets` の docstring ── フタマツヅキ・
    ミス・サイゴンが実際にそうである）。「持っている」の反応は代表 1 会場の stage_id
    に付くが、**行く日（`ticket`）は本人が選んだ本当の会場に付く**ので、代表会場と
    一致するとは限らない ── 呼ぶ側（`_rebucket`）は同じ作品の会場をまとめて渡す。

    **本人が確定した日を優先する。** メールから拾っただけで確定していない日は
    使わない ── 確定前の日は別会場の回を誤って拾っている可能性がある。**確定した
    券が 1 枚も無ければ、上演期間の千秋楽を使う** ── 千秋楽を過ぎれば、どの回を
    観たにせよ上演そのものは終わっている。
    """
    if isinstance(stage_ids, str):
        stage_ids = [stage_ids]
    confirmed = [t["date"] for sid in stage_ids for t in (tickets.get(sid) or [])
                if t.get("confirmed")]
    if confirmed:
        return max(confirmed)
    import recommend2 as RC2
    e = RC2.period_end(c.get("period") or "")
    return e.isoformat() if e else ""


def _promote_owned_tickets(today: str) -> None:
    """「すでに持っている」と答えた公演のうち、上演が終わった分を works の行にする。

    起案者の指摘（2026-08-26）──「フタマツヅキは購入済みにも入っていて、公演日が
    登録されていて、公演日が過ぎているのに評価一覧に追加されていない。なぜ？」

    調べると、**「持っている」（`reaction.owned`）と「行く日」（`ticket`）は公演の id
    （stage_id）だけで持っているが、評価待ち（`waiting_rows`）が見るのは `works` の行
    （`work_key` だけで持っている）で、この 2 つの間に橋が無かった。** 上演日を過ぎても
    `works` に行が無いままなので、`waiting_rows` には一生出てこない。

    **`add_work`（手で足す）と同じ鍵の作り方で行を作る。** 後から購入確認メールが
    届いても同じ作品として重なるようにするためである。**すでに行があれば何もしない**
    （二重に作らない・手で直した内容を消さない）。
    """
    import feedback as FB
    import rate_performances as R
    con = FB.connect()
    try:
        react, tickets = FB.reactions(con), FB.tickets(con)
    finally:
        con.close()
    owned = [sid for sid, r in react.items() if r.get("owned") == 1]
    if not owned:
        return
    idx = _upcoming_index()["rows"]
    con = R.connect()
    try:
        have_sid = {str(w.get("stage_id") or "") for w in R.read_works(con).values()
                    if w.get("stage_id")}
        wrote = False
        for sid in owned:
            if sid in have_sid:
                continue
            c = idx.get(sid) or {}
            title = react.get(sid, {}).get("title") or c.get("title") or ""
            done = _owned_done_date(sid, c, tickets)
            if not title or not done or done > today:
                continue
            key = f"{R.title_key(title)}#{done}"
            con.execute(
                "INSERT INTO works (work_key, title, first_date, last_date, times, verdict,"
                " chosen, note_impression, note_motive, stage_id, updated_at)"
                " VALUES (?,?,?,?,1,NULL,NULL,'','',?,datetime('now','localtime'))"
                " ON CONFLICT(work_key) DO NOTHING",
                (key, title, done, done, sid))
            wrote = True
        if wrote:
            con.commit()
    finally:
        con.close()


def _auto_own_from_mail(today: str) -> None:
    """まだ「すでに持っている」を押していない公演でも、購入確認メールが
    あれば自動で「持っている」にする。

    起案者の指示（2026-08-26）──「メール取り込みでまだ追加されていない購入済み
    公演があるなら、自動的に『購入済み公演』に追加されて」。

    **`sync_mail_tickets` は、すでに「持っている」を押した公演にしか行く日を
    足さない**（押す前の候補は探す対象に入っていない）。**押すこと自体を、
    確認メールが特定できるならこちらで肩代わりする** ── `sync_mail_tickets` と
    同じ絞り方（上演期間にその日が入っている・複数当たれば会場名でも絞る）を使う。

    **反応には `presented` の行が要る。**（`FB.reactions` は題名をそこから引く）
    週次の推薦で出したことが無い公演（探して直接買った分）は `presented` に
    行が無いので、無ければここで作る。
    """
    import feedback as FB
    import recommend2 as RC2
    buys = _future_purchases(today)
    if not buys:
        return
    idx = _upcoming_index()["rows"]
    by_workkey: dict[str, list[tuple[str, dict]]] = {}
    for sid, c in idx.items():
        by_workkey.setdefault(RC2.work_key(c.get("title") or ""), []).append((sid, c))
    con = FB.connect()
    try:
        react = FB.reactions(con)
        label = f"mail-{today}"
        wrote = False
        for b in buys:
            hit = [(sid, c) for sid, c in by_workkey.get(RC2.work_key(b["title"]), [])
                   if _in_period(c.get("period") or "", b["date"])
                   and react.get(sid, {}).get("owned") != 1]
            if len(hit) > 1 and b["venue"]:
                narrowed = [(sid, c) for sid, c in hit if b["venue"] in (c.get("theater") or "")]
                hit = narrowed or hit
            if len(hit) != 1:
                continue
            sid, c = hit[0]
            title = c.get("title") or b["title"]
            con.execute(
                "INSERT INTO presented (label, stage_id, rank, title, score, bundle,"
                " reasons, created_at) VALUES (?,?,0,?,0,'mail','{}',"
                "datetime('now','localtime')) ON CONFLICT(label, stage_id) DO NOTHING",
                (label, sid, title))
            FB.react(con, label, sid, owned=1, source="mail")
            FB.add_ticket(con, sid, b["date"], b["time"], source="mail", uid=b["uid"])
            react[sid] = {"owned": 1, "title": title}
            wrote = True
        if wrote:
            con.commit()
    finally:
        con.close()


def _collapse_tracking_tours(rows: list, RC2) -> list:
    """「興味あり」の束を、**作品単位で 1 行にまとめる。**

    起案者の指摘（2026-08-26）── 「母さん、ラブソングです。」で東京公演もあるはずなのに
    宮城の電力ホールのものだけが出ていた。**「興味あり」を押した会場だけを積む作りに
    なっていたのが原因である。** `recommend2.py` はツアーの他会場を代表 1 件に畳んで
    `tours` として持たせるが、**この畳み込みは「興味あり」に振り分けられなかった会場
    だけを対象にしている**（`recommend2.py` の該当箇所を参照）。押した会場はそこから
    早く抜けるので畳み込みに加わらず、押していない他会場（この例では東京公演）は
    別の代表会場の `tours` に紛れ込み、この画面からは辿れなくなる。

    **`DG.all_candidates()`（押した・押していないに関わらない全会場）から、
    同じ作品の会場を拾い直す。** ここでまとめる会場は「まだ買っていない」ものなので、
    押しているかどうかに関係なく行けるかどうかを全部見せる ── 押していない会場を
    隠すと、押した 1 会場しか行けないと誤解される。
    """
    if not rows:
        return rows
    import digest as DG
    order: list = []
    by_work: dict = {}
    for c in rows:
        k = RC2.work_key(c.get("title") or "", str(c.get("stage_id") or ""))
        if k not in by_work:
            by_work[k] = []
            order.append(k)
        by_work[k].append(c)
    all_by_work: dict = {}
    for c in DG.all_candidates():
        k = RC2.work_key(c.get("title") or "", str(c.get("stage_id") or ""))
        all_by_work.setdefault(k, []).append(c)
    out = []
    for k in order:
        group = sorted(by_work[k],
                       key=lambda c: RC2.period_start(c.get("period") or "") or "9999")
        rep = dict(group[0])
        have = {str(c.get("stage_id") or "") for c in group}
        others = [c for c in all_by_work.get(k, [])
                 if str(c.get("stage_id") or "") not in have]
        extra = [{"stage_id": str(o.get("stage_id") or ""), "theater": o.get("theater") or "",
                 "pref": o.get("pref") or "", "period": o.get("period") or "",
                 "days": o.get("days") or 0, "price": o.get("price") or "",
                 "url": o.get("url") or "", "onsale": o.get("onsale") or "確認できず"}
                for o in others]
        rep["tours"] = extra + [t for t in (rep.get("tours") or [])
                                if str(t.get("stage_id") or "") not in have]
        out.append(rep)
    return out


def _rebucket(d: dict) -> dict:
    """保存された一覧に、**いまの反応を当て直す。**

    **点は動かさない。** 並び（`ranked` の順）はそのまま使い、押された反応で
    「推薦・追いかけている・観る予定・その他」のどれに入るかだけを決め直す
    ── `recommend2.py` が書き出すときに使っている規則と同じである。

    **反応が付いていないお気に入り（網 A）は、いつでもお気に入りに戻る。** 登録した名前の
    公演は「内容を問わず知らせる」ものなので、束の割り振りを反応より後に見る。
    """
    import datetime
    import feedback as FB
    import recommend2 as RC2
    today = datetime.date.today().isoformat()
    _auto_own_from_mail(today)
    con = FB.connect()
    try:
        react = FB.reactions(con)
        tickets = FB.tickets(con)
    finally:
        con.close()
    # **作品単位にも畳む。** ツアーの別会場は stage_id が違うので、ID だけでは戻ってくる
    react_w = {RC2.work_key(v.get("title") or ""): v
               for v in react.values() if v.get("title")}
    sids_by_workkey = _react_groups(react)

    def r_of(c: dict) -> dict:
        return (react.get(str(c.get("stage_id") or ""))
                or react_w.get(RC2.work_key(c.get("title") or "")) or {})

    order = ("favourites", "ranked", "others", "owned", "tracking", "started")
    seen: set = set()
    pool: list = []
    for k in order:
        for c in d.get(k) or []:
            sid = str(c.get("stage_id") or "")
            if sid in seen:
                continue
            seen.add(sid)
            pool.append((k, c))
    # **「持っている」だけの公演も拾う。** `d[...]` は週次の推薦（`recommend2.json`）
    # から来るので、**一度も推薦に出たことが無い公演**（探して直接買った・メールから
    # 自動で「持っている」にした ── `_auto_own_from_mail`）は、反応が付いていても
    # ここまでの `pool` に入らない。**`_upcoming_index()` から拾い直す**
    # （探す画面が使っているのと同じ、もっと広い索引）
    for sid, r in react.items():
        if r.get("owned") != 1 or sid in seen:
            continue
        c = _upcoming_index()["rows"].get(sid)
        if not c:
            continue
        seen.add(sid)
        pool.append(("others", {**c, "stage_id": sid}))
    out: dict = {k: [] for k in order}
    for k, c in pool:
        r = r_of(c)
        if r.get("owned") == 1:
            # **上演が終わった分は「観る予定」から外す。** 評価待ちに移った
            # （`_promote_owned_tickets`）ので、ここにも残すと同じ公演が
            # 「購入済み公演」と「評価一覧」の両方に出てしまう
            sid = str(c.get("stage_id") or "")
            sids = sids_by_workkey.get(RC2.work_key(c.get("title") or ""), [sid])
            done = _owned_done_date(sids, c, tickets)
            if done and done <= today:
                continue
            out["owned"].append(c)
            # **お気に入りに当たった分は、持っていても外さない**（起案者の指示・
            # 2026-08-26 ──「おすすめに出ないようにして（お気に入りには出ていて
            # よい）」）。お気に入りは「読むだけのお知らせ」なので、券を持ったことと
            # 知らせを読むことは両立する ── **「持っている」だけがこの例外を持つ。**
            if c.get("a"):
                out["favourites"].append(c)
        elif r.get("interest") == 1:
            # **興味ありを押した公演は、お気に入りには重ねない**（起案者の指摘・
            # 2026-08-26 ──「公演カレンダーで同じ公演が興味ありとお気に入りの
            # 2つずつあるのはなぜ？」）。以前はここに来る前の行で `c.get("a")` を
            # 無条件にお気に入りへ足していたため、名前が当たった公演に興味ありを
            # 押すと両方の束に入っていた。お気に入りは「まだ気づいていないかも
            # しれない公演を知らせる」役目なので、すでに興味ありと答えた時点で
            # その役目は済んでいる ── 「持っている」だけが上の例外を持つ。
            out["tracking"].append(c)
        elif r.get("interest") == 0:
            # **興味なしも同じ理由で重ねない。** 名前は当たっているが「興味なし」と
            # 答えた時点で、お気に入りが知らせる役目はすでに済んでいる
            out["others"].append(c)
        elif c.get("a"):
            out["favourites"].append(c)
        elif k in ("ranked", "others"):
            out["ranked"].append(c)
        else:
            # **点の付いていない行を推薦枠に入れない。** 観る予定・追いかけている・
            # お気に入り・初日を迎えた公演は、点を付ける前に枠から出しているので
            # 正規化した点（`s`）を持っていない。**入れると順位の付かないカードが
            # 推薦に並ぶ**ので、反応が読めないときは控えの束に残す
            out[k].append(c)
    # **「興味あり」は作品単位で 1 行にまとめる。** 押した会場だけを積むと、押していない
    # 他会場（ツアーのもう 1 都市）がこの束から辿れなくなる（`_collapse_tracking_tours`）
    out["tracking"] = _collapse_tracking_tours(out["tracking"], RC2)
    # **お気に入りと追いかけているものは上演日の近い順。** 用途が買い忘れの防止なので、
    # 点の順ではなく締切の順に並べる（`recommend2.py` と同じ）
    for k in ("favourites", "tracking"):
        out[k].sort(key=lambda c: RC2.period_start(c.get("period") or "") or "9999")
    e = dict(d)
    e.update(out)
    return e


# ------------------------------------------------- 順位付けの効かせ方を変える
#
# 起案者の指示（2026-08-24）──「実際にどの項目をどれくらい推薦に影響させるのか？
# っていうのを各ユーザーがフィルターで調整できるようにしてほしい」「パラメータで
# ５段階程度で効かせ方を調整できるようにしてほしい」。
#
# ## 既定では何も変えない
#
# **段階の真ん中「ふつう」が、これまでと同じ効き方である。** 役職ごとの重みは実測の
# 判別力で置いたもの（出演 1.0 ＞ 演出・脚本 0.4 ＞ 裏方 0.1。単独の AUC は
# 出演 0.611 ＞ 演出・脚本 0.540 ＞ 裏方 0.500）なので、**一人の好みを既定に書き込むと、
# 「利用者ごとに調整できるようにする」という指示そのものと正反対になる。** 動かすのは本人で、
# 動かさなければ実測どおりに効く。
#
# ## 段階は「いまの効き方の何倍か」で置く
#
# 絶対の重みを 5 段に割り当てる案は採らない ── 実測の重みが段の途中に落ちるものがあり
# （翻訳 0.3）、**段に合わせるために測った値を書き換えることになる。** 倍率にすれば、
# 「ふつう」は必ず実測どおりになる。**画面には倍率の数字を出さない**（内部の指標を
# 当事者に見せない）。出すのは言葉と、その項目で一致している候補の件数である。
#
# ## 「効かせない」はスコアと理由の両方から外す
#
# 理由として出せないものが順位を動かすと、「なぜこれが出たか」を説明できない公演が
# 上位に来る（企画書 2 章）。**外した項目だけで拾われていた公演は推薦から消える**ので、
# 消える件数を画面に書く（あふれた分の行き先を必ず言う）。
#
# ## その場で効く
#
# 点の再計算は保存済みの内訳（`why_b`・`why_c`）だけで足りるので、**更新をやり直さずに
# 開いた瞬間から効く。** 内訳には 1 件ごとの寄与と役職と履歴の本数が入っている。
WEIGHT_SCHEMA = """
CREATE TABLE IF NOT EXISTS rank_weight (
    grp        TEXT PRIMARY KEY,
    step       TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

# 5 段階。**真ん中が既定で、実測どおりの効き方である。**
WEIGHT_STEPS = (("off", "効かせない", 0.0),
                ("weak", "あまり効かせない", 0.5),
                ("mid", "ふつう", 1.0),
                ("strong", "少し強く", 2.0),
                ("max", "とても強く", 4.0))
STEP_MUL = {k: m for k, _l, m in WEIGHT_STEPS}
DEFAULT_STEP = "mid"
# **段の名前と札を画面のスクリプトへ渡す。** 画面の側に書き写すと、つまみの位置と
# 札の言葉がずれる ── 言葉の出どころを 1 つにする
SCRIPT = (SCRIPT
          .replace("__TAGURI_WSTEPS__",
                   json.dumps([k for k, _l, _m in WEIGHT_STEPS], ensure_ascii=False))
          .replace("__TAGURI_WLABEL__",
                   json.dumps({k: l for k, l, _m in WEIGHT_STEPS}, ensure_ascii=False)))

# 役職のまとめ方。**演劇のクレジットの慣習的な区分に寄せた**（キャスト／創作／技術／制作）。
# 22 種を 1 行ずつ並べると 1 件しか一致していない役職まで画面に並ぶので、まとめる。
# **「宣伝だけ外して美術は残す」ができる細かさ**を残すために、裏方を 1 つにはしない。
ROLE_GROUPS = (
    ("cast", "出演者", ("出演",)),
    ("author", "演出・脚本・翻訳",
     ("演出", "脚本", "作", "原作", "翻訳", "潤色", "構成", "演出・振付")),
    ("craft", "つくり（美術・照明・音響・映像・衣裳・振付など）",
     ("美術", "照明", "音響", "映像", "衣裳", "衣装", "振付", "音楽", "作曲", "編曲",
      "歌唱指導", "ヘアメイク", "メイク", "小道具", "大道具", "特殊効果", "特効",
      "方言指導", "アクション", "アクション監督", "殺陣", "人形", "オーケストラ",
      "演奏", "指揮", "録音", "選曲")),
    ("stage", "進行（舞台監督・技術監督・演出助手など）",
     ("舞台監督", "技術監督", "演出助手", "舞台監督助手", "スタッフ", "進行",
      "舞台美術製作", "大道具製作")),
    ("produce", "制作・宣伝（製作・プロデューサー・宣伝・票券など）",
     ("製作", "制作", "プロデューサー", "エグゼクティブプロデューサー", "宣伝",
      "宣伝美術", "票券", "企画", "広報", "協力", "提携", "主催")),
    ("other", "その他の役職（上のどれにも入らないもの）", ()),
    ("theme", "作品の内容（あらすじの題材）", ()),
)
GROUP_LABEL = {k: l for k, l, _r in ROLE_GROUPS}
# **見出しに出す短い名前。** 括弧の中の例まで並べると、見出しが 1 行で読めなくなる
GROUP_SHORT = {"cast": "出演者", "author": "演出・脚本・翻訳", "craft": "つくり",
               "stage": "進行", "produce": "制作・宣伝", "other": "その他の役職",
               "theme": "作品の内容"}
_ROLE_TO_GROUP = {r: k for k, _l, roles in ROLE_GROUPS for r in roles}


def group_of(role: str) -> str:
    """役職が属するまとめ。**知らない役職は「その他の役職」に入れる。**

    落とさずに受け止める先を必ず持つ ── 名前の付いていない役職が調整の対象から漏れると、
    **どの段に置いても効き方が変わらない行が黙って残る。**
    """
    return _ROLE_TO_GROUP.get((role or "").strip(), "other")


def read_weights() -> dict:
    """いまの効かせ方。**保存が無ければ全部「ふつう」である。**"""
    import rate_performances as R
    con = R.connect()
    try:
        con.executescript(WEIGHT_SCHEMA)
        rows = {r["grp"]: r["step"] for r in con.execute("SELECT grp, step FROM rank_weight")}
    finally:
        con.close()
    return {k: (rows.get(k) if rows.get(k) in STEP_MUL else DEFAULT_STEP)
            for k, _l, _r in ROLE_GROUPS}


def save_weight(grp: str, step: str) -> dict:
    """効かせ方を 1 つ書く。**受け付ける組み合わせは列挙したものだけ**（守り 4）。"""
    import rate_performances as R
    if grp not in GROUP_LABEL:
        raise ValueError("その項目は無い")
    if step not in STEP_MUL:
        raise ValueError("その段階は無い")
    con = R.connect()
    try:
        con.executescript(WEIGHT_SCHEMA)
        with con:
            con.execute("INSERT INTO rank_weight (grp, step, updated_at) VALUES (?, ?, ?)"
                        " ON CONFLICT(grp) DO UPDATE SET step=excluded.step,"
                        " updated_at=excluded.updated_at",
                        (grp, step, R.now()))
    finally:
        con.close()
    return {"ok": True, "grp": grp, "label": GROUP_LABEL[grp], "step": step}


def save_weights(w: dict) -> dict:
    """効かせ方を**まとめて 1 回で書く。**

    起案者の指示（2026-08-24）──「推薦の効かせ方を変えたら、確定ボタンを押して再度推薦を
    読み込む形にしてほしい」。**つまみを動かすたびに書いて読み込み直す形をやめた** ──
    7 つのつまみを続けて動かしたいのに、1 つ動かすごとに画面が入れ替わってしまう。
    **押したときに 1 回だけ書く。**
    """
    import rate_performances as R
    # **全部を確かめてから書く。** 1 件ずつ書くと、4 つ目が間違っていたときに
    # **3 つだけ効いた設定**が残る ── 押した人は「確定した」と読むので、半分効いた
    # 状態を作ってはいけない
    rows = []
    for k, v in (w or {}).items():
        k, v = str(k), str(v)
        if k not in GROUP_LABEL:
            raise ValueError(f"その項目は無い: {k}")
        if v not in STEP_MUL:
            raise ValueError(f"その段階は無い: {v}")
        rows.append((k, v))
    if not rows:
        raise ValueError("効かせ方が 1 つも来ていない")
    con = R.connect()
    try:
        con.executescript(WEIGHT_SCHEMA)
        with con:
            con.executemany(
                "INSERT INTO rank_weight (grp, step, updated_at) VALUES (?, ?, ?)"
                " ON CONFLICT(grp) DO UPDATE SET step=excluded.step,"
                " updated_at=excluded.updated_at",
                [(k, v, R.now()) for k, v in rows])
    finally:
        con.close()
    return {"ok": True, "n": len(rows)}


# ---------------------------------------------------------------- 設定
#
# 起案者の指示（2026-08-26）──「一括の設定画面をつくってほしい。たとえば『全部の表示を
# 指定した都道府県のみにする』などの細かい設定をしたい」。
#
# **表は「効かせ方」（`rank_weight`）と分ける。** どちらも「保存しておく好み」ではあるが、
# 効かせ方は行ごとに列（`grp`, `step`）の意味が決まっている表で、**設定はこの先も
# 項目が増えていく**（起案者の言葉どおり「一括の設定画面」で、都道府県はその 1 例である）。
# 項目が増えるたびに表の列を増やすのではなく、**鍵と値だけを持つ表にして、値の中身は
# 項目ごとに JSON で決める。**
SETTING_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_setting (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

PREF_SETTING_KEY = "pref_filter"


def read_pref_setting() -> list[str]:
    """既定の都道府県の絞り込み。**保存が無ければ全国**（絞り込みなし）。

    **これまでは「保存はしない・既定は全国」だった**（`/recommend` の以前の注記）。
    起案者の今回の指示で、**この判断を撤回する** ── 「全部の表示を指定した都道府県
    のみにする」という設定を作る以上、閉じるたびに全国へ戻っては設定にならない。
    """
    import rate_performances as R
    con = R.connect()
    try:
        con.executescript(SETTING_SCHEMA)
        row = con.execute("SELECT value FROM app_setting WHERE key=?",
                          (PREF_SETTING_KEY,)).fetchone()
    finally:
        con.close()
    if not row:
        return []
    try:
        v = json.loads(row["value"])
    except ValueError:
        return []
    return [p for p in RR.PREFS if p in set(v)] if isinstance(v, list) else []


def save_pref_setting(prefs) -> dict:
    """既定の都道府県の絞り込みを 1 回で書く。**受け付けるのは列挙した都道府県だけ**
    （守り 4 ── 任意の文字列を書き込める口を作らない）。"""
    import rate_performances as R
    if not isinstance(prefs, list) or len(prefs) > 47:
        raise ValueError("都道府県の並びがおかしい")
    keep = [p for p in RR.PREFS if p in set(prefs)]
    con = R.connect()
    try:
        con.executescript(SETTING_SCHEMA)
        with con:
            con.execute(
                "INSERT INTO app_setting (key, value, updated_at) VALUES (?, ?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value,"
                " updated_at=excluded.updated_at",
                (PREF_SETTING_KEY, json.dumps(keep, ensure_ascii=False), R.now()))
    finally:
        con.close()
    return {"ok": True, "prefs": keep}


def _card_h2(name: str, text: str, extra: str = "") -> str:
    """「設定」の札の見出し。**`IC.h2` と中身は同じだが、`<summary>` で出す。**

    起案者の指示（2026-08-26）──「設定の各項目はデフォルトで折りたたんで表示して」。
    札を `<details class="card">` にすると、見出しより下（本文・フォーム）は
    既定で隠れる。**見出しの形（絵記号・文字・右のバッジ）は変えない** ── 畳めるか
    どうかは開閉の仕組みの違いであって、見出しの読み方まで変える理由が無い。
    """
    return f'<summary>{IC.ico(name, 18)}<span>{text}</span>{extra}</summary>'


def page_settings() -> str:
    """**一括の設定画面。**（起案者の指示・2026-08-26）

    ## 決めごとの下に、たまにしか押さない道具を並べる

    起案者の言葉は「たとえば」で始まっており、**都道府県の設定は例の 1 つ**として
    挙げられたものである。**画面は複数の項目を縦に並べる形にしておき**、この設定が
    その最初の 1 枚になった ── 次に別の設定が要るとき、この画面に節を 1 つ足せばよい。

    **「書き出す」（もとは独立の画面）・「別の端末に記録を移す」（新規）・
    「取り消した記録」（もとは日記帳の下）・「行かなかった公演」（もとは日記帳の
    年の外の耳）も、同じ画面に札として並べた**（起案者の指示・2026-08-26）。
    決めごとではなく道具だが、**どれも「たまにしか押さない」という点で、週次で
    見る画面には要らない**のは都道府県の既定と同じである。

    ## 「全部の表示」とは、実際にはどれを指すか

    **まだ答えていない候補の順位（「今週のおすすめ」）だけに効く。** それ以外には
    効かせない ── **公演カレンダーも対象から外した。** 最初はここも含める案で書いたが、
    公演カレンダーが並べているのは「券を持っている」「興味あり」「お気に入りに当たった」
    という、**もう答えの出た公演である。** 都道府県の既定を「東京都」にした状態で
    大阪に観に行く券を買っていたら、カレンダーがそれを隠すことになる ── **すでに
    決めたことを、この設定が上書きしてはいけない。** 同じ理由で、興味あり・お気に入り・
    購入済み公演・記録を見返す（過去に観た記録）も対象から外している。

    ## 押した先で何が起きるか

    **「今週のおすすめ」を開くたびに、この都道府県で絞り込んだ状態になる。** 開いた
    その場でも一時的に別の県へ変えられる（「観に行ける場所で絞り込む」）が、**次に
    開いたときはこの設定に戻る** ── 一時的な変更と、既定の変更を混ぜない。

    ## 各項目は既定で畳んでおく（2026-08-26）

    起案者の指示 ──「設定の各項目はデフォルトで折りたたんで表示して」。**この画面に
    来る用は「1 つの決めごとを確かめて直す」ことで、5 枚まとめて読み通す画面ではない。**
    開いたまま並べると、直したい 1 項目にたどり着くまでに他の 4 枚を目で追うことになる。
    **畳んでいても、いま何を選んでいるかは見出しの右のバッジで読める**（`_card_h2`）ので、
    開かなくても現在の設定は分かる。
    """
    prefs = read_pref_setting()
    d, _wait = _load()
    counts = RR.pref_counts(d)
    rcounts = PM.region_counts(d)
    keep = set(prefs)
    chips = "".join(
        f'<label class="pchip{" on" if p in keep else ""}">'
        f'<input type="checkbox" name="pref" value="{E(p)}"{" checked" if p in keep else ""}>'
        f'<span class="pl">{E(p)}</span><span class="pn">{counts.get(p, 0)}</span></label>'
        for p in RR.PREFS if counts.get(p))
    now = ("全国" if not prefs else
           "・".join(prefs) + f"（{len(prefs)} 県）")
    body = f"""<h1>設定</h1>
<p class="lede">この仕組みぜんたいに効く、決めごとを置く場所です。<b>1 件ずつではなく、
まとめて確かめてから保存します。</b></p>
<details class="card">{_card_h2("gear", "観に行ける場所を決めておく",
 f'<span class="badge part">いまは{E(now)}</span>')}
<p class="lead">都道府県を選んで保存すると、<b>「今週のおすすめ」と「公演カレンダー」を
開くたびに、その都道府県で絞り込んだ状態になります。</b>選ばなければ全国です。
<b>いくつでも同時に選べます。</b><br>
<b>すでに「興味あり」を押した公演・お気に入り・買った券には効きません。</b>
一度決めたことを、この設定で見えなくすることはありません。</p>
<form class="pfil" id="pref-setting" onsubmit="return false">
{PM.panel(counts, rcounts)}
<div class="pchips">{chips}</div>
<div class="pfoot"><button type="button" data-set-pref="1">{IC.ico("gear")}この都道府県を既定にする</button>
<button type="button" class="pall-btn" data-set-pref-all="1">全国に戻す</button>
<span class="said"></span></div>
</form></details>
{_export_card_html()}
{_data_copy_card_html()}
{_dropped_html()}
{_skipped_html()}"""
    return layout("設定", "/settings", body, RR.STYLE)


def _p90(vals) -> float:
    """正規化の分母。**最大では割らない**（外れ値 1 件に全体が潰される。`recommend2.py` と同じ）。"""
    v = sorted(x for x in vals if x > 0)
    return v[int(len(v) * 0.9)] if v else 1.0


def _apply_weights(d: dict, w: dict | None = None) -> dict:
    """効かせ方を当てて、点と理由と並びを作り直す。

    **保存済みの内訳だけで足りる。** `why_b` は 1 件ごとに（寄与, 役職, 名前, 履歴の本数）を
    持っているので、**役職の重みで割れば元の寄与に戻せる** ── 更新をやり直さずに、
    倍率を掛け直すだけで点が出る。

    **「効かせない」は理由からも消す。** 説明できない公演を上位に置かないためである
    （企画書 2 章）。その結果、外した項目だけで拾われていた公演は点が 0 になるので、
    **推薦の一覧から落ちる。** 落ちた件数は画面に書く。
    """
    import recommend2 as RC2
    w = w or read_weights()
    if all(v == DEFAULT_STEP for v in w.values()):
        return dict(d, weights=w, w_dropped=0)

    def mul(grp: str) -> float:
        return STEP_MUL.get(w.get(grp) or DEFAULT_STEP, 1.0)

    def redo(c: dict) -> dict:
        c = dict(c)
        wb = []
        for it in c.get("why_b") or []:
            contrib, role, person, n = it[0], it[1], it[2], it[3]
            base = RC2.ROLE_W.get(role, RC2.BACKSTAGE_W) or RC2.BACKSTAGE_W
            m = mul(group_of(role))
            if m <= 0:
                continue
            wb.append([round(contrib * m, 6), role, person, n])
        wc = ([] if mul("theme") <= 0 else
              [[round(it[0] * mul("theme"), 6)] + list(it[1:]) for it in (c.get("why_c") or [])])
        c["why_b"], c["why_c"] = wb, wc
        c["b"] = round(sum(x[0] for x in wb), 4)
        c["c"] = round(sum(x[0] for x in wc), 4)
        c["n_match"] = len(wb)
        # **効く一致の数にも効かせ方を掛ける。**「出演を強く」を選んでも順位が動かない
        # 状態にしないためである ── 並べる 1 段目はこの数で、**掛けないと重みは 2 段目の
        # 同点崩しにしか効かない**（実測 ── 出演を 4 倍にしても上位 3 件が 1 件も
        # 動かなかった）。**「強く」と書いたのに動かない目盛りは、無いのと同じである。**
        #
        # **「ふつう」では倍率が 1 なので、数え方はこれまでと変わらない**（出演、または
        # 履歴 2 本以上を 1 件として数える。検証 028）。既定の並びは実測どおりに保たれる。
        c["strong"] = round(sum(mul(group_of(x[1])) for x in wb
                                if x[1] == "出演" or x[3] >= 2), 3)
        c["total"] = round(c["b"] + RC2.W_C * c["c"], 4)
        return c

    e = dict(d)
    for k in ("favourites", "ranked", "others", "owned", "tracking", "started"):
        e[k] = [redo(c) for c in (d.get(k) or [])]
    keep = {id(c) for c in e["others"]}
    rows = e["ranked"] + e["others"]
    nb, nc = (_p90([x["b"] for x in rows if x["total"] > 0]),
              _p90([x["c"] for x in rows if x["total"] > 0]))
    for x in rows:
        x["bn"], x["cn"] = min(x["b"] / nb, 1.5), min(x["c"] / nc, 1.5)
        x["s"] = round(x["bn"] + x["cn"], 3)
        x["both"] = x["b"] > 0 and x["c"] > 0
    # **並べる鍵は変えない**（効く一致の数 → 正規化スコア。検証 044）
    order = sorted(rows, key=lambda x: (-x["strong"], -x["s"]))
    # **推薦枠からは、理由が 1 つも残らなかった公演を落とす** ── 順位付きで出す一覧なので、
    # 説明できない公演を並べられない（企画書 2 章）。**「その他」の束は点で落とさない**
    # ── あの束に入っているのは本人が「興味なし」と答えたものなので、
    # **効かせ方をいじった結果として本人の答えが消えてはならない**
    e["ranked"] = [c for c in order if id(c) not in keep and c["total"] > 0]
    e["others"] = [c for c in order if id(c) in keep]
    dropped = sum(1 for c in order if id(c) not in keep and c["total"] <= 0)
    e["weights"], e["w_dropped"] = w, dropped
    return e


def weight_form(d: dict) -> str:
    """効かせ方を変える口。**左から右へつまんで動かし、確定を押すと読み込み直す。**

    起案者の指示（2026-08-24）──「確定ボタンを押して再度推薦を読み込む形にしてほしい。
    ボタンのデザインを他と統一して。左から右につまみながら調節するパラメータみたいな
    イメージ」。

    ## つまみにした理由

    **5 つのボタンを横に並べる形をやめた。** 段には**弱い → 強いという順序がある**ので、
    同じ大きさのボタンを 5 つ並べると「5 つの別の選択肢」に見える。**位置そのものが強さを
    表す形**にすれば、いまどのくらいに置いているかが目で分かる。

    ## 確定を押すまで書かない

    つまみを動かすたびに保存して読み込み直すと、**7 つのつまみを続けて動かしたいのに
    1 つ動かすごとに画面が入れ替わる。** 動かしている途中は画面に触らず、
    **押したときに 1 回だけ書いて、そこで推薦を読み込み直す。**

    ## ボタンは他の画面と同じものを使う

    都道府県の絞り込みと同じ `.pfoot` / `.pall` を使う ── **同じ働きのボタンが画面ごとに
    違う見た目をしていると、押していいものかどうかを毎回考えることになる。**

    ## 数字を出さない

    出すのは言葉と、その項目で一致している候補の件数だけである（倍率や寄与は内部の指標
    なので当事者の画面には置かない）。**「ふつう」が既定であることを書く** ── 何もしなければ
    実測どおりに効くことが伝わらないと、触らないと損をしているように読める。
    """
    w = d.get("weights") or read_weights()
    cnt = d.get("w_counts") or {}
    keys = [k for k, _l, _m in WEIGHT_STEPS]
    labels = {k: l for k, l, _m in WEIGHT_STEPS}
    changed = [f"{GROUP_SHORT[k]}を{labels[v]}"
               for k, _l, _r in ROLE_GROUPS
               for v in [w.get(k) or DEFAULT_STEP] if v != DEFAULT_STEP]
    now = ("すべて「ふつう」（これまでと同じ効き方）" if not changed else
           "／".join(changed))
    rows = []
    for k, label, _roles in ROLE_GROUPS:
        cur = w.get(k) or DEFAULT_STEP
        i = keys.index(cur)
        n = cnt.get(k) or 0
        rows.append(
            f'<div class="wrow{" off" if cur == "off" else ""}" data-grp="{k}">'
            f'<span class="wl">{E(label)}</span>'
            f'<span class="wn">おすすめの候補 {n} 件で一致</span>'
            f'<input class="wsl" type="range" min="0" max="{len(keys) - 1}" step="1"'
            f' value="{i}" data-weight="{k}"'
            f' aria-label="{E(label)}の効かせ方">'
            f'<span class="wv">{E(labels[cur])}</span></div>')
    drop = d.get("w_dropped") or 0
    dropped = ("" if not drop else
               f'<p class="lead">いまの設定で、おすすめに出なくなった公演が {drop} 件あります。'
               f'「すべて「ふつう」に戻す」を押すと戻ります。</p>')
    # **目盛りの意味は 1 か所にだけ書く。** 7 行それぞれに 5 つの言葉を並べると、
    # 読む量が増えるばかりで、どの行を動かすかの判断には使われない
    scale = ('<div class="wscale"><span>← ' + E(labels["off"]) + "</span>"
             + f'<span class="wmid">{E(labels[DEFAULT_STEP])}（既定）</span>'
             + "<span>" + E(labels["max"]) + " →</span></div>")
    return f"""<div class="wfil">
<details class="pbox wbox" id="weights">
<summary>{IC.ico("light", 15)}おすすめの効かせ方を変える ── いまは<b>{E(now)}</b></summary>
<p class="lead">おすすめの順位に、どの情報をどれくらい効かせるかを決められます。
つまみを動かして「この効かせ方でおすすめを読み込む」を押すと、一覧を作り直します。
押すまでは変わりません。既定は「ふつう」です。
いちばん左の「効かせない」にすると、その情報は順位からも理由からも消えます。
件数は、おすすめの候補のうち、その情報が一致している公演の数です ──
件数が少ない項目は、動かしても一覧はあまり変わりません。</p>
{scale}
{"".join(rows)}
<div class="pfoot"><button data-wsave="1">{IC.ico("light")}この効かせ方でおすすめを読み込む</button>
 <button class="pall-btn" data-wreset="1">すべて「ふつう」に戻す</button>
 <span class="wsaid"></span></div>
{dropped}
<p class="lead">お気に入りに登録した名前の公演は、この設定に関係なく出ます。</p>
</details></div>"""


def _weight_counts(raw: dict) -> dict:
    """項目ごとに、いま一致している候補の件数。

    **押す前に分かるようにする**（都道府県の札と同じ）。**数えるのは効かせ方を当てる前の
    一覧である** ── 当てた後で数えると、「効かせない」にした行の件数が 0 になって、
    戻す判断ができなくなる。
    """
    # **数えるのは推薦の候補だけにする。** 「その他」（興味なしと答えた公演）まで含めると、
    # **17 件で一致と書いてあるのに推薦の上位には 2 件しか出ない**ことになる ──
    # 一致の件数は「この項目を動かすと推薦がどれくらい動くか」を読むための数である
    n = {k: 0 for k, _l, _r in ROLE_GROUPS}
    for c in (raw.get("ranked") or []):
        seen = set()
        for it in c.get("why_b") or []:
            seen.add(group_of(it[1]))
        if c.get("why_c"):
            seen.add("theme")
        for g in seen:
            n[g] = n.get(g, 0) + 1
    return n

def _overlay_one(c: dict, themes: dict, hand: dict) -> dict:
    """1 枚に、いまの内容（機械の抽出と、手で入れた分）を当て直す。"""
    sid = str(c.get("stage_id") or "")
    t = themes.get(("candidate", sid)) or {}
    c["themes"] = [e["word"] for e in (t.get("elements") or []) if e.get("word")]
    c["themes_by"] = t.get("elements_by") or ""
    # **ここで切り詰めない。** 機械の抽出は 60〜300 字におさまるよう指示してあるが、
    # 手で入れた分は 1200 字まで許している（`hand_themes.MAX_SYNOPSIS`）。かつては
    # ここで [:300] していたため、「続きを読む」で畳みを開いても 300 字より先が
    # 誰の目にも出なかった ── 表示の見た目の畳みは CSS（`.syn .txt` の line-clamp）
    # が担っており、文字列そのものを切る理由はない
    syn = t.get("synopsis") or ""
    if syn:
        c["synopsis"] = syn
        c["synopsis_by"] = t.get("synopsis_by") or ""
    h = hand.get(sid)
    if h:
        c["hand"] = {"synopsis": h.get("synopsis") or "", "url": h.get("url") or "",
                     "words": h.get("elements") or [], "fields": h.get("fields") or {}}
    return c


def _overlay_themes(d: dict) -> dict:
    """保存された一覧に、**いまの内容を当て直す。**

    **一覧は起動のときに組む**（`recommend2.py`）ので、そのあとで手で入れた題材は
    次の起動まで画面に出ない。**押した結果はその場で出す**（起案者の指示 2026-08-24）ので、
    読むたびに当て直す ── 機械の抽出も同じ口から来るので、月 1 回の取り直しの結果も
    起動を待たずに出る。
    """
    import hand_themes as HT
    import net_c as C
    try:
        themes, hand = C.load_themes(), HT.load()
    except (OSError, ValueError):
        return d
    for rows in d.values():
        if not isinstance(rows, list):
            continue
        for c in rows:
            if isinstance(c, dict) and c.get("stage_id"):
                _overlay_one(c, themes, hand)
    return d


def _load() -> tuple[dict, list]:
    """画面が読む材料。**保存された一覧に、いまの反応と効かせ方を当て直して返す。**"""
    raw, _ = RR.load()
    d = _apply_weights(_rebucket(raw), read_weights())
    d["w_counts"] = _weight_counts(raw)
    return _overlay_themes(d), waiting_rows()


def _notes_no() -> dict:
    """**「興味なし」に添えた、見送った理由。** 公演ごとに引く。

    `_notes()` とは列が違う ── **見送った理由から「お気に入り」への昇格候補を作っては
    いけない**ので、そもそも別の列に入れてある（`tools/taguri/reasons.py` は `note` しか
    読まない）。
    """
    return _note_column("note_no")


def _notes() -> dict:
    """「興味あり」に添えた理由の文を、公演ごとに引く。

    **書いたものを読み返せるようにするためである。** 理由の文は次の推薦とお気に入りの
    候補に効く入力なので（`tools/taguri/reasons.py`）、**書いた本人が後から確かめられない
    ままにすると、測るためだけの入力に戻ってしまう。**
    """
    return _note_column("note")


def _note_column(col: str) -> dict:
    """理由の列を公演ごとに引く。**列の名前は呼ぶ側が決める**（外からは来ない）。"""
    assert col in ("note", "note_no")
    try:
        con = sqlite3.connect(DB)
        rows = con.execute(f"SELECT stage_id, {col} FROM reaction"                # noqa: S608
                           f" WHERE {col} IS NOT NULL AND TRIM({col}) <> ''"
                           " ORDER BY updated_at").fetchall()
        con.close()
    except sqlite3.Error:
        return {}
    return {str(sid): note for sid, note in rows}


# ---------------------------------------------------------------- 更新でできなかったこと
# **段の名札 → その段ができないと、使う人に何が起きるか。**
#
# `tools/taguri/run.py` は「取れなかったことを画面に出したうえで開くほうが正しい」と
# 決めているのに、**失敗は端末に出るだけだった**（起案者の指摘・2026-08-24）。
# ショートカットから開いた人は端末を見ないので、**カレンダーを取り込めなかった週も、
# いつもと同じ一覧が出てくる。件数が減っていても気づけない。**
#
# **書くのは、処理の名前ではなく結果である。**「カレンダーの取り込みに失敗しました」では、
# 読んだ人は何を差し引いて一覧を見ればよいのか分からない。**一覧のどこがふだんと違うのかを
# 書く。**
RUN_MISS = {
    "mail": "買った公演を取り込めませんでした ── 最近買ったぶんが、"
            "評価待ちに出てこないことがあります。",
    "candidates": "これから観られる公演を取り直せませんでした ── "
                  "前に取ったときの一覧をそのままお出ししています。",
    "link": "記録と公演ページの結び付けができませんでした ── "
            "結び付いていない記録は、おすすめの材料になりません。",
    "themes": "公演の内容を読み取れませんでした ── "
              "「どんな話か」を理由に出せない公演があります。",
    "favourites": "お気に入りに登録した名前で、公演を探せませんでした ── "
                  "<b>登録した名前の新着が、今回は届いていないことがあります。</b>",
    "calendar": "上演予定を取り込めませんでした ── "
                "<b>一覧の件数が、ふだんより少なくなっています。</b>",
    "posters": "ポスターを取り込めませんでした ── 絵の出ない公演があります。",
    "lookback": "「記録を見返す」の材料を組めませんでした ── "
                "図が出ないことがあります。",
}


def run_updated_at() -> str:
    """**この一覧をいつ作ったかを、日付と時刻の文で返す。**

    `run.py` の `save_status`（`run_status.json` の `at`）を読む。**推薦の計算は
    毎回の実行のいちばん最後に行われる**ので、この時刻がそのまま「今週のおすすめを
    作った時刻」になる（起案者の指示・2026-08-26 ── いつ更新されたかを画面に
    書いてほしい）。読めないときは空文字を返し、呼び出す側は何も出さない。
    """
    import datetime
    f = ROOT / "data" / "review" / "run_status.json"
    if not f.exists():
        return ""
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        at = datetime.datetime.fromisoformat(d["at"])
    except (ValueError, OSError, KeyError):
        return ""
    return f"{at.year}年{at.month}月{at.day}日 {at.hour}:{at.minute:02d}"


def run_status_html() -> str:
    """**今回の更新でできなかったことを、一覧の先頭に出す。**

    **飛ばした段は出さない。** `--fetch` を付けなかったことは失敗ではない
    （`run.py` の `save_status`）。**全部通ったときは何も出さない** ──
    毎回「異常はありません」と出すと、本当に出たときに読まれなくなる。
    """
    f = ROOT / "data" / "review" / "run_status.json"
    if not f.exists():
        return ""
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return ""
    miss = [RUN_MISS[k] for k, v in (d.get("steps") or {}).items()
            if v == "failed" and k in RUN_MISS]
    if not miss:
        return ""
    return ('<div class="runmiss"><p><b>今回の更新で、できなかったことがあります。</b>'
            'いつもと違うところをお知らせします。</p><ul>'
            + "".join(f"<li>{m}</li>" for m in miss)
            + '</ul><p class="rm-f">外の状況によることが多いので、'
              '<b>もう一度実行すると直っていることがあります。</b></p></div>')


# ---------------------------------------------------------------- はじめる（初期状態）
def is_fresh() -> bool:
    """**まだ 1 件もお出しできない状態か。**

    お出しできるもの（推薦・お気に入りの新着）が無く、観た記録も無いときは、
    ふだんの一覧を出しても 0 件の枠が並ぶだけである。**そこに「まず何をすれば
    0 件でなくなるのか」が書かれていなかった**（2026-08-24、記録を空にして確かめた）。
    この状態のときだけ、入口を「はじめる」に差し替える。

    **登録しただけでは、まだこちら側に留まる。** 名前を登録しても、公演を取り寄せる
    までは新着が 0 件のままなので、次にやることを出し続ける必要がある。
    """
    try:
        d, _ = _load()
    except Exception:                                               # noqa: BLE001
        return True
    if d.get("recommend") or d.get("favourites") or d.get("tracking"):
        return False
    return not _works()


def _start_state() -> dict:
    """はじめる画面が出す 3 つの段の、いまの状態。"""
    dec = RC.load_declared()
    try:
        d, _ = _load()
        n_cand = int(d.get("n_cand") or 0)
    except Exception:                                               # noqa: BLE001
        n_cand = 0
    return {"dec": dec,
            "n_dec": sum(len(v) for v in dec.values()),
            "n_cand": n_cand,
            # **クレジット付きの候補を取り寄せたかどうかで、2 段目の済みを決める。**
            # カレンダーは毎回落としてくるので、これがあるかどうかでは判定できない
            "fetched": (ROOT / "data" / "review" / "candidates.jsonl").exists(),
            "n_works": len(_works())}


def _step_card(n: int, title: str, done: bool, lead: str, inner: str = "") -> str:
    """はじめる画面の 1 段。**順序があるので番号を出す**（3 つ横並びの札にしない）。"""
    mark = ('<span class="badge part">済んでいます</span>' if done else
            '<span class="badge">これからです</span>')
    return (f'<div class="card start-step{" done" if done else ""}">'
            f'{IC.h2("check" if done else "plus", f"{n} {title}", mark)}'
            f'<p class="lead">{lead}</p>{inner}</div>')


def page_start() -> str:
    """**何も入っていないときの、最初の画面。**

    起案者の指示（2026-08-24）──「その人の好みに合わせたツールなので、そこもまっさらな
    状態じゃなきゃおかしい。データが何もないときの最初の初期画面を作成する必要がある」。

    **「まだ無い」ことを丁寧に説明する画面は、すでに 8 つあった。** 足りなかったのは
    **「まず何をすると 0 件でなくなるのか」**である。そこで、この画面は説明ではなく
    **順序**を出す ── 名前を登録する → 公演を取り寄せる → 観た記録を入れる、の 3 段で、
    それぞれ済んでいるかどうかを添える。

    **1 段目だけで動き始める。** 登録した名前の公演は、観た記録が 1 件も無くても
    無条件でお出しする（企画書 4 章）。**観た記録が要るのは 3 段目の推薦のほうだけ**
    なので、「記録が無いと何も始まらない」と読ませてはいけない。
    """
    s = _start_state()
    kinds = "".join(f'<option value="{E(k)}">{E(k)}</option>' for k in RC.KINDS)
    tags = "".join(
        f'<span class="tag" data-kind="{E(k)}" data-name="{E(n)}">{E(k)}「{E(n)}」'
        f'<button data-fav="remove">✕</button></span>'
        for k in RC.KINDS for n in s["dec"].get(k, []))
    form = (f'<div class="fav-add"><select id="fav-kind">{kinds}</select>'
            f' <input id="fav-name" type="text" placeholder="劇団名・俳優名・作品名・題材"'
            f' size="26">'
            f' <button data-fav="add">{IC.ico("star")}登録する</button>'
            f'<span class="said"></span></div>'
            + (f'<div class="tags">{tags}</div>' if tags else ""))

    step1 = _step_card(
        1, f"見逃したくない名前を登録する（いま {s['n_dec']} 件）", s["n_dec"] > 0,
        "劇団・俳優・演出家・作品・原作者・題材のどれでも登録できます。"
        "<b>登録した名前の公演は、内容を問わず、件数の制限も付けずに出します。</b>"
        "1 件登録するだけで動き始めます。"
        "<br>あとから「おすすめ ▸ お気に入り」で足せますし、外せます。", form)

    step2 = _step_card(
        2, "公演の情報を取り寄せる", s["fetched"],
        (f"手元にこれから観られる公演を {s['n_cand']} 件持っています。"
         "月に 1 回ほど取り直せば十分です。"
         if s["fetched"] else
         "まだ 1 度も取り寄せていません。<b>いったんこの画面を閉じて、次の 1 行を実行して"
         "ください。</b>15 分ほどかかりますが、必要なのは月に 1 回です。"
         '<br><code class="cmd">python3 tools/taguri/run.py --fetch</code><br>'
         "取り寄せが済むと、1 段目で登録した名前に当たる公演が「お気に入り」に出ます。"))

    step3 = _step_card(
        3, f"観た公演を入れる（いま {s['n_works']} 件・任意です）", s["n_works"] > 0,
        "<b>観た記録が 1 件も無いうちは、好みからのおすすめは出ません</b> ── "
        "おすすめは、◎ を付けた公演の作り手から作るためです。"
        "<b>1 段目で登録した名前の公演は、記録が無くても出ます。</b>"
        '<br><a href="/register?t=__TAGURI_TOKEN__">公演情報の登録</a> から、'
        "購入確認メールの取り込みか、手での追加ができます。"
        '観た公演には <a href="/rate?t=__TAGURI_TOKEN__">観た公演の評価</a> で '
        "◎○△× を付けてください。")

    body = f"""{run_status_html()}<h1>はじめに ── 見逃したくない名前を 1 つ登録してください</h1>
<p class="lede">たぐりは、<b>これから観られる公演の中から、見逃したくないものを毎週出す</b>
仕組みです。いまは登録も記録も無いので、出せるものがありません。
<b>下の 3 つのうち、1 つ目だけで動き始めます。</b></p>
{step1}
{step2}
{step3}
<p class="lede">ナビゲーションから、それぞれの画面をいま見ることもできます。
<b>どの画面もまだ 0 件です。</b></p>"""
    return layout("はじめる", "/recommend", body, RR.STYLE + START_CSS)


START_CSS = """
.start-step .badge{margin-left:10px}
.start-step.done{opacity:.72}
.start-step .lead a{color:var(--acc);font-weight:600}
code.cmd{display:inline-block;margin:10px 0 4px;padding:8px 14px;border-radius:8px;
 background:var(--plane);border:1px solid var(--ring);font-size:13px;
 font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--ink);
 user-select:all}
"""


# --------------------------------------------------- おすすめ ▸ 今週のおすすめ
# **絞り込んだ一覧を「出した」と記録する差し込み口。** `tools/taguri/serve.py` が入れる
# （ポスターの差し込み口と同じ形）。**なぜ要るかは `page_recommend` の説明にある。**
RECORD = None


def page_recommend(prefs=()) -> str:
    """答えの画面。**都道府県で絞り込める**（起案者の指示・2026-08-24）。

    ## 絞り込んだ一覧も「出した」と記録する

    **記録しないと、抑制が壊れる。** 反応は stage_id で保存するが、**同じ作品のツアーは
    会場ごとに別の stage_id を持つ**ので、作品単位に畳み直さないと外した公演が別会場として
    戻ってくる（検証 026）。その畳み直しは `presented` に残った題名を使って行うので、
    **提示の記録が無い公演に「興味なし」と答えると、翌週その作品が全国の枠に戻ってくる。**

    そこで、**絞り込んで出した一覧はその場で `presented` に足す**（`bundle='recommend_pref'`）。
    **全国の上位 15 件とは別の束にする** ── 週次の指標（提示 → 興味あり → 購入 → ◎ の連鎖）の
    分母は「その週に全国で出した 15 件」なので、絞り込んで出したぶんを混ぜると分母が動く。
    """
    d, wait = _load()
    n_tr = len(d.get("tracking") or [])
    # **綴りと並びはここで正す。** 選択は URL から来るので、知らない県名は落とす
    prefs = [p for p in RR.PREFS if p in set(prefs or ())]
    rows, n_hit = RR.filtered(d, prefs, RR.TOP)
    if prefs and rows and RECORD:
        RECORD(rows, prefs)
    where = "・".join(prefs) if len(prefs) <= 3 else f"{prefs[0]}ほか {len(prefs) - 1} 県"
    if not prefs and not rows:
        # **出していないものを「出しています」と書かない。** 0 件のときも同じ文を
        # 出していたため、初めて使う人の画面に「その上位をお出ししています」と
        # 書かれていた（2026-08-24 の実測）。**0 件は、次にすることを書く場所である。**
        head = "今週のおすすめはありません"
        # **1 行にまとめる。** ソースを複数行に割ると、生の HTML にも改行文字が
        # そのまま残る ── ふだんは CSS が畳んで表示に出ないが、コピーしたときに
        # 元の割り方どおりの行として出てしまう（起案者の指摘・2026-08-26）
        lede = (f'<p class="pnow">これから観られる公演 {d["n_cand"]} 件のうち、'
                "好みに合いそうだと判断できたものはありませんでした。"
                "おすすめは、観た公演に付けた ◎ から作り手の名簿を作って出しています。"
                '<a href="/rate?t=__TAGURI_TOKEN__">観た公演の評価</a>で ◎ を付けるか、'
                '<a href="/start?t=__TAGURI_TOKEN__">はじめる</a>で見逃したくない名前を'
                "登録してください。登録した名前の公演は、観た記録が無くても出ます。</p>")
        # **お気に入りをこの場に埋め込む案は撤回した（2026-08-29）。** 一度
        # 埋め込んで試したが、起案者の指摘 ──「やっぱりおすすめにはお気に入りを
        # 表示しないで。紛らわしかった」。**「今週のおすすめ」は統計的な判断（◎の
        # 蓄積から）を出す場所で、お気に入りは「無条件で出す」別の性質の一覧である
        # ── 同じ場所に混ぜると、どちらの理由で出ているのかが読み手に分からなくなる。**
        # 案内の文（上の`lede`）から`/recommend/favourites`へのリンクを辿る形に戻す。
    elif not prefs:
        head = f"今週のおすすめ {len(rows)} 件"
        lede = (f'<p class="lede">これから観られる公演 {d["n_cand"]} 件のうち、'
                f'好みに合いそうだと判断できたのは {d["n_scored"]} 件でした。'
                f"上位 {len(rows)} 件を表示しています。"
                "すでに答えた公演は、この一覧から外して下に畳んであります。</p>")
    elif not rows:
        head = f"{where}のおすすめはありません"
        lede = (f'<p class="pnow">これから観られる公演 {d["n_cand"]} 件のうち、'
                f'<b>{E(where)}</b>で観られるものはありませんでした。'
                "ほかの都道府県を選ぶか、全国に戻してください。</p>")
    else:
        # **切り落とした件数を必ず書く。** 15 件で切ったことだけを書くと、一覧が全部だと読まれる
        tail = (f"好みに合いそうな順に、上位 {len(rows)} 件を表示しています"
                f"（残り {n_hit - len(rows)} 件は出していません）。"
                if n_hit > len(rows) else f"{len(rows)} 件すべてを表示しています。")
        head = f"{where}のおすすめ {len(rows)} 件"
        lede = (f'<p class="pnow"><b>{E(where)}</b>で観られる公演のうち、'
                f"好みに合いそうだと判断できたのは {n_hit} 件でした。{tail}</p>")
    # **地図と地方の札を差し込む**（起案者の指示・2026-08-25）。**絞り込みの中身は
    # 変わらない** ── どちらも同じチェックを反転させるだけの押し口である
    pc = RR.pref_counts(d)
    RR.EXTRA = lambda: PM.panel(pc, PM.region_counts(d))
    upd = run_updated_at()
    upd_html = f'<p class="note">この一覧は {E(upd)} に作りました。</p>' if upd else ""
    body = f"""{run_status_html()}<h1>{E(head)}</h1>
{lede}
{upd_html}
<div class="fil2">{RR.pref_form(pc, prefs)}{weight_form(d)}</div>
{RR.cards_html(d, rows)}
<p class="lede">気になった公演の「興味あり」を押すと、
<a href="/recommend/interest?t=__TAGURI_TOKEN__">「興味あり」（いま {n_tr} 件）</a>に移ります。</p>
{IC.h2("flag", "もう追いかけない公演 ── 畳んでいますが、消していません")}
<p class="lede">すでに答えた公演です。上の都道府県の絞り込みは、ここには効きません。</p>
{RR.bundles_html(d, _notes_no())}
{RR.limits_html(d, rows)}"""
    return layout("今週のおすすめ", "/recommend", body, RR.STYLE, active_sub="/recommend")


# ---------------------------------------------------------------- おすすめ ▸ 興味あり
def page_interest(month: str = "", page: int = 1) -> str:
    """**もぎった公演を追いかける画面。** フローの 2 段目である。

    **畳んだ束から画面に出した**（起案者の指示・2026-08-24 でフローを 3 段にしたため）。
    買い忘れを防ぐための一覧なのに `<details>` の中で題名と日程だけの行になっていて、
    **開くまで見えず、開いても値段と発売状況が分からなかった。**

    **順位は付けない。** 上演日の近い順に並べる ── 買うならいちばん近いものから買う。
    """
    d, wait = _load()
    rows = d.get("tracking") or []
    show, mfil, mfoot = RR.month_pick(rows, month, page, "/recommend/interest")
    body = f"""<h1>追いかけている {len(rows)} 件</h1>
<p class="lede">「興味あり」を押した公演を、上演日の近い順に並べています。順位は付けていません。
チケットを取れたら「すでに持っている」を押してください ── 観る予定に移り、
上演日を過ぎると評価待ちに並びます。<br>
「なぜ気になったか」に書いた名前は、
<a href="/recommend/favourites?t=__TAGURI_TOKEN__">お気に入り</a>に追う候補として並びます。</p>
{mfil}
{RR.tracking_html(d, _notes(), show)}
{mfoot}"""
    return layout("興味あり", "/recommend", body, RR.STYLE, active_sub="/recommend/interest")


# ---------------------------------------------------------------- おすすめ ▸ 開幕リマインド
def page_reminder(prefs=(), week: str = "this") -> str:
    """答えていない候補と、券を持っている公演の直近予定。**独立した画面。**（起案者の
    指示・2026-08-25 ──「そのページは独立しておすすめの傘下においてください」）。

    **今週に加えて来週も見られる**（起案者の指示・2026-08-26）。**`week` は URL だけで
    持つ**（月の絞り込み・興味ありの月タブと同じ規約 ── 起動のあいだ覚える必要が無い
    札は素のリンクにする）。都道府県の絞り込み（`srv.prefs`）とは持ち方が違うので別の
    引数にしてある。

    **最初は `/recommend` の冒頭に埋め込んでいた。** 「おすすめ」がすでに唯一の入口だから
    そこに足せば十分だと考えたが、**起案者は独立した画面を求めた。** 埋め込みのままだと、
    916 件（週の候補の全体）の絞り込みフォームの上に毎回この帯が出て、「今週のおすすめ」
    という画面の役目（答えの 15 件を見る）と「まだ答えていないものを知る」という役目が
    1 枚に混ざる。**役目が違えば画面も分ける**という、この仕組みの既定の考え方に合わせた。

    材料の作り方と HTML は `digest.py` に置く。この関数は材料を渡して外枠を着せるだけ
    である（`page_trace` と同じ役割分担）。

    **都道府県で絞り込める**（起案者の指示・2026-08-26 ──「開幕リマインドも選んだ
    都道府県だけに絞って表示して。そもそもこのページに都道府県のフィルタリング機能を
    つけて」）。**`/recommend` と同じ絞り込み（`srv.prefs`）を共有する** ── 別々の
    絞り込みにすると、「おすすめ」で大阪府に絞ったのに「開幕リマインド」では全国が出て
    くることになり、どちらが今の設定なのか読み手に分からなくなる。件数と地図は
    「今週開幕する公演」の中で数える ── `/recommend` の件数（好みに合いそうな候補）とは
    母数が違うので、使い回すと数字が合わなくなる。

    絞り込みが効くのは「今週開幕する公演（全部）」だけで、「直近の観劇予定」には効かせない
    （`digest.panel` の docstring 参照 ── すでに券を持っている予定を、絞り込みのせいで
    見落とすと本末転倒である）。
    """
    d, wait = _load()
    import datetime
    today = datetime.date.today()
    prefs = [p for p in RR.PREFS if p in set(prefs or ())]
    week = week if week in dict(DG.WEEKS) else "this"
    offset = list(dict(DG.WEEKS)).index(week)
    wr = DG.week_rows(d, today, offset=offset)
    pc = RR.pref_counts({"ranked": wr})
    RR.EXTRA = lambda: PM.panel(pc, PM.region_counts({"ranked": wr}))
    note = ('都道府県は<b>いくつでも同時に選べます</b>。選んだ県で開幕する公演を、'
            '<b>順位は付けずに日付が近い順で全部</b>表示します。数字は、その県で'
            f'{dict(DG.WEEKS)[week]}開幕する件数です。<b>選ばなければ全国です。</b>'
            'ツアーで来る公演は、その会場のある県として数えます。<br>'
            '<b>「今週のおすすめ」と同じ絞り込みです</b>'
            '── どちらの画面で選んでも、両方に効きます。')
    body = f"""<h1>開幕リマインド ── 見逃していませんか</h1>
<p class="lede"><b>好みに合うかどうか、すでに答えたかどうかに関わらず、
初日が近い公演を全部出します。</b>まだ「興味あり」も「興味なし」も答えていない公演が、
答える間もなく開幕してしまうのが、見逃しの本当のリスクです。
未回答の行はその場で答えられます。</p>
{RR.pref_form(pc, prefs, action="/recommend/reminder", note=note, hidden={"w": week})}
{DG.panel(d, today, ticket_map(), prefs, week)}"""
    return layout("開幕リマインド", "/recommend", body,
                  RR.STYLE + DG.STYLE, active_sub="/recommend/reminder")


# ---------------------------------------------------------------- おすすめ ▸ お気に入り
def page_favourites(month: str = "", page: int = 1) -> str:
    d, wait = _load()
    favs = d.get("favourites") or []
    show, mfil, mfoot = RR.month_pick(favs, month, page, "/recommend/favourites")
    dec = RC.load_declared()
    kinds = "".join(f'<option value="{E(k)}">{E(k)}</option>' for k in RC.KINDS)
    # **登録済みの札に封蝋を押す。** 押してある名前は「必ず出す」と自分で決めたもので、
    # 解除するまで効き続ける ── **枠の中には名前の頭文字を入れる**（空の蝋を並べると、
    # どの約束の印なのかが分からず、模様になる）
    tags = "".join(
        f'<span class="tag" data-kind="{E(k)}" data-name="{E(n)}">'
        f'<span class="wax" aria-hidden="true">{E(n[:1])}</span>'
        f'<span class="tgn">{E(k)}「{E(n)}」</span>'
        f'<button data-fav="remove">✕</button></span>'
        for k in RC.KINDS for n in dec.get(k, []))
    # ---- 一覧を先に出し、道具は畳んだ 1 行にする -----------------------------
    #
    # 起案者の指摘（2026-08-24）──「『理由から拾った名前』と『登録と解除』が幅をとって
    # いて、肝心のお気に入り一覧にたどりつくのが結構スクロールした後になってしまっている」。
    #
    # **この画面に来る用は「新着を読む」である。** 名前を足す・外すのはときどきの用で、
    # 理由から拾った候補は 0 件のことも多い。**開いた道具 2 つを先に置くと、読みに来た
    # 人が毎週 1 画面ぶんスクロールしてから本題に着く**（登録済み 41 件の札だけで
    # 10 行ある）。
    #
    # **消さずに畳む。** 候補の件数は理由を書いたことへの返りなので（`reasons.py`）、
    # 下に送って気づかれなくすると輪が切れる ── **見出しに件数を出したまま畳めば、
    # 1 行で「3 件ある」と分かる。** 別ページに分ける道は採らない（ときどきの用に
    # ナビゲーションの席を 1 つ使うことになるうえ、候補の返りがさらに遠くなる）。
    #
    # **枠は都道府県の絞り込みと同じ `.pbox`、横並びも同じ `.fil2` を使う。** 同じ
    # 「畳んである道具」に別の見た目を作らない。
    #
    # **新着が 0 件のときだけ、道具を開いて出す。** そのときは読むものが無く、
    # 用があるのは「名前を足す」側である。
    keep = not favs
    tools = (f'<div class="fil2">{_promotions_html(keep)}'
             f'<details class="pbox" id="names"{" open" if keep else ""}>'
             f'<summary>{IC.ico("star")}登録した名前 <b>{sum(len(v) for v in dec.values())} 件</b>'
             f' ── 足す・外す</summary>'
             f'<p class="lead">観た記録に無い名前も登録できます。'
             f'おすすめは ◎ を付けた公演の作り手からしか作れないので、'
             f'まだ観たことのない劇団や、人から聞いただけの名前は、ここから登録してください。'
             f'<b>表記ゆれ（漢字とカタカナ、送り仮名の違いなど）は自動では気づけません。</b>'
             f'ありそうなときは、両方の書き方をそれぞれ登録してください。</p>'
             f'<div class="fav-add"><select id="fav-kind">{kinds}</select>'
             f' <input id="fav-name" type="text" placeholder="団体名・人名・作品名・題材"'
             f' size="26"> <button data-fav="add">登録する</button>'
             f'<span class="said"></span></div>'
             f'<div class="tags">{tags}</div></details>'
             f'{_declined_html()}</div>')
    body = f"""<h1>お気に入り ── 新着 {len(favs)} 件</h1>
<p class="lede">登録した名前の公演を、内容も件数も問わずにすべて出します。順位は付けていません。
件数が多いので、上演月で分けて表示しています。</p>
{tools}
{mfil}
{RR.favourites_html(d, show)}
{mfoot}"""
    return layout("お気に入り", "/recommend", body, RR.STYLE, active_sub="/recommend/favourites")


def _declined_html() -> str:
    """**出さないと決めた語**と、見送った理由から拾った候補（お気に入りの裏返し）。

    起案者の指摘（2026-08-24）──「今なぜ興味ないのかで入力した理由は今後の推薦には
    反映されていますか」。**反映していなかった** ので、返す道をここに作った。

    **お気に入りと同じ画面に置く。** 追う名前と出さない語は表と裏なので、
    **1 か所で見えないと、何を追って何を外しているのかが分からなくなる。**
    枠は登録の札と同じ畳んだ箱（`.pbox`）を使う ── 同じ「畳んである道具」に
    別の見た目を作らない。
    """
    words = RC.load_declined()
    try:
        rows = RE.demotions()
        err = ""
    except Exception as e:                                          # noqa: BLE001
        rows, err = [], f'<p class="empty">見送った理由を読むところで失敗しました（{E(e)}）。</p>'
    tags = "".join(
        f'<span class="tag" data-word="{E(w)}">「{E(w)}」'
        f'<button data-dec="remove">✕</button></span>' for w in words)
    cand = "".join(
        f'<div class="prom"><span class="k">出さない</span>'
        f'<span class="w">{E(r["word"])}</span>'
        f'<span class="src">これから観られる公演 {r["hits"]} 件に当たります'
        + (f'・{r["n"]} 回書かれました' if r["n"] > 1 else "") + "</span>"
        f'<button data-dec="add" data-word="{E(r["word"])}">出さない</button>'
        f'<span class="said"></span>'
        f'<span class="q">「{E(r["notes"][0][:80])}」'
        + (f' ── {E(r["titles"][0][:30])}' if r["titles"] else "") + "</span></div>"
        for r in rows[:12])
    head = (f'出さない語 <b>{len(words)} 語</b>'
            + (f' ── 候補が {len(rows)} 語あります' if rows else ""))
    return f"""<details class="pbox" id="declined">
<summary>{IC.ico("flag")}{head}</summary>
<p class="lead">ここに入れた語が題名・団体・劇場・出演者・題材のどれかに出てくる公演は、
おすすめに出しません。消してはいないので、語を外せば戻ります。
お気に入りに登録した名前の公演は、この語に当たっても外れません。
<b>ただし「主催」で登録した名前だけで出てきた公演は例外で、この語に当たれば外れます</b>
（劇場が自主で組む公演を丸ごと拾う登録なので、団体・人・作品・原作者のような
狭い登録とは扱いが違います）。</p>
{tags if words else '<p class="empty">まだ 1 つも外していません。</p>'}
<div class="fav-add"><input id="dec-word" type="text"
  placeholder="出さない語（例: バレエ）" size="22">
 <button data-dec="add">出さない</button><span class="said"></span></div>
<p class="lead">「興味なし」に添えた理由の文から拾った語のうち、これから観られる公演に
実際に当たるものです。数字は当たる件数です。0 件の語と、「舞台」「公演」のような広い語は
出していません。押すと、その語を出さない語に加えます。</p>
{err}{cand if rows else '<p class="empty">まだ候補はありません。「興味なし」を押したあとに出てくる欄へ理由を書くと、その文から拾った語がここに並びます。</p>'}
</details>"""


def _promotions_html(open_: bool = False) -> str:
    """**理由の文から拾った名前を、登録の候補として出す。**

    理由欄が成立する条件はここにある ── **書いた内容が本人に返る。** 名簿（推定）は
    「◎ を付けた公演の作り手」しか材料に持てないので、**外で知った名前は理由の文でしか
    系に入らない。** 実測でも、決め手になった名前 9 件のうち 2 件は履歴に 1 度も
    出てこない名前だった。
    """
    try:
        rows = RE.promotions()
    except Exception as e:                                          # noqa: BLE001
        # **失敗も畳んだ枠の中で言う。** 枠を変えると、この画面の道具が 1 つ
        # 増えたように見える
        return (f'<details class="pbox" id="promos"><summary>{IC.ico("user")}'
                f'理由から拾った名前 <b>読み取れませんでした</b></summary>'
                f'<p class="lead">理由の文を読むところで失敗しました（{E(e)}）。'
                f'登録した名前と新着の一覧には影響しません。</p></details>')
    st = RE.stats()
    if not rows:
        return f"""<details class="pbox" id="promos"{" open" if open_ else ""}>
<summary>{IC.ico("user")}理由から拾った名前 <b>まだありません</b></summary>
<p class="lead">理由を書いたのは {st["理由が書かれた反応"]} 件です。
<b>「興味あり」を押したあとに出てくる欄に理由を書くと、その文に出てきた人・団体・題材・
作品が、ここに登録の候補として並びます。</b>日程や値段が理由のときは、名前が出てこないので
候補は増えません。</p></details>"""
    body = "".join(
        f'<div class="prom"><span class="k">{E(r["kind"])}</span>'
        f'<span class="w">{E(r["word"])}</span>'
        f'<span class="src">{E(r["source"])}'
        + (f'・{r["n"]} 回書かれた' if r["n"] > 1 else "") + "</span>"
        f'<button data-fav="promote" data-kind="{E(r["kind"])}" data-name="{E(r["word"])}">'
        f'これは追う</button><span class="said"></span>'
        f'<span class="q">「{E(r["notes"][0][:80])}」'
        + (f' ── {E(r["titles"][0][:30])}' if r["titles"] else "") + "</span></div>"
        for r in rows[:20])
    return f"""<details class="pbox" id="promos"{" open" if open_ else ""}>
<summary>{IC.ico("user")}理由から拾った名前 <b>{len(rows)} 件</b> ── 追いますか？</summary>
<p class="lead">「興味あり」に添えた理由の文に出てきた言葉のうち、まだ登録していないものです。
押すとお気に入りに入り、その場でその名前の公演を取りに行きます ──
以後、その名前の公演は件数の制限なしに新着へ出ます。
文字がそのまま一致したものだけを拾っているので、姓だけ・愛称・略称は出てきません。</p>
{body}</details>"""


# ---------------------------------------------------------------- 公演情報の登録
def _works() -> list[dict]:
    """観た作品の全件。**購入の記録から組み直して、保存済みの評価を重ねる。**

    `works` の表だけを読むと、**評価を付けたことのある作品しか出てこない**（96 行に対し
    購入から導ける作品は 111 以上ある）── 取り込んだばかりの公演が画面に出ないことになり、
    「取り込む → 評価する」の輪が閉じない。**表は評価の置き場所で、作品の一覧ではない。**
    """
    import rate_performances as R
    purchases = R.load_purchases()
    con = R.connect()
    try:
        excluded = R.read_excluded(con)
        merges = R.read_merges(con)
        works = R.load_works(purchases, R.read_splits(con), excluded, merges)
        saved = R.read_works(con)
        # **行かなかった回を読む。** この表は前の画面（`rate_performances.py`）が書いた
        # もので、実データに 23 回ぶん入っていた。**この画面がそれを読んでいなかったため、
        # 本人が「行かなかった」と答えた 7 件が評価待ちに戻っていた** ── 一度答えたことを
        # 聞き直す画面になっていた。**答えの置き場所は 1 つで、読む側が全部それを見る。**
        attended = R.read_attendance(con)
        # **手で入れた出演者とポスターを、記録ごとに載せる。** 直す欄がこれを読んで
        # 「いま何が入っているか」を出す（`_edit_html`）── 入れたものが画面に
        # 出ないなら、入れたのか消えたのかが本人に分からない
        hand = R.read_hand(con)
    finally:
        con.close()
    # **いま公演ページの材料が取れているかを、記録ごとに持つ。** 結び付ける欄の文言を
    # `stage_id` の有無だけで決めると、**メールから引けている 54 件にも「結び付いて
    # いません」と出る** ── 直す必要の無いものを直せと促すことになる
    have_cr, by_uid = set(), {r["uid"]: r for r in purchases}
    cr = ROOT / "data" / "credits" / "credits.jsonl"
    if cr.exists():
        keys = set()
        for line in cr.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                c = json.loads(line)
                if c.get("fields"):
                    keys.add((c.get("date"), c.get("mail_title")))
        for w in works:
            for sh in w.get("shows") or []:
                pr = by_uid.get(sh["uid"]) or {}
                if (pr.get("date"), pr.get("title")) in keys:
                    have_cr.add(w["work_key"])
                    break
    # **自動で結び付けた分に印を付ける。** 機械が題名から探して結び付けたものは、
    # **本人が確かめていない** ── 間違っていれば観ていない公演の作り手が名簿に入るので、
    # 画面に「自動で結び付けました」と書いて、外せることを示す
    auto: dict = {}
    lk = ROOT / "data" / "credits" / "linked.jsonl"
    if lk.exists():
        for line in lk.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                r = json.loads(line)
                if r.get("matched") and r.get("auto"):
                    auto[r["work_key"]] = str(r.get("stage_id") or "")
    out, seen = [], set()
    for w in works:
        sv = saved.get(w["work_key"]) or {}
        seen.add(w["work_key"])
        _shows = w.get("shows") or []
        for _s in _shows:
            _s["attended"] = bool(attended.get(f"{_s['uid']}|{w['work_key']}", 1))
        _gone = [s for s in _shows if not s["attended"]]
        # **回が 1 つも残らないときだけ「観ていない」とする。** 3 回のうち 1 回を落とした
        # のは観た公演であって、減るのは回数だけである（セット券で片方だけ席を立った場合も
        # ここに当たる ── `attendance` は作品ごと・回ごとに持っている）
        _unseen = bool(_shows) and len(_gone) == len(_shows)
        _times = (len(_shows) - len(_gone)) if _shows else (w.get("times") or 1)
        out.append({"work_key": w["work_key"], "title": w["title_display"],
                    "first_date": w.get("first_date") or "", "last_date": w.get("last_date") or "",
                    "times": max(_times, 1), "bucket": w.get("bucket") or "",
                    # **観ていない記録は、観た記録と同じ数え方をしない**（下の `page_records`
                    # は図と件数から外し、`run.py` の評価待ちは並べない）
                    "unseen": _unseen, "skipped": len(_gone),
                    "verdict": sv.get("verdict") or "",
                    "note_impression": sv.get("note_impression") or "",
                    "stage_id": sv.get("stage_id") or "",
                    "auto_linked": bool(sv.get("stage_id")
                                        and auto.get(w["work_key"]) == sv.get("stage_id")),
                    "has_credits": w["work_key"] in have_cr,
                    # 直す画面が要る分。**どのメールから来た値かを出さないと直せない**
                    "suspect": bool(w.get("suspect")),
                    "merged": w.get("merged") or [],
                    "hand": hand.get(w["work_key"]) or {},
                    "shows": _shows})
    # **手で足した記録は購入から導けない。** 落とすと、招待や当日券で観た分が消える
    #
    # **外した分とまとめた分は、ここでも落とす。** メールから導ける記録は
    # `load_works` が外すが、手で足した記録はその流れに乗らない ── 片方だけが効くと、
    # 「取り消したのに残っている」「まとめたのに 2 件出る」ことになる
    dropped = {u[5:] for u, _p in excluded if u.startswith("work:")}
    into: dict[str, list] = {}
    for k, sv in saved.items():
        if k in seen or k in dropped:
            continue
        if k in merges:
            into.setdefault(merges[k], []).append(
                {"work_key": k, "title": sv.get("title") or ""})
            continue
        out.append({"work_key": k, "title": sv.get("title") or "", "bucket": "manual",
                    "first_date": sv.get("first_date") or "", "last_date": sv.get("last_date") or "",
                    "times": sv.get("times") or 1, "verdict": sv.get("verdict") or "",
                    "note_impression": sv.get("note_impression") or "",
                    # **手で足すときに入力した会場。** 以前は感想の欄に入れられていて
                    # どこからも読まれていなかった（`rate_performances._add_venue`）。
                    # **本人が入力した事実は、読まれる場所に出す**
                    "venue": sv.get("venue") or "",
                    # **開演時刻も同じ列に持つ**（`rate_performances._add_time`）
                    "time": sv.get("time") or "",
                    "stage_id": sv.get("stage_id") or "",
                    "auto_linked": bool(sv.get("stage_id")
                                        and auto.get(k) == sv.get("stage_id")),
                    "has_credits": False,
                    # **回を持たないので `attendance` には書けない。** 手で足した記録が
                    # 間違いだったときに外す口は「この記録を取り消す」のほうである
                    "unseen": False, "skipped": 0,
                    "suspect": False, "merged": [], "hand": hand.get(k) or {},
                    "shows": []})
    for w in out:
        if w["work_key"] in into:
            w["merged"] = list(w["merged"]) + into[w["work_key"]]
    out.sort(key=lambda w: w["last_date"] or "0000", reverse=True)
    return out


# ---------------------------------------------------------------- すでにある情報から選ぶ
#
# **手で足す欄は、白紙から書かせる場所ではない。** 起案者の指示（2026-08-24）──
# 「手で追加した公演が、すでにある情報なら候補として表示するようにしてほしい」。
#
# **同じ公演の情報が、すでに 3 か所にある。**
#
# | どこ | 何が入っているか | 何の役に立つか |
# |---|---|---|
# | 自分の記録 | 観た作品（メールから導けるもの＋手で足したもの） | **二重に足すのを防ぐ** |
# | 候補（`candidates.jsonl`） | これから／最近の公演 818 件。題名・団体・劇場・都道府県・日程 | 劇場と日程が**そのまま入る** |
# | 公演ページの控え（`credits.jsonl`） | 過去に観た公演と公演ページの結び付き | 過去の分でも id が付く |
#
# **外へは取りに行かない**（企画書 5 章の守り 5）。手元にあるものだけを出すので、
# **古い公演は候補に出ない** ── 出ないことは画面に書く。
def _suggest_pool() -> list[dict]:
    """候補の母集団を組む。**題名で引けるように、正規化した鍵を添えておく。**"""
    import rate_performances as R
    rows: list[dict] = []
    for w in _works():
        rows.append({"kind": "record", "key": w["work_key"], "title": w["title"],
                     "date": w.get("first_date") or "", "venue": "",
                     "note": ("評価 " + w["verdict"] if w.get("verdict") else "評価はまだです"),
                     "times": w.get("times") or 1, "stage_id": w.get("stage_id") or ""})
    cand = ROOT / "data" / "review" / "candidates.jsonl"
    if cand.exists():
        for line in cand.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            c = json.loads(line)
            days = RR._start(c.get("period") or "")
            one = RR.short_period(c.get("period") or "")
            rows.append({"kind": "stage", "src": 0,
                         "key": str(c.get("stage_id") or ""),
                         "title": c.get("title") or "",
                         # **日程は 1 日公演のときだけ入れる。** 期間のある公演で初日を
                         # 勝手に入れると、観ていない日が記録に残る
                         "date": days if "〜" not in one else "",
                         "venue": c.get("theater") or "",
                         "note": f'{c.get("group") or ""}／{one}（{c.get("pref") or ""}）',
                         "group": c.get("group") or "",
                         "times": 1, "stage_id": str(c.get("stage_id") or "")})
    lk = ROOT / "data" / "credits" / "linked.jsonl"
    if lk.exists():
        for line in lk.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            c = json.loads(line)
            if not c.get("matched"):
                continue
            rows.append({"kind": "stage", "src": 1,
                         "key": str(c["stage_id"]),
                         "title": c.get("page_title") or c.get("title") or "",
                         "date": c.get("date") or "",
                         "venue": (c.get("fields") or {}).get("劇場", ""),
                         "note": f'題名から探し直した公演／{c.get("period") or ""}',
                         "group": "",
                         "times": 1, "stage_id": str(c["stage_id"])})
    cr = ROOT / "data" / "credits" / "credits.jsonl"
    if cr.exists():
        for line in cr.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            c = json.loads(line)
            # **公演ページに当たらなかった控えは候補にしない。** 155 行のうち 25 行は
            # 検索が当たっておらず id を持たない ── 選んでも結び付く先が無い
            if not c.get("stage_id"):
                continue
            rows.append({"kind": "stage", "src": 2,
                         "key": str(c.get("stage_id") or ""),
                         "title": c.get("mail_title") or "",
                         "date": c.get("date") or "",
                         "venue": (c.get("fields") or {}).get("劇場", ""),
                         "note": ("過去の公演ページ"
                                  + (f'（{c["match_level"]}）' if c.get("match_level") else "")
                                  + f'／{c.get("period") or ""}'),
                         "group": "",
                         "times": 1, "stage_id": str(c.get("stage_id") or "")})
    for r in rows:
        r["k"] = R.title_key(r["title"])
    return _merge_by_stage([r for r in rows if r["k"]])


def _merge_by_stage(rows: list[dict]) -> list[dict]:
    """**同じ公演の行を 1 つに畳む。** 1 行 = 1 公演にする。

    起案者の指摘（2026-08-24）──「推薦に使う公演、を押すと候補が何個も出てくるのなんで？
    公演自体の詳細は作品ごとに１つずつもっていて、それを親データとし、複数観にいったものは
    子ノードして結びつける形式をとれば、複数同じ候補が何個も出てくるのを防げる？」

    ## 指摘のとおりだった

    **`credits.jsonl` は「観に行った回」ごとに 1 行を持っている**（鍵は 観劇日 と メールの
    件名）。**同じ公演を 3 回観れば、同じ `stage_id` の行が 3 本ある。** 候補はその行を
    そのまま並べていたので、**1 つの公演が 3 回出てきた。** 実測では 29 公演がのべ 90 行に
    なっていた（本来は 29 行）。

    **親を `stage_id` にして畳む。** ファイルの持ち方（回ごと）は変えない ── 記録の側は
    観劇日で引くので、そこを作り替えると評価と感想の置き場所が動く。**読む側で親に
    まとめれば、同じ結果が migration なしで得られる。**

    ## 題名は全部を検索の鍵として残す

    畳むと題名が 1 つになるが、**出どころによって書き方が違う**（「受取人不明」と
    「ｕｎｒａｔｏ＃１３ 『受取人不明 ＡＤＤＲＥＳＳ ＵＮＫＮＯＷＮ』」）。1 つだけ残すと
    **もう一方の書き方で打った人が引けなくなる**ので、鍵は全部持つ（`ks`）。

    ## 日付は、全部が同じときだけ残す

    畳んだ行の日付は「観に行った回」なので、3 回ぶんあれば 3 通りある。**勝手に 1 つを選ぶと、
    観ていない日が記録に入る**（期間のある公演で初日を入れない、と同じ理由）。

    **同じ作品の別の上演は畳まない。** ツアーの別会場は `stage_id` が違い、**出演者も
    座組も違う。** 畳むと、観ていない会場の作り手が名簿に入る ── どの上演だったかは
    本人しか知らないので、選ぶ手がかり（劇場・日程）を出したまま並べる。
    """
    out: list[dict] = []
    at: dict[str, dict] = {}
    for r in rows:
        sid = r.get("stage_id") or ""
        if not sid or r["kind"] != "stage":
            out.append(dict(r, ks=[r["k"]]))
            continue
        cur = at.get(sid)
        if cur is None:
            cur = dict(r, ks=[r["k"]], _dates={r["date"]} if r["date"] else set())
            at[sid] = cur
            out.append(cur)
            continue
        if r["k"] not in cur["ks"]:
            cur["ks"].append(r["k"])
        if r["date"]:
            cur["_dates"].add(r["date"])
        # **出どころの順に、詳しいほうを採る**（一覧 → 題名から探し直した分 → 過去の控え）。
        # 一覧の行は団体・都道府県・期間を持っているので、選ぶ手がかりがいちばん多い
        if r.get("src", 9) < cur.get("src", 9):
            for f in ("title", "k", "note", "src"):
                cur[f] = r[f]
        if not cur["venue"] and r["venue"]:
            cur["venue"] = r["venue"]
        if not cur.get("group") and r.get("group"):
            cur["group"] = r["group"]
    for r in out:
        ds = r.pop("_dates", None)
        if ds is not None:
            r["date"] = next(iter(ds)) if len(ds) == 1 else ""
    return out


def search_web(q: str) -> dict:
    """**押されたときだけ、外の公演情報から探す。**（`tools/taguri/stage_search.py`）

    起案者の指示（2026-08-24）──「『手で足す』のところに『るつぼ』って入れても候補が
    出てこないのなら『検索』のボタンをおして、その場で情報を拾ってきて登録できるように
    してほしい」。

    **`suggest` とは別の口である。** `suggest` は打っている最中に走る読み口なので手元しか
    見ない。こちらは押されたときだけ走るので外へ行く ── **同じ口にまとめると、打つたびに
    外へ行くことになる。**

    探し方は更新の段と同じものを使う（`link_works.search_stages`）。**探し方を 2 通り
    作らない** ── 同じ題名で画面と更新の段の結果が違うと、どちらが正しいのか確かめようが
    ない。**当てるのは題名だけで、選ぶのは本人である**（この欄では観劇日がまだ無いので、
    日付で同名の別公演を落とせない）。
    """
    import stage_search as SS
    return SS.search(q)


def work_group(r: dict) -> str:
    """**作品の鍵。** 同じ作品の別会場を 1 つにまとめ、**別の作品は混ぜない。**

    起案者のイメージ（2026-08-24）──「作品ページは親として必ず一個でその下に各地方ごとの
    子ノード、さらにその下に観にいった情報の子ノード（複数回行ってれば複数個持つ）を持つ
    ような木構造」。

    ## 作品の親は、取得元が持っていない

    CoRich は**会場ごとの上演に 1 ページ**を割り当てており、**作品そのものの id が無い。**
    だから親は自分で組む必要がある。「地方が変わると公演ページが変わる」のは、そういう
    作りだからである。

    ## 題名だけでは足りない

    題名の鍵だけで畳むと、**別の団体が同じ戯曲を上演したものが 1 つの作品になる**
    （実データで「ハムレット」── 能登演劇堂のイエローヘルメッツ公演と KARAS APPARATUS の
    公演が畳まれた）。**畳むと、観ていない公演の作り手が名簿に入る。**

    **団体が分かっていて違うなら、別の作品として分ける。** 団体が分からない行
    （過去の公演ページから来た分は団体の欄を持たない）は、**それ自体を 1 つの作品として
    置く** ── 分からないものを勝手に寄せない。**間違うなら、分ける側に間違える。**
    """
    g = R_NORM(r.get("group") or "")
    return f'{r["k"]}|{g}' if g else f'{r["k"]}|@{r.get("stage_id") or r.get("key") or ""}'


def suggest(q: str, limit: int = 8) -> dict:
    """入力中の題名に当たる「すでにある情報」を返す。

    **前方一致を先に出す。** 打ちかけの文字に対して、途中に含むだけのものを先に出すと、
    打つほど順番が入れ替わって選べない。**自分の記録は同点なら先に出す** ──
    二重に足すのを防ぐのが、この欄のいちばん大事な役目である。
    """
    import rate_performances as R
    k = R.title_key(q or "")
    if len(k) < 2:
        return {"q": q, "rows": []}
    seen, out = set(), []
    for r in _suggest_pool():
        # **畳んだ行は題名を複数持つ。** 出どころによって書き方が違うので、
        # 1 つだけで照合すると、もう一方の書き方で打った人が引けなくなる
        best = None
        for rk in r.get("ks") or [r["k"]]:
            if k == rk:
                sc = 0
            elif rk.startswith(k):
                sc = 1
            elif k in rk:
                sc = 2
            elif rk in k and len(rk) >= 4:
                sc = 3
            else:
                continue
            if best is None or (sc, len(rk)) < best:
                best = (sc, len(rk))
        if best is None:
            continue
        score = best[0]
        dedup = (r["kind"], r["key"], r["title"], r["date"])
        if dedup in seen:
            continue
        seen.add(dedup)
        out.append(dict(r, _s=(score, 0 if r["kind"] == "record" else 1, best[1])))
    out.sort(key=lambda r: r["_s"])
    # **打ち切りは作品の単位で数える**（起案者の指摘・2026-08-24）。行で切ると、
    # **14 会場を回るツアーが 1 作品で枠を使い切る**（「名探偵プリキュア!ドリームステージ♪」は
    # 実データで 14 会場ある）。**同じ作品の会場は、1 件と数える。**
    kept, groups = [], set()
    for r in out:
        g = (r["kind"], work_group(r))
        if g not in groups and len(groups) >= limit:
            continue
        groups.add(g)
        kept.append(r)
        if len(kept) >= limit * 8:
            break
    out = kept
    # **ポスターは端末内にあるものだけ載せる。** 打っている最中に走る読み口なので、
    # ここから外へ取りに行かない（企画書 5 章の守り 5）── 1 文字打つたびに外部へ
    # 要求が出ることになる。**取り込みは更新の段で行う**（`tools/taguri/posters.py`）
    have = PO.have()
    # **観に行った回の数を、上演ごとに添える**（木の 3 段目）。すでに記録がある上演は、
    # **選ぶときのいちばん強い手がかり**である ── 自分が行ったのはこれだ、と分かる
    mine: dict = {}
    for r in _suggest_pool():
        if r["kind"] == "record" and r.get("stage_id"):
            mine[str(r["stage_id"])] = mine.get(str(r["stage_id"]), 0) + (r.get("times") or 1)
    return {"q": q, "rows": [dict({x: r[x] for x in
                                   ("kind", "key", "title", "date", "venue", "note",
                                    "times", "stage_id")},
                                  wk=work_group(r),
                                  mine=mine.get(str(r.get("stage_id") or ""), 0),
                                  poster=have.get(str(r.get("stage_id") or ""), ""))
                             for r in out]}


# ---------------------------------------------------------------- 同じ公演かを確かめる
def similar_works(title: str, exclude_key: str = "", limit: int = 5) -> list[dict]:
    """題名が近い記録を返す。**判定はしない。同じかどうかを知っているのは本人だけである。**

    起案者の指示（2026-08-24）──「タイトルをユーザーが編集したときに、同じタイトルとか
    名前が近いものは『これと同じ公演ですか？（公演詳細を統合しますか？）』って確認してほしい」。

    **自動では束ねない。** 鍵が一致するか一方が他方を含むものは `_merge_contained` が
    すでに自動で束ねている。ここで拾うのは**そこに当たらなかった近いもの**なので、
    機械が決めると別の公演を 1 つにしてしまう ── 同じ戯曲の別の上演（「ハムレット」が
    年に何本もある）は題名が完全に一致するが、別の公演である。**必ず聞く。**
    """
    import difflib
    import rate_performances as R
    k = R.title_key(title or "")
    if len(k) < 2:
        return []
    out = []
    for w in _works():
        if w["work_key"] == exclude_key:
            continue
        wk = R.title_key(w["title"])
        if not wk:
            continue
        if wk == k:
            score = 1.0
        elif (wk in k or k in wk) and min(len(wk), len(k)) >= 4:
            score = 0.9
        else:
            score = difflib.SequenceMatcher(None, k, wk).ratio()
            if score < 0.72:
                continue
        out.append({"work_key": w["work_key"], "title": w["title"],
                    "first_date": w.get("first_date") or "",
                    "last_date": w.get("last_date") or "",
                    "times": w.get("times") or 1, "verdict": w.get("verdict") or "",
                    "mails": len(w.get("shows") or []), "score": round(score, 3)})
    out.sort(key=lambda r: -r["score"])
    return out[:limit]


def merge_works(work_key: str, other_key: str) -> dict:
    """2 つの記録を 1 つの公演にまとめる。

    ## 残すほうは機械が決める

    **メールの回を持っているほうを残す。** 両方が持つ／どちらも持たないときは、
    **上演日が早いほう**を残す。**本人に選ばせない** ── どちらを残すかは記録の作りの話で、
    本人が知っている事実（同じ公演かどうか）ではない。**聞くべきことだけを聞く。**

    ## 評価と感想は宙に浮かせない

    残るほうの欄が空なら移す。**両方に入っていたら、残るほうを優先して消さない**
    （消える側の行も `works` に残るので、取り消せば戻る）。
    """
    import rate_performances as R
    ws = {w["work_key"]: w for w in _works()}
    a, b = ws.get(work_key), ws.get(other_key)
    if not a or not b:
        raise ValueError("その記録は見つからない")
    if work_key == other_key:
        raise ValueError("同じ記録どうしはまとめられない")
    ma, mb = len(a.get("shows") or []), len(b.get("shows") or [])
    if ma != mb:
        keep, drop = (a, b) if ma > mb else (b, a)
    else:
        keep, drop = ((a, b) if (a.get("first_date") or "9999")
                      <= (b.get("first_date") or "9999") else (b, a))
    con = R.connect()
    try:
        R.save_merge(con, drop["work_key"], keep["work_key"])
        saved = R.read_works(con)
        kv, dv = saved.get(keep["work_key"]) or {}, saved.get(drop["work_key"]) or {}
        moved = []
        if not (kv.get("verdict") or "") and (dv.get("verdict") or ""):
            moved.append("評価")
        if not (kv.get("note_impression") or "").strip() \
                and (dv.get("note_impression") or "").strip():
            moved.append("感想")
        if moved:
            con.execute(
                "INSERT INTO works (work_key, title, first_date, last_date, times,"
                " verdict, chosen, note_impression, note_motive, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,'',datetime('now','localtime'))"
                " ON CONFLICT(work_key) DO UPDATE SET verdict=COALESCE(works.verdict,"
                " excluded.verdict), note_impression=CASE WHEN trim(works.note_impression)=''"
                " THEN excluded.note_impression ELSE works.note_impression END,"
                " updated_at=excluded.updated_at",
                (keep["work_key"], keep["title"], keep.get("first_date") or "",
                 keep.get("last_date") or "", keep.get("times") or 1,
                 dv.get("verdict"), kv.get("chosen"), dv.get("note_impression") or ""))
            con.commit()
        # **手で入れた出演者・ポスターも宙に浮かせない。** 評価・感想と同じ規則で、
        # 残るほうの欄が空なら消えるほうから移す（起案者の指示・2026-08-26 ──
        # まとめる前にすでに手で入れてあった分を、入れ直させない）。**消えるほうの
        # `hand_credits` の行はそのまま残す** ── 取り消せば戻るのは評価・感想と同じ
        hand = R.read_hand(con)
        kh, dh = hand.get(keep["work_key"]) or {}, hand.get(drop["work_key"]) or {}
        take_fields = (not hand_credit_count(kh.get("fields") or {})
                       and hand_credit_count(dh.get("fields") or {}))
        take_poster = not (kh.get("poster") or "") and bool(dh.get("poster") or "")
        if take_fields:
            moved.append("手で入れた出演者")
        if take_poster:
            moved.append("手で入れたポスター")
        if take_fields or take_poster:
            R.save_hand(con, keep["work_key"],
                        fields=(dh.get("fields") or {}) if take_fields else None,
                        poster=(dh.get("poster") or "") if take_poster else None)
    finally:
        con.close()
    return {"ok": True, "kept": keep["work_key"], "kept_title": keep["title"],
            "dropped": drop["work_key"], "dropped_title": drop["title"], "moved": moved}


def unmerge_work(work_key: str) -> dict:
    """この記録にまとめた分を、全部もとに戻す。**戻せなければ誤操作が取り返せない。**"""
    import rate_performances as R
    con = R.connect()
    try:
        n = R.delete_merges(con, into_key=work_key)
    finally:
        con.close()
    return {"ok": True, "n": n}


# ------------------------------------------- 公演ページが無い公演を、手で埋める
#
# 起案者の指示（2026-08-24）──「公演ページが無い公演のために、ポスターと出演者を手で
# 入れられるようにする」。
#
# **なぜ要るのか。** 出演者もポスターも公演ページからしか来ない作りだったので、
# **ページが無い公演では取りようが無かった。** 実測 ── 材料の無い記録は 48 件あり、
# そのうち 15 件を外の公演情報から探して当たったのは 6 件だった。残りは題名に販売側の
# 冠が付いているもの（直せる）と、**「ナディラ」のようにページ自体が無いもの**である。
# 後者は本人しか知らない。
#
# **手で入れた分は、公演ページの分に足す**（置き換えない）。ページから取れている分を
# 消す理由は無い ── 消したいときは「結び付けを外す」のほうである。

# 手で入れられる欄。**公演ページの欄と同じ名前にする**（`measure_nets.parse_credits` が
# そのまま読める）。**スタッフだけは自由記述である** ── 役職の数は決まっておらず、
# 選択肢にすると入れられない役職が出る（実データのスタッフ欄は 40 種以上の役職を持つ）。
HAND_FIELDS = (
    ("出演", "出演者", "1 行に 1 名でも、読点や中黒で区切っても構いません"),
    ("演出", "演出", ""),
    ("脚本", "脚本・原作・翻訳", ""),
    ("スタッフ", "そのほかの作り手", "「美術：〇〇」のように役職を添えると、"
     "役職ごとに数えられます。役職が分からないものは名前だけで構いません"),
)

# **画像は端末内に写して、名前もこちらで決める。** 選んだファイルの名前をそのまま使うと、
# 同じ名前の別の絵が上書きし合う（`poster.jpg` は誰の端末にもある）。
HAND_IMG_MAX = 12 * 1024 * 1024
HAND_IMG_KINDS = {b"\xff\xd8\xff": ".jpg", b"\x89PNG": ".png",
                  b"RIFF": ".webp", b"GIF8": ".gif"}


def hand_credit_count(fields: dict) -> int:
    """手で入れた欄から、名簿に入る**人数**を数える。

    **入れた結果を数で返す。** 打った文字が何人として読まれたのかは、区切り方によって
    変わる（読点・中黒・改行）── **本人が確かめられないと、打ち方が合っているのか
    分からない。** 数え方は名簿を作る処理と同じものを使う。

    **数えるのは人であって、(役職, 人) の組ではない。** `measure_nets.parse_credits` が
    返すのは役職ごとの組なので、演出と脚本を兼ねる 1 人は 2 組になる ── そのまま数えると
    「4 名入れたのに 5 名と出る」ことになる（起案者の報告・2026-08-26 の裏で見つけた別の
    数え違い。本題は演出・脚本欄の【】タグで名前ごと消えていたことだったが、それを直すと
    次にここが顔を出す）。**「◯名を入れてあります」は人数の約束で読まれる**ので、
    2 つめの要素（人名）だけを数える。
    """
    if not fields:
        return 0
    try:
        import measure_nets as MN
        return len({person for _role, person in MN.parse_credits(fields)})
    except Exception:                                               # noqa: BLE001
        return 0


def save_hand_credits(work_key: str, fields: dict) -> dict:
    """手で入れた出演者・作り手を書く。**空にした欄は消す。**"""
    import rate_performances as R
    keep = {k: str(fields.get(k) or "").strip()[:4000]
            for k, _l, _h in HAND_FIELDS if str(fields.get(k) or "").strip()}
    con = R.connect()
    try:
        R.save_hand(con, work_key, fields=keep)
    finally:
        con.close()
    n = hand_credit_count(keep)
    return {"ok": True, "n": n, "fields": keep,
            "said": (f"{n} 名を名簿に入れました" if n else
                     "手で入れた出演者を消しました")}


def _card_by_stage(sid: str) -> dict:
    """保存された一覧から 1 枚を引く。**無ければ最小限の枠を作る**（一覧から外れた公演）。"""
    d, _ = _load()
    for rows in d.values():
        if not isinstance(rows, list):
            continue
        for c in rows:
            if isinstance(c, dict) and str(c.get("stage_id") or "") == sid:
                return c
    return {"stage_id": sid, "title": "", "synopsis": "", "themes": []}


def save_hand_theme(stage_id: str, *, words: str = "", synopsis: str = "",
                    url: str = "", fields: dict | None = None) -> dict:
    """**公演ページから内容を読み取れなかった公演に、本人が内容を入れる。**

    起案者の問い（2026-08-25）──「『あらすじを取れませんでした』の作品を
    自分で追加することはできる？」。[検証 048](../../docs/verification/048-empty-and-cap.md) で、
    **取れなかった 344 件の 45% は本文がどこにも書かれていない**と分かった ──
    抽出をどう直しても埋まらないので、**残る道は本人が入れることである。**

    **区切りは読点でも空白でもよい。** 打ち方を 1 通りに強いる理由が無い。

    ## 出演者・作り手も、ここから入れられる（2026-08-26）

    起案者の指摘 ──「corich とかにもちゃんと出演者情報が載ってるのに拾うのに
    失敗している」。公演ページの抽出は役職ごとに 1 行しか拾えない書式があり、
    複数名いても最初の 1 名しか拾えないことがあった（実測）。出演者・作り手は
    `hand_credits`（日記帳の「手で入れる」）と同じ規則で**足す** ── 取れている
    役職でも全員は取れていないことがあるので、抽出を消さずに補う。
    """
    import hand_themes as HT
    sid = str(stage_id or "").strip()
    if not sid:
        raise ValueError("どの公演か分かりません")
    ws = [w for w in re.split(r"[、,，・/／\s]+", words or "") if w.strip()]
    syn, u = (synopsis or "").strip(), (url or "").strip()
    n_cast = hand_credit_count(fields or {})
    HT.save(sid, words=ws, synopsis=syn, url=u, fields=fields or {})
    c = _card_by_stage(sid)
    # **読み取りが要るのは、本人がタグを打たなかったときだけである。**
    # 打ったタグを、貼った文から読み取ったタグで上書きしない
    read = (bool(syn) or bool(u)) and not ws
    said = ("入れた内容を保存しました" if ws or syn or u or n_cast else "入れた内容を消しました")
    return {"ok": True, "html": RR.syn_block(c), "said": said, "read": read,
            "title": c.get("title") or ""}


def hand_theme_refresh(stage_id: str) -> dict:
    """**あらすじの枠を、いまの中身で組み直すだけ。** 書き込みは起きない。

    貼った本文からのタグの読み取りは別のスレッドで走っている（`read_hand_theme`）ので、
    保存した直後の応答にはまだタグが無い。**画面が数秒おきにここを呼び、タグが
    届いたところで枠だけ差し替える**（`SCRIPT` の `pollHandTheme`）── 開き直さないと
    タグが出ない、という手待ちを無くすためである（起案者の指示・2026-08-26）。
    """
    sid = str(stage_id or "").strip()
    if not sid:
        raise ValueError("どの公演か分かりません")
    return {"html": RR.syn_block(_card_by_stage(sid))}


def read_hand_theme(stage_id: str) -> dict:
    """**貼られた本文・URL からタグを読み取る。** 時間がかかるので画面は待たない
    （`serve.py` が別のスレッドで走らせ、画面が数秒おきに拾いに行ってタグが出る）。

    **URL があるときは、そちらを先に使う。** 貼り直した URL は「取りに行く先を直した」
    ものなので、**結果は機械の抽出として控えに残す**（出典が付けられる）。
    """
    import hand_themes as HT
    sid = str(stage_id or "").strip()
    h = HT.load().get(sid) or {}
    title = (_card_by_stage(sid).get("title") or "")
    if h.get("url"):
        try:
            return HT.extract_to_themes(sid, title, h["url"])
        except ValueError:
            pass                        # 取れなければ、貼られた本文の側で読む
    text = (h.get("synopsis") or "").strip()
    if not text:
        return {"ok": False}
    _syn, ws = HT.read_content(sid, title, text)
    if ws:
        HT.save(sid, words=ws)
    return {"ok": bool(ws), "words": ws}


def save_hand_poster(work_key: str, data_url: str) -> dict:
    """選んだ画像を端末内に写して、この記録のポスターにする。

    **外へは出さない。** 受け取るのは画面が読み込んだファイルの中身だけで、
    どこへも送らない（企画書 5 章の守り 5 は、そのままである）。

    **中身で種類を見分ける。** 拡張子は名乗りにすぎないので、先頭の数バイトで判定して、
    知らない形式は受け付けない。
    """
    import base64
    import hashlib
    import rate_performances as R
    raw = (data_url or "").split(",", 1)
    if len(raw) != 2 or not raw[0].startswith("data:image/"):
        raise ValueError("画像を選んでください")
    try:
        data = base64.b64decode(raw[1], validate=True)
    except Exception:                                               # noqa: BLE001
        raise ValueError("画像を読めませんでした") from None
    if len(data) > HAND_IMG_MAX:
        raise ValueError("画像が大きすぎます（12MB まで）")
    ext = next((e for sig, e in HAND_IMG_KINDS.items() if data.startswith(sig)), "")
    if not ext:
        raise ValueError("JPEG・PNG・WebP・GIF のどれかを選んでください")
    # **名前は「記録＋中身」から作る。** 記録だけから作ると、入れ替えても名前が同じで
    # **ブラウザが古い絵を出し続ける**（同じ URL なので取りに来ない）。中身を混ぜれば
    # 別の絵は別の名前になり、入れ替えたことが 1 回で画面に出る。
    wh = hashlib.sha1(work_key.encode()).hexdigest()[:16]
    name = f"hand-{wh}-{hashlib.sha1(data).hexdigest()[:8]}{ext}"
    PO.IMG.mkdir(parents=True, exist_ok=True)
    # **1 記録につき 1 枚だけ持つ。** 前の絵を消さないと、入れ替えるたびに溜まる
    for stale in PO.IMG.glob(f"hand-{wh}*"):
        stale.unlink()
    path = PO.IMG / name
    path.write_bytes(data)
    # **縮めると拡張子が変わることがある。** `posters.shrink` は幅を詰めるときに JPEG で
    # 書き直して元のファイルを消すので、**縮める前の名前を控えると、無いファイルを
    # 指すことになる**（実測 ── PNG を入れたら画面のポスターが空になった）
    if PO.shrink(path) and path.suffix != ".jpg":
        name = path.with_suffix(".jpg").name
    con = R.connect()
    try:
        R.save_hand(con, work_key, poster=name)
    finally:
        con.close()
    return {"ok": True, "poster": name, "said": "ポスターを入れ替えました"}


def drop_hand_poster(work_key: str) -> dict:
    """手で入れたポスターを外す。**元の（結び付け・推測の）絵に戻る。**"""
    import hashlib
    import rate_performances as R
    for stale in PO.IMG.glob("hand-" + hashlib.sha1(work_key.encode()).hexdigest()[:16] + "*"):
        stale.unlink()
    con = R.connect()
    try:
        R.save_hand(con, work_key, poster="")
    finally:
        con.close()
    return {"ok": True, "said": "手で入れたポスターを外しました"}


def link_stage(work_key: str, stage_id: str) -> dict:
    """記録を、手元の公演データに結び付ける（`works.stage_id`）。

    **これが無いと、手で足した記録は推薦に効かない。** 名簿（網 B）とあらすじの要素（網 C）は
    公演ページのクレジットとあらすじから作るが、**メールから導けない記録には、そこへ行く道が
    無かった** ── 評価を付けても、材料が 1 件も取れない。

    **メールから導ける記録にも使える。** 評価済み 91 作品のうちクレジットが引けたのは
    54 件で、**残り 37 件は評価が付いているのに名簿へ 1 人も出していない**（メールの件名と
    公演ページの題名が突き合わない）。同じ口で直せる。

    **結び付けを外せるようにする**（`stage_id` に空を渡す）── 別の公演に結び付けてしまうと、
    **観ていない公演の作り手が名簿に入る。** 戻せなければ取り返せない。
    """
    import rate_performances as R
    if stage_id and not stage_id.isdigit():
        raise ValueError("公演の id は数字である")
    w = next((x for x in _works() if x["work_key"] == work_key), None)
    if w is None:
        raise ValueError("その記録は見つからない")
    title = ""
    if stage_id:
        title = next((r["title"] for r in _suggest_pool()
                      if r["kind"] == "stage" and r["key"] == stage_id), "")
        if not title:
            # **手元に無ければ、その場で取りに行く。**「ネットの公演情報から探す」で
            # 見つけて選んだ直後は、まだ手元の控え（`_suggest_pool` が読む 3 つの
            # ファイル）に無い ── 起案者の指摘（2026-08-26）「できなかった、じゃなくて
            # 情報を取りに行ってください」。**同じ不具合を「手で足す」の検索欄で
            # 起案者から報告されたことがあり**（`stage_search.adopt` の docstring
            # 「公演 428905（手元のデータに見当たりません）」）、そちらは直っていたが
            # 結び付け（この関数）には同じ手当てが通っていなかった。同じ手当てを通す
            import stage_search as SS
            SS.adopt(stage_id, work_key=work_key, title=w["title"],
                     date=w.get("first_date") or "")
            title = next((r["title"] for r in _suggest_pool()
                          if r["kind"] == "stage" and r["key"] == stage_id), "")
        if not title:
            raise ValueError("その公演の情報を取りに行きましたが、見つかりませんでした")
    con = R.connect()
    try:
        con.execute(
            "INSERT INTO works (work_key, title, first_date, last_date, times, verdict,"
            " chosen, note_impression, note_motive, stage_id, updated_at)"
            " VALUES (?,?,?,?,?,NULL,NULL,'','',?,datetime('now','localtime'))"
            " ON CONFLICT(work_key) DO UPDATE SET stage_id=excluded.stage_id,"
            " updated_at=excluded.updated_at",
            (work_key, w["title"], w.get("first_date") or "", w.get("last_date") or "",
             w.get("times") or 1, stage_id or None))
        con.commit()
    finally:
        con.close()
    return {"ok": True, "work_key": work_key, "stage_id": stage_id, "title": title}


_STAGE_LABELS: dict = {}


def stage_label(stage_id: str) -> str:
    """結び付けた公演を、人が読める形で返す。**id の数字だけを画面に出さない。**

    **1 度だけ組んで使い回す。** 記録の一覧は 119 行あり、行ごとに候補の母集団を
    組み直すと、**読む画面が結び付けの都合で遅くなる。**（元になるファイルが書き換わったら
    組み直す ── 更新の直後に古い題名を出さないため）
    """
    if not stage_id:
        return ""
    files = [ROOT / "data" / "review" / "candidates.jsonl",
             ROOT / "data" / "credits" / "credits.jsonl",
             ROOT / "data" / "credits" / "linked.jsonl"]
    stamp = tuple(f.stat().st_mtime_ns if f.exists() else 0 for f in files)
    if _STAGE_LABELS.get("stamp") != stamp:
        ix = {}
        for r in _suggest_pool():
            if r["kind"] == "stage" and r["key"] not in ix:
                ix[r["key"]] = "／".join(
                    x for x in (r["title"], r.get("venue") or "", r.get("date") or "") if x)
        _STAGE_LABELS.clear()
        _STAGE_LABELS.update({"stamp": stamp, "ix": ix})
    got = _STAGE_LABELS["ix"].get(str(stage_id))
    return got or f"公演 {stage_id}（手元のデータに見当たりません）"


# ---------------------------------------------------------------- 取り込みを取り消す
#
# 起案者の指示（2026-08-24）──「取り込んだ過去の公演を取り消しできる機能もほしい。
# まちがったものが拾われてしまっているので」。
#
# ## 単位は「記録 1 件」にする
#
# 除外の表は**（回, 演目）ごと**に持っている ── セット券で 2 演目のうち片方だけが舞台で
# ないことがあり、回ごと外すと相方まで消えるからである。**その単位のまま画面に出すと、
# 押した人が「1 件取り消したのに 2 行出てくる」ことになる。** そこで、外すときに
# **`work:<記録の鍵>` という目印も一緒に置き、戻す画面はその目印を 1 行として出す。**
#
# ## 除外の表に書く ── 別の表を作らない
#
# **`excluded` は学習の側も見ている**（`measure_nets.load_rated` が使う `R.State`）。
# 画面用に別の表を作ると、**取り消したはずの公演が名簿の材料に残る** ── まちがって
# 拾われたものを外したい、という指示の目的がそこで果たされない。
def drop_work(work_key: str) -> dict:
    """取り込んだ記録を候補から外す。

    **消さずに外す。** 外した内容は `excluded` に残るので、いつでも戻せる ──
    誤操作が取り返せない作りにしない。**メールそのものにも触らない。**
    """
    import rate_performances as R
    w = next((x for x in _works() if x["work_key"] == work_key), None)
    if w is None:
        raise ValueError("その記録は見つからない")
    pairs = [(s["uid"], s["program"]) for s in (w.get("shows") or [])]
    # **目印を必ず置く。** 回を全部外しても `works` の行は残るので、目印が無いと
    # 「手で足した記録」として一覧に出続ける（実データで確認した）
    pairs.append((f"work:{work_key}", w["title"]))
    con = R.connect()
    try:
        R.save_excluded(con, pairs, True)
    finally:
        con.close()
    return {"ok": True, "work_key": work_key, "title": w["title"],
            "n": len(w.get("shows") or []) or 1}


def _dropped_state():
    """外した記録を、記録の単位に組み直して返す（目印, 目印に属する（回, 演目），
    完全に取り消した work_key，完全に取り消した目印無し演目）。
    """
    import rate_performances as R
    con = R.connect()
    try:
        ex = R.read_excluded(con)
        merges = R.read_merges(con)
        # **除外を外した状態で組み直す。** 外した記録が何回ぶんだったかは、
        # 外したあとの一覧からは分からない
        full = R.load_works(R.load_purchases(), R.read_splits(con), set(), merges)
    finally:
        con.close()
    marks = {u[5:]: p for u, p in ex if u.startswith("work:")}
    # **「完全取り消し」は、専用の目印を別に置く。**（起案者の指示・2026-08-26 ──
    # 「取り消した記録、には『完全取り消し』のボタンもつけてほしい」）**除外そのもの
    # （回・演目の組）は動かさない** ── 外すと次の読み込みでその記録が復活してしまう。
    # 完全取り消しが動かすのは「取り消した記録」の一覧に出すかどうかだけである。
    purged = {u[7:] for u, p in ex if u.startswith("purged:")}
    purged_legacy = {p for u, p in ex if u.startswith("purged-legacy:")}
    by_key = {w["work_key"]: w for w in full}
    # **`owned` は、完全に取り消した work_key ぶんも組む。** そうしないと、その回・演目の
    # 組が「目印付きの分」としては数えられなくなり、目印無しの古い除外の集計に紛れ込んで
    # 二重に出てしまう（`dropped_works` の `legacy` はここで漏れた分を拾う仕組みである）
    owned: dict[str, set] = {}
    for k in marks.keys() | purged:
        owned[k] = {(s["uid"], s["program"]) for s in (by_key.get(k) or {}).get("shows", [])}
    return ex, marks, owned, purged, purged_legacy


def dropped_works() -> list[dict]:
    """外した記録の一覧。**取り消せる機能には、戻す口が要る。**

    **目印の無い古い除外も出す。** 前の画面（`rate_performances.py` の一覧）から外した分が
    実データに 6 件あり、出さないと**戻す手段が画面から消える。**

    **完全に取り消した分は、ここには出さない。** 一覧をたたむのが「完全取り消し」の
    目的なので、目印（`purged:`／`purged-legacy:`）が付いた分は素通りする。
    """
    ex, marks, owned, purged, purged_legacy = _dropped_state()
    rows = [{"key": k, "title": t, "n": len(owned.get(k) or ()) or 1, "legacy": False}
            for k, t in marks.items() if k not in purged]
    taken = {pair for v in owned.values() for pair in v}
    legacy: dict[str, int] = {}
    for uid, program in ex:
        if uid.startswith(("work:", "purged:", "purged-legacy:")):
            continue
        if (uid, program) in taken or program in purged_legacy:
            continue
        legacy[program] = legacy.get(program, 0) + 1
    rows += [{"key": p, "title": p, "n": n, "legacy": True} for p, n in legacy.items()]
    return sorted(rows, key=lambda r: r["title"])


def restore_work(key: str) -> dict:
    """外した記録を戻す。**目印のあるものは記録ごと、古い除外は演目ごとに戻す。**"""
    import rate_performances as R
    ex, marks, owned, _purged, _purged_legacy = _dropped_state()
    if key in marks:
        pairs = [(f"work:{key}", marks[key])] + sorted(owned.get(key) or ())
    else:
        pairs = [(u, p) for u, p in ex if not u.startswith("work:") and p == key]
    if not pairs:
        raise ValueError("外した記録に見つからない")
    con = R.connect()
    try:
        R.save_excluded(con, pairs, False)
    finally:
        con.close()
    return {"ok": True, "key": key, "n": len(pairs)}


def purge_work(key: str) -> dict:
    """取り消した記録を、**戻す口ごと「取り消した記録」の一覧から消す。**

    起案者の指示（2026-08-26）──「取り消した記録、には『完全取り消し』のボタンも
    つけてほしい」。まちがって取り込まれた記録は、直しても直しても同じ発行元から
    毎回同じ形で届くことがあり、**戻せる一覧に積もり続けると、戻す気の無い行が
    「取り消した記録」の大半を占める**ことになる。

    **除外そのものには触らない。** 除外を外すと、次の読み込みでその記録が
    生き返ってしまう ── 「完全」は一覧から消すことであって、除外を強めることでは
    ない。目印だけを `work:`／目印無し から `purged:`／`purged-legacy:` に切り替え、
    `dropped_works` がそれを読み飛ばすようにする。
    """
    import rate_performances as R
    ex, marks, _owned, purged, purged_legacy = _dropped_state()
    con = R.connect()
    try:
        if key in marks and key not in purged:
            title = marks[key]
            R.save_excluded(con, [(f"work:{key}", title)], False)
            R.save_excluded(con, [(f"purged:{key}", title)], True)
        elif key not in purged_legacy and any(
                p == key for u, p in ex if not u.startswith(("work:", "purged:", "purged-legacy:"))):
            title = key
            R.save_excluded(con, [(f"purged-legacy:{key}", key)], True)
        else:
            raise ValueError("取り消した記録に見つからない")
    finally:
        con.close()
    return {"ok": True, "key": key, "title": title}


# ------------------------------------------------------- 行かなかった公演を外す
#
# 起案者の指示（2026-08-24）──「観た公演の評価に、実際には見ていないものが混じっている。
# 消せるようにしてほしい」。
#
# ## 「取り消す」とは別の口である
#
# **券を買ったが行かなかった公演と、舞台ではないものが取り込まれた記録は、別のことである。**
# 前者は記録として正しく、後者は記録そのものが間違っている。**同じ口にまとめると、
# 行かなかった公演が「まちがって拾われたもの」として記録から消える** ── 買った事実は
# 残っているので、消すと「観ていないのに買った」ことを後から数えられない。
#
# | 実際 | 押す口 | 書く先 | どうなるか |
# |---|---|---|---|
# | 券は買ったが観ていない | 行かなかった | `attendance` | 記録に残るが、観た本数と図には数えない |
# | 舞台ではないものが取り込まれた | この記録を取り消す | `excluded` | 記録から外れる（戻せる） |
#
# ## 表を新しく作らない
#
# **`attendance` は前の画面（`rate_performances.py`）が既に持っていた表**で、実データに
# 23 回ぶん入っている。**新しい画面がこの表を読んでいなかったため、本人が 2026-08-20 に
# 「行かなかった」と答えた 7 件が評価待ちに戻っていた。** 画面用に別の表を作ると、
# 同じ答えが 2 か所に散って同じことがまた起きる。
def set_unseen(work_key: str, unseen: bool) -> dict:
    """「行かなかった」を付ける／外す。**回ごとに書く。**

    **単位は回である。** 3 回のうち 1 回を落としたのは観た公演なので、作品の側に
    「観ていない」という欄は作らない ── 作ると、回数と食い違ったときにどちらが正なのかが
    決まらなくなる。作品が「観ていない」になるのは、**回が 1 つも残らないときだけ**である。

    **消さずに外す。** 買った記録はそのまま残るので、いつでも観たほうへ戻せる。
    """
    import rate_performances as R
    w = next((x for x in _works() if x["work_key"] == work_key), None)
    if w is None:
        raise ValueError("その記録は見つからない")
    shows = w.get("shows") or []
    if not shows:
        # 手で足した記録は回を持たないので、この表には書けない。**代わりの口を名指しする**
        raise ValueError("この記録は購入から来ていないので、"
                         "「この記録を取り消す」から外してほしい")
    con = R.connect()
    try:
        for s in shows:
            R.save_attendance(con, w, s["uid"], not unseen)
    finally:
        con.close()
    return {"ok": True, "work_key": work_key, "title": w["title"],
            "unseen": bool(unseen), "n": len(shows)}


def save_work_field(work_key: str, *, verdict=None, note=None) -> dict:
    """評価または感想を 1 つ書く。**受け付ける項目は列挙したものだけ**（守り 4）。

    **`UPDATE` だけでは足りない。** 取り込んだばかりの作品はまだ `works` に行が無く、
    「その作品は記録に無い」と断られていた ── 取り込みと評価が繋がらない原因になる。
    購入から導ける作品なら行を作り、導けない（手で足した）ものは行を更新する。
    """
    import rate_performances as R
    con = R.connect()
    try:
        works = R.load_works(R.load_purchases(), R.read_splits(con), R.read_excluded(con))
        w = next((x for x in works if x["work_key"] == work_key), None)
        sv = R.read_works(con).get(work_key) or {}
        if w is None:
            if not sv:
                raise ValueError("その作品は記録に無い")
            col, val = ("verdict", verdict) if verdict is not None else ("note_impression", note)
            con.execute(f"UPDATE works SET {col}=?,"
                        " updated_at=datetime('now','localtime') WHERE work_key=?",
                        (val, work_key))
            con.commit()
            return {"ok": True, "work_key": work_key, "manual": True}
        # **他の欄を消さない。** 評価を押しただけで感想が消えるのは、いちばん困る失敗である
        R.save_work(con, w, {
            "verdict": verdict if verdict is not None else sv.get("verdict"),
            "chosen": sv.get("chosen"),
            "note_impression": note if note is not None else (sv.get("note_impression") or ""),
            "note_motive": sv.get("note_motive") or ""})
        return {"ok": True, "work_key": work_key, "manual": False}
    finally:
        con.close()


def save_visit_note(uid: str, note: str) -> dict:
    """1 回ぶんの、推薦には使わないメモを書く。**`visit_note` 表の注記を見る。**

    `save_work_field` と違い、作品（`works`）の行があるかどうかを確かめない ──
    uid そのものが鍵で、作品と結び付いているかどうかを問わない。
    """
    import rate_performances as R
    con = R.connect()
    try:
        return R.save_visit_note(con, uid, note)
    finally:
        con.close()


def add_work(title: str, date: str = "", venue: str = "", stage_id: str = "",
             time: str = "") -> dict:
    """メールに残らない経路（招待・当日窓口・人に取ってもらった分）を手で足す。

    **自動取り込みを入力の確定源にしない。** 記録に残らない経路ほど、強い意味を持つ観劇が
    通ることがある。**鍵の形は購入から作るものと同じにする**（後から購入の記録が届いたときに
    同じ作品として重なるため）。

    **候補から選んだときは、その公演の id を残す**（`stage_id`）── どの公演のことなのかが
    決まっていれば、ポスターも公演ページも当て推量なしに引ける。手で打った分は空のままで、
    **空であることが「まだ結び付いていない」という事実である。**

    **足したあとに、題名の近い記録を返す。** 二重に足したことに、その場で気づける。

    **開演時刻も、会場と同じように受け取る**（起案者の指示・2026-08-26 ──「メールから
    拾った公演じゃなくても、自分で劇場や時間を追加できるようにしてほしい」）。
    足したあとで直すときは `_fix_manual` が同じ列を書き換える。
    """
    import rate_performances as R
    key = f"{R.title_key(title)}#{date or 'undated'}"
    con = R.connect()
    try:
        if con.execute("SELECT 1 FROM works WHERE work_key=?", (key,)).fetchone():
            raise ValueError("その作品はもう登録してある")
        # **会場は会場の列に入れる。** ここは以前 `note_impression`（感想）に
        # 「劇場: 〜」と書いていた ── `works` に会場の列が無かったためである。
        # **本人が読み書きする自由記述の欄に、システムが値を置いてはいけない** ──
        # 感想の件数に数えられ、◎ の作品なら推薦の理由に「あなたの言葉」として
        # 引用される（起案者の報告 2026-08-24。移行は `rate_performances._add_venue`）
        con.execute(
            "INSERT INTO works (work_key, title, first_date, last_date, times, verdict,"
            " chosen, note_impression, note_motive, stage_id, venue, time, updated_at)"
            " VALUES (?,?,?,?,1,NULL,NULL,'','',?,?,?,datetime('now','localtime'))",
            (key, title, date, date, stage_id or None, venue or "", time or ""))
        con.commit()
    finally:
        con.close()
    # **選んだ公演を、その場で手元の控えに写す。** 「検索」で外から拾った公演は、まだ
    # どの控えにも無い ── 写さないと、**本人が選んで結び付けた直後に「手元のデータに
    # 見当たりません」と出る**（起案者の報告 2026-08-24）。更新の段に任せる作りだったが、
    # **更新の段は評価が付いた記録しか見ない**ので、評価を付けるまで空のままだった。
    # **通信は 0 回で済む**（探したときに公演ページを控えている）。落ちても登録は残す
    adopted = {}
    if stage_id:
        import stage_search as SS
        adopted = SS.adopt(stage_id, work_key=key, title=title, date=date)
    return {"ok": True, "work_key": key, "stage_id": stage_id, "adopted": adopted,
            "similar": similar_works(title, key)}


def _import_upto_line() -> str:
    """**どこまで取り込んであるかを、記録から出す。**

    以前は「いまの取り込みは 2026-04-08 で止まっています」と日付を直に書いていたが、
    **これは起案者の端末の値**であって、初めて使う人には当てはまらない
    （2026-08-24 の実測で、1 通も取り込んでいない画面にこの日付が出ていた）。
    """
    src = ROOT / "data" / "tickets" / "performances.jsonl"
    last = ""
    if src.exists():
        import email.utils
        for line in src.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            md = json.loads(line).get("mail_date") or ""
            try:
                d = email.utils.parsedate_to_datetime(md).date().isoformat()
            except (TypeError, ValueError):
                continue
            last = max(last, d)
    if not last:
        return ("<b>まだ 1 通も取り込んでいません</b>ので、押すと過去のぶんから入ります"
                "（初回は時間がかかります）。")
    return (f"<b>いまの取り込みは {last} までです</b>ので、押すとその後の分が入ります。")


# **取り込みの段は、取り込む側が名乗る。** ここに名前を写すと、段を足したときに
# 目盛りだけが古いまま残る ── 走っていないときに出す下書きとしてだけ持つ
# （実際に出る名前は `tools/tickets/extract_performances.py` の `tick` が流してくる）。
IMPORT_STEPS = ["メールを探す", "差出人を確かめる", "公演を取り出す"]


def _import_bar(imp: dict | None = None) -> str:
    """取り込みの進み具合を出す帯。

    起案者の指示（2026-08-25）──「経過がわかるバーがほしい。進行状況を一目で」。

    ## なぜ 1 本の帯だけでは足りないか

    取り込みは 3 つの段でできていて、**そのうち最初の段は、何通あるかが分かる前の
    待ち時間である**（受信箱の走査と認証）。ここを「0 パーセント」の帯で出すと、
    止まっているのと区別が付かない ── **総数が分かるまでは伸ばさずに流し、分かって
    から伸ばす。** どの段に居るのかは帯の下の 3 つの点で出すので、**帯が伸びない間も
    何をしているかは読める。**

    ## 画面を開き直したときも続きから出す

    取り込みは画面を閉じても走り続ける（`serve.py`）。**開き直したときに帯が消えて
    いると、走っているのに終わったように見える** ── 走っている最中に組んだ画面は
    帯を開いた状態で書き出し、そのまま聞きに行かせる（`data-run`）。

    ## 終わっても勝手に読み込み直さない

    この画面には手で公演を足す入力欄が並んでいる。取り込みは数分かかるので、
    **待つ間にそちらを書いていることがある** ── 終わった拍子に読み込み直すと、
    書きかけが消える。押し口を 1 つ出して、**読み込み直す時機は本人が決める。**
    """
    d = imp or {}
    run = bool(d.get("running"))
    total, n = int(d.get("total") or 0), int(d.get("n") or 0)
    step = int(d.get("step") or 1)
    # **どこまで伸ばすかは取り込みを見ている側が決める**（`serve._pct`）。
    # ここで数え直すと、走っている最中に開き直したときだけ帯の長さが違う
    pct = int(d.get("pct") or 0) if run else 0
    seek = run and not total          # 何通あるかが分かる前（受信箱を探している間）
    cls = "ibar" + (" iwait" if seek else "")
    dots = "".join(
        '<li class="{}">{}</li>'.format(
            "on" if run and i + 1 == step else ("fin" if i + 1 < step else ""), E(name))
        for i, name in enumerate(IMPORT_STEPS))
    return (
        '<div class="{cls}" data-ibar{open} role="progressbar"'
        ' aria-valuemin="0" aria-valuemax="100" aria-valuenow="{pct}">'
        '<div class="ist"><span class="istep">{name}</span>'
        '<span class="inum">{num}</span><span class="irest"></span></div>'
        '<div class="itrack"><div class="ifill"{w}></div></div>'
        '<ol class="isteps">{dots}</ol>'
        '<div class="idone"><button data-reload="1">取り込んだ分を画面に出す</button></div>'
        '</div>'
    # **探している間は幅を書かない。** 直に書いた指定は規則より強いので、
    # `width:0%` を置くと流れる帯（`.ibar.iwait .ifill`）が幅 0 のまま動かない
    ).format(cls=cls, open=' data-run="1"' if run else " hidden", pct=pct,
             w="" if seek else f' style="width:{pct}%"',
             name=E(str(d.get("name") or "取り込んでいます")),
             num="{} / {} 通".format(n, total) if total else "", dots=dots)


def _imported_list(titles: list | None) -> str:
    """**今回の取り込みで入った公演の題名を、そのまま並べる。**

    起案者の指示（2026-08-25）──「押したら実際に今回取り込まれた公演タイトルを
    表示してほしい。『公演A／公演B・・・』のように羅列するだけでいいので」。

    **件数だけでは、入ったのが自分の知っている公演かどうかが分からない。**
    「新しく入った公演 3 件」は、入ったことは言えても**何が入ったのかを言えない** ──
    確かめられるのは題名だけである。

    **日付も会場も付けない。** ここは入ったことを確かめる場所で、記録を読む場所では
    ない（読むのは「記録を見返す」である）── 列を増やすと、確かめるために読む量が増える。
    """
    if not titles:
        return ""
    return ('<div class="impgot"><b>今回取り込んだ公演</b><span class="impgot-l">'
            + "／".join(E(str(t)) for t in titles) + "</span></div>")


def page_register(imp: dict | None = None, imported: list | None = None) -> str:
    """入力の画面。**読む画面と分ける。**

    週 3 分で一覧を読む動作に「取り込む」「足す」「評価する」を混ぜると、
    読みに来たのか書きに来たのか分からなくなる（起案者の指示で独立させた）。

    **「観ればよかった」の登録もここに置く**（起案者の指摘・2026-08-24）。日記帳に
    置いていたが、**あちらは思い出を読む画面で、ここは足す画面である** ── 名前も
    「登録」であり、足す操作の置き場所はここに揃える。**ただし ①② と性質が違う**
    （観ていない公演なので、観た本数・図・評価待ち・推薦の材料のどれにも入らない）。
    その違いは札の見出しと本文の両方に書く ── 同じ画面に並ぶと、観た公演を足す口と
    見分けが付かなくなる。
    """
    wait = waiting_rows()
    all_w = _works()
    # **上演前のものは評価待ちに入れない**（企画書 4 章）
    unrated = [w for w in all_w if not w.get("verdict") and w.get("bucket") != "upcoming"]
    line = (imp or {}).get("line") or ""
    missed = missed_rows()
    body = f"""<h1>公演情報の登録</h1>
<p class="lede">公演を記録に足す場所です。<b>入口は 3 つあります</b> ──
購入確認メールから自動で取り込む、メールに残らない分（招待・当日窓口・人に取ってもらった分）を
手で足す、<b>観ればよかった公演（観ていないもの）を足す</b>の 3 つです。
評価は「観た公演の評価」で付けます。評価が無くても記録は残せます。</p>

<div class="card">{IC.h2("mail", "① 購入確認メールから取り込む")}
<p class="lead">前回より後に届いたメールだけを見ます。{_import_upto_line()}</p>
<div class="imp"><button data-imp="1"{" disabled" if (imp or {}).get("running") else ""}>{IC.ico("mail")}取り込みを始める</button>
 <span class="said">{E(line)}</span></div>
{_import_bar(imp)}{_imported_list(imported)}</div>

<div class="card">{IC.h2("plus", "② 手で 1 件足す ── メールに残らない分")}
<p class="lead">招待・当日窓口・人に取ってもらった分は購入確認メールに残らないので、
ここから足してください。</p>
<div class="add-work"><input id="w-title" type="text" placeholder="公演の題名" size="26"
  autocomplete="off"><input id="w-stage" type="hidden" value="">
 <input id="w-date" type="date"> <input id="w-time" type="time" aria-label="開演時刻（任意）">
 <input id="w-venue" type="text" placeholder="劇場（任意）" size="14">
 <button data-add-work="1">{IC.ico("plus")}登録する</button>
 <button data-sug-web="1">{IC.ico("search")}CoRichで検索</button><span class="said"></span></div>
<div id="sug" class="sug"></div>
<p class="ed-lead"><b>題名を 2 文字入れると、手元の情報から候補が出ます。</b>
選ぶと劇場・日程・出演者・作り手が一緒に入り、次のおすすめの材料になります。
すでに記録にあるものは「記録あり」と出るので、二重に足さずに済みます。<br>
<b>候補に出てこないときは「検索」を押してください。</b>その場で公演情報を探します
（8 秒ほどかかります）。同じ題名の公演が複数出ることがあります ──
別の劇場での上演や再演なので、劇場と日程を見て、観たものを選んでください。<br>
ポスターが出るのは、手元に画像がある公演だけです。</p></div>

<div class="card">{IC.h2("flag", "③ 「観ればよかった」を足す ── 観ていない公演",
 f'<span class="badge part">{len(missed)} 件</span>' if missed else "")}
<p class="lead">出てこなかったせいで見逃した公演を登録してください。
どこで漏れたのか（一覧に無かった／順位が低かった／出したのに押されなかった）と、
演者・あらすじを調べて下に出します（数十秒かかることがあります）。<br>
<b>①② と違って、これは観ていない公演です。</b>観た本数にも、図にも、評価待ちにも入らず、
評価（◎）の材料にもなりません。再演や別会場での上演を次は見逃したくないときは、
下の一覧から「お気に入りに入れる」を押してください。</p>
<div class="miss-add"><input id="miss-title" type="text" placeholder="公演の題名" size="30">
 <button data-miss="1">{IC.ico("flag")}登録する</button><span class="said"></span></div>
{_missed_html(missed)}</div>

<p class="lede">①② で登録した公演は、上演が終わると
<a href="/rate?t=__TAGURI_TOKEN__">「観た公演の評価」（いま {len(wait)} 件）</a>に並びます。
評価はそちらで付けてください。</p>"""
    return layout("公演情報の登録", "/register", body, RR.STYLE)


def _pool_titles() -> dict:
    """候補の母集団の題名（正規化 → 1 件）。**取り込んだ一覧に居たかを見るためだけ**に使う。"""
    out: dict[str, dict] = {}
    f = ROOT / "data" / "review" / "candidates.jsonl"
    if not f.exists():
        return out
    for line in f.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        try:
            c = json.loads(line)
        except ValueError:
            continue
        k = R_NORM(c.get("title") or "")
        if k:
            out.setdefault(k, c)
    return out


def missed_rows() -> list[dict]:
    """登録した「観ればよかった」と、**どこで漏れたのかの判定**。

    ## なぜ判定まで出すのか

    **札には「どこで漏れたのかを後から調べるためのもの」と書いてある。** 登録した題名を
    並べるだけでは、その約束を果たしていない（**出力は、自分で書いた仕様を満たしてから
    見せる**）。判定に要る材料は全部手元にある ── 母集団（`candidates.jsonl`）と、
    その週に出した一覧（`presented`）である。

    ## 3 つに分ける

    | 判定 | 意味 | 次に効く手 |
    |---|---|---|
    | `shown` | 出したのに押されなかった | 出し方（理由の書き方・並び）の問題 |
    | `pool` | 一覧には居たが、出す枠に届かなかった | 順位の付け方・効かせ方の問題 |
    | `none` | 母集団に居なかった | 情報源の穴。取り込む先を増やすしかない |

    **どれも「本人が悪い」ではなく、仕組みのどこが足りないかを指す。**
    """
    if not DB.exists():
        return []
    con = sqlite3.connect(DB)
    try:
        # **表が無い DB からも呼ばれる。** 表を作るのは画面を立てる側（`serve.py`）で、
        # この関数は画面を組むだけの呼び出し（検査・書き出し）からも通る ── **無いことは
        # 失敗ではないので、空として返す**（画面には「まだ登録はありません」が出る）
        try:
            rows = [{"title": t, "at": (at or "")[:10], "note": n or "",
                     "stage_id": sid or "", "venue": venue or "", "period": period or "",
                     "fields": (json.loads(fj) if fj else {}),
                     "synopsis": syn or "", "lookup_note": lnote,
                     "looked_up": looked is not None}
                    for t, at, n, sid, venue, period, fj, syn, lnote, looked in con.execute(
                        "SELECT title, created_at, note, stage_id, venue, period,"
                        " fields_json, synopsis, lookup_note, looked_up_at FROM missed"
                        " ORDER BY created_at DESC")]
        except sqlite3.OperationalError:
            return []
        if not rows:
            return []
        # **出した題名は、いちばん新しい提示を採る。** 何度も出している公演があるので
        shown: dict[str, tuple] = {}
        try:
            for t, lab, rk in con.execute(
                    "SELECT title, label, rank FROM presented ORDER BY label"):
                k = R_NORM(t or "")
                if k:
                    shown[k] = (lab, rk)
        except sqlite3.OperationalError:
            pass
    finally:
        con.close()
    pool = _pool_titles()
    for r in rows:
        k = R_NORM(r["title"])
        if k in shown:
            r["where"], r["lab"], r["rank"] = "shown", shown[k][0], shown[k][1]
        elif k in pool:
            r["where"] = "pool"
        else:
            r["where"] = "none"
    return rows


MISSED_WHERE = {
    "shown": ("出したのに押されなかった",
              "この公演は一覧に出していました。出し方（理由の書き方・並び順）の側で"
              "見落とされたということです。"),
    "pool": ("一覧には居たが、出す枠に届かなかった",
             "取り込んだ公演の中には居ましたが、順位が足りず 15 件の枠に入りませんでした。"
             "「おすすめの効かせ方」で効かせる情報を変えると入ることがあります。"),
    "none": ("取り込んだ公演の中に無かった",
             "そもそも母集団に入っていませんでした。順位をいくら変えても出てきません ── "
             "情報源を増やすしかない分です。"),
}


def _missed_lookup_html(r: dict) -> str:
    """演者とあらすじ。**登録した直後に調べた分をそのまま出す**（`Server._lookup_missed`）。

    起案者の指示（2026-08-25）── 「観ればよかった」で足した公演は、演者やあらすじを
    調べてまず表示してほしい。**出演者の並びは推薦カードと同じ関数を使う**
    （`RR.cast_block`）── 事実の並べ方を 2 通り作らない。
    """
    if not r["looked_up"]:
        return '<p class="empty">演者とあらすじを調べています…</p>'
    if not r["stage_id"]:
        return (f'<p class="empty">{E(r["lookup_note"] or "この題名の公演ページが"
                "見つかりませんでした")}</p>')
    out = [RR.cast_block({"fields": r["fields"]})]
    if r["synopsis"]:
        out.append(f'<div class="syn"><p class="txt">{E(r["synopsis"])}</p>'
                   f'<span class="src">［出典: CoRich の公演ページ］</span></div>')
    else:
        out.append('<p class="empty">あらすじを取れませんでした'
                   '（公演ページに内容の記載がありません）。</p>')
    if r["lookup_note"]:
        out.append(f'<p class="empty">{E(r["lookup_note"])}</p>')
    return "".join(out)


def _missed_html(rows: list[dict]) -> str:
    """登録した「観ればよかった」の一覧。**登録したものが戻ってこない状態にしない。**

    **出演者・作り手は、自動で次の推薦に混ざる**（起案者の指示・2026-08-26 ──
    「『観ればよかった』で挙がった人名は『興味あり』のボタンを押した扱いと同じにして、
    推薦に反映させて」）。以前は「お気に入りに入れる」という別の押し口を置いていたが、
    **その機能は不要と指示され、外した。** 見逃して悔しいと登録した時点で「もっと知り
    たい」という意思表示なので、演者・作り手が調べ終わり次第、押す操作なしに反映される
    （`recommend2.py` の `M.interest_credits`／`M.add_interest_roster`）。

    **評価（◎）と同じ強さでは扱わない。** 観ていない公演なので、実際に観て良かった
    ものより弱い、控えめな信号として名簿に混ぜる ── 正例の主役は ◎ を付けた公演の
    ままである。

    **演者とあらすじも出す**（起案者の指示・2026-08-25）。どこで漏れたのかとは別の
    事実なので、節を分ける（`_missed_lookup_html`）。
    """
    if not rows:
        return ('<p class="empty">まだ登録はありません。'
                '<b>登録すると、その公演がどこで漏れたのか（取り込んだ一覧に無かった／'
                '順位が足りなかった／出したのに押されなかった）と、'
                '演者・あらすじをここに出します。</b></p>')
    out = []
    for r in rows:
        head, why = MISSED_WHERE[r["where"]]
        rank = (f'（{E(r["lab"])} に {r["rank"]} 番目で出しています）'
                if r["where"] == "shown" else "")
        out.append(f'<div class="prom"><span class="k">{E(head)}</span>'
                   f'<span class="w">{E(r["title"])}</span>'
                   f'<span class="src">{E(r["at"])} に登録{rank}</span>'
                   f'<span class="q">{why}</span>'
                   f'{_missed_lookup_html(r)}</div>')
    return (f'<p class="lead">登録した {len(rows)} 件と、<b>どこで漏れたのか</b>・'
            f'<b>演者とあらすじ</b>です。'
            f'出演者・作り手は、調べ終わり次第、次の推薦に自動で反映されます'
            f'（観ていない公演なので、◎ より弱い扱いです）。'
            f'</p>{"".join(out)}')


# ---------------------------------------------------------------- 観た公演の評価
def _rate_base() -> dict:
    """3 枚が共通で使う材料と件数。**数え方を 1 か所に置く。**

    帯の件数と各画面の中身が別々に数えていると、**帯に 22 件と出ているのに開くと
    18 件しか無い**という食い違いが起きる（「記録を見返す」の 3 枚と同じ判断）。
    """
    d, wait = _load()
    all_w = _works()
    # **上演前のものは評価待ちに入れない**（企画書 4 章）。
    #
    # **「行かなかった」を付けた記録も出さない**（起案者の指示・2026-08-25 ──
    # 「評価ページで『行かなかった』を選んだものは表示しないでほしい」）。
    # **答えたのに一覧から消えないのは、押した意味が無い** ── 実測で未評価の 21 件のうち
    # 12 件が「行かなかった」で、答え終わったものが答えるべきものの倍あった。
    # 評価待ちの帯（`waiting_rows`）と評価一覧（`rated`）はすでに外していたので、
    # **3 枚のうちここだけが外していなかった。**
    #
    # **消したのではなく、この一覧から外しただけである。** 記録は日記帳に残り、
    # 「やはり観た」で戻せる（`_rec_row`）── 買った事実は消さない、というこれまでの
    # 判断のままである。**外した件数は画面に書く**（黙って減らさない）。
    unrated = [w for w in all_w if not w.get("verdict")
               and w.get("bucket") != "upcoming" and not w.get("unseen")]
    n_skip = sum(1 for w in all_w if w.get("unseen") and not w.get("verdict")
                 and w.get("bucket") != "upcoming")
    rated = [w for w in all_w if w.get("verdict") and not w.get("unseen")]
    no_note = [w for w in rated
               if w["verdict"] == "◎" and not (w.get("note_impression") or "").strip()]
    return {"d": d, "wait": wait, "all": all_w, "unrated": unrated,
            "rated": rated, "no_note": no_note, "n_skip": n_skip}


def _rate_counts(b: dict) -> dict:
    return {"/rate": len(b["rated"]), "/rate/unrated": len(b["unrated"]),
            "/rate/notes": len(b["no_note"])}


# 1 枚の紙に出す件数（起案者の指示・2026-08-24 ──「○ にも『次の 15 件』の送りを
# 付けて」）。**お気に入り・興味ありの 8 件とは別に持つ** ── あちらは「観るかどうかを
# 決める」ために値段・あらすじ・出演者まで載った券が並ぶので 1 枚が大きい。**こちらは
# 読み返す行なので、同じ高さに 15 行入る。**
SHEET_TOP = 15


# **索引の耳は `render_recommend` に 1 つだけ置く。** 月の絞り込み（`RR.month_pick`）も
# 同じ耳を出すようになったので、**組み立てる側と同じ場所に無いと、また 2 つに分かれる。**
# 見た目の指定（`.idx` / `.ix` / `.idxsheet`）はこのファイルの `APP_CSS` にある ──
# 耳が出るのはこのシステムの画面だけなので、意匠の検査（`test_design.py`）が
# 見に来る場所を動かしていない。
index_tabs = RR.index_tabs


def _venue_key(w: dict) -> str:
    """会場を絞り込むときの束ね方。**全角・半角の空白の有無だけの違いを 1 つにまとめる。**

    実測で「紀伊國屋サザンシアターTAKASHIMAYA」（4 件）と「紀伊國屋サザンシアター
    TAKASHIMAYA」（2 件、間に半角空白）が別の会場として数えられていた ── 同じ劇場が
    2 つの札に割れると、片方を選んでも残りが漏れる。表示は `_venue_of` の文字のまま、
    束ねる鍵だけ空白を落とす。
    """
    v = _venue_of(w)
    return re.sub(r"[\s　]+", "", v) if v else "none"


def _venue_form(ws: list, keep: set, action: str, hidden: dict) -> str:
    """会場で絞り込む札（起案者の指示・2026-08-26 ──「評価一覧を…会場の場所とかでも
    絞り込めるようにして」）。

    **都道府県の絞り込み（`RR.pref_form`）と同じ形にする。** 「いくつでも選べる」
    絞り込みは画面をまたいで同じ操作なので、折りたたんだチェックボックスの札という
    形をここでも使う ── 別の見た目を作ると、また「同じ操作に 2 つの形」が並ぶ。

    **都道府県ではなく、実際の会場名を札にする。** 評価一覧の記録はすでに観た公演で、
    都道府県のタグを持たない（`RR.PREFS` は今後の候補を都道府県で探す側の分類であって、
    観た記録の会場名とは別の軸である）。**押しても何も出ない札は並べない**（0 件の会場は
    出さない）ので、`ws` に会場が 1 つも無ければ札そのものを出さない。
    """
    counts: dict[str, int] = {}
    label: dict[str, str] = {}
    for w in ws:
        k = _venue_key(w)
        counts[k] = counts.get(k, 0) + 1
        label.setdefault(k, _venue_of(w) or "会場が分かりません")
    if not counts:
        return ""
    order = sorted((k for k in counts if k != "none"),
                   key=lambda k: (-counts[k], label[k]))
    if "none" in counts:
        order.append("none")
    keep = keep & set(counts)
    chips = "".join(
        f'<label class="pchip{" on" if k in keep else ""}">'
        f'<input type="checkbox" name="venue" value="{E(k)}"{" checked" if k in keep else ""}>'
        f'<span class="pl">{E(label[k])}</span><span class="pn">{counts[k]}</span></label>'
        for k in order)
    now = ("すべて" if not keep else
           "・".join(label[k] for k in order if k in keep) + f"（{len(keep)} 会場）")
    hidden_in = "".join(f'<input type="hidden" name="{E(hk)}" value="{E(hv)}">'
                        for hk, hv in hidden.items() if hv)
    hidden_qs = "".join(f"&amp;{E(hk)}={E(hv)}" for hk, hv in hidden.items() if hv)
    return f"""<form class="pfil" method="get" action="{E(action)}">
<input type="hidden" name="t" value="__TAGURI_TOKEN__">
{hidden_in}
<details class="pbox">
<summary>{IC.ico("search", 15)}会場で絞り込む ── いまは<b>{E(now)}</b></summary>
<p class="lead">会場は<b>いくつでも同時に選べます</b>。選んだ会場で観た記録だけを表示します。
数字は、いま選んでいる評価・年の中でその会場の件数です。</p>
<div class="pchips">{chips}</div>
<div class="pfoot"><button type="submit">{IC.ico("search")}この会場で絞り込む</button>
<a class="pall" href="{E(action)}?t=__TAGURI_TOKEN__{hidden_qs}">すべての会場に戻す</a></div>
</details></form>"""


def page_rate(verdict: str = "", year: str = "", venues=(), page: int = 1) -> str:
    """**評価 ▸ 一覧。付けた評価を ◎○△× ごとに、札で切り替えて出す画面。**

    起案者の指示（2026-08-24）──「『評価』ってナビゲーションバーのボタンを押したら
    過去の自分の評価一覧が出てきて、サブページとして未評価でページを分けてもいいのでは？」
    ──「○ 合っていた 47 作品 とかが ◎ の下に羅列されていってるけど、そうじゃなくて
    タブ切り替えみたいにしたらいいのでは？」。

    ## なぜ縦に積むのをやめたか

    **畳んだ束を縦に積むと、次の束の見出しが前の束の下端にある。** ◎ を開いた状態では
    37 行のあとに「○ 47 作品」が来るので、**◎ を読み終わるまで ○ の存在が画面に出ない。**
    札を横に並べれば、5 つの束と件数が最初から 1 行で見える。

    ## 耳は素のリンクにする

    **月の絞り込み・探すの暦と同じ形にした**（`RR.index_tabs`）── 同じ「1 つ選ぶと
    一覧が切り替わる」操作なので、別の見た目と別の仕掛けを作らない。**素のリンクなので
    JavaScript を要さず、押した先の URL がそのまま「いまどの束を見ているか」である。**

    この節は一度、**書いてあるとおりでなくなっていた** ── ここを索引の耳に変えた
    あとも「`.mchip` と同じ形にした」と書き残していたため、**注釈だけを読むと
    そろっているように見えて、画面には 2 つの形が並んでいた。**

    ## 「すべて」の札は置かない

    98 件を 1 本に並べると、札にした意味が消える。**全部を続けて読む道はすでにある** ──
    日記帳が観た日の順に全件を並べている。

    ## 「まだ答えていない」の帯を消した（起案者の指示・2026-08-25 ── 機能重複）

    **この画面にあった帯は、「未評価」（`/rate/unrated`）と同じ用を果たしていた。**
    帯は「上演が終わって答えていない分」だけを先頭に出し、余りは「未評価」へのリンクで
    逃がす作りだったが、**「未評価」は左のナビゲーションから 1 回で開ける専用の画面**
    としてすでにある。同じ一覧を 2 か所で持つと、直した先が片方だけになる事故が
    起きる ── 持たせるのは「未評価」だけにする。

    ## 代わりに「評価の分布」を先頭に置いた（同日の指示）

    もとは「眺める」にあった図（`charts.verdict_panel`）を移した。**この画面の名前が
    「評価一覧」で、開く理由が「自分がどう評価してきたか」だからである** ──
    図そのものは変えていない。

    ## 年・会場でも絞れる（起案者の指示・2026-08-26）

    「評価一覧を年とか会場の場所とかでも絞り込めるようにして」。**耳（`index_tabs`）は
    評価の下に年をもう 1 段重ねる** ── 日記帳の年の耳と同じ軸・同じ形で、選んだ評価の
    中だけを年で束ね直す。**会場は年と違って数が多い**（実測で 98 件に 39 通りの会場名が
    ある）ので、耳ではなく都道府県の絞り込み（`RR.pref_form`）と同じ、折りたたんだ
    チェックボックスの札にする（`_venue_form`）── 3〜8 枚の耳と 30 枚超の札は、
    そもそも選ぶときの操作感が違う。

    ## 「公演詳細を直す」を外した（同日の指示・機能重複の解消）

    「いま評価一覧と日記帳の機能がほぼ同じになってしまうので、評価一覧は評価が見られる
    程度の機能でよい」。**これまで `editable=True` を渡していたので、各行に題名・日付・
    会場を直す欄（`_edit_html`）が付いていた** ── これは日記帳の役目（「1 公演ごとの
    記録と、直す口を置く画面」）とまったく同じで、直した先が片方だけになる事故のもとに
    なる。**評価一覧に残すのは「評価を押し直す」（`rate_reopen`）と感想だけにする** ──
    どちらも評価そのものに属する操作で、日記帳には無い（`rate_reopen` はこの画面専用と
    決めてある）。記録そのものを直す道は日記帳に一本化する。
    """
    b = _rate_base()
    rated = b["rated"]
    verdict_fig = CH.verdict_panel([w for w in b["all"] if not w.get("unseen")])
    # 束ごとに分ける。**空の束の札は出さない**（押しても何も出ない選択肢を並べない）
    by_v = {g: sorted((w for w in rated if w["verdict"] == g),
                      key=lambda w: w.get("first_date") or "", reverse=True)
            for g in CH.VERDICT_ORDER}
    live = [g for g in CH.VERDICT_ORDER if by_v[g]]
    if not live:
        body = (f'<h1>評価一覧</h1>{verdict_fig}'
                f'<p class="empty">まだ評価が付いた記録はありません。</p>')
        return layout("評価一覧", "/rate", body, RR.STYLE, active_sub="/rate")
    # **既定は ◎ である。** 名簿の材料であり、感想の引用が返るのも ◎ の作品だけなので、
    # 確かめたくなるのはここである。**「すべて」は明示的に選んだときだけ**
    # （`v=all`。空文字は「まだ何も選んでいない」の意味のままにしておく ──
    # 年の耳と違い、評価はデフォルトで◎に絞ることに変えていないため）。
    sel = verdict if (verdict in live or verdict == "all") else (
        "◎" if "◎" in live else live[0])
    all_sorted = sorted(rated, key=lambda w: w.get("first_date") or "", reverse=True)
    chips = index_tabs(
        [("all", "すべて", len(rated))]
        + [(g, f'{g}{f" {VERDICT_LABEL[g]}" if g in VERDICT_LABEL else ""}', len(by_v[g]))
           for g in live], sel,
        lambda g: f"/rate?t=__TAGURI_TOKEN__&amp;v={quote(g)}", "評価",
        show_label=True)
    ws = all_sorted if sel == "all" else by_v[sel]

    # --- 年で絞る。**選んだ評価の中だけを、日記帳と同じ軸で束ね直す。** --------------
    years: dict[str, int] = {}
    for w in ws:
        y = (w.get("first_date") or "")[:4]
        k = y if y.isdigit() else "none"
        years[k] = years.get(k, 0) + 1
    ykeys = sorted((k for k in years if k != "none"), reverse=True)
    if "none" in years:
        ykeys.append("none")
    ysel = year if year in years else ""
    vkeep = {v for v in venues if v}

    def yurl(y: str) -> str:
        return (f"/rate?t=__TAGURI_TOKEN__&amp;v={quote(sel)}"
                + (f"&amp;y={quote(y)}" if y else "")
                + "".join(f"&amp;venue={quote(v)}" for v in sorted(vkeep)))

    # **「すべて」の耳は置く（評価の耳とは違う判断）。** 評価には「すべて」を置かない
    # （98 件を 1 本に並べると耳にした意味が消える ── 日記帳が全件を持っている）が、
    # **年は 1 つの評価の中の絞り込みなので、戻り先の「すべて」が無いと困る。**
    ytabs = index_tabs(
        [("", "すべての年", len(ws))]
        + [(k, "上演日が分からない" if k == "none" else f"{k} 年", years[k])
           for k in ykeys],
        ysel, yurl, "年", show_label=True)
    ws_y = (ws if not ysel else
            [w for w in ws if not (w.get("first_date") or "")[:4].isdigit()] if ysel == "none"
            else [w for w in ws if (w.get("first_date") or "")[:4] == ysel])

    # --- 会場で絞る。**耳ではなく都道府県と同じ折りたたみの札にする**（`_venue_form`）
    vform = _venue_form(ws_y, vkeep, "/rate",
                        {"v": sel, "y": ysel})
    ws_v = ws_y if not vkeep else [w for w in ws_y if _venue_key(w) in vkeep]

    # **文の中では括弧に入れる。** 「とても合っていたを付けた」と続いてしまう
    lab = ("すべての評価" if sel == "all" else
           f"{sel}{f'（{VERDICT_LABEL[sel]}）' if sel in VERDICT_LABEL else ''}")
    # **1 つの札の中も 15 作品ずつにする。** ○ は 47 作品あるので、札で切り替えても
    # 1 枚が画面 8 枚ぶんになる。**あふれた分の行き先は送りに書く**（消していない）
    show, now, foot = RR.paginate(
        ws_v, page, SHEET_TOP,
        lambda pg: (f"/rate?t=__TAGURI_TOKEN__&amp;v={quote(sel)}"
                    + (f"&amp;y={quote(ysel)}" if ysel else "")
                    + "".join(f"&amp;venue={quote(v)}" for v in sorted(vkeep))
                    + (f"&amp;p={pg}" if pg > 1 else "")),
        "作品")
    # **押し直す口と感想だけを出す。** 題名・日付・会場を直す欄（`_edit_html`）は
    # 出さない ── それは日記帳の役目（起案者の指示・2026-08-26）
    rows = "".join(_rec_row(w, poster=_poster_html(w), rate_reopen=True)
                   for w in show)
    body = f"""<h1>評価一覧 ── 付けた {len(rated)} 件</h1>
<p class="lede">付けた評価を ◎○△× ごとに分けています。<b>付ける基準は
「自分に合っていたか」で、作品の出来ではありません。</b>評価は作品ごとに 1 つです。
おすすめは ◎ を付けた公演の作り手から作るので、<b>ここに答えると次のおすすめが変わります。</b>
題名・日付・会場そのものを直したいときは<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>
です。</p>
{verdict_fig}
{chips}
{ytabs}
{vform}
<div class="idxsheet">
<p class="mnow"><b>{E(lab)}</b>を付けた作品を、観た日の新しい順に {now}
ほかの評価は、上のインデックスで切り替えられます。
評価をまたいで続けて読むときは<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>です。</p>
{rows}</div>
{foot}"""
    return layout("評価一覧", "/rate", body, RR.STYLE, active_sub="/rate")


def _poster_html(w: dict) -> str:
    """1 件の半券。**出し方を 1 か所に置く**（3 枚とも同じ形で出す）。"""
    f, _sid, _src = poster_of(w)
    return (f'<img class="poster" src="/img/{E(f)}?t=__TAGURI_TOKEN__" alt=""'
            f' loading="lazy">' if f else "")


def page_unrated() -> str:
    """**評価 ▸ 未評価。** 評価が付いていない記録を全部出す 1 枚。

    **上演日が分からない記録も入る。** 日付が無いと「上演が終わったか」を判定できない
    ので、一覧の帯（評価待ち）には出てこない ── **その分がどこにあるかを言う場所が
    無いと、答えたつもりで残り続ける。**
    """
    b = _rate_base()
    unrated = sorted(b["unrated"], key=lambda w: w.get("first_date") or "", reverse=True)
    # **外した分の行き先を書く。** 黙って減らすと、答えた記録がどこへ行ったのか
    # 分からない ── **戻す口はその行き先にしか無い**（`_rec_row` の「やはり観た」）
    skipped = ("" if not b["n_skip"] else
               f'<br><b>「行かなかった」を付けた {b["n_skip"]} 件は、'
               f'ここには出していません。</b>'
               f'<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>に残っていますので、'
               f'付け間違えたときはその行の「やはり観た」で戻してください。')
    body = f"""<h1>未評価 ── {len(unrated)} 件</h1>
<p class="lede">評価が付いていない記録です。<b>上演日が分からない記録も含みます</b> ──
日付が無いと上演が終わったかを判定できないので、「まだ答えていない」には出てきません。{skipped}<br>
<b>実際には観ていない公演が混じっていたら、各行の「公演詳細を直す」から外せます。</b>
券を買って行かなかった公演と、舞台ではないものが取り込まれた記録を、そこで書き分けられます
── どちらもあとで戻せます。</p>
{"".join(_rec_row(w, poster=_poster_html(w), rate_always=True, editable=True)
         for w in unrated) or '<p class="empty">評価が付いていない記録はありません。</p>'}"""
    return layout("未評価", "/rate", body, RR.STYLE, active_sub="/rate/unrated")


def page_notes() -> str:
    """**評価 ▸ 感想。** ◎ を付けたのに感想が無い作品に、一文を書き足す 1 枚。"""
    b = _rate_base()
    body = f"""<h1>感想 ── ◎ を付けた {len(b["no_note"])} 件</h1>
{_pending_notes_html(b["all"], collapsed=False)}"""
    return layout("感想", "/rate", body, RR.STYLE, active_sub="/rate/notes")


def _pending_notes_html(all_w: list[dict], collapsed: bool = True) -> str:
    """◎ なのに感想が無い作品を、**畳んだ有限の束**として置く。

    ## なぜここに置くのか

    **溜まっている分は、評価待ちとは別のことである。** 評価待ちは「観た帰りにやること」で、
    こちらは「思い出せるうちに書けること」である。同じ並びに混ぜると、**評価が済んでいる
    作品が未評価のように見える。**

    ## 畳む

    ◎ の 30 件は**急ぎでも催促でもない**。開いた状態で 15 行並べると、評価待ちの 8 件より
    大きな塊になり、**この画面の用が「感想を書く画面」に見える。**

    ## ◎ に限り、15 件ずつ出す

    引用が返るのは ◎ の作品だけなので（推薦の理由は ◎ から作る）、○ を並べると
    返りの無い入力を頼むことになる。**順序は何度も観た順・新しい順** ── 思い出せる
    度合いがそのまま書ける見込みなので、溜まった順（古い順）に出すと、いちばん
    書けないものが先頭に来る。
    """
    # **件数と一覧は同じ材料から数える。** DB の件数（`stats`）と画面の一覧（`all_w`）は
    # 一致しない ── 取り消した記録と「行かなかった」記録は一覧から落ちるので、
    # **「30 件あります」と書いて 28 件しか出ない**ことになる
    rows = IM.pending(all_w, limit=None)
    n_all = len(rows)
    rows = rows[:IM.ROUND]
    if not rows:
        return ""
    # **1 枚の画面になったので、畳まない。** 畳んで置く理由は「評価待ちより大きな塊に
    # なって、この画面の用が感想を書く画面に見える」ことだったが、**その画面自身に
    # なったのだから、その理由はもう当たらない**（起案者の指示・2026-08-24 でサブページに
    # 分けた）。呼ぶ側が畳みたいときだけ畳む
    inner = IM.pending_html(rows, n_all)
    if not collapsed:
        return inner
    return (f'<details class="more"><summary>◎ を付けた作品に、感想を書き足す'
            f'（{n_all} 件）</summary>{inner}</details>')


# ---------------------------------------------------------------- 公演詳細を直す
def mail_hints(uid: str) -> dict:
    """直すための手がかりを、メール本文から拾って返す。

    **本文は保存しない**（企画書 2 章）── 端末内のファイルをその場で読むだけである。
    出さないと当事者は直せない ── 抽出が題名を切ったとき、正しい題名はほぼ本文に
    書いてある（「公演名：…」の次の行に続きがある形）。
    """
    import rate_performances as R
    return {"uid": uid, "hints": R.mail_hints(uid, limit=12)}


def fix_work(work_key: str, *, title: str | None = None,
             shows: list[dict] | None = None) -> dict:
    """公演詳細を直し、**題名が近い記録があれば一緒に返す。**

    **直すことと、束ねるかどうかは別の操作である。** 直した題名はその場で保存する
    （本人が頼んだのはそれである）。そのうえで、**同じ公演かどうかを聞く** ──
    機械には決められないので、判定はせず、近い記録を並べて本人に確かめてもらう
    （`similar_works` の注記）。
    """
    out = _fix_work(work_key, title=title, shows=shows)
    if title is not None and not out.get("gone"):
        out["similar"] = similar_works(out.get("title") or title,
                                       out.get("work_key") or work_key)
    return out


def _fix_work(work_key: str, *, title: str | None = None,
              shows: list[dict] | None = None) -> dict:
    """1 公演の詳細（題名・回ごとの上演日・劇場）を人が確定する。

    ## なぜ「記録を見返す」に置いたか

    **間違いに気づくのは、記録を眺めているときである。** 登録の画面は入力の場だが、
    題名が違うと分かるのは一覧に並んだ題名を読んだ瞬間なので、**気づいた場所で直せないと
    直さない。** 実データでは 129 作品のうち 24 件の題名で括弧が閉じていなかった。

    ## 題名は作品ごと、上演日と劇場は回ごと

    同じ公演を 3 回観ればメールは 3 通あり、**題名は 3 通で同じだが上演日は 3 通で違う。**
    題名を回ごとに聞くと同じ文字を 3 回書かせることになり、上演日を作品ごとに聞くと
    3 回ぶんの日付が 1 つに潰れる。**軸が違うものを同じ欄で聞かない。**

    ## 直すと束ね方が変わる

    題名を直すと `work_key`（題名の鍵＋初日）が変わる。**評価と感想が宙に浮くのが
    いちばん困る失敗**なので、直した先の作品へその場で引き継ぐ。`R.reconcile` は
    引き継げない ── 鍵の一方が他方を含むことを条件にしていて、題名が丸ごと違う
    （案内文を拾っていた）場合は当たらない。**元の行は消さない**（戻せなくなる）。
    """
    import corrections as CX
    import rate_performances as R
    if title is not None and not str(title).strip():
        raise ValueError("題名を空にはできない（抽出結果に戻すなら「戻す」を押す）")
    con = R.connect()
    try:
        # **`merges` を渡し忘れると「まとめた」記録で保存が壊れる。** `_works()`
        # （画面が読む側）はここに `R.read_merges(con)` を渡しており、まとめた記録の
        # `shows` にはまとめられた側の uid も混ざって出る。ここで渡し忘れると
        # `by_uid` がそのぶんの uid を知らないまま作られ、画面が送ってきたその行を
        # 「この公演の回ではない」と誤判定して**保存そのものが全部失敗する**
        # （起案者の報告・2026-08-26 ──「観に行った日付を追加して保存しようとしたら
        # 『できなかった：この公演の回ではない』と表示された」。実データで確認 ──
        # 『チェーホフの奏でる物語』が該当）
        works = R.load_works(R.load_purchases(), R.read_splits(con), R.read_excluded(con),
                             R.read_merges(con))
        w = next((x for x in works if x["work_key"] == work_key), None)
        if w is None:
            return _fix_manual(con, work_key, title, shows)
        by_uid = {s["uid"]: s for s in w["shows"]}
        n = 0

        def put(s: dict, field: str, value: str) -> int:
            """1 項目を書き、**保存されている内容が変わったかを返す。**

            2 つのことをしている。**抽出と同じ値なら直しとして残さない** ── 画面は
            欄の中身をそのまま送るので、題名だけを直したときも上演日と劇場が一緒に
            届く。同じ値を直しとして残すと、**抽出が後で良くなっても古い値に固定され**、
            LLM に渡す実例にも差の無い行が混ざる。そして**変わっていないなら「直した」と
            言わない** ── 押したのに何も起きなかったことを、直したように書かない。
            """
            want = "" if str(value) == (s["extracted"].get(field) or "") else str(value)
            was = (s.get("fixed") or {}).get(field) or ""
            CX.save(con, s["uid"], field, want,
                    extracted=s["extracted"].get(field) or "",
                    domain=s["sender"], subject=s["subject"])
            return int(want != was)

        for uid, s in by_uid.items():
            if title is None:
                break
            n += put(s, "title", str(title))
            # **旧い画面が使っていた「1 行の splits」を消す。** 残すと題名の直しが
            # 2 か所にあることになり、どちらが効いているのか読めなくなる
            if len(R.read_splits(con).get(uid) or []) == 1:
                with con:
                    con.execute("DELETE FROM splits WHERE uid=?", (uid,))
        for row in shows or []:
            s = by_uid.get(str(row.get("uid") or ""))
            if s is None:
                raise ValueError("この公演の回ではない")
            for f in ("date", "venue", "time"):
                if row.get(f) is not None:
                    n += put(s, f, str(row[f]))
        return dict(_rekey(con, work_key, set(by_uid)), n=n)
    finally:
        con.close()


def unfix_work(work_key: str) -> dict:
    """この公演に付けた直しを全部取り消し、抽出結果に戻す。

    **戻せなければ誤操作が取り返せない。** 直しの行は消えるが、評価と感想は
    `works` の表にあるので消えない（束ね方が戻るぶん、鍵の引き継ぎだけ行う）。
    """
    import corrections as CX
    import rate_performances as R
    con = R.connect()
    try:
        works = R.load_works(R.load_purchases(), R.read_splits(con), R.read_excluded(con))
        w = next((x for x in works if x["work_key"] == work_key), None)
        if w is None:
            raise ValueError("その記録は購入から導けない（手で足した記録は直しを持たない）")
        uids = {s["uid"] for s in w["shows"]}
        for uid in uids:
            for f in CX.FIELDS:
                CX.save(con, uid, f, "")
        return dict(_rekey(con, work_key, uids), n=0, cleared=True)
    finally:
        con.close()


def _rekey(con, work_key: str, uids: set) -> dict:
    """直した後の作品を引き当て、評価・感想・手で入れた分を新しい鍵へ移す。

    ## 移した後の古い鍵の行は残さない（起案者の指摘・2026-08-26）

    **前は、移し終えた古い行をそのまま残していた。** `_works()` は「メールから
    導けず、まとめられてもいない行」を手で足した記録として拾うので、**直しただけの
    記録が、直す前の題名のまま別の記録として並んでしまっていた**（実測 ── 評価
    付きの記録の題名を直しただけで、まとめてもいないのに件数が 1 件増え、
    「公演詳細を直す」を開くと直した後の自分自身が「同じ公演です（まとめる）」の
    候補に出た）。**`unfix_work` はこの行に戻すのではなく、直しを消してから
    `_rekey` をもう一度呼ぶ**ので、消しても取り消しは壊れない。

    **この記録に、ほかの記録がまとめて入っていたら、その先も付け替える。**
    付け替えないと、直した後は「まとめた記録」が誰からも指されなくなる。
    """
    import rate_performances as R
    after = R.load_works(R.load_purchases(), R.read_splits(con), R.read_excluded(con))
    new = next((x for x in after if uids & {s["uid"] for s in x["shows"]}), None)
    if new is None:
        # 直した題名が「演劇でない」語に当たると候補から外れる。**黙って消さない**
        return {"ok": True, "work_key": work_key, "title": "", "moved": False,
                "gone": True}
    moved = False
    if new["work_key"] != work_key:
        sv = R.read_works(con).get(work_key) or {}
        if any(sv.get(k) for k in ("verdict", "chosen", "note_impression", "note_motive")):
            try:
                R.save_work(con, new, {
                    "verdict": sv.get("verdict"), "chosen": sv.get("chosen"),
                    "note_impression": sv.get("note_impression") or "",
                    "note_motive": sv.get("note_motive") or ""})
                moved = True
            except ValueError:
                pass          # 上演前になった（日付を直した）ときは評価を移さない
        # **手で入れた出演者・ポスターも同じ理由で移す。** 空欄だけ埋める
        # （`merge_works` と同じ規則）
        hand = R.read_hand(con)
        kh, oh = hand.get(new["work_key"]) or {}, hand.get(work_key) or {}
        take_fields = (not hand_credit_count(kh.get("fields") or {})
                       and hand_credit_count(oh.get("fields") or {}))
        take_poster = not (kh.get("poster") or "") and bool(oh.get("poster") or "")
        if take_fields or take_poster:
            R.save_hand(con, new["work_key"],
                        fields=(oh.get("fields") or {}) if take_fields else None,
                        poster=(oh.get("poster") or "") if take_poster else None)
        with con:
            con.execute(
                "UPDATE merges SET into_key = ?, updated_at = datetime('now','localtime')"
                " WHERE into_key = ?", (new["work_key"], work_key))
            con.execute("DELETE FROM works WHERE work_key = ?", (work_key,))
    else:
        # 鍵が同じでも、直した題名を表に映しておく（書き出しと探すが読む列である）
        with con:
            con.execute("UPDATE works SET title=?, first_date=?, last_date=?,"
                        " updated_at=datetime('now','localtime') WHERE work_key=?",
                        (new["title"], new["first_date"], new["last_date"], work_key))
    return {"ok": True, "work_key": new["work_key"], "title": new["title_display"],
            "moved": moved, "gone": False}


def _fix_manual(con, work_key: str, title: str | None, shows: list[dict] | None) -> dict:
    """購入から導けない記録（手で足した分・束ね直しで浮いた分）を直す。

    **`works` の表を直に書き換える。** 直しの表（`corrections.py`）は「メールの抽出を
    どう読み替えるか」を置く場所なので、元のメールが無い記録には使えない ──
    その代わり、`works` に持たせた `venue`／`time` の列を直に書き換える。

    **劇場・開演時刻は、メールから来た記録とは違う欄になる**（起案者の指示・2026-08-26 ──
    「メールから拾った公演じゃなくても、自分で劇場や時間を追加できるようにしてほしい」）。
    以前はここで「劇場はこの形の記録には持っていない」と言っていたが、その後
    `add_work` が会場を、この変更が時刻を `works` に直接持たせるようにしたので、
    もう成り立たない ── **抽出値との比較（`corrections.effective`）が無いだけで、
    直せないわけではない。**
    """
    import corrections as CX
    import rate_performances as R
    sv = R.read_works(con).get(work_key)
    if not sv:
        raise ValueError("その記録は見つからない")
    new_title = str(title).strip() if title is not None else (sv["title"] or "")
    date = sv["first_date"] or ""
    venue = sv.get("venue") or ""
    time_ = sv.get("time") or ""
    for row in shows or []:
        if row.get("date") is not None:
            date = CX._clean_value("date", str(row["date"]))
        if row.get("venue") is not None:
            venue = CX._clean_value("venue", str(row["venue"]))
        if row.get("time") is not None:
            time_ = CX._clean_value("time", str(row["time"]))
    key = f"{R.title_key(new_title)}#{date or 'undated'}"
    if key != work_key and R.read_works(con).get(key):
        raise ValueError("その題名・日付の記録はもう別にある")
    with con:
        con.execute("UPDATE works SET work_key=?, title=?, first_date=?, last_date=?,"
                    " venue=?, time=?, updated_at=datetime('now','localtime') WHERE work_key=?",
                    (key, new_title, date, date or sv["last_date"], venue, time_, work_key))
    return {"ok": True, "work_key": key, "title": R.norm(new_title), "moved": key != work_key,
            "gone": False, "n": 1, "manual": True}


# ---------------------------------------------------------------- 記録を見返す
_CREDIT_LEVEL: dict | None = None


def credit_level(stage_id: str) -> str:
    """その公演ページが、どれくらい確からしく結び付いたか（`fetch_credits.rank_candidate`）。

    **「同じ演目の別の上演」を黙って通さない。** CoRich のページは会場ごとに分かれるので、
    ツアーや別クールでは同じ演目の別のページに当たる ── **出演者はおおむね同じでも、
    ポスターと日程は別の上演のものである。** どちらなのかは控えに書いてあるので、
    直す欄でそのまま出す。
    """
    global _CREDIT_LEVEL
    if _CREDIT_LEVEL is None:
        _CREDIT_LEVEL = {}
        f = ROOT / "data" / "credits" / "credits.jsonl"
        if f.exists():
            for line in f.read_text(encoding="utf-8").split("\n"):
                if not line.strip():
                    continue
                c = json.loads(line)
                if c.get("stage_id"):
                    _CREDIT_LEVEL[str(c["stage_id"])] = c.get("match_level") or ""
    return _CREDIT_LEVEL.get(str(stage_id or ""), "")


_POSTER_IX: dict | None = None


def _poster_index() -> dict:
    """日付 → 公演 id の索引。**1 度だけ組む**（記録の一覧は 119 行あり、行ごとに
    組み直すと読む画面が遅くなる ── `stage_label` と同じ理由）。

    元になる `credits.jsonl` が変わるのは月 1 回の取り寄せのときで、そのあいだ画面は
    立っていないので、起動のあいだ持ち回ってよい。
    """
    global _POSTER_IX
    if _POSTER_IX is None:
        _POSTER_IX = PO.work_index()
    return _POSTER_IX


def poster_of(w: dict) -> tuple[str, str, str]:
    """記録に出すポスターを決める。返すのは (ファイル名, 公演 id, 出どころ)。

    **本人が結び付けた公演を先に見る**（起案者の指示・2026-08-24 ──「ポスターが
    間違っていたとき、後から編集できるようにしてほしい」）。**これまでは観た日から
    推測した公演しか見ていなかったので、結び付けを直してもポスターが変わらなかった**
    ── 直す口があるのに、直しても絵が変わらないのでは直せたことにならない。

    **推測を使うのは、結び付けが無いときだけにする。** 推測は「同じ日に観た公演の
    ページ」を当てているだけで、実測ではその結び付け自体が外れていることがある
    （2026-08-24 の調べで、控え 130 件のうち 80 件は観た日が結び付いたページの
    上演期間の外にあった）。**本人が確定した結び付けのほうが常に強い。**
    """
    have = PO.have()
    # **手で入れた絵が、いちばん強い。**（起案者の指示・2026-08-24 ──「公演ページが
    # 無い公演のために、ポスターと出演者を手で入れられるようにする」）**本人が選んだ
    # 1 枚を、結び付けや推測が上書きしてよい理由は無い。**
    hp = (w.get("hand") or {}).get("poster") or ""
    if hp and hp in set(have.values()):
        return hp, "", "hand"
    sid = str(w.get("stage_id") or "")
    if sid:
        return have.get(sid, ""), sid, "link"
    guess = PO.match(w["title"], w.get("first_date") or "", _poster_index())
    if guess:
        return have.get(str(guess), ""), str(guess), "guess"
    return "", "", "none"


WEEK = "月火水木金土日"


def _date_parts(iso: str) -> tuple[str, str, str]:
    """`2024-03-15` を（年・月日・曜日）に割る。**割れなければ空で返す。**

    **曜日まで出すのは、観た日を思い出す手がかりが曜日にもあるからである**
    （平日の夜か、土曜の昼か）。読み取れない日付を「不明」と書き換えて埋めない。
    """
    import datetime
    try:
        d = datetime.date.fromisoformat((iso or "")[:10])
    except ValueError:
        return "", "", ""
    return f"{d.year}", f"{d.month}.{d.day:02d}", WEEK[d.weekday()]


def _venue_of(w: dict) -> str:
    """記録の会場。**直した値を先に見て、無ければ抽出した値を見る。**"""
    if (w.get("venue") or "").strip():
        return w["venue"].strip()
    seen, out = set(), []
    for sh in w.get("shows") or []:
        v = ((sh.get("fixed") or {}).get("venue") or sh.get("venue") or "").strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    if not out:
        return ""
    return out[0] if len(out) == 1 else f"{out[0]} ほか {len(out) - 1} 会場"


def _stamp(w: dict, v: str) -> str:
    """評価を、余白に押した印として出す（起案者の指示・2026-08-24 ──「評価の◎とかの
    ハンコがもっとスタンプで押したっぽいデザインだったらよりリアル」）。

    ## 飾りだが、中身は事実である

    **枠は意匠だが、入っている字は本人が付けた評価そのものである。** 実物に見える枠に
    実物でないものを入れない ── だから枠の中に作り手が考えた語は 1 つも入れていない。

    ## 傾きは作品ごとに決めて、読み込み直しても動かさない

    **乱数にすると、開くたびに全部の印が傾き直す。** 判子は 1 回押したら向きが決まる
    ものなので、`work_key` から角度を作る（同じ記録なら毎回同じ向きに落ちる）。

    ## 「まだ判断できない」は別の色にする

    ◎○△× と同じえんじで押すと、**評価が付いた記録と見分けが付かない。**
    金にして、字の大きさも落とす（3 文字ではなく 7 文字なので円に入らない）。
    """
    rot = (sum(w["work_key"].encode()) % 13) - 6
    if not v:
        # **空の枠を残す。** 印が無いことが余白の空きとして出ないと、行によって
        # 高さが変わって上から順に読めない。**枠の中には何も書かない** ──
        # 押す口はすぐ下の行にあり、そこに何をするかが書いてある
        return (f'<span class="stamp none" data-stamp="1" style="--rot:{rot}deg"'
                f' aria-label="評価はまだ付いていません"></span>')
    hold = len(v) > 1
    return (f'<span class="stamp{" hold" if hold else ""}" data-stamp="1"'
            f' style="--rot:{rot}deg">{E(v)}</span>')


def _cast_html(people) -> str:
    """日記帳の1件に出す出演者。**「推薦の理由」と同じ枠（`.cast`）を使う**
    （起案者の指示・2026-08-26 ──「各作品あらすじとキャストをみられるようにして
    ほしい」）。

    データは `measure_nets.load_rated()` が作る `(役職, 人物名)` の一覧をそのまま使う
    ── 日記帳の記録は、公演ページから来たもの・手で足したもの・題名で結び付け直した
    ものが混ざっており、生の `fields`（公演ページの欄そのもの）を組み直すには
    `load_rated()` と同じ突き合わせが要る。**同じ結果を二重に計算しない。**
    """
    if not people:
        return ""
    cast = sorted({n for r, n in people if r == "出演"})
    others: dict[str, list[str]] = {}
    for r, n in people:
        if r in ("演出", "脚本"):
            others.setdefault(r, []).append(n)
    if not cast and not others:
        return ""
    rows = []
    if cast:
        head = "、".join(E(n) for n in cast[:RR.CAST_SHOWN])
        rest = cast[RR.CAST_SHOWN:]
        more = (f'<span class="rest">、{"、".join(E(n) for n in rest)}</span>'
                f'<button class="mrb" data-more="1">ほか {len(rest)} 名を見る</button>'
                if rest else "")
        rows.append(f'<div class="cr"><span class="cl">出演</span>'
                    f'<span class="cv">{head}{more}</span></div>')
    for role in ("演出", "脚本"):
        ns = sorted(set(others.get(role, [])))
        if ns:
            rows.append(f'<div class="cr"><span class="cl">{E(role)}</span>'
                        f'<span class="cv">{"、".join(E(n) for n in ns)}</span></div>')
    return f'<div class="cast">{"".join(rows)}</div>'


def _synopsis_html(text: str) -> str:
    """日記帳の1件に出すあらすじ。**「推薦の理由」の枠（`.syn`）と同じ畳み方にする**
    （3 行で畳み、押すと開く。既存の共通スクリプトがそのまま効く）。

    出典の確からしさの検査（`syn_block` が候補側でしている、公演ページの本文との
    照合）はしない ── **候補にすら無かった古い記録が多く、照合する相手が無い。**
    ここは事実（過去に何が取れたか）をそのまま見せるだけの場所である。
    """
    text = (text or "").strip()
    if not text:
        return ""
    return (f'<div class="syn"><p class="txt">{E(text)}</p>'
            f'<button class="mrb" data-more="1">続きを読む</button></div>')


def _rec_row(w: dict, *, poster: str = "", rate_always: bool = False,
             editable: bool = False, extra: str = "", rate_reopen: bool = False,
             id_suffix: str = "", visit_uid: str = "", visit_note: str = "") -> str:
    """1 公演の記録を 1 件出す。**1 件が 1 日ぶんの帳面になる**（起案者の指示・2026-08-24
    ──「記録を観るページは日記帳っぽいとなおいい」）。

    ## なぜ日付を余白に出したか

    **1 件ずつ読み返すときの手がかりは、題名ではなく日付である**（「あのときの」で
    思い出す）。それまで日付は題名の右に小さく添えてあり、**108 件が同じ角丸の枠で縦に
    並んで、どれも同じ重さで見えていた。**

    左の余白に日付と印を置き、境に幕の色の縦線を 1 本引く ── **枠で囲まずに 1 件を
    切れる**ので、108 件並んでも角丸の箱が 108 個並ばない。

    ## 帳面らしさは書体に頼らない

    余白・罫・日付・印で作る。明朝が入っていない端末ではゴシックに落ちるので、
    **書体が乗ったときに効く上乗せとして扱う**（`--mincho`）。

    ## `id_suffix` ── 「すべて表示」に開いたときの、図の点からの飛び先（2026-08-26）

    図の点は作品の `work_key` だけを指す。**「すべて表示」に開くと、同じ作品が複数行に
    分かれ、`id` がそのまま重なる**（HTML は同じ `id` を 2 つ以上持てない）。
    呼ぶ側（`_flatten_visits` を使う画面）が回ごとに `id_suffix` を渡すことで、
    行ごとに違う `id` にする。

    ## `visit_uid`／`visit_note` ── 「すべて表示」だけに出す、回ごとのメモ（2026-08-26）

    **渡されたときだけ出す。** 「作品でまとめる」の 1 行は複数回ぶんを畳んでいるので、
    どの回のことかが決まらない ── 呼ぶ側（`page_works` の `group=="visit"`）だけが
    `visit_uid` を渡す。中身は `_visit_note_html` を見る。
    """
    v = w.get("verdict") or ""
    # **行かなかった記録に、◎○△× は出さない。** 観ていない公演に評価を付けると、
    # その公演の作り手が名簿に入る（名簿は ◎ を付けた公演から作る）── 観ていない公演の
    # 作り手を好みの証拠にすることになる。**代わりに、戻す口をその場に置く。**
    unseen = bool(w.get("unseen"))
    if unseen:
        rate = (f'<span class="rb notseen" data-work="{E(w["work_key"])}">'
                f'<b class="nsm">行かなかった</b>'
                f'<button data-seen="{E(w["work_key"])}">やはり観た</button>'
                f'<span class="said"></span></span>')
    else:
        btns = ('<span class="rb" data-work="' + E(w["work_key"]) + '"'
                + ('' if (not v or rate_always) else ' hidden')
                + '>'
                + "".join(f'<button data-v="{g}">{g}</button>' for g in ("◎", "○", "△", "×"))
                + '<span class="said"></span></span>')
        # **付けた評価は、押してから開く口で直せるようにする**（起案者の指示で「一覧」が
        # 独立した画面になったので、**そこで押し間違いに気づいても直す口が無いのはおかしい**）。
        # **98 行に 4 つずつボタンを並べない** ── 読む一覧が記入用紙に見える。
        # 感想の欄と同じ「押してから開く」形にそろえる
        # **押し直す口は、評価の一覧にだけ出す。** 日記帳の 108 行すべてに置くと、
        # 読む一覧の 1 行ごとに押し口が 1 つ増える（1 行 30px ぶん縦に伸びる）──
        # あちらは思い出を読む画面で、直しに来る画面ではない
        rate = btns if (not v or rate_always) else (
            '<button class="wnb" data-rate-open="1">評価を押し直す</button>' + btns
            if rate_reopen else "")
    # **一部の回だけ行かなかったことも書く。** 回数が減った理由がこの行から辿れないと、
    # 「3 回買ったのに 2 回になっている」と読める
    times = ""
    if not unseen:
        n = w.get("times") or 1
        if w.get("skipped"):
            times = f"{n} 回観た（あと {w['skipped']} 回は行かなかった）"
        elif n > 1:
            times = f"{n} 回観た"
    # **会場は題名の次の行に置く。** 手で足すときに入力した値がどこにも出ていなかった
    # （感想の欄に紛れ込んだままだった）。**入力を求めたなら、読める所に出す。**
    #
    # **控えの側からも拾う。** これまでは手で足した記録の `venue` しか見ておらず、
    # **購入確認メールから取れている 62 件（120 件中）の会場が画面に 1 度も出ていなかった。**
    # 「どこで観たか」は日付と並ぶ思い出の手がかりなので、取れているものは出す。
    # **ツアーは会場数まで書く** ── 1 つだけ出すと、他の会場で観た回が無かったことになる
    where = " ".join(f'<span>{E(x)}</span>' for x in
                     (_venue_of(w), times) if x)
    imp_head, imp_box = _impression_parts(w)
    vn_head, vn_box = _visit_note_html(visit_uid, visit_note) if visit_uid else ("", "")
    y, md, wd = _date_parts(w.get("first_date") or "")
    if md:
        dt = (f'<span class="dt"><span class="y">{y}</span>'
              f'<span class="md">{md}</span><span class="wd">{wd}</span></span>')
    else:
        # **読み取れなかったことを、日付の場所に書く。** 別の所に注記を出すと、
        # 余白が空いている理由が分からない
        dt = '<span class="dt no">上演日が<br>分かりません</span>'
    pin = (f'<span class="pin">{poster}</span>' if poster
           else '<span class="pin"><span class="noposter" aria-hidden="true"></span></span>')
    # **図の点から飛べるように名前を付ける。** 年輪と地図は 1 件 1 件が識別できることを
    # 崩さない作りなので、押した先がこの行である
    return (f'<article class="rec-row{" check" if w.get("suspect") else ""}'
            f'{" skipped" if unseen else ""}"'
            f' id="w-{E(CH._anchor(w["work_key"]))}{E(id_suffix)}">'
            f'<span class="marg">{dt}{"" if unseen else _stamp(w, v)}</span>'
            f'<div class="page">'
            f'<div class="ttl">{E(w["title"])}</div>'
            + (f'<div class="where">{where}</div>' if where else "")
            # **あらすじ・出演者は会場の下に置く。** 思い出をたどる手がかりの並びに
            # 沿わせる ── 日付・題名・どこで観たか、の次に「何だったか」が来る
            + _synopsis_html(w.get("synopsis"))
            + _cast_html(w.get("people"))
            # **行の中に差し込む欄**（探す画面の「ヒットした箇所」）。題名のすぐ下に
            # 置く ── 別の行に出すと、どの記録に掛かる説明なのかが分からなくなる
            + extra
            + (f'<div class="tools">{rate}{imp_head}{vn_head}</div>'
               if (rate or imp_head or vn_head) else "")
            + imp_box + vn_box
            + (_edit_html(w) if editable else "")
            + f'</div>{pin}</article>')


def _impression_parts(w: dict) -> tuple[str, str]:
    """1 件の記録に添える感想。**押すまで入力欄を開かない**（起案者の指示・2026-08-24）。

    ## なぜ畳むか

    **記録が増えるほど、読む画面が縦に伸びる。** 実測で、この画面は 107 作品で画面
    18 枚ぶんあり、**1 行 163px のうち 76px は常に開いていた入力欄だった。** 観た本数は
    増える一方なので、1 行の高さがそのまま毎年の伸び方になる。

    **同じ判断をすでに 2 か所でしている。** 評価待ちの行（`impressions.wait_note_html`）と
    追いかけている一覧の理由欄（`render_recommend.why_note`）は、どちらも押すまで開かない。
    **並べて読む画面に入力欄を並べると、読みに来た画面が入力用紙に見える。**

    ## 書いてある感想は、入力欄ではなく文として出す

    畳んで隠すのではない ── **書いた 1 件 1 件が思い出なので、読み返せる形で出す。**
    `textarea` の中に入れておくと、読むために枠の中をなぞることになる。書き直したいときだけ
    入力欄に変える（理由欄と同じ形）。
    """
    key = E(w["work_key"])
    note = (w.get("note_impression") or "").strip()
    box = (f'<div class="inote" hidden><textarea data-note="{key}" rows="2"'
           f' placeholder="どう感じましたか（任意です。書かなくても記録は残ります）"'
           f'>{E(note)}</textarea><span class="said"></span></div>')
    if note:
        # **書いてあるものは、罫の上の 1 行として置く。** 押し口の列には混ぜない ──
        # 読み返す文が押し口と並ぶと、書いた文まで操作の一部に見える
        return ("", f'<div class="inw"><div class="inr"><span class="inl">感想</span>'
                    f'<span class="int">{E(note)}</span>'
                    f'<button class="wnb" data-note-open="1">書き直す</button></div>'
                    f'{box}</div>')
    # **まだ何も書いていないときは、押し口の列に入れる。** 評価の ◎○△× と並ぶ ──
    # どちらも「観た帰りにその場で答える」操作である
    return ('<button class="wnb" data-note-open="1">感想を書く'
            '<span class="opt">任意</span></button>',
            f'<div class="inw">{box}</div>')


def _visit_note_html(uid: str, note: str) -> tuple[str, str]:
    """1 回ぶんの、**推薦には使わないメモ。**「すべて表示」でしか出さない
    （起案者の指示・2026-08-26 ──「『すべて表示』のページだけに、今後の推薦には
    含まれないその公演用のメモ欄をつけて」）。

    ## 感想（`_impression_parts`）と何が違うか

    **感想は作品単位で 1 つ、推薦の理由にもつながる材料である。** 前の問い（回ごとに
    感想を書きたいかもしれない）に対し、**感想の欄そのものは割らないと決めた** ──
    同じ理由が回の数だけ薄まるため。**この欄は感想の代わりではなく、別の性質のもの**
    として作った。持つのは uid（1 回）だけで、`work_key` は持たない。

    **推薦の計算からは触れない。** `rate_performances.read_visit_notes`／
    `save_visit_note` は `visit_note` 表だけを読み書きし、`recommend2.py`・
    `measure_nets.py` のどちらもこの表を読まない（見出しの「推薦には使いません」は
    そのまま実装の境界でもある）。

    **見た目は感想の欄と同じ形（押すまで畳む・書いてあれば文で出す）にそろえたが、
    色は付けない**（`--curtain` を使わない）── 感想は「なぜ出てきたか」の見出しと
    同じ色にして推薦の材料であることを示しているが、**この欄はその逆を言う欄**
    なので、同じ色を使うと「これも材料になる」と誤読される。
    """
    box = (f'<div class="vnote" hidden><textarea data-vnote="{E(uid)}" rows="2"'
           f' placeholder="この回だけの覚え書き（任意。推薦には使いません）"'
           f'>{E(note)}</textarea><span class="said"></span></div>')
    if note:
        # **`.opt`（「任意」の小さな枠）は付けない。** すでに書いてある行は「任意で
        # 書けます」という誘いの段階を過ぎている ── 感想の欄（`.inr`）も同じ判断
        return ("", f'<div class="vnw"><div class="vnr"><span class="vnl">この回のメモ</span>'
                    f'<span class="vnt">{E(note)}</span>'
                    f'<button class="wnb" data-vnote-open="1">書き直す</button></div>'
                    f'{box}</div>')
    return ('<button class="wnb" data-vnote-open="1">この回のメモを書く'
            '<span class="opt">任意</span></button>',
            f'<div class="vnw">{box}</div>')



def _edit_html(w: dict) -> str:
    """公演詳細を直す欄。**畳んで置く。**

    記録を見返す画面は読む画面なので、**開いたときに全部の行に入力欄が並んでいると、
    読みに来たのか直しに来たのかが分からなくなる。** 押して開く形にすれば、
    間違いに気づいた行だけが入力の場になる。

    **抽出が何を出したかを併記する。** 直す作業は「合っているものを合っていると
    確かめる」ほうが件数として多いので、抽出値と直した値の差が見えないと確かめられない。

    **開演時刻も、日付・劇場と同じ列で直せる**（起案者の指示・2026-08-26 ──
    「日にちだけじゃなくて時間も入力できる欄を追加して」）。抽出は時刻を取れないか
    間違えることがあるので、`corrections.FIELDS` に "time" を足し、日付・劇場と
    同じ「抽出値と直した値を比べる」規則（`put`）にそのまま乗せた。

    **手で足した記録（購入から導けない分）にも、劇場・開演時刻の欄を出す**（同日の
    指示・続き ──「メールから拾った公演じゃなくても、自分で劇場や時間を追加できる
    ようにしてほしい」）。この形の記録は抽出値を持たない（比べる相手が無い）ので、
    `_fix_manual` が `works.venue`／`works.time` を直に書き換える別の道を通る ──
    見た目の欄は同じでも、保存の仕組みは分かれている。
    """
    key = E(w["work_key"])
    # **欄には、保存されている直しの文字をそのまま出す。** 一覧の題名は表示用に
    # 正規化してある（全角英数を半角に寄せた形）ので、それを欄に出すと、
    # 何も触らずに保存を押しただけで正規化した文字が直しとして保存されてしまう
    fix_t = next((s["fixed"]["title"] for s in w.get("shows") or []
                  if (s.get("fixed") or {}).get("title")), "")
    fixed_t = bool(fix_t)
    if not w.get("shows"):
        # 購入から導けない記録（手で足した分・束ね直しで浮いた分）。抽出値を持たないので
        # 「抽出: 」の併記は無いが、欄そのものはメールから来た記録と同じ形にする
        rows = (f'<div class="ed-show"><input type="date" data-ed-date="" '
                f'value="{E(w.get("first_date") or "")}">'
                f'<input type="time" data-ed-time="" value="{E(w.get("time") or "")}"'
                f' aria-label="開演時刻">'
                f'<input type="text" data-ed-venue="" value="{E(w.get("venue") or "")}"'
                f' placeholder="劇場" size="18">'
                f'<span class="ed-m">この記録はメールから来ていないので、'
                f'手で入れた内容だけが入ります。</span></div>')
        src = ""
    else:
        rows = "".join(
            f'<div class="ed-show" data-uid="{E(s["uid"])}">'
            f'<input type="date" data-ed-date="{E(s["uid"])}" value="{E(s["date"])}">'
            f'<input type="time" data-ed-time="{E(s["uid"])}" value="{E(s["time"])}"'
            f' aria-label="開演時刻">'
            f'<input type="text" data-ed-venue="{E(s["uid"])}" value="{E(s["venue"])}"'
            f' placeholder="劇場" size="18">'
            f'<span class="ed-m">抽出: '
            f'{E(s["extracted"]["date"] or "日付なし")}'
            + (f'・{E(s["extracted"]["venue"])}' if s["extracted"]["venue"] else "")
            + (f'・{E(s["extracted"]["time"])}' if s["extracted"].get("time") else "")
            + (' <b>（直した）</b>' if (s.get("fixed") or {}).get("date")
               or (s.get("fixed") or {}).get("venue")
               or (s.get("fixed") or {}).get("time") else "")
            + "</span></div>"
            for s in w["shows"])
        src = "".join(
            f'<div class="ed-src"><b>{E(s["sender"])}</b>'
            f'<span>{E(s["subject"][:90])}</span>'
            f'<span class="ed-m">抽出した題名: 「{E(s["extracted"]["title"])}」</span>'
            f'<div class="ed-hints" data-hints="{E(s["uid"])}"></div></div>'
            for s in w["shows"])
    # **まとめた記録があることを、まとめた場所に出す。** 別の場所に出すと、
    # 「2 件あったはずのものが 1 件になっている」理由がこの行から辿れない
    mg = w.get("merged") or []
    merged = (f'<button data-unmerge="{key}">まとめた {len(mg)} 件を戻す</button>'
              if mg else "")
    # **「行かなかった」を、直す欄の中にも置く。** 評価待ちの側には出してあるが、
    # 気づく場所はそこだけではない ── 記録を見返していて思い出すこともある。
    # **手で足した記録には出さない**（回を持たないので `attendance` に書けない）
    skip_btn = ("" if (w.get("unseen") or not w.get("shows")) else
                f'<button data-unseen="{key}">行かなかった</button>')
    # **無いボタンの説明を書かない。** 手で足した記録には「行かなかった」が出ないので、
    # 説明だけを出すと**押せない口を探させることになる**
    if w.get("unseen"):
        skip_lead = ('<b>この記録には「行かなかった」が付いています。</b>'
                     '観た本数と図、評価待ちからは外れています ── '
                     'この行の上にある「やはり観た」で戻せます。<br>')
    elif skip_btn:
        skip_lead = ('<b>「行かなかった」は、券を買って観に行かなかった公演に'
                     '付けてください。</b>記録は残ったまま、観た本数と図、'
                     '評価待ちから外れます（あとで戻せます）。<br>')
    else:
        skip_lead = ""
    mg_note = ("" if not mg else
               '<p class="ed-lead">この記録には、同じ公演としてまとめた記録が入っています ── '
               + "、".join(f'「{E(m["title"])}」' for m in mg[:4])
               + (f' ほか {len(mg) - 4} 件' if len(mg) > 4 else "") + "。</p>")
    # **結び付けは、直す欄の中に置く。** 題名と上演日を直すのと同じ「この記録を正しくする」
    # 作業であり、別の画面に出すと、間違いに気づいた場所から辿れない
    sid = w.get("stage_id") or ""
    # **3 通りを書き分ける。** 「結び付いていません」を材料の取れている記録にも出すと、
    # **直す必要の無いものを直せと促すことになる**（実データで 66 件がそれに当たる）
    if sid and w.get("auto_linked"):
        link_note = ("<b>題名から探して、自動で結び付けました。</b>合っているか確かめて"
                     "ください ── <b>違う公演だと、観ていない公演の作り手が名簿に入ります。</b>"
                     "違っていたら「結び付けを外す」を押してください。")
    elif sid:
        link_note = "この公演の出演者・作り手・あらすじを、おすすめの材料にしています。"
    elif w.get("has_credits"):
        link_note = ("メールから公演ページを引けているので、<b>この記録はすでにおすすめの材料に"
                     "なっています。</b>結び付けは要りません ── 別の公演の情報が出ていたら、"
                     "ここで正しい公演を選び直してください。")
    elif hand_credit_count((w.get("hand") or {}).get("fields") or {}):
        # **「推薦に効きません」と書き続けない。** 手で入れた出演者は名簿に入るので、
        # 結び付いていなくても効いている ── **事実でないことを画面に出さない**
        link_note = ("<b>この記録は、どの公演とも結び付いていません。</b>そのかわりに、"
                     "下の欄に手で入れた出演者と作り手がおすすめの材料に入っています。"
                     "公演ページが見つかったときは、上の欄で選ぶとあらすじも一緒に入ります。")
    else:
        link_note = ("<b>この記録は、まだどの公演とも結び付いていません。</b>結び付けると、"
                     "その公演の出演者・作り手・あらすじがおすすめの材料に入ります ── "
                     "<b>結び付いていない記録は、評価を付けてもおすすめには効きません。</b>"
                     "公演ページが見つからないときは、下の欄に手で入れられます。")
    # **結び付いていても、選び直す欄を出す。**（起案者の指示・2026-08-24 ──「ポスターが
    # 間違っていたとき、後から編集できるようにしてほしい」）**これまでは、結び付いている
    # 記録には「外す」しか無かった** ── 違う公演に付いていることに気づいても、
    # 一度外してから探し直すことになり、**外した状態で探し当てられないと材料ごと失う。**
    link = (f'<div class="ed-link" data-work="{key}">'
            f'<span class="ed-lk">おすすめに使う公演</span>'
            + (f'<span class="ed-lv{" auto" if w.get("auto_linked") else ""}">'
               f'{E(stage_label(sid))}</span>'
               f'<button data-unlink="{key}">結び付けを外す</button>' if sid else "")
            # **欄には、いまの題名を最初から入れておく**（起案者の指示・2026-08-26）。
            # 空欄だと、まず自分でこの記録の題名を打ち直すところから始まる ──
            # 直した題名（`fix_t`）があればそれを、無ければ元の題名を出す
            + f'<input type="text" data-lk-q="{key}" size="24" autocomplete="off"'
              f' value="{E(fix_t or w["title"])}"'
              f' placeholder="{"別の公演に付け替える" if sid else "公演の題名で探す"}">'
              f'<button data-lk-web="{key}">{IC.ico("search")}CoRichの公演情報から探す</button>'
              f'<span class="said"></span><div class="lk-sug"></div>'
            + "</div>")
    # **ポスターは、いま何が出ているかと、どこから来たかを一緒に出す。**
    # **絵だけを出すと、違っていることに気づいても直せる場所が分からない。**
    pf, _psid, psrc = poster_of(w)
    pimg = (f'<img src="/img/{E(pf)}?t=__TAGURI_TOKEN__" alt="" loading="lazy">'
            if pf else '<span class="ed-pn"></span>')
    lvl = credit_level(_psid) if _psid else ""
    tour = ("<br><b>これは、同じ演目でも別の会場・別の時期の上演のページです。</b>"
            "出演者はおおむね同じですが、ポスターと日程はその上演のものです。"
            if lvl == "同じ演目の別の上演" else "")
    if pf and psrc == "link":
        pnote = ("<b>結び付けた公演のポスターです。</b>付け替えると、こちらも入れ替わります。"
                 + tour)
    elif pf:
        pnote = ("<b>観た日から推測して出しています。</b>違っていたら、上の欄で正しい公演を"
                 "選んでください ── <b>選ぶとポスターも入れ替わります。</b>" + tour)
    elif sid:
        pnote = ("結び付けた公演のポスターは、まだ手元にありません"
                 "（月 1 回の取り寄せのときに一緒に写しています）。")
    else:
        pnote = ("この記録にポスターはまだありません。上の欄で公演を選ぶと、"
                 "その公演のポスターが出ます。")
    if psrc == "hand":
        pnote = ("<b>手で入れたポスターです。</b>下の「ポスター・クレジットを手入力する」から"
                 "入れ替えられますし、外すと元の絵に戻ります。")
    poster_row = (f'<div class="ed-pos"><span class="ed-lk">ポスター</span>'
                  f'<span class="ed-pv">{pimg}</span>'
                  f'<span class="ed-m">{pnote}</span></div>')
    hand_box = _hand_html(w, key)
    return f"""<details class="editor" data-work="{key}">
<summary>公演詳細を直す{'（直してあります）' if fixed_t else ''}{f'・まとめた {len(mg)} 件' if mg else ''}</summary>
{mg_note}
<p class="ed-lead">題名は<b>作品ごと</b>に、上演日と劇場は<b>観た回ごと</b>に直せます。
直した内容は次の取り込みにも効きます ── 同じ発行元が同じ題名を出したら、
自動で直した側になります。</p>
<label class="ed-t">題名
 <input type="text" data-ed-title="{key}" value="{E(fix_t or w["title"])}" size="44"></label>
{link}
{poster_row}
<p class="ed-lead">{link_note}</p>
{hand_box}
{rows}
<div class="ed-btns"><button data-fix="{key}">この内容で保存する</button>
 <button data-unfix="{key}">抽出結果に戻す</button>
 <button data-mail="{key}">メールの中身を見る</button>
 {merged}{skip_btn}<button class="danger" data-drop="{key}">この記録を取り消す</button>
 <span class="said"></span></div>
<p class="ed-lead">{skip_lead}
<b>「この記録を取り消す」は、舞台ではないものが取り込まれてしまったときです。</b>
この記録は一覧から外れますが、<b>消してはいません</b> ──
「設定」の「取り消した記録」から、いつでも戻せます。</p>
<div class="ed-mail" hidden>{src}</div></details>"""


def _hand_html(w: dict, key: str) -> str:
    """ポスター・クレジットを手入力する欄。**畳んで置く。**

    起案者の指示（2026-08-24）──「公演ページが無い公演のために、ポスターと出演者を
    手で入れられるようにする」。**見出しは「ポスターと出演者を手で入れる」→
    「ポスター・クレジットを手入力する」に改めた**（起案者の指示・2026-08-26）。

    **畳むのは、ふだん使う欄ではないからである。** 公演ページが見つかる公演では、
    上の「推薦に使う公演」で選ぶほうが速いし確かである（1 度の操作で出演者・作り手・
    あらすじ・ポスターが全部入る）。**ここは、探しても見つからなかった公演の行き先である。**

    **開く前に、いま入っている人数を見出しに出す。** 入れたのに何も起きていないように
    見えるのがいちばん困るので、**畳んだままでも入っていることが分かる形にする。**
    """
    hand = w.get("hand") or {}
    hf = hand.get("fields") or {}
    n = hand_credit_count(hf)
    hp = hand.get("poster") or ""
    boxes = "".join(
        f'<label class="hand-f">{E(label)}'
        + (f'<span class="hand-h">{E(hint)}</span>' if hint else "")
        + f'<textarea data-hand="{E(field)}" rows="{3 if field == "スタッフ" else 2}"'
          f' placeholder="">{E(hf.get(field) or "")}</textarea></label>'
        for field, label, hint in HAND_FIELDS)
    # **入れた絵は、その場に出す。** 選んだ直後に絵が変わらないと、写せたのかが分からない
    pv = (f'<img src="/img/{E(hp)}?t=__TAGURI_TOKEN__" alt="">' if hp
          else '<span class="ed-pn"></span>')
    off = (f'<button data-hand-off="{key}">手で入れた絵を外す</button>' if hp else "")
    return f"""<details class="hand" data-work="{key}">
<summary>ポスター・クレジットを手入力する{f'（出演者 {n} 名を入れてあります）' if n else ''}{'・ポスターを入れてあります' if hp else ''}</summary>
<p class="ed-lead"><b>公演ページが見つからない公演は、ここに直に書けます。</b>
書いた出演者と作り手は、<b>次のおすすめの材料になります</b>（◎ を付けた公演の作り手として
数えます）。<b>公演ページから取れている分は消えません</b> ── ここに書いた分を足します。</p>
<div class="hand-p"><span class="ed-pv">{pv}</span>
 <label class="hand-file">ポスターの画像を選ぶ
  <input type="file" accept="image/*" data-hand-img="{key}"></label>
 {off}<span class="said"></span>
 <span class="hand-h">端末の中に写すだけで、どこにも送りません。JPEG・PNG・WebP・GIF、
  12MB までです。</span></div>
{boxes}
<div class="pfoot"><button data-hand-save="{key}">この内容で名簿に入れる</button>
 <span class="said"></span></div>
</details>"""


def _dropped_html() -> str:
    """取り消した記録の管理。**「設定」の 1 枚の札にする。**（起案者の指示・2026-08-26
    ──「取り消した記録の管理は設定で行うようにして」）。

    **もとは日記帳の下に畳んで置いていた。** 日記帳を開く理由は思い出を読むことで
    あって外した記録の後始末ではないので、そこに常設するのは筋が違った ──
    「たまにしか押さない道具」を集める場所は、すでに「設定」にある
    （書き出す・別の端末に記録を移す）。同じ理由でここへ移した。

    **空でも節を出す。** 出しておかないと、取り消したものがどこへ行ったのかが画面から
    分からず、「消えた」と読まれる ── 戻せることが伝わらなければ、取り消しは押されない。

    **ボタンは他の札と同じ形にする**（起案者の指摘・2026-08-26 ──「ボタンのデザインを
    サイトの他デザインとも統一して」）。以前は `.drop-row button` に見た目を持たせて
    おらず、丸い錠剤形（`.card button` の規約）を持つ他の押し口と違って見えていた。
    ここも `.card` の中に置くことで、同じ規約をそのまま使う。
    """
    rows = dropped_works()
    if not rows:
        return f"""<details class="card">{_card_h2("check", "取り消した記録")}
<p class="lead">取り消した記録はありません。<b>まちがって取り込まれたものは、
各行の「公演詳細を直す」を開いて「この記録を取り消す」から外せます</b> ──
外した分はここに並び、いつでも戻せます。</p></details>"""
    body = []
    for r in rows:
        n = r["n"]
        how = f"メール {n} 通ぶん" if not r["legacy"] else f"以前に外した分・{n} 通ぶん"
        body.append(f'<div class="drop-row"><span class="dt">{E(r["title"])}</span>'
                    f'<span class="dm">{E(how)}</span>'
                    f'<div class="drop-btns">'
                    f'<button data-restore="{E(r["key"])}">戻す</button>'
                    f'<button class="danger" data-purge="{E(r["key"])}">完全に取り消す</button>'
                    f'</div><span class="said"></span></div>')
    return f"""<details class="card">{_card_h2("check", "取り消した記録",
     f'<span class="badge part">{len(rows)} 件</span>')}
<p class="lead">一覧・評価待ち・おすすめの材料から外してあるだけなので、
「戻す」を押せばもとに戻ります。メールそのものは消していません。<b>「完全に取り消す」
はこの一覧からも消します</b> ── 外した状態は変わりませんが、戻す口が無くなります。</p>
{"".join(body)}</details>"""


def _skipped_html() -> str:
    """「行かなかった」公演の管理。**「設定」の 1 枚の札にする**（起案者の指示・
    2026-08-26 ──「他の実装と同様に、行かなかったにしたものは設定画面で管理して、
    設定から『やはり観た』で復帰できるようにしてください」）。

    **もとは日記帳の年の外の専用の耳に置いていた**（同じ日の先の指示 ──「日記帳で
    『行かなかった』を選んだ作品は日記帳から消して」への対応）。**「取り消した記録」
    が同じ理由（たまにしか押さない道具は設定に集める）で設定へ移ったので、こちらも
    そろえた**（起案者の言う「他の実装」）。**日記帳には、耳も含めて一切出さない。**

    **空でも節を出す**（`_dropped_html` と同じ理由）。出しておかないと、
    「行かなかった」と答えた記録がどこへ行ったのか画面から分からない。

    **札の形は `_dropped_html` と同じにする**（`.drop-row`／`.drop-btns`）。
    押せるのは「やはり観た」の 1 つだけで、二重に確認する操作でもない ── 「戻す」と
    同じ重さの操作なので、同じ見た目にする。
    """
    rows = [w for w in _works() if w.get("unseen")]
    if not rows:
        return f"""<details class="card">{_card_h2("check", "行かなかった公演")}
<p class="lead">「行かなかった」と答えた公演はありません。<b>評価待ちや日記帳の
各行で「行かなかった」を押すと、ここに並びます。</b></p></details>"""
    body = []
    for w in rows:
        _y, md, _wd = _date_parts(w.get("first_date") or "")
        when = f"{_y}年{md.split('.')[0]}月{int(md.split('.')[1])}日" if md else "上演日が分かりません"
        body.append(f'<div class="drop-row"><span class="dt">{E(w["title"])}</span>'
                    f'<span class="dm">{E(when)}</span>'
                    f'<div class="drop-btns">'
                    f'<button data-seen="{E(w["work_key"])}">やはり観た</button>'
                    f'<span class="said"></span></div></div>')
    return f"""<details class="card">{_card_h2("check", "行かなかった公演",
     f'<span class="badge part">{len(rows)} 件</span>')}
<p class="lead">券を買ったが「行かなかった」と答えた公演です。件数と図には数えていません。
<b>「やはり観た」を押すと、観た記録に戻ります。</b></p>
{"".join(body)}</details>"""


def _records_empty_note() -> str:
    """記録が 1 件も無いときに、図の代わりに出す文。**空欄のまま見出しだけを残さない。**"""
    return ('<p class="pnow">観た公演の記録がまだ無いので、図は出せません。'
            '<a href="/register?t=__TAGURI_TOKEN__">公演情報の登録</a>で'
            '購入確認メールを取り込むか、観た公演を手で足すと、'
            '<b>本数・評価の分かれ方・行った場所・時期</b>がここに出ます。</p>')


def _compare_empty_note() -> str:
    """これからの公演との比較が出せないときの文。**何件たまれば出るのかまで書く。**"""
    return ('<p class="pnow">まだ比べられません。'
            'ここはこれから観られる公演の一覧と観た記録を並べて差を出す画面なので、'
            '記録が入ると出るようになります。</p>')


def _check_line(n: int) -> str:
    """読み取りを間違えた記録の件数を書く行。**0 件のときに「この 0 件」と書かない。**"""
    if not n:
        return ("<b>いまのところ、読み取りを間違えたらしい記録はありません。</b>"
                "見つかったものは、この一覧の先頭に出します。")
    return (f"購入確認メールからの読み取りに失敗した跡がある記録が {n} 件あります"
            f"（括弧が閉じていないなど）。<b>この {n} 件を先に出しています。</b>"
            f"直した内容は、次の取り込みと公演ページの検索にも効きます。")


def _d3_tag(*panels: str) -> str:
    """同梱した d3 を読む札。**使う図が 1 つでもあるときだけ置く。**

    **図の側に置いてはいけない。** はじめは「作り手の再会」の中に書いていたが、d3 を使う
    図が 2 つになったとき、**後の図が前の図の札にぶら下がる形**になっていた ── 並び順を
    入れ替えると、後の図が黙って描かれなくなる。**依存を並び順に持たせない。**

    図が無いときは置かない ── 280KB を読ませる意味が無い。
    """
    if not any(x.strip() for x in panels):
        return ""
    return '<script src="/vendor/d3.js?t=__TAGURI_TOKEN__"></script>'


# **評価の 3 枚。** 一覧（見る）→ 未評価（答える）→ 感想（書き足す）の順を示すデータ。
# **画面には帯として出していない**（起案者の指摘・2026-08-25 で段の帯を全廃した）。
# `test_design.py` がこの並びとラベルを直接検査しているので、データとしては残す。
SUB_RATE = (
    ("/rate", "評価一覧", "check", "付けた評価を ◎○△× ごとに見ます"),
    ("/rate/unrated", "未評価", "clock", "まだ評価が付いていない記録です"),
    ("/rate/notes", "感想", "pencil", "◎ を付けた作品に感想を書き足します"),
)

# ◎○△× が何を言っているかを、画面に出す言葉で持つ。**作品の出来ではなく
# 「自分に合っていたか」である**（`render_recommend.waiting_html` に書いてある基準）
VERDICT_LABEL = {
    "◎": "とても合っていた", "○": "合っていた",
    "△": "あまり合わなかった", "×": "合わなかった",
}




def _records_base() -> dict:
    """3 つの画面が共通で使う材料と件数。**数え方を 1 か所に置く。**

    起案者の指示（2026-08-24）──「『見返す』の中でも 3 章に分かれてると思うのですが、
    それぞれページを独立させて左のナビゲーションバーから飛べるようにして」。

    **分けたあとに数え方が分かれるのがいちばん危ない。** 同じ「観た作品数」が画面ごとに
    違う数字で出ると、どちらが本当なのか読み手には確かめようがない。**行かなかった記録を
    除く判断も、ここ 1 か所でしか行わない。**
    """
    ws = _works()
    # **行かなかった公演を「観た」に数えない。** 図と件数は観た記録だけで作る ──
    # 観ていない公演を本数・年輪・地図に入れると、**行っていない劇場に点が立つ。**
    # **一覧からは外さない** ── 買った事実は残っているし、戻す口がこの行にしか無い
    seen_ws = [w for w in ws if not w.get("unseen")]
    try:
        import measure_nets as M
        rated_rows = M.load_rated()
    except Exception:                                               # noqa: BLE001
        rated_rows = []
    return {
        "ws": ws, "seen": seen_ws, "rated_rows": rated_rows,
        "n_skip": len(ws) - len(seen_ws),
        # **ポスターの枚数は、行を組まずに数える。** 年で畳む形なので行は
        # `_rows_by_year` が組む ── ここで全件を組むと同じ行を 2 回作ることになる
        "n_pos": sum(1 for w in ws if poster_of(w)[0]),
        "n_rated": sum(1 for w in seen_ws if w.get("verdict")),
        "n_notes": sum(1 for w in seen_ws if (w.get("note_impression") or "").strip()),
    }


def _synopsis_by_key() -> dict[str, str]:
    """観た記録（学習側）のあらすじを、`work_key → あらすじ` の形にする。

    `tools/credits/extract_theme_llm.py --side rated` が書く `themes.jsonl` の `id` は、
    `measure_nets.load_rated()` と同じ経路（`state.works` の `work_key`）を通っているので、
    そのまま突き合わせられる。**空のあらすじ（本文が取れなかった行）は入れない**
    ── 空文字を入れると、日記帳の側で「取れませんでした」と出す・出さないの判定が
    ここと `_synopsis_html` の 2 か所に分かれる。
    """
    path = ROOT / "data" / "credits" / "themes.jsonl"
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("side") != "rated":
            continue
        syn = (r.get("synopsis") or "").strip()
        if syn:
            out[r.get("id") or ""] = syn
    return out


def _records_lede(d: dict) -> str:
    """3 つの画面に共通で置く、母数と守りの 1 段落。

    **どの画面から入っても同じことが言えるようにする。** 分けた結果「外に出していない」と
    書いてある画面と書いていない画面ができると、**書いていない画面では外に出していると
    読める。** 母数（観た作品数）も同じ理由で全画面に置く。
    """
    skip = ("" if not d["n_skip"] else
            f'<br>「行かなかった」と答えた {d["n_skip"]} 件は、件数と図から外しています。'
            f'「日記帳」には出さず、「設定」の「行かなかった公演」にまとめてあり、'
            f'「やはり観た」で戻せます。')
    return (f'<p class="lede">観た記録は <b>{len(d["seen"])} 作品</b>です'
            f'（評価が付いているのは {d["n_rated"]} 件、感想が書いてあるのは '
            f'{d["n_notes"]} 件）。この画面の数字は、すべて手元のデータだけで作っています。'
            f'{skip}</p>')


def page_records() -> str:
    """記録を見返す ▸ **眺める。** 図で見る画面と、これから上演される公演との差を
    見る画面（もとの「比べる」）を、1 枚に統合した画面。

    ## なぜ 3 つに分けたか（2026-08-24 の判断）

    1 枚の画面に「図で見る」「これからの公演と比べる」「1 公演ごとに読む」が縦に並んでいた。
    **この 3 つは、開く理由が違う。** 図は全体の形を見に来るとき、比べるは自分の偏りを
    知りたいとき、日記帳は 1 本の公演を思い出したいとき ── **同じ画面に積むと、いちばん下の
    「日記帳」に用がある人が毎回 8 枚の図を通り過ぎることになる。**

    **図の点を押すと「日記帳」の行へ飛ぶ**（`charts.ROW_HREF`）。分けても、図から 1 件に
    降りる道は切らない ── **1 件 1 件が識別できないと振り返りの図は無価値である。**

    ## 「眺める」と「比べる」を統合した（起案者の指示・2026-08-26）

    「比べると眺めるを統合して」。**2026-08-24 の判断（上）を覆すのではない** ──
    「比べる」を分けた理由は「自分の記録の確認」と「これからの公演との差」の区別を
    画面の名前で言えるようにすることだったが、**日記帳のような「開く理由が違う画面」
    ほどの距離が、この 2 つの間には無かった**。両方とも「観た記録をもとに図を見る」
    画面で、開く場所（「記録を見返す」の中）も対象読者も同じである。**1 つの見出し
    （`<h2>比べる ── これから上演される公演との差</h2>`）で区切り、同じページの中で
    続けて読める形にした。** `/records/compare` は無くなり、この画面（`/records`）に
    一本化した。

    ## 年表を先頭に置き、「年ごとの本数」の棒はそこへ畳んだ（2026-08-25）

    起案者の指示 ──「『観劇史』と銘打って表示するくらいなら、もっとその人の年表らしい
    ものを書いたほうがいい」。**年ごとの本数の棒は、年表の左の列がそのまま持っている**
    ので、同じ数字を 2 か所で出すのをやめた（`tools/taguri/chronicle.py`）。
    **残りの図は残す** ── 劇場・地図・人の流れは、年の軸では出ない話である。

    ## 「一緒に出てくる人の網」を、独立した画面へ出した（2026-08-25）

    起案者の指示 ──「画像みたいな相関図を自動生成するページをつくってほしい」。
    **8 枚の中の 1 枚では狭い** ── 専用の画面にしてほしいという指示なので、ここからは
    外し、`page_network`（`/records/network`）へ移した。中身（`people.py` の `panel`）は
    変えていない。

    ## 独立させたのをやめ、この画面へ戻した（起案者の指示・2026-08-27）

    「独立した『相関図』のページを消して、眺めるに移動して」。**上の判断（8 枚の
    中の 1 枚では狭い）を誤りだったとして覆すのではない** ── 実際に独立させて
    使ってみたところ、この形にしてほしいという指示があったので戻す。`page_network`
    （`/records/network`）は削除し、この画面の `<div class="figs">` へ `PE.panel()`
    を戻した。**中身（図そのもの・時間のつまみ・LLM の読み）は変えていない。**

    ## 「評価の分布」を「評価一覧」へ移した（起案者の指示・2026-08-25）

    **図そのものは変えていない**（`charts.verdict_panel`）。開く理由が「自分がどう
    評価してきたか」という、この画面ではなく「評価一覧」（`/rate`）の話だったので、
    そちらの先頭へ移した。同じ図を 2 か所に出すと、直した先が片方だけになる事故が起きる。

    ## 「観劇の年表」も、独立した画面へ出した（起案者の指示・2026-08-26）

    「『観劇の年表』を独立した『観劇史年表』というページにして独立させて」。**「相関図」を
    独立させたのと同じ判断** ── 先頭に置いたとはいえ、8 枚の中の 1 枚では、
    年表だけを見たい人にとっては狭い。`page_chronicle`（`/records/chronicle`）へ移した。
    中身（`chronicle.py` の `panel`）は変えていない。

    ## 「作り手の再会」を外した（同日の指示・機能重複の解消）

    「『眺める』の『作り手の再会』…は消してよい」。**中身（`timeline.py`）は削除して
    いない** ── 呼ぶ先を無くしただけである。似た問い（1 人ずつの続き方）は「たどる」
    （`page_trace`）でも 1 本ずつ追えるので、一望する図としては storyline（`SL.panel`。
    「観る世界が乗り換わっている」を言う、こちらしか言えない図）だけを残した。

    ## 「上演日数の偏り」「料金」「座組の大きさ」「まだ行っていない劇場」を外した
    （同日の指示）

    「『比べる』の…『上演日数の偏り』『料金』…『座組の大きさ』…『まだ行っていない
    劇場』は消してよい」。**「上演日数の偏り」「料金」は図そのもの（`render_lookback.py`
    の `run_panel`／`price_panel`）を削除し、そこから読み取っていた「気づき」の行 2 つ
    も `action_panel` から外した** ── 根拠の表が無いまま気づきだけが残ると読めない。
    **「座組の大きさ」（`compare.py` の `panel`）と「まだ行っていない劇場」
    （`venues.py` の `open_panel`）は呼ばなくなったが、中身は削除していない。**
    """
    d = _records_base()
    seen_ws, rated_rows = d["seen"], d["rated_rows"]
    sl_html = SL.panel(rated_rows) if rated_rows else ""
    if not d["seen"]:
        # **記録が 0 件のときに、内部の失敗文言を画面に出さない。** 以前はここで
        # 例外が起き、`max() iterable argument is empty` がそのまま出ていた。
        # **空は失敗ではないので、空として書く。**
        cmp_panels, lstyle = "", ""
    else:
        try:
            import render_lookback as RL
            # **足した 2 軸は「まだ比較できない軸」の前に入れる。** できないことの説明は、
            # できることを全部並べたあとに来ないと読めない
            # **比べる相手が何かは、いちばん先に置く**（どの図にも同じように掛かる）
            cmp_panels, lstyle = RL.body(_compare_panel(rated_rows),
                                         head=_pop_note(rated_rows)), RL.STYLE
        except Exception:                                           # noqa: BLE001
            cmp_panels = ('<p class="empty">これからの公演との比較は、いまの記録では組めませんでした。'
                          '観た公演が増えると出るようになります。</p>')
            lstyle = ""
    body = f"""<h1>眺める ── 図で見る</h1>
{_records_lede(d)}
{_records_empty_note() if not seen_ws else ""}
<div class="figs">
{CH.spiral_panel(seen_ws)}
{CH.map_panel(seen_ws)}
{CH.venue_panel(rated_rows, shows_by_key={
    w["work_key"]: [s["venue"] for s in (w.get("shows") or [])
                    if s.get("attended", True) and s.get("venue")]
    for w in seen_ws})}
{_d3_tag(sl_html)}{sl_html}
{PE.panel(rated_rows)}
</div>
<h2>比べる ── これから上演される公演との差</h2>
<p class="lede">観た記録を、これから観られる公演の一覧と並べて、差の大きいところを出しています。</p>
{'' if d["seen"] else _compare_empty_note()}
<div class="figs">{cmp_panels}</div>"""
    return layout("眺める", "/records", body,
                  RR.STYLE + SL.STYLE + lstyle, active_sub="/records")


def page_chronicle() -> str:
    """記録を見返す ▸ **観劇史年表。** 記録を年の順に並べ、その年に何が始まったかを見る画面。

    起案者の指示（2026-08-26）──「『観劇の年表』を独立した『観劇史年表』というページに
    して独立させて、『記録を見返す』の下において」。**新しく作った図は無い** ── 「相関図」を
    独立させたときと同じ判断で、もとは「眺める」の図の 1 枚（`chronicle.py` の `panel()`）
    だったものを、専用の画面がほしいという指示に沿ってそこから外し、ここへ移しただけ
    である。中身（事実の抽出・図・LLM の読み）は変えていない。
    """
    d = _records_base()
    main = CR2.panel(d["seen"], d["rated_rows"])
    if not main:
        # **落ちても「記録を見返す」の他の画面は生きている。** ここだけ空にする
        # （`page_trace` と同じ判断）
        main = ('<section class="card"><p class="empty">まだ年表を描けるだけの'
                '記録がありません。上演日の分かる記録が増えると出るようになります。'
                '</p></section>')
    body = f"""<h1>観劇史年表 ── 何が始まった年か</h1>
{_records_lede(d)}
{main}"""
    return layout("観劇史年表", "/records/chronicle", body,
                  RR.STYLE + CR2.STYLE, active_sub="/records/chronicle")


def _pop_note(rated_rows: list) -> str:
    """比べる相手を名指しする 1 枚。**落ちても画面は出す。**"""
    try:
        return CP.pop_note(rated_rows)
    except Exception:                                               # noqa: BLE001
        return ""


def _compare_panel(rated_rows: list) -> str:
    """題材・作りの型を、これからの公演と比べる 2 枚。**落ちても画面は出す。**

    **「座組の大きさ」は外した**（起案者の指示・2026-08-26 ──「『比べる』の…
    『座組の大きさ』…は消してよい」）。`compare.py` の `panel()` 側で外している ──
    ここでは呼び分けない。
    """
    if not rated_rows:
        return ""
    try:
        return CP.panel(rated_rows)
    except Exception:                                               # noqa: BLE001
        return ""


def page_trace(name: str = "", via: str = "") -> str:
    """記録を見返す ▸ **たどる。** 1 つの名前を選び、その名前が通っている公演を読む画面。

    起案者の指示（2026-08-25）── 案 1（名前をつまむと、その名前が通っている公演が
    手元に並ぶ）と案 2（そこから次の名前へ乗り換わった道筋）。仕様は
    `docs/000007-records-trace-spec.md`。

    **図と件数の作り方は `trace.py` に置く。** この関数は材料を渡して外枠を着せるだけで
    ある ── 数え方を画面の側に書くと、`_records_base` に 1 か所だけ置いた数え方が
    画面ごとに分かれる。
    """
    d = _records_base()
    try:
        main = TR.body(d["rated_rows"], name, via)
    except Exception:                                               # noqa: BLE001
        # **落ちても「記録を見返す」の他の画面は生きている。** ここだけ空にする
        main = ('<section class="card"><p class="empty">この線は、いまの記録では'
                '組めませんでした。観た公演が増えると出るようになります。</p></section>')
    body = f"""<h1>たどる ── 1 つの名前をたどる</h1>
{_records_lede(d)}
<p class="lede">名前を 1 つ選ぶと、<b>その名前をいつ知って、そこから何につながったか</b>が出ます。
何本観たか・どの劇場が多いかは「眺める」で見られます。</p>
{main}"""
    return layout("たどる", "/records/trace", body,
                  RR.STYLE + TR.STYLE, active_sub="/records/trace")



def _flatten_visits(ws: list[dict]) -> list[dict]:
    """「作品でまとめる」の記録を、「すべて表示」の行に開く（起案者の指示・2026-08-26 ──
    「日記で『作品ごと』にくくるのと、行った公演数分表示するの（同じ作品でも複数回
    行ってるなら複数回羅列）と2つを選べるようにして」。名前は後から
    「作品でまとめる」「すべて表示」に改めた）。

    **開けるのは、購入の控えから来た `shows`（回ごとの日付・会場を持つ）が 2 件以上
    ある記録だけ。** 手で足した記録（`add_work`）は 1 回ぶんの日付しか持たず、
    複数回観たことを回ごとに分ける材料が無い ── 開かずに、そのまま 1 行で出す。

    **開いた行は、日付・会場・`shows` だけ差し替えた作品のコピーである。** 評価・感想・
    出演者・ポスターは作品ぶんしか無い（回ごとには持っていない）ので、同じ値をそのまま
    複製する ── 「劇作家の苦悩に心揺さぶられた」という感想は、観た 5 回のどの日にも
    等しく紐づく。
    """
    out = []
    for w in ws:
        shows = [s for s in (w.get("shows") or []) if s.get("attended")]
        if len(shows) <= 1:
            out.append(w)
            continue
        for sh in shows:
            out.append({**w, "first_date": sh.get("date") or w.get("first_date"),
                        "last_date": sh.get("date") or w.get("last_date"),
                        "venue": "", "times": 1, "shows": [sh]})
    out.sort(key=lambda w: w.get("first_date") or "0000", reverse=True)
    return out


def page_works(year: str = "", page: int = 1, want: str = "", group: str = "work") -> str:
    """記録を見返す ▸ **日記帳。** 1 公演ごとの記録と、直す口を置く画面。

    起案者の指示（2026-08-24）──「日記帳のページも同様にして」（評価の一覧を索引の耳で
    切り替える形にしたのと同じにする）。

    ## なぜ年で切るか

    **観た本数は増える一方なので、一覧の長さがそのまま毎年の伸び方になる。** 実測で
    107 作品のこの画面は縦に画面 18 枚ぶんあった。**年は、この画面がすでに使っている
    軸である**（観劇の年輪・年ごとの本数）── 新しい区切りを作ったのではなく、図で見て
    いる軸を一覧にも通した。探すときの手がかりも「去年の秋ごろ」のように年から入る。

    ## 畳んで積むのをやめた

    **畳んだ束を縦に積むと、次の年の見出しが前の年の下端にある。** いちばん新しい年を
    開いた状態では、16 行のあとに「2025 年」が来る ── **その年を読み終わるまで、
    ほかの年が何件あるのかが画面に出ない。** 耳を横に並べれば、年と件数が最初から
    1 行で見える。

    ## 「先に確かめてほしい」は耳の 1 枚にする

    読み取りに失敗した跡がある記録は年をまたいで散らばるので、年で切るとその分が
    各年に散る。**1 枚にまとめて、いちばん左の耳に置く** ── 件数が耳に出ているので、
    開いていなくても「直すものがある」ことは分かる。

    **既定は開かない。** 日記帳は思い出を読みに来る画面なので、開いた先が直しの
    作業一覧になっていると、読みに来た人が毎回それを閉じることになる。

    ## 「行かなかった」は日記帳から完全に外し、設定に移した（2026-08-26）

    起案者の指摘 ──「日記帳で『行かなかった』を選んだ作品は日記帳から消して」。
    **最初は年の外の専用の耳に分けたが**（観ていない記録が混ざると、観た記録を
    読み返す流れが途切れるため）、**続けて「他の実装と同様に、設定画面で管理して」
    と指示された。**「取り消した記録」を設定へ移したのと同じ判断（たまにしか
    押さない道具は「設定」に集める）をこちらにもそろえ、**耳ごと日記帳から
    外した。** 戻す口（「やはり観た」）は「設定」の側にある（`_skipped_html` を
    参照）。

    ## 取り消した記録の管理は、この画面から「設定」へ移した（2026-08-26 に撤回）

    **もとはここに置いていた** ── 1 件ずつの記録に対する操作なので、図の画面に置くと
    押す口だけが本体から離れる、という判断だった。**この判断を撤回する**（起案者の
    指示・2026-08-26 ──「取り消した記録の管理は設定で行うようにして」）。日記帳を
    開く理由は思い出を読むことであって、外した記録の後始末はそこに常設するほどの
    頻度ではない ── 「たまにしか押さない道具」を集める場所は、すでに「設定」に
    ある（書き出す・別の端末に記録を移す）。詳細は `_dropped_html` を参照。

    **「観ればよかった」の登録は、ここから外した**（起案者の指摘・2026-08-24 ──
    「『観ればよかった』の登録は公演情報の登録のページじゃない？」）。**取り消した記録と
    同じ「1 件ずつの記録に対する操作」だと考えて並べていたが、それが間違いだった** ──
    取り消しは**すでにある記録を戻す**操作で、「観ればよかった」は**この仕組みに 1 度も
    入らなかった公演を新しく足す**操作である。足す操作の置き場所は「公演情報の登録」
    である。

    ## あらすじ・出演者を、記録ごとに出す（2026-08-26）

    起案者の指示 ──「各作品あらすじとキャストをみられるようにしてほしい」。**新しく
    取得はしない。** `measure_nets.load_rated()`（名簿作りのために、公演ページの
    クレジット・手で足した分・結び付け直した分を突き合わせ済み）と、`themes.jsonl`
    の学習側抽出（`extract_theme_llm.py --side rated`）が、すでに同じ材料を持っている。
    **推薦の理由の欄（`RR.cast_block`／`RR.syn_block`）と同じ枠を使うが、簡略にした
    版を別に作った** ── あちらは公演ページとの照合や手直しの入力欄まで持つが、
    ここは古い記録が多く照合する相手（候補側のキャッシュ）が無いことが多いので、
    **事実をそのまま見せるだけにする。**

    ## 「作品でまとめる」と「すべて表示」を選べるようにした（2026-08-26）

    起案者の指示 ──「日記で『作品ごと』にくくるのと、行った公演数分表示するの
    （同じ作品でも複数回行ってるなら複数回羅列）と2つを選べるようにして」。
    名前は「作品ごと」「観た回ごと」で作ったあと、起案者の指示で
    「作品でまとめる」「すべて表示」に改めた（同日）。

    **束ねる軸（年）は変えず、束の中身の切り方だけを変える。** 「作品でまとめる」は
    これまでどおり 1 作品 1 行（`ws`）。「すべて表示」は `_flatten_visits` で
    開き、同じ作品を 3 回観ていれば 3 行に分けて出す ── 行ごとに自分の日付・
    会場を持ち、「N 回観た」の注記は出さない（その行自体が 1 回だから）。

    **年の耳はどちらの軸でも動く。** 「すべて表示」では、1 つの作品が複数の年に
    ぶんかれて出ることがある（初演を2019年に、再演を2024年に観た場合など）──
    これは「作品でまとめる」では起こらない（束ねた行は初日の年 1 つにしか属さない）。
    **どちらが正しいかではなく、束ね方が違うので当然そうなる**、という違いである。

    **評価・感想・出演者は、開いた行のどれにも同じ値が付く。** これらは作品ぶんしか
    持っていない（回ごとには記録していない）ため。**日付を選んで見比べるための
    機能ではない** ── 何回行ったかを、行った日ごとに並べて読み返すための切り替えである。

    ## 「すべて表示」だけに、回ごとのメモを付けた（起案者の指示・2026-08-26）

    「感想は作品ごとにしか持てない。回ごとに書きたいかもしれない」という話の続きで、
    「『すべて表示』のページだけに、今後の推薦には含まれないその公演用のメモ欄を
    つけて」という指示になった。**感想（作品ごと・1 つ）はそのままにし、別の欄
    （`visit_note` 表・uid ごと）を「すべて表示」にだけ足した。** 「作品でまとめる」
    では 1 行が複数回を畳んでいて、どの回のことかが決まらないので出さない。
    詳しくは `_visit_note_html` を見る。
    """
    d = _records_base()
    ws = d["ws"]
    # **あらすじ・出演者を、記録ごとに引けるようにしておく**（起案者の指示・2026-08-26
    # ──「各作品あらすじとキャストをみられるようにしてほしい」）。
    #
    # **`_records_base` の `rated_rows` は使わない ── 評価が付いていない記録が落ちる。**
    # 日記帳は評価の有無に関わらず全記録を出す画面なのに、クレジットは評価済みだけを
    # 読んでいたため、**結び付けた直後でまだ評価していない記録には、取れているはずの
    # クレジットが出ない**という食い違いがあった（起案者の指摘 ──「ハード・プロブレム
    # （まだ評価していない記録）にキャストが出ていない」）。ここだけ
    # `include_unrated=True` で読み直す（`page_records` など、正例だけを
    # 使う画面の既定は変えない）。
    import measure_nets as M
    people_by_key = {r["key"]: r.get("people") or []
                     for r in M.load_rated(include_unrated=True)}
    syn_by_key = _synopsis_by_key()
    # **回ごとのメモは「すべて表示」でしか要らない。** 「作品でまとめる」では
    # `row()` から `visit_uid` を渡さないので、読んでも使われない ── それでも
    # `group` を見ずに毎回読むのは、この画面の主目的（軸を切り替える）とは無関係な
    # 分岐を増やすだけなので、`group == "visit"` のときだけ読む
    import rate_performances as R
    visit_notes = {}
    if group == "visit":
        con = R.connect()
        try:
            visit_notes = R.read_visit_notes(con)
        finally:
            con.close()

    def row(w: dict) -> str:
        f, _sid, _src = poster_of(w)
        p = (f'<img class="poster" src="/img/{E(f)}?t=__TAGURI_TOKEN__" alt="" loading="lazy">'
             if f else "")
        # **「すべて表示」で開いた行は、券自身の uid で `id` を分ける**（`_rec_row` の
        # 説明を見る）。「作品でまとめる」では 1 作品 1 行なので要らない
        uid = w["shows"][0]["uid"] if (group == "visit" and w.get("shows")) else ""
        sfx = f"-{uid}" if uid else ""
        w = {**w, "people": people_by_key.get(w["work_key"]) or [],
             "synopsis": syn_by_key.get(w["work_key"], "")}
        return _rec_row(w, poster=p, editable=True, id_suffix=sfx,
                        visit_uid=uid, visit_note=visit_notes.get(uid, ""))

    check = [w for w in ws if w.get("suspect")]
    # **「行かなかった」は年の外にも出さない。** 設定の「行かなかった公演」札に
    # 完全に移したので（`_skipped_html`）、日記帳側は単純に除くだけでよい
    rest = [w for w in ws if not w.get("suspect") and not w.get("unseen")]
    # **「作品でまとめる」と「すべて表示」の切り替え**（起案者の指示・2026-08-26）。
    # 束ねる軸（年）はどちらでも同じ手順を使うので、ここで先に軸を決めてしまう
    rest_visit = _flatten_visits(rest)
    groups = [("work", "作品でまとめる", len(rest)), ("visit", "すべて表示", len(rest_visit))]
    group = group if group in ("work", "visit") else "work"
    rest = rest_visit if group == "visit" else rest
    # **年で束ねる。** 並びは `_works` の順（新しい順）をそのまま保つ ── 日付の無い
    # 記録は最後に来るので、専用の耳に回す
    years: dict[str, list] = {}
    for w in rest:
        y = (w.get("first_date") or "")[:4]
        years.setdefault(y if y.isdigit() else "none", []).append(w)
    keys = sorted((k for k in years if k != "none"), reverse=True)
    if "none" in years:
        keys.append("none")
    piles = {k: years[k] for k in keys}
    if check:
        piles["check"] = check
    # 耳の並び ── 確かめてほしい分を左端に、そのあとを年の新しい順にする
    order = (["check"] if check else []) + keys
    label = {"none": "上演日が分からない", "check": "先に確かめてほしい"}
    tabs = [(k, label.get(k, f"{k} 年"), len(piles[k])) for k in order]
    # **既定はいちばん新しい年。** 確かめてほしい分は開かない（上記）
    sel = year if year in piles else (keys[0] if keys else order[0])
    # **図の点から来たときは、その記録が載っている耳と紙を開く。**
    # 年輪と地図は断片（`#w-…`）で 1 件を指すが、**紙が 15 件ずつに切られている以上、
    # その行が載っていない紙を開いても飛べない** ── どの耳のどのページに載っているかを
    # 知っているのはこちらなので、探すのもこちらでやる（`charts.ROW_HREF` の `w=`）
    if want:
        for k in order:
            for n, w in enumerate(piles[k]):
                if CH._anchor(w["work_key"]) == want:
                    sel, page = k, n // SHEET_TOP + 1
                    break
            else:
                continue
            break
    hit = piles[sel]

    def url(k: str, pg: int = 1, g: str = "") -> str:
        return ("/records/works?t=__TAGURI_TOKEN__"
                + (f"&amp;y={quote(k)}" if k else "")
                + (f"&amp;p={pg}" if pg > 1 else "")
                + (f"&amp;g={g}" if g and g != "work" else ""))

    show, now, foot = RR.paginate(hit, page, SHEET_TOP, lambda pg: url(sel, pg, group), "件")
    lead = ("読み取りに失敗した跡がある記録です。年をまたいで散らばるので、"
            "1 枚にまとめてあります。" if sel == "check" else
            "上演日が分からない記録です。日付が無いと年で切れないので、"
            "1 枚にまとめてあります。" if sel == "none" else
            f"{sel} 年に観た記録です。")
    n_syn = sum(1 for w in ws if syn_by_key.get(w["work_key"]))
    n_cast = sum(1 for w in ws
                 if any(r == "出演" for r, _ in people_by_key.get(w["work_key"], [])))
    # **軸の説明は、選んでいるほうだけ言う。** 両方の定義を毎回読ませると、
    # 「今どっちを見ているか」より先に用語の説明を読むことになる
    gnote = ("同じ作品は 1 行にまとめています。複数回観ていれば、日付は最初に観た日を出し、"
             "「N 回観た」と添えます。" if group == "work" else
             "観た回ごとに 1 行で出しています（すべて表示は、畳まずに 1 回ずつ出す、"
             "という意味です）。同じ作品を複数回観ていれば、行った日の数だけ並びます。"
             "評価・感想はどの行にも同じ値が付きます（回ごとには記録していません）。"
             "<b>「この回のメモ」だけは行ごとに別々に持てます</b>（推薦には使いません）。")
    body = f"""<h1>日記帳 ── 1 公演ごとの記録</h1>
{_records_lede(d)}
<p class="lede">1 件ごとに、日付・評価・感想が出ます。<b>感想は各行の「感想を書く」から
書けます</b>（欄から離れたときに保存されます）。<b>題名・上演日・劇場は、各行の
「公演詳細を直す」から直せます。</b>ポスターを出せたのは {d["n_pos"]} 件、
あらすじが出せたのは {n_syn} 件、出演者が出せたのは {n_cast} 件です。{gnote}
{_check_line(len(check))}</p>
{index_tabs(groups, group, lambda g: url(sel if sel in piles else "", 1, g),
            "作品でまとめる・すべて表示を切り替える")}
{index_tabs(tabs, sel, lambda k: url(k, 1, group), "年で切り替える")}
<div class="idxsheet">
<p class="mnow">{lead}{now}ほかの年は、上のインデックスで切り替えられます。</p>
{"".join(row(w) for w in show)}</div>
{foot}"""
    return layout("日記帳", "/records/works", body, RR.STYLE,
                  active_sub="/records/works")


# ---------------------------------------------------------------- 探す
_INDEX: dict | None = None


def _index() -> dict:
    """探すための索引 ── 作品ごとの「人」と「題材」。

    **評価が付いていない記録も入れる**（`measure_nets.load_rated(include_unrated=True)`）。
    起案者の指示で探した結果からその場で評価できるようにした以上、**評価の無い記録が
    出てこないと、探して評価する道がそこで閉じる。** 学習側の呼び出しは既定のままなので、
    正例が ◎ だけであることは動かない。

    **評価と感想はここに入れない。** 索引は起動のあいだ作り直さないので、押した評価が
    索引に残っていると**画面が古い評価を出す。** 題名・日付・評価・感想は `_works()` から
    毎回引き直し、索引は「人」と「題材」だけを持つ。
    """
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    import measure_nets as M
    themes = {}
    # **まだ 1 度も取り寄せていない状態を、失敗として扱わない**（`measure_nets` と同じ）。
    # 初めて使う端末にはこのファイルが無い ── 題材で引けないだけで、探す画面は成り立つ
    tf = ROOT / "data" / "credits" / "themes.jsonl"
    for line in (tf.read_text(encoding="utf-8").split("\n") if tf.exists() else []):
        if not line.strip():
            continue
        t = json.loads(line)
        if t.get("side") != "rated":
            continue
        el = t.get("elements") or []
        if isinstance(el, str):
            try:
                el = json.loads(el or "[]")
            except ValueError:
                el = []
        themes[t["id"]] = [w for w in el if isinstance(w, str) and w]
    rows = M.load_rated(include_unrated=True)
    _INDEX = {"by_key": {r["key"]: r for r in rows}, "themes": themes,
              "n_all": len(rows), "n_people": sum(1 for r in rows if r["people"])}
    return _INDEX


def _hit_why(q: str, w: dict, ix: dict) -> tuple[str, list[tuple[str, str]]]:
    """1 件が当たった理由と、当たった名前を返す。

    **ヒットした箇所を必ず書く。** 「堺雅人」で引いた結果に題名だけが並ぶと、その公演の
    どこに堺雅人がいるのかが分からない ── **出演なのか、演出なのか、題材の言葉なのかで
    意味が違う。**
    """
    key = RR._norm(q)
    r = ix["by_key"].get(w["work_key"]) or {}
    who = [(role, person) for role, person in (r.get("people") or [])
           if key in RR._norm(person)]
    th = [t for t in (ix["themes"].get(w["work_key"]) or []) if key in RR._norm(t)]
    why = []
    if key in RR._norm(w["title"]):
        # **題名に当たったことは、題名をもう 1 度書かなくても分かる。** すぐ上の行に
        # 出ているので、名前を繰り返すと当たった場所の説明が題名の複製になる
        why.append(("題名", ""))
    for role, person in who[:6]:
        why.append((role, person))
    if th:
        why.append(("題材", "・".join(th[:4])))
    if not why:
        return "", []
    body = "".join(f'<span class="hw"><span class="k">{E(k)}</span>{E(v)}</span>'
                   if v else f'<span class="hw">{E(k)}</span>' for k, v in why)
    # **言い方を「当たったところ」→「ヒットした箇所：」に変えた**（起案者の指示・
    # 2026-08-26）。`RR.ticket` の探した結果（`why_html`）と同じ言葉にそろえてある。
    return (f'<div class="hitwhy"><span class="hl">ヒットした箇所：</span>{body}</div>',
            [(k, v) for k, v in why if k not in ("題名", "題材")]
            + [("題材", t) for t in th])


def _search_follow(names: list[tuple[str, str]]) -> str:
    """探した名前を、その場でお気に入りに登録する口。

    **探す画面は「この先どうするか」で終わる。** 「あの俳優、前に何で観たっけ」を引いた
    あとに続くのは、**その人の次の公演を見逃したくない**という用件である。ところが
    お気に入りに登録できるのは、これまでお気に入りの画面で名前を打ち込む道だけだった ──
    **いま名前が目の前にあるのに、別の画面で打ち直させることになっていた。**

    **すでに登録してある名前は出さない。** 押しても何も起きない口を並べない。
    """
    dec = RC.load_declared()
    have = {(k, RR._norm(n)) for k, ns in dec.items() for n in ns}
    seen, out = set(), []
    for role, name in names:
        kind = "題材" if role == "題材" else "人"
        if (kind, RR._norm(name)) in have or (kind, name) in seen:
            continue
        seen.add((kind, name))
        out.append(f'<div class="prom"><span class="k">{E(kind)}</span>'
                   f'<span class="w">{E(name)}</span>'
                   f'<button data-fav="promote" data-kind="{E(kind)}" data-name="{E(name)}">'
                   f'これは追う</button><span class="said"></span></div>')
    if not out:
        return ""
    return f"""<div class="card">{IC.h2("star", "この名前を追いますか？",
 f'<span class="badge part">{len(out)} 件</span>')}
<p class="lead">お気に入りに登録すると、<b>この名前の公演がこれから始まるときに、
件数の制限も条件も付けずに新着へ出ます。</b>いま探している名前を、ここから登録できます。</p>
{"".join(out[:8])}</div>"""


_UPCOMING: dict | None = None


def reset_caches() -> None:
    """索引を捨てる。**押した直後に取りに行った分を、次に開いた画面へ効かせる。**

    索引は起動のあいだ作り直さないので、**押した直後に取りに行ったクレジットや、
    お気に入りで引いた公演が、探す画面にだけ出てこない**（`serve.py` の仕事の列が
    1 件終わるたびにここを呼ぶ）。取ることと使える形にすることを別の実行に分けない、
    という約束の続きである。
    """
    global _INDEX, _UPCOMING
    _INDEX = None
    _UPCOMING = None


def _upcoming_index() -> dict:
    """これから観られる公演の索引。**探す画面が「今後の公演」を引くために持つ。**

    起案者の指摘（2026-08-24）──「『探す』って過去の公演だけなの？　今後の公演も含めて
    かと思ってた」。**これは思い込みで境目を引いていた** ── 探す画面には「これから観られる
    公演はおすすめの画面が受け持ちます」と書いてあったが、**おすすめが受け持つのは
    「こちらから出す 15 件」であって、「本人が名前を思いついて引く」ことではない。**
    名前で引ける相手が過去にしかいないなら、**その俳優の次の公演があっても分からない。**

    ## 3 つの控えを全部見る

    | | 件数 | 何が入っているか |
    |---|---|---|
    | `candidates.jsonl` | 818 | 一覧を走査して集めた候補 |
    | `calendar.jsonl` | 470 | ステイジーズカレンダー（網羅を担う側） |
    | `favourites.jsonl` | 19 | 登録した名前で直接引いたもの |

    **推薦に出るのは点の付いた 85 件だけである。** 探すのはそこではなく、**手元にある
    これから観られる公演すべて**でなければ、「無い」と答えたことにならない。

    **同じ公演は id で 1 件に畳む。** 3 つの控えは重なっている。
    """
    global _UPCOMING
    if _UPCOMING is not None:
        return _UPCOMING
    rows: dict[str, dict] = {}
    # **探して拾った分を先に置く**（`picked.jsonl`）── 本人が名指しで拾った公演なので、
    # 同じ id が一覧にもあるときは、そちらより先に見つかってよい
    for name in ("picked.jsonl", "candidates.jsonl", "calendar.jsonl", "favourites.jsonl"):
        f = ROOT / "data" / "review" / name
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            c = json.loads(line)
            sid = str(c.get("stage_id") or "")
            if sid:
                rows.setdefault(sid, c)
    themes: dict[str, list] = {}
    tf = ROOT / "data" / "credits" / "themes.jsonl"
    for line in (tf.read_text(encoding="utf-8").split("\n") if tf.exists() else []):
        if not line.strip():
            continue
        t = json.loads(line)
        if t.get("side") != "candidate":
            continue
        el = t.get("elements") or []
        if isinstance(el, str):
            try:
                import ast
                el = ast.literal_eval(el)
            except (ValueError, SyntaxError):
                el = []
        words = [e.get("word") for e in el if isinstance(e, dict) and e.get("word")]
        if words:
            themes[str(t.get("id") or "")] = words
    _UPCOMING = {"rows": rows, "themes": themes}
    return _UPCOMING


def _hit_upcoming(q: str, c: dict, themes: dict) -> tuple[str, list]:
    """これから観られる 1 件が、打った言葉のどこに当たったか。

    **役割まで書く。** 「出演」なのか「演出」なのか「団体」なのかで、観るかどうかの
    決まり方が違う（観た記録の側と同じ約束）。
    """
    import measure_nets as M
    key = RR._norm(q)
    sid = str(c.get("stage_id") or "")
    why, names = [], []
    if key in RR._norm(c.get("title") or ""):
        why.append(("題名", ""))
    if key in RR._norm(c.get("group") or ""):
        why.append(("団体", c.get("group") or ""))
        names.append(("団体", c.get("group") or ""))
    for role, person in M.parse_credits(c.get("fields") or {}):
        if key in RR._norm(person):
            why.append((role, person))
            names.append((role, person))
    th = [t for t in (themes.get(sid) or []) if key in RR._norm(t)]
    if th:
        why.append(("題材", "・".join(th[:4])))
        names += [("題材", t) for t in th]
    if key in RR._norm(c.get("theater") or ""):
        why.append(("劇場", c.get("theater") or ""))
    if not why:
        return "", []
    seen, out = set(), []
    for k, v in why:
        if (k, v) in seen:
            continue
        seen.add((k, v))
        out.append(f'<li class="rs found"><span class="net">{E(k)}</span>{E(v)}</li>'
                   if v else f'<li class="rs found"><span class="net">{E(k)}</span></li>')
    return "".join(out[:6]), names


def _web_hits(q: str, on: bool) -> str:
    """**手元に無ければ、公演情報からその場で探す。**

    起案者の指摘（2026-08-24）──「おすすめの 15 件とかにもまだ載ってないけど今後の情報を
    検索して探したいときとかは？」。**手元の 1,301 件は、月 1 回の取得で集めた分でしかない**
    ── そこに無い公演は、いくら手元を探しても出てこない。

    ## 押したときだけ外に行く

    打っている最中には行かない（手で足す欄と同じ約束）。**1 リクエスト／秒を守るので
    1 回に 8 秒ほどかかる** ── 押す前にそう書く。

    ## 見つけた公演は、押せば手元に入る

    「興味あり」を押した時点で控えに加え、一覧を組み直す（`serve.py` の `_pick`）──
    **押した記録だけが残ってどの一覧にも出てこない、という状態を作らない。**

    ## 終わった公演も出し、その場で記録として登録できる（2026-08-26 に撤回）

    **以前は終わった公演を弾いていた。** ここは「これから観られる公演」を探す場所と
    決めていたためだが、起案者の指摘 ──「探すで CoRich の検索結果が終わった上演だと
    弾かれてしまう。終わった上演も表示して検索結果のページからも直で登録できるように
    してほしい」を受けてこの判断を撤回する。**弾いていた理由（「興味あり」を押せる形で
    終演済みの公演が出てくる）はそのまま残る**ので、終わった公演には三択ではなく
    `RR.register_button`（観た記録として登録する）を出す（`mode="ended"`）。

    **すでに登録した分は、赤字で「追加済みです」と言う**（起案者の指示・2026-08-26。
    `mode="ended_added"`）。ボタンは同じ検索を打つたびに毎回出るので、押したことを
    覚えていないと二重に押しに行ってしまう ── `works.stage_id` に当たれば済んでいる。
    """
    ask = (f'<div class="webq" id="web"><p class="lead">'
           f'手元にあるこれから観られる公演の一覧は、月に 1 度集めた分です。'
           f'<b>そこに無い公演も、CoRichの公演情報からその場で探せます。</b></p>'
           f'<a class="mpage" href="/search?t=__TAGURI_TOKEN__&amp;q={E(q)}&amp;web=1#web">'
           f'{IC.ico("search")}CoRichの公演情報から探す（8 秒ほどかかります）</a></div>')
    if not on:
        return ask
    import stage_search as SS
    r = SS.search_full(q)
    if r.get("error"):
        return (f'<div class="webq" id="web"><h2>CoRichの公演情報から探した結果</h2>'
                f'<p class="empty">{E(r["error"])}</p></div>')
    import datetime
    today = datetime.date.today().isoformat()

    def _ended(c: dict) -> bool:
        """楽日が今日より前なら、終わっている。**期間を読めないものは残す。**"""
        ms = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", c.get("period") or "")
        if not ms:
            return False
        y, mo, d = ms[-1]
        return f"{y}-{int(mo):02d}-{int(d):02d}" < today
    rows = r.get("rows") or []
    if not rows:
        return (f'<div class="webq" id="web"><h2>CoRichの公演情報から探した結果</h2>'
                f'<p class="empty">公演情報にも見つかりませんでした。'
                f'<b>題名の一部だけで探すと当たることがあります</b>'
                f'（団体名や副題を外してお試しください）。</p></div>')
    known = set(_upcoming_index()["rows"])
    # **すでに登録した分は、ボタンではなく結果を出す。**（起案者の指示・2026-08-26 ──
    # 「実際に CoRich の検索から...ボタンを押して追加した公演には、『追加済みです』
    # などを赤文字で出して」）。同じ言葉で探し直すと同じ公演がまた出るので、
    # 押す前に「もう済んでいる」と分かるようにする。
    registered = {str(w.get("stage_id") or "") for w in _works() if w.get("stage_id")}
    n_end = 0
    cards = []
    for c in rows:
        sid = str(c.get("stage_id") or "")
        why = f'<li class="rs found"><span class="net">題名</span>{E(c.get("title") or "")}</li>'
        if sid in known:
            why += '<li class="rs state">この公演は手元にもあります</li>'
        ended = _ended(c)
        mode = "recommend"
        if ended:
            n_end += 1
            if sid in registered:
                why += '<li class="rs state">観た記録として登録済みです</li>'
                mode = "ended_added"
            else:
                why += '<li class="rs state">上演は終わっています</li>'
                mode = "ended"
        cards.append(RR.ticket(c, mode=mode, why_html=why))
    end_note = (f' うち {n_end} 件は上演が終わっています ── '
                f'「観た記録として登録する」から記録に足せます。' if n_end else "")
    return (f'<div class="webq" id="web"><h2>CoRichの公演情報から探した結果 {len(rows)} 件</h2>'
            f'<p class="lead">手元の一覧には無かった公演も含みます。{end_note}'
            f'まだ上演される公演は「興味あり」を押すと手元に加わり、追いかけている一覧に'
            f'入ります。この探し方では、都道府県と団体名は出ません。</p>{"".join(cards)}</div>')


def _upcoming_hits(q: str, ym: str = "", top: int = 8) -> tuple[str, list, int]:
    """これから観られる公演のうち、打った言葉に当たったもの。

    ## 出すのは推薦と同じ 1 枚である

    **観るかどうかを決めるのに要るものは、推薦から来ても探して来ても同じ**（値段・日程・
    あらすじ・出演者）。違うのは「なぜ出てきたか」だけなので、そこを「ヒットした箇所」に
    差し替える（`RR.ticket` の `why_html`）。

    ## 点の付いた 85 件より広く見て、出すのは 8 枚まで

    **引く相手は手元の 1,300 件すべてである** ── 推薦に出る 85 件だけを見ると、
    「無い」と答えたことにならない。ただし **1 枚が 500〜660px あるので、当たった分を
    全部並べると画面が伸びる**（起案者の指示で 1 画面 8 枚に揃えたばかりである）。
    **切ったときは、あふれた分の行き先を書く** ── ここでは「言葉を絞る」がその行き先で、
    件数を出して何件から切ったかを言う。

    ## すでに答えた公演は、答えたことを書く

    「興味なし」と答えた公演が探した結果に出てくるのは正しい（**探しているのは本人で
    ある**）。ただし**もう一度三択を出すと、前に答えたことが無かったことになる**ので、
    いまの状態を 1 行足す。
    """
    up = _upcoming_index()
    d, _ = _load()
    rich: dict[str, dict] = {}
    for k in ("ranked", "recommend", "favourites", "others", "owned", "tracking", "started"):
        for c in (d.get(k) or []):
            rich.setdefault(str(c.get("stage_id") or ""), c)
    state: dict[str, str] = {}
    for k, lab in (("tracking", "追いかけています（興味ありと答えました）"),
                   ("owned", "観る予定です（すでに持っていると答えました）"),
                   ("others", "興味なしと答えました")):
        for c in (d.get(k) or []):
            state[str(c.get("stage_id") or "")] = lab
    hits = []
    for sid, c in up["rows"].items():
        if ym and ym not in _period_months(c.get("period") or ""):
            continue
        if q:
            why, names = _hit_upcoming(q, c, up["themes"])
        else:
            # **月だけで引いたときは、ヒットした箇所が「上演月」である**
            why, names = (f'<li class="rs found"><span class="net">上演</span>'
                          f'{E(RR.short_period(c.get("period") or ""))}</li>', [])
        if why:
            hits.append((sid, {**c, **rich.get(sid, {})}, why, names))
    # **並べ方は、月で見ているかどうかで変える。**
    # 月の一覧では **その月に始まる公演を先に、続いている公演を後に（終わりの近い順）**
    # ── 初日の順に並べると、**去年から続いているロングランが「10 月の公演」の先頭に
    # 立つ**（実測で「4/6〜3/31」の公演が 10 月の 1 番目に出た）。月を選んでいないときは
    # 上演日の近い順のままにする。**順位は付けない** ── これは推薦ではなく、探した結果である
    if ym:
        def _key(x):
            st = RR._start(x[1].get("period") or "") or "9999"
            ends = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})",
                              x[1].get("period") or "")
            en = (f"{ends[-1][0]}-{int(ends[-1][1]):02d}-{int(ends[-1][2]):02d}"
                  if ends else "9999")
            return (0, st) if st[:7] == ym else (1, en)
        hits.sort(key=_key)
    else:
        hits.sort(key=lambda x: RR._start(x[1].get("period") or "") or "9999")
    names: list = []
    for _sid, _c, _why, ns in hits:
        names += ns
    if not hits:
        return ("", [], 0)
    show = hits[:top]
    cards = []
    for sid, c, why, _ns in show:
        st = state.get(sid)
        w = why + (f'<li class="rs state">{E(st)}</li>' if st else "")
        cards.append(RR.ticket(c, mode="interest" if sid in
                               {str(x.get("stage_id")) for x in (d.get("tracking") or [])}
                               else "recommend", why_html=w))
    tail = ("" if len(hits) <= top else
            f'<p class="lead">当たったのは {len(hits)} 件で、上演日の近い {top} 件を'
            f'表示しています。<b>残りは'
            + ("言葉を足すと絞れます" if not q else "言葉を絞ると出てきます")
            + '</b>（人名・団体名・劇場名など）。</p>')
    if ym:
        _y, _, _m = ym.partition("-")
        _head = f"{_y} 年 {int(_m)} 月に観られる公演"
    else:
        _head = "これから観られる公演"
    order = ("この月に始まる公演を先に、すでに続いている公演を後に（終わりの近い順）"
             "並べています。" if ym else "上演日の近い順です。")
    return (f'<h2>{E(_head)} {len(hits)} 件</h2>'
            f'<p class="lead">{order}順位は付けていません。'
            f'<b>ここから「興味あり」を押すと、追いかけている一覧に入ります。</b></p>'
            f'{tail}{"".join(cards)}', names, len(hits))


def _found_row(w: dict, why: str = "") -> str:
    """探した結果の 1 件。**記録を見返す画面と同じ行を出す。**

    言葉で引いても暦で引いても、出すものは同じである ── **引き方が違うだけで、
    見つけたあとにすることは同じ**（評価する・感想を書く・題名を直す）。

    **ポスターは `poster_of` で決める**（起案者の指摘・2026-08-26 ──「銀河鉄道の父」の
    手で入れたポスターが探す画面の行には出ない）。以前はここだけ `PO.match` で推測
    した会場のポスターを直接引いており、**手で入れた絵も、結び付けた公演のポスターも
    見ていなかった** ── `_edit_html` が同じ行の下に出す「いま何が入っているか」の
    プレビューとは別の道で絵を決めていたため、片方だけ食い違って見えていた。
    """
    f, _sid, _src = poster_of(w)
    poster = (f'<img class="poster" src="/img/{E(f)}?t=__TAGURI_TOKEN__" alt=""'
              f' loading="lazy">' if f else "")
    return _rec_row(w, poster=poster, rate_always=True, editable=True, extra=why)


def _period_months(period: str, cap: int = 18) -> list[str]:
    """その公演を**観られる月**を並べて返す（初日の月から楽日の月まで）。

    **暦は「この月に観られるか」で引くものである。** 9/1〜10/30 の公演は 9 月にも
    10 月にも観られる ── **初日の月にだけ置くと、10 月の暦から消える。**
    おすすめの月の札（`RR.month_pick`）が初日で切っているのとは別の規則である。
    あちらは 31 件を分けるための区切りで、**こちらは「いつ観られるか」の問いに答える。**

    **長すぎる期間は打ち切る。** ロングランや期間の読み違いで、1 件が暦を埋め尽くさない。
    """
    ms = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    if not ms:
        return []
    a = int(ms[0][0]) * 12 + int(ms[0][1]) - 1
    b = int(ms[-1][0]) * 12 + int(ms[-1][1]) - 1
    b = max(a, min(b, a + cap))
    return [f"{k // 12:04d}-{k % 12 + 1:02d}" for k in range(a, b + 1)]


def _up_month_counts(rows) -> dict:
    """これから観られる公演を、月ごとに数える。**今月より前は数えない。**"""
    import datetime
    now = datetime.date.today().strftime("%Y-%m")
    out: dict[str, int] = {}
    for c in rows:
        for m in _period_months(c.get("period") or ""):
            if m >= now:
                out[m] = out.get(m, 0) + 1
    return out


def _month_grid(ws: list, up_rows, side: str, sel: str, q: str = "") -> str:
    """観た月／これから観られる月のマス目。**言葉が思い出せないときの入口である。**

    起案者の提案（2026-08-24）── 最初は観た記録だけの暦として作り、そのあと
    「観た月から引けます。のカレンダーを未来の公演検索にも適用できませんか」と言われた。

    ## 1 つの暦を、2 つの側で切り替える

    **暦を 2 つ並べない。** 同じ形の表が縦に 2 つあると、どちらを見ているのかが
    分からなくなる。**上の 2 つの札で側を選び、表は 1 つにする。**

    ## 日めくりの暦にはしない

    **記録の散らばり方に形を合わせた。** 観た記録は 6 年で 108 作品、実際に劇場にいた日は
    67 日 ── **日めくりにすると 2,190 マス中 67 マスしか埋まらない。** 月で切れば
    72 マス中 45 マスに記録があり、6 年ぶんが 1 画面に収まる。

    ## 空の月は押せないようにする

    押しても何も起きない選択肢を並べない（都道府県・月の札と同じ規則）。

    ## 濃さだけで意味を運ばない

    マスの濃さは件数だが、**数字もそのまま書く**（企画書 5 章の絵記号と同じ約束）。
    """
    n_past: dict[str, int] = {}
    n_none = 0
    for w in ws:
        d = (w.get("first_date") or "")[:7]
        if len(d) == 7:
            n_past[d] = n_past.get(d, 0) + 1
        else:
            n_none += 1
    n_up = _up_month_counts(up_rows)
    n = n_up if side == "up" else n_past
    if not n and not n_none:
        return ""
    # **いまに近い年を上に置く。** 観た記録は新しい年から、これからの公演は近い年から
    # ── どちらも「上の行がいまに近い」で揃う
    years = sorted({k[:4] for k in n}, reverse=(side != "up"))
    top = max(n.values()) if n else 1
    head = "".join(f'<span class="mh">{i}</span>' for i in range(1, 13))
    qs = f"&amp;q={E(q)}" if q else ""
    rows = []
    for y in years:
        cells = []
        for i in range(1, 13):
            ym = f"{y}-{i:02d}"
            c = n.get(ym, 0)
            if not c:
                cells.append('<span class="cal-c off" aria-hidden="true"></span>')
                continue
            lv = 1 if c * 3 <= top else (2 if c * 3 <= top * 2 else 3)
            cells.append(
                f'<a class="cal-c l{lv}{" on" if ym == sel else ""}"'
                f' href="/search?t=__TAGURI_TOKEN__&amp;cal={E(side)}{qs}&amp;ym={ym}#cal"'
                f' aria-label="{y} 年 {i} 月 {c} 件">{c}</a>')
        rows.append(f'<span class="cal-y">{E(y)}</span>' + "".join(cells))
    none_cell = ("" if (n_none == 0 or side == "up") else
                 f'<a class="cal-none{" on" if sel == "none" else ""}"'
                 f' href="/search?t=__TAGURI_TOKEN__&amp;ym=none#cal">'
                 f'上演日が分からない記録<span class="mn">{n_none}</span></a>')
    # **どちら側の暦を見るかも索引の耳で切り替える。** ここだけ丸いピルで残っていた ──
    # 評価一覧・日記帳・月の絞り込みと同じ「1 つ選ぶと下の中身が入れ替わる」操作なので、
    # 画面ごとに別の形を覚え直させない
    tabs = index_tabs(
        [("past", "観た記録", len(ws)), ("up", "これから観られる公演", len(up_rows))],
        side, lambda k: f"/search?t=__TAGURI_TOKEN__&amp;cal={k}{qs}#cal",
        "どちらの暦を見るか")
    lead = ("<b>これから観られる月から引けます。</b>数字はその月に観られる公演の数です"
            "（上演期間がその月にかかっているもの）。<b>件数が多い月は、言葉と一緒に"
            "使うと絞れます。</b>"
            if side == "up" else
            "<b>観た月から引けます。</b>数字はその月に観た作品の数です。"
            "押すと、その月の記録が下に出ます。")
    return f"""<div class="cal" id="cal">
{tabs}
<div class="idxsheet loose"><p class="mnow">{lead}</p>
<div class="cal-grid"><span class="cal-y"></span>{head}{"".join(rows)}</div>
{none_cell}</div></div>"""


def _month_rows(ws: list, ym: str) -> str:
    """暦から選んだ月の記録。**言葉で引いたときと同じ行を出す。**

    **月を選んでいないときは、何も出さない。** 72 マスの暦の下に 108 件を全部並べると、
    暦が「選ぶもの」に見えなくなる。
    """
    if not ym:
        return ('<p class="empty">上の暦から月を選ぶと、その月に観た記録が出ます。'
                'これから観られる公演は、言葉を入れて引いてください。</p>')
    if ym == "none":
        hit = [w for w in ws if len((w.get("first_date") or "")) < 7]
        where = "上演日が分からない記録"
        lead = ('<p class="lead"><b>上演日が入っていない記録です。</b>'
                '各行の「公演詳細を直す」から日付を入れると、暦から引けるようになります。</p>')
    else:
        hit = [w for w in ws if (w.get("first_date") or "")[:7] == ym]
        y, _, m = ym.partition("-")
        where = f"{y} 年 {int(m)} 月に観た記録"
        lead = ""
    hit.sort(key=lambda w: w.get("first_date") or "", reverse=True)
    if not hit:
        return f'<h2>{E(where)}</h2><p class="empty">この月の記録はありません。</p>'
    return (f'<h2>{E(where)} {len(hit)} 件</h2>{lead}'
            + "".join(_found_row(w) for w in hit))


def page_search(q: str, ym: str = "", web: bool = False,
                cal_side: str = "past") -> str:
    """探す画面。**結果は、記録の行そのものにする**（起案者の指示・2026-08-24）。

    ## 出すだけの画面にしない

    指示 ──「探すページを充実させたい。今さがしても結果が出るだけなので、そこから
    評価できるようにしたり過去の記録を見られるようにしたり」。

    **これまでは題名・日付・劇場を 1 行に出して終わりだった。** 探して思い出した瞬間が、
    **評価と感想がいちばん出てくる瞬間**なのに、そこから何もできなかった ── 評価を
    付けるには「観た公演の評価」へ、感想を書くには「記録を見返す」へ移り、**もう一度
    同じ作品を探し直す**必要があった。

    **記録を見返す画面と同じ行を出す**（`_rec_row`）。新しい部品は作らない ── 評価・
    感想・公演詳細を直す・ポスターは、すでにその行が持っている。探す画面の仕事は
    **どの行を出すかを決めることだけ**である。

    ## ヒットした箇所を、行の中に書く

    どこに一致したのか（題名／出演／演出／題材）を題名のすぐ下に出す。**「堺雅人」で
    引いた結果に題名だけが並ぶと、その公演のどこにその名前があるのかが分からない。**

    ## 引き方は 2 つ ── 言葉と、暦

    起案者の提案（2026-08-24）──「『探す』のページにカレンダーから探せるのがあるといい」。
    **言葉を思い出せないときの入口である**（「去年の秋に観たやつ、なんだっけ」）。

    **2 つは同時に使わない。** 言葉で引いたら暦の選択は外れ、月を押したら言葉は空になる ──
    「前田文子の 2025 年 11 月」という引き方は、**どちらの入口から入っても結果が
    1 件以下になりやすく、覚えていない側を 2 つ重ねることになる。** 出すものは同じ行なので、
    見つけたあとにできること（評価・感想・題名を直す）はどちらから来ても変わらない。
    """
    ix = _index()
    n_up = len(_upcoming_index()["rows"])
    note = (f'<p class="note"><b>出演者や題材で引けるのは、公演ページを見つけられた記録だけです</b>'
            f'（観た記録では {ix["n_people"]} 作品／全 {ix["n_all"]} 作品）。'
            f'ほかの記録は題名で引けます。</p>')
    form = f"""<form class="fav-add" method="get" action="/search">
<input type="hidden" name="t" value="__TAGURI_TOKEN__">
<input type="text" name="q" value="{E(q)}" size="28" placeholder="人名・団体・題材・題名">
<button type="submit">{IC.ico("search")}探す</button></form>"""
    head = f"""<h1>探す</h1>
<p class="lede">人名・団体・題材・題名で、<b>これから観られる公演 {n_up} 件と観た記録の
両方から探します。</b>見つけたものには、この画面のまま答えられます ──
これから観られる公演には「興味あり」を、観た記録には評価と感想を書けます。</p>{form}{note}"""
    # **評価と感想は毎回引き直す。** 索引は起動のあいだ作り直さないので、押した評価が
    # そのまま出てしまう（探した先で評価できる画面なので、これは必ず起きる）
    ws = _works()
    seen_ws = [w for w in ws if not w.get("unseen")]
    side = "up" if cal_side == "up" else "past"
    cal = _month_grid(seen_ws, _upcoming_index()["rows"].values(), side, ym, q)
    if not q:
        # **言葉が無いときは、暦だけで引く。** どちらの側を選んでいるかで出すものが変わる
        if side == "up":
            up_html, _n, n_up = _upcoming_hits("", ym)
            body = (up_html if ym else
                    '<p class="empty">上の暦から月を選ぶと、その月に観られる公演が出ます。</p>')
        else:
            body = _month_rows(seen_ws, ym)
        return layout("探す", "/search", head + cal + body, RR.STYLE)
    hits, names = [], []
    for w in ws:
        why, found = _hit_why(q, w, ix)
        if why:
            hits.append((w, why))
            names += found
    hits.sort(key=lambda x: x[0].get("first_date") or "", reverse=True)
    rows = [_found_row(w, why) for w, why in hits]
    up_html, up_names, n_up = _upcoming_hits(q, ym if side == "up" else "")
    names += up_names
    web_html = _web_hits(q, web)
    if not hits and not n_up:
        # **月で絞っているときは、そう書く。** 「見つかりません」とだけ出すと、
        # **手元に無いのか、その月に無いのかが分からない**
        narrowed = ""
        if ym and side == "up":
            _y, _, _m = ym.partition("-")
            narrowed = (f'<b>いまは {_y} 年 {int(_m)} 月に絞っています。</b>'
                        f'ほかの月にはあるかもしれません ── 暦の月を押し直すか、'
                        f'<a href="/search?t=__TAGURI_TOKEN__&amp;cal=up&amp;q={E(q)}">'
                        f'月の指定を外して</a>お試しください。<br>')
        body = (f'<p class="empty">{narrowed}手元には、これから観られる公演にも観た記録にも'
                '見つかりませんでした。<b>公演ページを見つけられなかった記録は、'
                '出演者や題材では引けません</b> ── その場合は題名でお試しください。</p>')
        return layout("探す", "/search", head + body + web_html + cal, RR.STYLE)
    if not hits:
        past = ('<h2>観た記録</h2>'
                '<p class="empty">観た記録の中には見つかりませんでした。</p>')
        return layout("探す", "/search",
                      head + _search_follow(names) + up_html + past + web_html + cal,
                      RR.STYLE)
    n_un = sum(1 for w, _ in hits if not w.get("verdict"))
    lead = (f'<h2>観た記録 {len(hits)} 件</h2>'
            + (f'<p class="lead">このうち {n_un} 件はまだ評価が付いていません。'
               f'<b>この場で ◎○△× を押せます。</b></p>' if n_un else
               '<p class="lead">評価を付け直すことも、感想を足すこともできます。</p>'))
    return layout("探す", "/search",
                  head + _search_follow(names) + up_html + lead + "".join(rows)
                  + web_html + cal, RR.STYLE)


# ---------------------------------------------------------------- 書き出す
def export_payload() -> dict:
    """持ち出せる形。**囲い込まないことが記録としての価値の条件である**（企画書 2 章）。"""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    out: dict = {}
    for t in ("works", "ratings", "attendance", "reaction", "ticket", "presented",
              "splits", "excluded", "missed"):
        try:
            out[t] = [dict(r) for r in con.execute(f"SELECT * FROM {t}")]
        except sqlite3.Error:
            out[t] = []
    con.close()
    out["declared"] = RC.load_declared()
    return out


# 書き出しに入るものの名前。**画面には、何を数えたものなのかが分かる言葉を出す。**
#
# 以前はここに `works ── 108 件` `ratings ── 51 件` `reaction ── 91 件` と、
# **データベースの表の名前をそのまま並べていた。** 表の名前は作る側の都合で付いた
# 記号であって、**読む人にとっては何が 108 件あるのかを言っていない。**
#
# **英語の名前も小さく添える。** この画面の用は「これから保存するファイルに何が
# 入っているか」を言うことで、**ファイルの中の項目名は実際に英語である** ──
# ほかの道具で開いたときにどの並びがどれなのかが分からないと、持ち出せたことにならない。
# 主に読むのは日本語のほうなので、英語は控えの大きさで置く。
EXPORT_LABEL = {
    "works": "観た公演の記録（作品ごと）",
    "ratings": "観た回ごとの評価と感想",
    "attendance": "観に行ったかどうかの答え",
    "reaction": "おすすめへの答え（持っている・興味あり・興味なし）",
    "ticket": "券の日にち",
    "presented": "これまでにお出しした一覧",
    "splits": "1 通のメールを複数の公演に分けた指定",
    "excluded": "取り込みから外した公演",
    "missed": "「観ればよかった」の登録",
    "declared": "お気に入りに登録した名前と題材",
}


def _export_card_html() -> str:
    """「書き出す」の札。**もとは独立の画面だった**（起案者の指示・2026-08-26 ──
    「とりあえず書き出し機能はあまり使わないので設定に移動してしまって」）。
    たまにしか押さない道具という点で、「設定」の他の項目と役目が近い。
    """
    d = export_payload()
    li = "".join(
        f'<li>{E(EXPORT_LABEL.get(k, k))} <b>'
        f"{len(v) if isinstance(v, list) else sum(len(x) for x in v.values())} 件</b>"
        f'<span class="xk">{E(k)}</span></li>'
        for k, v in d.items())
    n_img = len(PO.have())
    return f"""<details class="card">{_card_h2("download", "書き出す")}
<p class="lead">記録・評価・感想・お気に入りを、1 つのファイルにまとめて保存できます。
中身は下のとおりで、ほかの道具で読める形（JSON）です。</p>
<ul class="lead">{li}</ul>
<a class="dl" href="/export.json?t=__TAGURI_TOKEN__" download="taguri-export.json">
 taguri-export.json を保存する</a>
<p class="note"><b>ポスター {n_img} 枚と、半券の写真は入りません。</b>
ポスターは外部サイトの画像を写したものなので、書き出しには含めていません。
半券の写真は、いまのところ 1 枚も持っていません。</p></details>"""


def _data_dir_size() -> int:
    """`data/review` 配下の合計バイト数。**「別の端末に記録を移す」札**で、
    ダウンロードの重さを先に言うために使う。
    """
    total = 0
    base = ROOT / "data" / "review"
    if base.exists():
        for p in base.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    return total


def _human_size(n: int) -> str:
    return f"{n // 1024} KB" if n < 1024 * 1024 else f"{n / (1024 * 1024):.0f} MB"


def _data_copy_card_html() -> str:
    """「別の端末に記録を移す」の札（起案者の指示・2026-08-26 ──「その設定に
    ファイルをコピーする機能を追加してください。あまりパソコンに詳しくない人でも
    できるようにワンタッチで」）。

    ## サーバー越しには送らない

    **この仕組みは `127.0.0.1` にしか耳を傾けない**（企画書 5 章の守り 2）。同じ
    Wi-Fi の別の端末へ直接送る形にするには、この縛りを崩して LAN に耳を傾ける
    必要があり、**「同じ LAN の他の端末から観劇記録が読める」という、守りが名指しで
    挙げている危険をそのまま作ることになる。** 採らない。

    ## 「ワンタッチ」を、押せる範囲に絞った

    **1 回押すと、`data/review` 配下（記録・取得物・ポスター）を 1 つの ZIP に
    まとめてダウンロードできる。** ここまでが「ワンタッチ」である。**そのファイルを
    別の端末へ運ぶ操作（クラウドストレージ・USB・AirDrop 等）と、向こうの
    `data/review` フォルダに置き換える操作は、本人が普段使っている手段に委ねる**
    ── 運ぶ手段は端末の組み合わせで変わるので、ここで 1 つに決め打ちできない。

    ## 「書き出す」（JSON）とは中身が違う

    「書き出す」は、**ほかの道具でも読める形に絞った抜粋**（ポスター・半券の写真は
    含まない）。こちらは、**同じ端末で `run.py` を動かすのに要るものを漏らさず**
    含める ── ポスターも、これまでに取得した候補・あらすじもそのまま入るので、
    移した先ですぐに今までどおり使える。
    """
    size = _human_size(_data_dir_size())
    return f"""<details class="card">{_card_h2("download", "別の端末に記録を移す")}
<p class="lead">このボタンを押すと、いまの端末の記録をまとめて 1 つのファイル
（ZIP・約 {E(size)}）としてダウンロードできます。<b>別の端末で続きから使うには、
ダウンロードしたファイルを展開し、中身をその端末の <code>data/review</code>
フォルダに置き換えて、<code>python3 tools/taguri/run.py</code> を実行してください。</b></p>
<a class="dl" href="/data.zip?t=__TAGURI_TOKEN__" download="taguri-data.zip">
 記録をまとめてダウンロードする</a>
<p class="note">この仕組みはインターネットにも、同じ Wi-Fi の他の端末にも直接は
つながりません。ファイルを運ぶところは、お使いの方法（クラウドストレージ・USB
など）で行ってください。</p></details>"""


# ---------------------------------------------------------------- 券の日にち
#
# 起案者の指示（2026-08-25）──「公演カレンダーの『すでに持っている』公演を、帯の中で
# 一点で表示したい。1 作品に対して複数持っている場合も考えて」。
#
# **帯は期間しか言えなかった。** 「すでに持っている」は押した印（`reaction.owned`）
# しか持っておらず、**何日の回に行くのかがどこにも無かった**ので、暦には
# 「この期間のどこかに行く」としか書けなかった（`stage_calendar.py` の説明）。
# 日にちを 1 枚ずつ持てば点が置ける ── 置き場所は `feedback.ticket`（1 行 1 枚）。
#
# **日にちの出どころは 2 つある。**
#
# | 出どころ | 何が取れるか |
# |---|---|
# | **購入確認メール** | 上演日と時刻。すでに取り込んである（`performances.jsonl`）。実測で先の券が 2 件あり、うち 1 件は時刻まで入っていた |
# | **本人が入れる** | メールが無い券（窓口・当日券・譲り受け）と、メールから起こした行の直し |
#
# **探すのは機械、確定は人である。** メールから起こした行は本人が消せる・直せるし、
# **どの公演の券か決められなかった分は黙って捨てず、暦の下に件数と題名で出す。**
def _future_purchases(today: str) -> list[dict]:
    """購入確認メールから起こした、**これから先の回**。**人が直した値を使う。**"""
    import rate_performances as RP
    out = []
    for r in RP.load_purchases():
        d, t = r.get("date_eff") or "", (r.get("title_eff") or "").strip()
        if d >= today and t:
            out.append({"uid": str(r.get("uid") or ""), "title": t, "date": d,
                        "time": (r.get("time") or "")[:5],
                        "venue": r.get("venue_eff") or ""})
    return out


def sync_mail_tickets(owned: list[dict], today: str = "") -> list[dict]:
    """メールの券を暦の公演に結び付ける。**結び付かなかった分を返す。**

    **作品の題名だけでは足りない。** 同じ作品がツアーで別会場にかかっていると
    公演の id が違うので（フタマツヅキ・ミス・サイゴンが実際にそうである）、
    **上演期間にその日が入っていることまで見て 1 件に絞る。** 会場名が取れていれば
    そちらでも絞る。**それでも 1 件に決まらないものは推測しない。**
    """
    import datetime
    import feedback as FB
    import recommend2 as RC2
    today = today or datetime.date.today().isoformat()
    buys = _future_purchases(today)
    if not buys:
        return []
    con = FB.connect()
    try:
        left = []
        for b in buys:
            k = RC2.work_key(b["title"])
            hit = [c for c in owned
                   if RC2.work_key(c.get("title") or "") == k
                   and _in_period(c.get("period") or "", b["date"])]
            if len(hit) > 1 and b["venue"]:
                hit = [c for c in hit if b["venue"] in (c.get("venue") or "")] or hit
            if len(hit) != 1:
                left.append(b)
                continue
            FB.add_ticket(con, str(hit[0].get("stage_id") or ""), b["date"],
                          b["time"], source="mail", uid=b["uid"])
        return left
    finally:
        con.close()


def _in_period(period: str, day: str) -> bool:
    """`day`（YYYY-MM-DD）が上演期間の中か。**読めない期間は入っていない扱いにする。**"""
    import recommend2 as RC2
    s, e = RC2.period_start(period or ""), RC2.period_end(period or "")
    if not s or not e:
        return False
    return str(s) <= day <= e.isoformat()


def ticket_target(stage_id: str, date: str) -> str:
    """行く日の入力が、どの会場の stage_id に当たるかを決める。

    起案者の指示（2026-08-26）──「行く日は公演の地方ごとにわけるのではなく、
    各作品に対して入力欄は１個で、地方の日程は各作品に対してまとめて羅列して」。
    1 つの入力欄が同じ作品の複数の会場を代表しているとき（`stage_calendar._own_merged`）、
    入れた日がどの会場の上演期間に入るかで、書き込む先を決める。

    **押した会場の期間にまず当てはめる。** 合えばそのまま ── 1 会場しか無い、
    いちばん多い場合はここで終わる。**合わなければ、同じ作品（`RC2.work_key` が
    同じ）の他の会場を `_upcoming_index()` から探し、期間に日が収まる会場があれば
    そちらへ回す。** `_upcoming_index()` は候補・カレンダー・お気に入りの 3 つの控えを
    合わせた「これから観られる公演すべて」の索引なので、いま owned／tracking の
    束に入っていない会場（まだ反応していない他会場）も見つかる。

    **どこにも収まらなければ、元の stage_id のまま返す。** 呼び出し側
    （`save_ticket`）に、いつもどおり「上演期間の中の日を入れてください」と
    断らせる ── ここで別の会場を無理に当てはめない。
    """
    import recommend2 as RC2
    idx = _upcoming_index()["rows"]
    c = idx.get(stage_id)
    if c and _in_period(c.get("period") or "", date):
        return stage_id
    title = (c or {}).get("title") or ""
    if not title:
        return stage_id
    k = RC2.work_key(title, stage_id)
    for sid, cand in idx.items():
        if sid == stage_id or RC2.work_key(cand.get("title") or "", sid) != k:
            continue
        if _in_period(cand.get("period") or "", date):
            return sid
    return stage_id


def ticket_map() -> dict[str, list[dict]]:
    """公演の id → 持っている券。"""
    import feedback as FB
    con = FB.connect()
    try:
        return FB.tickets(con)
    finally:
        con.close()


def save_ticket(stage_id: str, date: str, time: str = "", *,
                action: str = "add") -> dict:
    """券を 1 枚足す・確定する・取り消す。**画面から呼ぶ口である。**

    **「確定」は、機械が読み取った 1 枚を本人が引き受ける操作である**（起案者の指示
    2026-08-25）。購入確認メールから起こした行は確定前として置いてあり、押されるまで
    暦でも塗らない ── 読み取りは間違いうるので、確かめていないものを確かめたように
    見せない。

    **上演期間の外の日は受け付けない。** 受け付けると、暦に置く列が無いので
    **記録はされたのに札が出ない** ── 押したのに何も起きない画面になる。

    **「足す」だけは、渡された stage_id を書き込む前に当て直す**（`ticket_target`）。
    起案者の指示（2026-08-26）で「行く日を入れる」を作品単位の 1 つの入力欄にした
    ので、渡ってくる stage_id はその作品の代表会場でしかない ── **入れた日が代表
    会場の期間に無ければ、同じ作品の他の会場を探して回す。** 「確定」「取り消し」は
    すでに書かれている券を狙うので、渡された stage_id（＝押した券自身の会場）を
    そのまま使う ── 当て直すと、別の会場の同じ日付の券を誤って操作しかねない。
    """
    import feedback as FB
    sid = str(stage_id or "").strip()
    if not sid.isdigit():
        raise ValueError("公演が分かりません")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date or ""):
        raise ValueError("日にちは 2026-09-05 の形で入れてください")
    tm = (time or "").strip()
    if tm and not re.fullmatch(r"\d{2}:\d{2}", tm):
        raise ValueError("時刻は 14:00 の形で入れてください")
    con = FB.connect()
    try:
        if action == "del":
            FB.del_ticket(con, sid, date, tm)
        elif action == "confirm":
            FB.confirm_ticket(con, sid, date, tm)
        else:
            sid = ticket_target(sid, date)
            c = _upcoming_index()["rows"].get(sid) or {}
            if c and not _in_period(c.get("period") or "", date):
                raise ValueError(f'{c.get("period") or "上演期間"} の中の日を入れてください')
            FB.add_ticket(con, sid, date, tm, source="screen")
        return {"ok": True, "stage_id": sid, "tickets": FB.tickets(con).get(sid) or []}
    finally:
        con.close()


# ---------------------------------------------------------------- 公演カレンダー
def page_calendar(kinds: set[str] | None = None, prefs: set[str] | None = None) -> str:
    """追いかけている公演を、月ごとの暦に期間の帯で並べる画面。

    起案者の指示（2026-08-24）──「興味ありとお気に入りを一括でカレンダーに表示する
    『公演カレンダー』のページが独立してあってもいいんじゃない？」。**乗せるものは
    「すでに持っている」を加えた 3 種類**（起案者の選択）。

    **この画面は答えを出さない。** 順位を付けず、束の割り振りも変えない ── すでに
    決まっている 3 つの束を、日付という別の軸に置き直しただけである（企画書 1 章
    「システムが出す答えは 1 つである」を壊さない）。**組み方の理由は
    `stage_calendar.py` の説明にある。**

    **`kinds`／`prefs` は絞り込み**（起案者の指示・2026-08-25 ──「公演カレンダーに
    フィルタリング機能をつけたい」）。`/recommend` の都道府県の絞り込みと同じく
    素の GET なので、この関数は要求のたびに `None`（絞り込みなし）から作り直す ──
    起動のあいだ覚える状態は持たない。組み方は `SC.panel`／`SC.filter_html` にある。
    """
    d, _ = _load()
    # **購入確認メールの券を、開くたびに結び付け直す。**（取り込みと結び付けは
    # 同じ 1 回で走らせる ── 分けると、メールは入っているのに暦に点が出ない状態が残る）
    left = sync_mail_tickets(d.get("owned") or [])
    tickets = ticket_map()
    # **「日程を追加する」はページの上に置く**（起案者の指示・2026-08-26 ──
    # 「行く日を入れる」は畳んだので、その早道になる。組み方は `SC.add_ticket_button_html`
    # にある。
    body = f"""<h1>公演カレンダー</h1>
{SC.add_ticket_button_html(d, tickets=tickets)}
<p class="lede">券を持っている公演・「興味あり」を押した公演・お気に入りに当たった公演を、
上演期間の帯で並べています。<b>いつまで観られるか</b>が 1 枚で分かります。
券を持っている公演は、行く日を入れるとその日が半券の形になって出ます。</p>
{SC.panel(d, tickets=tickets, unplaced=left, sel_kinds=kinds, sel_prefs=prefs)}"""
    return layout("公演カレンダー", "/calendar", body, RR.STYLE + SC.STYLE)


# ---------------------------------------------------------------- 購入済み公演
def page_tickets() -> str:
    """チケットをすでに買っている公演の一覧。

    起案者の指摘（2026-08-25）──「もうチケットを買っていてこれから観に行く公演に
    ついてまとめられているページがない」。**「すでに持っている」の束は、それまで
    2 か所に分かれていた** ── 公演カレンダーで束を「すでに持っている」だけに絞る、
    または「おすすめ」のいちばん下で「もう追いかけない公演（興味なしと答えた分）」と
    同じ見出しの下に畳んである一覧。**どちらも「これから観に行く」ことを主役にした
    画面ではなかった。** 独立した画面を作る案を選んだ（起案者の選択）。

    **画面の名前は「もう観に行く公演」→「持っているチケット」→「購入済み公演」と
    2 度直した**（起案者の指摘・2026-08-25 ──「『もう観に行く』って日本語変。
    チケットをすでに買ってる公演ってことだよね？」、続けて「持っているチケット、を
    『購入済み公演』に変えて」）。**決まっているのは「券を買ったか」だけである。**

    **中身はチケットカード。** 推薦・興味あり・お気に入りと同じ `RR.ticket()` を使う ──
    値段・上演期間・あらすじ・出演者という、観るかどうかを決めるのに要る事実は
    もう決まった後でも読み返す価値がある（`ticket()` の説明にある判断と同じ）。

    **並びは都道府県順（北から南）にする。** 公演カレンダーの縦の並びと同じ規約
    （起案者の指摘・2026-08-25）── ここも件数が増えれば同じ「県がごっちゃ」が起きる。
    同じ県の中は締切の近い順のままにした。

    ## 「行く日を入れる」は各カードの中に置く（2026-08-26 に撤回）

    前は、ページの上に置いた 1 つの「観劇日を追加する」ボタンから、公演を選んで
    入れるポップアップにまとめていた。**起案者の指摘 ──「『観劇日を追加する』の
    ボタンを消して、各公演ごとに観劇日を追加できる欄を設けてください」。** すでに
    そのカードを見ている状態なので、改めて公演を選び直す手間が要らない
    （`render_recommend.ticket` の `my_tickets` を見る）。**暦に出せていない券の
    知らせ（`ticket_manager_html`）だけはページの下に残す** ── どの公演の券か
    決められなかった分なので、特定のカードには置けない。
    """
    d, _ = _load()
    owned = d.get("owned") or []
    import datetime
    import feedback as FB
    import recommend2 as RC2

    def _rank(c: dict) -> tuple:
        p = c.get("pref") or ""
        e = RC2.period_end(c.get("period") or "")
        return (RR.PREFS.index(p) if p in RR.PREFS else len(RR.PREFS),
                e or datetime.date.max, c.get("title") or "")

    tickets = ticket_map()
    # **実際に持っている券の日時を、カードにも出す**（起案者の指摘・2026-08-26 ──
    # 「実際にチケットを持っている公演の日時も表示して」）。「行く日を入れる」道具
    # （下の帯）には出ているが、カード自身には出ていなかった。**券は代表会場とは
    # 違う stage_id に付いていることがある**ので、`_react_groups` で同じ作品の分を
    # まとめて集める（`_rebucket` が「観る予定」から外す判定に使うのと同じ集め方）
    con = FB.connect()
    try:
        groups = _react_groups(FB.reactions(con))
    finally:
        con.close()

    def _my_tickets(c: dict) -> list[dict]:
        sids = groups.get(RC2.work_key(c.get("title") or ""), [str(c.get("stage_id") or "")])
        # **どの会場の券かを、確定・取り消しの押し口が使えるように残す。** `tickets`
        # は会場（stage_id）ごとの辞書なので、まとめた時点で分からなくなる
        rows = [{**t, "sid": sid} for sid in sids for t in (tickets.get(sid) or [])]
        return sorted(rows, key=lambda t: (t["date"], t.get("time") or ""))

    cards = "".join(RR.ticket(c, mode="owned", my_tickets=_my_tickets(c))
                    for c in sorted(owned, key=_rank))
    left = sync_mail_tickets(owned)
    body = f"""<h1>購入済み公演 ── {len(owned)} 件</h1>
<p class="lede">「すでに持っている」と答えた公演と、購入確認メールから見つかった
公演です。<b>次の推薦は変わりません</b> ── 答えを出すのは推薦だけです。上演日を
過ぎると、この一覧からは外れ、<a href="/rate?t=__TAGURI_TOKEN__">評価一覧</a>の
評価待ちに移ります。行く日は、各公演の「行く日」の欄から入れられます。</p>
{cards or '<p class="empty">チケットを持っている公演はまだありません。'
          '推薦の画面で「すでに持っている」を押した公演が、ここに並びます。</p>'}
{SC.ticket_manager_html(unplaced=left)}"""
    return layout("購入済み公演", "/tickets", body, RR.STYLE + SC.STYLE)
