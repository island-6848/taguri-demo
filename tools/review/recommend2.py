#!/usr/bin/env python3
"""名簿と候補のクレジットを突き合わせて、推薦を出す（網 B が主）。

## 前の版（recommend.py）との違い

前の版は候補をステイジーズカレンダーから取っていたが、**カレンダーに公演名の列が無い**ため
人物で照合できず、網 B の寄与が 0 件だった（[検証 015](../../docs/verification/015-first-real-recommendation.md)）。
この版は `tools/review/fetch_candidates.py` が CoRich から集めた
**公演名とクレジットつきの候補**を使う。

## 正例は「◎」だけ

[検証 009](../../docs/verification/009-net-b-discrimination.md) のとおり、**○ 以上を正例にすると
判別力が AUC 0.556（でたらめ同然）まで落ちる。** 評価は ◎ 37% / ○ 49% で ○ に寄っているため、
基準線が 0.76 まで上がり、ほとんどの人物の寄与が 0 か負になるからである。**◎ だけを正例に
すると 0.744。** 企画書 4 章もこの切り方に直してある（網 B の o_p は「◎ を付けた本数」、
r_base は「全体の ◎ 率」）。**この版はその決定に合わせた。** 重み（◎1.0 ○0.7 △0.3 ×0）で
数える案は 0.648 で負けたので採らない。

## 団体も会場も理由に使わない

[検証 016](../../docs/verification/016-troupe-is-a-confounder.md) のとおり、団体の当たり率は
交絡する（東宝 11 作品のうち 9 作品がジャニーズ系の舞台だった）。**この版では団体を
スコアに入れない。**

**会場も外した。** 交絡（博多座で観た 2 本はどちらも 作品1）を残差で消す案を先に
試したが、[検証 019](../../docs/verification/019-scoring-fixes.md) で**会場だけで ◎ を当てる
AUC が 0.285** ── 0.5 を下回る、つまり使うと有害だと分かった。**残差にする以前に、
正の側が存在しない。** 避けたい会場は申告で持つ（負の側だけ）。

## 網 C を入れた（2026-08-20）

**理由として出せるのは人物（網 B）だけだった。** あらすじの規則による切り出しが実質 24% で、
内容の要素が 1 件も取れていなかったためである（検証 020）。抽出の担い手を LLM に変え
（`tools/credits/extract_theme_llm.py`）、**確定させた結果を読むだけ**にした。
この版で理由に出せるのは人物と**内容の要素**である。

**LLM はこのスクリプトの中では 1 回も呼ばない。** 抽出は別スクリプトで済ませて DB に確定させて
あるので、同じ DB から同じ順位と同じ理由文が出る（企画書 5 章）。

## 束は 5 つ ── 推薦枠には「まだ初日を迎えていない、判断していない公演」だけを置く

反応が付いた公演は、信号ごとに行き先を分ける（[検証 026](../../docs/verification/026-does-feedback-change-output.md)）。

| 反応 | 行き先 |
|---|---|
| すでに持っている | 枠から外す |
| **興味あり** | **「追いかけている」枠へ移す**（上演日の近い順。買い忘れを防ぐ用途なので軸が違う） |
| 興味なし | 「その他」へ畳む（消さない。あとから「観ればよかった」を拾うため） |
| 未回答・**まだ初日を迎えていない** | **推薦枠** |
| 未回答・**もう上演が始まっている** | 「初日を迎えた公演」へ移す。**推薦枠には出さない** ── 企画書 1 章は「初日を過ぎた公演は出さない。上演中の公演について、このシステムは何も言わない」と定めている |

    python3 tools/review/recommend2.py
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure_nets as M                       # noqa: E402
import net_c as C                             # noqa: E402  網 C（あらすじの要素）
from recommend import DECLARED, NOT_PLAY_TITLE               # noqa: E402
import recommend as RC1                                     # noqa: E402

CAND = ROOT / "data" / "review" / "candidates.jsonl"
# **お気に入りの名前で直接引いた公演。**（`tools/taguri/favourites.py`）
#
# **母集団に無い公演がここに入る。** 企画書 4 章「登録した団体・個人については、公式サイトを
# 直接見に行く ── 無条件で出すと決めた対象なのだから、母集団の制約を受ける理由がない」に
# あたる経路で、**設計にはあったが実装が無かった**（起案者の指摘「作り手9をお気に入り登録して
# いるのに、今後の公演が拾えてないのはなぜ？」から辿って分かった）。
# 実測 ── 一覧の走査で集めた 818 件に無い公演が **33 件**出てきた（作品4 3 会場・
# イェルマ・蝶々夫人・お気に入り79 ほか）。
FAV = ROOT / "data" / "review" / "favourites.jsonl"
# **ステイジーズカレンダーから足した公演。**（`tools/taguri/fetch_stage_calendar.py`）
#
# **CoRich とほとんど重なっていない。** カレンダーの楽日が今日以降の 738 件のうち、
# **542 件は CoRich から集めた候補に無かった**（東京が大半）。企画書 5 章の役割分担
# 「母集団の網羅性はカレンダー側が担保し、CoRich はクレジットが取れる候補を供給する」に
# 戻す ── 実装が CoRich だけになっていた。
#
# **クレジットは既定では付いていない**ので、網 B・C の点は 0 になる。**候補としては
# 生きている** ── お気に入りの団体照合と「初日までに 1 回出す」の対象には入る
# （クレジットが取れないことは候補から消す理由にならない。検証 037）。
CALENDAR = ROOT / "data" / "review" / "calendar.jsonl"
PICKED = ROOT / "data" / "review" / "picked.jsonl"

# **正例は「◎ かどうか」で数える。** 重み付き（◎1.0/○0.7/…）だと全体の当たり率が 0.76 になり、
# ほとんどの人物の寄与が負になって**1 作品あたり寄与が正の人物が中央値 0 人**になる。
# その結果、推薦の理由が 1 件ずつの単独になっていた。◎ 率（0.38）を基準にすると
# 中央値 3 人になり、**複数の理由が重なった公演が上位に来る。** AUC も 0.643 → 0.665。
POSITIVE = staticmethod(lambda v: 1.0 if v == "◎" else 0.0)

# **役職の重みは実測の判別力で置く。** 企画書 4 章は「演出・脚本を大きく、出演を中」
# （1.0/1.0/0.6）としていたが、単独の AUC は出演 0.611 > 演出・脚本 0.540 > 裏方 0.500 で**逆**。
# 裏方は 0 にはしない（理由として出せる）が、**優先度は最下位**にする。
ROLE_W = {"出演": 1.0, "演出": 0.4, "脚本": 0.4, "作": 0.4, "原作": 0.4, "翻訳": 0.3}
BACKSTAGE_W = 0.1

# **興味あり・観ればよかったの人物は、◎ より弱い正例として名簿に混ぜる**（起案者の
# 指示・2026-08-26 ──「『観ればよかった』で挙がった人名は『興味あり』のボタンを
# 押した扱いと同じにして、推薦に反映させて」）。**この値は AUC で測っていない**
# （◎/○/△/× や役職の重みと違い、まだ検証していない新しい信号である）。見たい・
# 見逃したと思っただけで実際に観て評価したわけではないため、◎（1.0）より
# 明確に弱い値から始める。当たり方を見て調整が要る。詳しい理由は
# `measure_nets.add_interest_roster` を参照
INTEREST_W = 0.5

# **順位付けに使う役職を、利用者が自分で選べるようにする案（未実装・納期外の候補）。**
#
# 起案者の提案 ──「その辺の**順位付けに使う情報をユーザが自分で設定できるような機能は
# 必要**ですね」。あわせて一人の利用者としての好みも述べている ──「**私なら**ヘアメイクや
# 宣伝の情報は理由として出されても絶対不要」。
#
# **既定は空にする。** 一人の好みを全員の既定に書き込むのは、
# **提案そのもの（利用者ごとに設定できるようにする）と正反対**である。
# 追記 3 で測ったとおり、**追う役職は人によって変わる**（申告した 9 人は出演 6・演出 2・裏方 0
# だが、繰り返し出会っているのは裏方・制作が 6 人）。
#
# **入れるときは、スコアと理由の両方から外す。** 理由として出せないものが順位を動かすと、
# 「なぜこれが出たか」を説明できない公演が上位に来る（企画書 2 章）。
ROLE_OFF: set[str] = set()
# 網 C（推定）の重み。**企画書 4 章のとおり、稼働している網で等分にする（B と C を 1:1）。**
#
# **一度 0 にしたが戻した。** 網 C だけで ◎ を当てる AUC は 0.551 ± 0.167 で、B に足しても
# 上がった回が 0/40 だった（検証 034）。判別だけを見れば 0 にする理由があるが、**候補を拾う役を
# 同時に消してしまう** ── 網 C を外すとスコアの付く候補が 136 件から 29 件に落ちる（検証 033）。
# 企画書 1 章は「外れを引かないこと（判別）ではなく、取りこぼさないこと（探索）」を中心に置いて
# いるので、**探索の役を判別の数字で落とさない。** 判別に効かないことは、順位の付け方の問題として
# 別に扱う（検証 034 の「順位を網 C で付けない」）。
W_C = 1.0
OUT = ROOT / "data" / "review" / "recommend2.json"


def nz(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "")).replace(" ", "").replace("　", "").lower()


def work_key(title: str, stage_id: str = "") -> str:
    """**同じ作品のツアー日程を 1 件にまとめる鍵。**

    まとめないと、照明が同じ巡業公演が 8 会場ぶん並んで一覧を占領する。**反応の抑制も
    この鍵で掛ける** ── stage_id で掛けると、外した公演がツアーの別会場として戻ってくる。
    """
    return re.sub(r"[『』「」\s　]", "", nz(title))[:24] or stage_id


def period_start(period: str) -> str:
    """初日を並べ替えできる形（YYYY-MM-DD）で返す。追跡枠を上演日の近い順にするために使う。

    **月日は 0 詰めしてから比べる。** 元の表記は「2026/08/26」だが 1 桁の月日も混ざりうるので、
    文字列のまま比べると 10 月が 8 月より前に来る。
    """
    m = re.search(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    return f"{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}" if m else ""


def period_end(period: str):
    ms = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    if not ms:
        return None
    y, m, d = ms[-1]
    return datetime.date(int(y), int(m), int(d))


ONSALE = re.compile(r"【発売日】\s*(20\d\d)/(\d{1,2})/(\d{1,2})")


def run_days(period: str) -> int:
    """**上演日数を返す。** 期間だけでなく日数を出すのは企画書 2 章の表示項目である
    ── 中央値 4 日・19% が 1 日公演なので、何日あるかで動き方が変わる（検証 008）。"""
    s, e = period_start(period), period_end(period)
    if not s or not e:
        return 0
    return (e - datetime.date.fromisoformat(s)).days + 1


def url_of(field: str) -> str:
    """公式サイトの URL。**見た直後に取れる行動を残すために出す**（企画書 2 章）。"""
    m = re.search(r'https?://[^\s"<>）)]+', field or "")
    return m.group(0).rstrip("。、") if m else ""


def onsale(fields: dict, today: datetime.date) -> str:
    """販売状況。**取れないものは「確認できず」と書いて出す**（企画書 2 章）。

    **判定できるのは発売日だけである。** CoRich の料金欄には全 818 件に「【発売日】」の見出しが
    あり、日付が入っているのは 672 件（82%）。**「販売終了」「予定枚数終了」は一覧にも
    公演ページの表にも無いので、ここでは判定できない** ── 落とさずに「確認できず」を添える
    （当日券の経路があるため消さない）。
    """
    ds = [datetime.date(int(y), int(m), int(d))
          for y, m, d in ONSALE.findall(json.dumps(fields, ensure_ascii=False))]
    if not ds:
        return "確認できず"
    first = min(ds)
    return f"{first.month}/{first.day} 発売" if first > today else "発売済み"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--today", default="2026-08-20")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--no-feedback", action="store_true",
                    help="反応を読まない（反映あり／なしを比べるため。検証 026）")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--no-snapshot", action="store_true")
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today)

    # **反応を読む。** 保存する側（snapshot）だけがあって、読む側が無かった ── その結果、
    # 「興味なし」と答えた 6 件と「すでに持っている」2 件が次の一覧に同じ順位でまた出た
    # （検証 022）。**保存先を作ったことと、反応が効いていることは別である。**
    import feedback as FB                                   # noqa: E402  循環を避けて遅延
    _con = FB.connect()
    react = {} if a.no_feedback else FB.reactions(_con)
    missed = [] if a.no_feedback else FB.missed_fields(_con)
    _con.close()
    # **作品単位にも畳んでおく。** ツアーの別会場は stage_id が違うので、ID だけでは戻ってくる。
    react_w = {work_key(v.get("title") or ""): v for v in react.values() if v.get("title")}

    rated = M.load_rated()
    pos = lambda v: 1.0 if v == "◎" else 0.0          # noqa: E731 （検証 009）
    base = sum(pos(r["verdict"]) for r in rated) / max(len(rated), 1)
    roster = M.build_roster(rated, pos)
    # **興味あり・観ればよかったの人物も名簿に混ぜる**（起案者の指示・2026-08-26）。
    # `base`（◎ の当たり率）は上の行ですでに確定させてあるので、ここで混ぜても動かない。
    # 詳しい理由は `measure_nets.interest_credits`／`add_interest_roster` を参照
    interest_people = M.interest_credits(react, missed)
    roster = M.add_interest_roster(roster, interest_people, INTEREST_W)
    # **網 C を入れた。** あらすじの要素は LLM が抽出して確定させたものを読むだけで、
    # ここで LLM を呼ばない（同じ DB から同じ順位が出る性質を壊さない）。
    themes = C.load_themes()
    declined = RC1.load_declined()
    lift = C.build_lift(rated, themes, pos)
    # 網 C の理由にも**裏づけた本数**を書く（網 B の「履歴 N 本」と揃える）
    n_word = C.rated_counts(rated, themes)

    # **splitlines() を使わない。** U+2028（行区切り）でも分割してしまい、
    # json.dumps(ensure_ascii=False) はこれを escape しないため、1 レコードが割れる。
    # **まだ 1 度も取り寄せていないときは 0 件から始める。** ここで止めると `run.py` の
    # 6 段目が落ち、**画面が 1 度も開かない**（2026-08-24 の実測）。候補が無いことは
    # 「まだ `--fetch` を実行していない」という状態であって、異常ではない
    cands = [json.loads(l) for l in
             (CAND.read_text(encoding="utf-8").split("\n") if CAND.exists() else [])
             if l.strip()]
    # **直接引いた分を足す。** 鍵は stage_id で、**一覧から取れた行のほうを残す**
    # （料金・都道府県などの欄が埋まっているため）
    for src, label in ((FAV, "お気に入りの名前で直接引いた公演"),
                       (CALENDAR, "ステイジーズカレンダーから足した公演"),
                       # **探して自分で拾った公演**（起案者の指摘・2026-08-24 ──
                       # 「おすすめの 15 件とかにもまだ載ってないけど今後の情報を検索して
                       # 探したいときとかは？」）。**月 1 回の取得では集まらない公演を、
                       # 本人が探して拾った控えである。** ここに足さないと、押した
                       # 「興味あり」がどの一覧にも出てこない
                       (PICKED, "探して拾った公演")):
        if not src.exists():
            continue
        have = {str(c["stage_id"]) for c in cands}
        extra = [json.loads(l) for l in src.read_text(encoding="utf-8").split("\n") if l.strip()]
        extra = [c for c in extra if str(c["stage_id"]) not in have]
        cands += extra
        print(f"{label}を {len(extra)} 件足した")
    print(f"評価済み {len(rated)} 作品／名簿 {len(roster)} 件"
          f"（興味あり・観ればよかったで {len(interest_people)} 件分を追加）"
          f"／候補 {len(cands)} 件／基準 {base:.2f}")

    # **初日を迎えた公演は推薦枠に出さない**（企画書 1 章「出す対象は『まだ初日を迎えていない公演』」）。
    #
    # **これは実装の誤りだった。** 絞り込みを楽日（`end < today`）だけで掛けていたため、
    # **すでに上演が始まっている公演が推薦の 15 件に混ざっていた**（起案者の指摘）。
    # 企画書は「初報が出た時点から、初日の前日まで」と定め、**「初日を過ぎた公演は出さない
    # ── 上演中の公演について、このシステムは何も言わない」**と書いている。
    # 見逃しを防ぐとは初報から初日までのあいだに気づかせることなので、**初日を過ぎた公演を
    # 推薦に混ぜると、この企画の利点そのものが薄まる。**
    #
    # **消すのではなく、別の束に移す。** 絞り込みの失敗は「順位を下げる」で吸収し、
    # 「候補から消す」は避けるという方針（企画書 3 章）に従う ── 消したものは二度と目に入らない。
    # **上演中で未回答のものは `started` に置き、間に合わなかったことが分かる形で残す。**
    #
    # **お気に入り（網 A）には掛けない。** 登録した名前の公演は「内容を問わず知りたい」と
    # 本人が言っているお知らせなので、上演中でも知らせる側が正しい。追跡と観る予定も同じ。
    fav, rest, owned, tracking, started, declined_rows = [], [], [], [], [], []
    for c in cands:
        end = period_end(c["period"])
        if not end or end < today:
            continue
        # **団体名は一覧の欄にしか無い。** 公演ページの表（fields）にも題名にも出ないので、
        # ここに入れないと申告した団体と照合できない（検証 021。「ガリレイの生涯／劇団劇団4」が
        # 申告した「劇団4」に当たらず推薦側に出ていた）。818 件で誤検出 0・追加 2 件
        blob = (c["title"] + " " + c.get("group", "") + " "
                + json.dumps(c["fields"], ensure_ascii=False))
        if any(k in c["title"] for k in NOT_PLAY_TITLE):
            continue
        # 網 A ── 申告した名前。**推薦と混ぜない**
        #
        # **団体と主催は「公演団体名」だけで照合する。** 起案者の指摘 ──「劇団4とか劇団7とか
        # 言ってるのは、客演まで興味がある人とない人がいる。**団体名を検索したときは原則
        # 主催公演の情報を拾うだけでよい。客演まで追いたい人は人名で指定する**」。
        # クレジット（`fields`）まで見ると、**その団体の俳優が他団体の公演に出るものが全部
        # 当たる** ── 実測で「劇団6」は 8 件当たり、そのすべてが客演だった。
        # **軸を分けると、登録した本人が範囲を決められる。**
        #
        # **`主催` が抜けていた。** 照合する種類に入っていなかったので、主催として登録した
        # 劇場3・劇場2は**1 度も当たっていなかった。**
        hits = [f"{k}「{w}」" for k in ("団体", "主催")
                for w in DECLARED[k] if nz(w) and nz(w) in nz(c.get("group", ""))]
        # 人・作品・原作者はクレジットまで見る（客演を拾うのがこの軸の役目である）
        hits += [f"{k}「{w}」" for k in ("人", "作品", "原作者")
                 for w in DECLARED[k] if nz(w) and nz(w) in nz(blob)]
        # **申告した題材も網 A に入れる。** 検証 003 で照合先を数えたとき、「題材3」「題材2」は
        # **あらすじから抽出した要素**に照合するものとして分類してあった。これまでは題名と
        # 公演ページの表に語があるかで探しており、「ガリレイの生涯」に「題材3」の字が無いため
        # 1 件も当たらなかった（検証 021 の指摘 4）。**要素経由で照合する。**
        th = themes.get(("candidate", c["stage_id"]))
        ws = C.words(th)
        c["synopsis"] = ((th or {}).get("synopsis") or "")[:300]   # 表示（検証 021 の指摘 1）
        # **画面に出す要素は、抽出したままの表記で持つ。** 照合に使う `C.words` は
        # `nz` で小文字化と空白落としをしているので、そのまま出すと
        # 「作品1」が「endlessshock」になる。**照合の都合を画面に持ち込まない。**
        c["themes"] = [e["word"] for e in ((th or {}).get("elements") or []) if e.get("word")]
        theme_hits = C.declared_hits(ws, c["synopsis"])
        hits += [f"題材「{w}」" for w in theme_hits]
        c["a"], c["end"] = sorted(set(hits)), end
        # **出さないと決めた語に当たったか**（お気に入りの裏返し・起案者の指示 2026-08-24）。
        # 見送った理由から本人が確定した語で、**題名・団体・劇場・出演・題材のどこかに
        # 出ていれば当たり**とする ── 「オペラ」は題名に出ないことがあり（「イタリアの
        # トルコ人」）、**劇場名（劇場3 オペラ劇場）で分かる。**
        # **申告（お気に入り）が勝つ ── ただし「主催」だけで当たった公演は勝たない**
        # （起案者の指示・2026-08-26 ──「『出さない語』は、お気に入りの中で『主催』の
        # ものだけにも適用してください」）。**主催の登録は劇場が自主で組む公演を丸ごと
        # 拾う軸で、団体・人・作品・原作者のような「この名前なら内容を問わず知りたい」
        # という狭い指定とは違う。** 主催で当たった公演のうち、除外の語にも当たるものは
        # 除外を勝たせる。**団体・人・作品・原作者・題材のどれかでも当たっていれば**、
        # その軸は変えていないので、これまでどおり除外の語には当たらない
        host_only = bool(c["a"]) and all(h.startswith("主催「") for h in c["a"])
        c["declined"] = "" if (c["a"] and not host_only) else next(
            (w for w in declined
             if nz(w) and (nz(w) in nz(blob) or any(nz(w) in nz(x) for x in ws))), "")
        _s = period_start(c["period"])
        # **初日が読めない行は落とさない。** 読めないものは推薦枠に残し、判断は本人に委ねる
        c["upcoming"] = (not _s) or datetime.date.fromisoformat(_s) > today
        c["opened"] = "" if c["upcoming"] else _s
        # **識別と行動に必要な項目を、ここで 1 件ごとに持たせる**（企画書 2 章「1 件に表示するもの」）。
        # 集計の都合で省くと、受け取る側には何のことか分からない（検証 021 の指摘 1 と同じ誤り）。
        c["days"] = run_days(c["period"])
        c["onsale"] = onsale(c["fields"], today)
        c["url"] = url_of(c["fields"].get("公式／劇場サイト", ""))

        people = M.parse_credits(c["fields"])
        parts = []
        for role, person in people:
            n, o = roster.get((role, person), (0, 0))
            if n == 0:
                continue
            rr = (o + M.SMOOTH_A) / (n + M.SMOOTH_B)
            w = ROLE_W.get(role, BACKSTAGE_W)
            contrib = (rr - base) * (n / (n + M.CONF_K)) * w
            if contrib > 0:
                parts.append((round(contrib, 4), role, person, n))
        parts.sort(reverse=True)
        # **上位 3 件の和が最良**（AUC 0.643 対 単独 0.615・全部の和 0.615・人数だけ 0.608）。
        # 重なりを足す方向は実測で裏づけられている。
        c["b"] = round(sum(p[0] for p in parts[:M.TOP_N]), 4)
        c["why_b"] = parts[:6]
        c["n_match"] = len(parts)
        # **効く一致の数。** 起案者の指摘「知っている人がたくさん出ているものから順に」を
        # 素の人数で数えると、**判別力の無い裏方が多いだけの公演が上位に来る**
        # ── 裏方は単独の AUC 0.500（でたらめ同然）で、決め手だった例は 7 件中 0 件
        # （検証 028）。**出演、または履歴 2 本以上の人物に限って数える。**
        c["strong"] = sum(1 for p in parts if p[1] == "出演" or p[3] >= 2)
        c["vr"], c["why_v"] = 0.0, ""
        c["theme"] = theme_hits
        # **あらすじの要素が 1 語も取れなかったことを記録する。** 下の並べ替えで
        # 「重なりが無い」と同じに扱ってはいけない ── **材料が無いことは、合わないことではない。**
        c["no_c_material"] = not ws
        # 網 C（推定）── ◎ を付けた作品に多い要素か。**寄与が正の上位 3 個の和**
        c["c"], _wc = C.strength(ws, lift)
        c["why_c"] = [[v, w, n_word.get(w, 0)] for v, w in _wc]
        # **申告はスコアに足さない。** 検証 012 で、申告を加点として混ぜると推定だけより
        # AUC が 0.744 → 0.660 に下がると出ている。**申告は網 A で無条件に出す側で使う。**
        #
        # **C-推定（lift）もスコアに入れない。** 企画書 4 章は稼働している網を等分で足すと
        # 書いているが、実測すると**網 C だけの AUC は 0.551 ± 0.167（40 回の取り直し）で、
        # B に足しても上がった回が 0/40** だった（検証 022）。原因は語が重ならないことである
        # ── 学習側 31 作品に出た 95 語のうち 3 作品以上に出るのは 9 語だけで、
        # しかも上位は「家族・恋愛・コメディ・友情」という**候補側でも高頻度な一般語**である。
        # 企画書が宣伝語について予想した挙動（全体でも高頻度なので lift が 0 に近づく）が、
        # 一般的な題材の語でも起きている。**寄与で判断するという手続き（裏方・会場と同じ）に従い、
        # 重みを 0 にする。** 値は記録して残すので、学習側が増えたら測り直せる。
        c["total"] = round(c["b"] + W_C * c["c"], 4)
        # **抑制は信号ごとに変える**（検証 022）。**学習に入れるかと、提示から下げるかは別に決める。**
        # すでに持っているものは束の定義に反するので枠から外し（「今週の推薦」は
        # **まだ判断していない公演**を出す場所である）、興味なしは**消さずに「その他」へ畳む**
        # ── 大半は好みの否定ではなく日程・場所・予算の制約なので、消すと
        # 「観ればよかった」を後から拾えなくなる。
        r = react.get(str(c["stage_id"])) or react_w.get(work_key(c["title"])) or {}
        if r.get("owned") == 1:
            owned.append(c)
            continue
        # **興味ありも推薦枠から出す。** 検証 026 では「興味ありは追跡の開始を兼ねる信号なので
        # 上演中は出し続けるのが正しい」と書いたが、**その判断を撤回する。** 起案者から
        # 「なんで一度興味ありにした演目がまたおすすめに出てるの？」という指摘を受けた ──
        # **推薦枠はまだ判断していない公演を出す場所**（購入済みを外したのと同じ理由）であり、
        # 判断が済んだものが席を占めると、探索に使える枠がその分だけ減る。
        # **消すのではなく別の束に移す**ので、追跡の用途は失われない。**並べる軸も変える** ──
        # 追跡枠の用途は買い忘れを防ぐことなので、スコア順ではなく**上演日の近い順**にする。
        if r.get("interest") == 1:
            tracking.append(c)
            continue
        # **出さないと決めた語に当たった公演は、推薦枠に出さない。**
        # **消さずに別の束に置く**（企画書 3 章 ── 消したものは二度と目に入らない）。
        # 本人が語を外せば、次に一覧を組み直したときに戻ってくる
        if c.get("declined"):
            declined_rows.append(c)
            continue
        c["folded"] = r.get("interest") == 0
        if c["a"]:
            fav.append(c)
        elif c["upcoming"] or c["folded"]:
            rest.append(c)
        else:
            started.append(c)

    # **他会場は件数ではなく日程つきで持つ。**「他会場 3 件」では読み手にできることが無い
    # ── 企画書 2 章は「ツアーの他会場の日程」を表示項目に挙げている。**地方公演は
    # カレンダーに載らないので、ここでしか目に入らない。**
    sib: dict = collections.defaultdict(list)
    best: dict = {}
    for c in rest:
        if c["total"] <= 0:
            continue
        k = work_key(c["title"], c["stage_id"])
        # **他会場は「行けるかどうか」を判断できる形で持つ。** 劇場名と日程だけでは、
        # **都道府県で絞り込んだときに主たる会場として出せない** ── 発売の状況も
        # 上演日数も公式サイトも無い行を、カードの本文に出すことになる（企画書 2 章の
        # 「1 件に表示するもの」を、絞り込んだ利用者にだけ満たさない形になる）
        sib[k].append({"stage_id": c["stage_id"], "theater": c["theater"],
                       "pref": c["pref"], "period": c["period"],
                       "days": c["days"], "price": c.get("price") or "",
                       "url": c["url"], "onsale": c["onsale"]})
        cur = best.get(k)
        if not cur or (c["total"], -c["end"].toordinal()) > (cur["total"], -cur["end"].toordinal()):
            c["tour"] = (cur or {}).get("tour", 0) + 1
            best[k] = c
        else:
            cur["tour"] = cur.get("tour", 1) + 1
    for k, c in best.items():
        c["tours"] = [v for v in sib[k] if v["stage_id"] != c["stage_id"]]
    # **尺度を揃えてから足す。** 企画書 4 章は「稼働している網で等分（B と C を 1:1）」だが、
    # **重みを 1:1 にしても寄与の分布が違えば効果は 1:1 にならない** ── 実測では
    # あらすじの要素 1 語が 0.0398、履歴 1 本の裏方 1 人が 0.0072 で、**要素 1 語が
    # 知っている人 5 人より重かった。** 起案者の指摘「あらすじだけを汲み取り過ぎてるよね？」の
    # 原因はここである。**各網を母集団の 90 パーセンタイルで割って同じ尺度に直す。**
    # 最大で割らない ── 網 B は最大 0.53 に対し 90%点 0.14 で、外れ値 1 件に全体が潰される。
    pool = list(best.values())

    def p90(vals) -> float:
        v = sorted(x for x in vals if x > 0)
        return v[int(len(v) * 0.9)] if v else 1.0

    nb, nc = p90([x["b"] for x in pool]), p90([x["c"] for x in pool])
    for x in pool:
        # 1.5 で止める ── 1 件だけ突き抜けた網が、もう一方の網を無意味にしないため
        x["bn"], x["cn"] = min(x["b"] / nb, 1.5), min(x["c"] / nc, 1.5)
        x["s"] = round(x["bn"] + x["cn"], 3)
        x["both"] = x["b"] > 0 and x["c"] > 0
        # **あらすじが取れていない公演を、重なりが無い公演と同じ層に落とさない。**
        # 実測 ── 「お気に入り61」は効く一致 3 件・正規化スコア 1.50（最大）なのに、
        # あらすじが取れていないだけで 13 位に沈んでいた。「獅子 THE LION-BEAT」も同じ。
        # **取得できないことを「合わない」と扱う誤り**で、V37 で明記した扱いに反する。
        # **ただし「材料が無い」だけで上位に上げない。** 候補が 818 → 863 件に更新された結果、
        # **192 件があらすじ未取得**になっており、全部を重なりありと同じ層に置くと
        # 材料の無い公演で上位が埋まる（実測 ── あらすじが出せた件数が 13 → 6 件に落ちた）。
        # **人物の側の証拠が強いもの（効く一致 2 件以上）に限って、重なりの要求を免除する。**
        x["tier"] = 0 if (x["both"] or (x.get("no_c_material") and x["strong"] >= 2)) else 1
    print(f"正規化の分母 ── 網 B の 90%点 {nb:.4f} ／ 網 C の 90%点 {nc:.4f}"
          f"／両方かかった {sum(1 for x in pool if x['both'])} 件")
    # **効く一致の数 → 正規化スコア**の順に並べる。
    #
    # **1 段目に「重なり」（tier）を置くのをやめた（検証 044）。** 1 種類の網だけで上位が
    # 埋まる状態を防ぐために入れた鍵だが、**測ると当たりを下げていた** ── 8 通りの並べ方の
    # うち 3 段の現行が最下位（AUC 0.692）で、この 1 段を外すと **0.710 に上がり、
    # 上位 15 件の同点も 6 件から 2 件に減る。** 2 軸が同時に良くなるので選ぶ余地がない。
    #
    # 原因は、**判別に効かないと測れた網（C）の 0 を層の境目に使っていたこと**である
    # （網 C 単独の AUC は 0.551 ± 0.167。検証 034）。あらすじは取れたが持ち上がりが正の語を
    # 1 つも持たなかった公演が、人物の証拠が強くても下の層に落ちていた ── 下の層の 58 作品の
    # うち効く一致 2 件以上を持つ 5 作品の ◎ 率は **0.80**（全体 0.37）で、
    # **いちばん当たるものをいちばん下に置いていた。** 検証 010「情報が薄いことと、
    # 好みに合わないことは別である」のすぐ隣にある誤りである。
    #
    # **tier は計算だけ残す**（scored_all に出して、後から層ごとの当たり率を数えるため）。
    ranked = sorted(pool, key=lambda x: (-x["strong"], -x["s"]))
    scored = [c for c in ranked if not c.get("folded")]
    folded = [c for c in ranked if c.get("folded")]

    # 上演中の束は**初日の新しい順**（間に合わなかったばかりのものを上に出す）
    started.sort(key=lambda c: c.get("opened") or "", reverse=True)
    print(f"初日を迎えたので推薦枠から外した {len(started)} 件"
          f"（うちスコアが付いていたのは {sum(1 for c in started if c['total'] > 0)} 件）")
    print(f"お気に入り {len(fav)} 件／スコアが付いた候補 {len(scored)} 件"
          f"／うち網 B が効いた {sum(1 for c in scored if c['b'] > 0)} 件")
    # 追跡枠は**上演日の近い順**。同じ作品のツアーは 1 件に畳む（推薦枠と同じ鍵）。
    seen_t: set = set()
    track = [c for c in sorted(tracking, key=lambda x: period_start(x["period"]) or "9999")
             if not (work_key(c["title"], c["stage_id"]) in seen_t
                     or seen_t.add(work_key(c["title"], c["stage_id"])))]
    print(f"追いかけている {len(track)} 件を推薦枠から出した（興味ありと答えたもの）")
    # **お気に入りの新着は件数を切らない。** 企画書 2 章は「件数制限なし・無条件」で、
    # **本人が「内容を問わず知りたい」と言っているもの**だからである。書き出しで
    # `fav[:20]` に切っていたため、26 件のうち 6 件が出力に載っていなかった。
    # **ツアーの別会場も 1 件に畳む**（畳まないと「オールトの雲」が 3 会場ぶん並ぶ）。
    # **並べる軸は上演日の近い順** ── 用途が買い忘れ・見逃しの防止なので追跡枠と同じにする。
    seen_f: set = set()
    favs = [c for c in sorted(fav, key=lambda x: period_start(x["period"]) or "9999")
            if not (work_key(c["title"], c["stage_id"]) in seen_f
                    or seen_f.add(work_key(c["title"], c["stage_id"])))]
    print(f"お気に入りの新着 {len(favs)} 件（申告した団体・人・作品・原作者・題材で当たったもの）")
    if declined_rows:
        import collections as _co
        top = _co.Counter(c["declined"] for c in declined_rows).most_common(4)
        print("出さないと決めた語に当たった " + str(len(declined_rows)) + " 件を枠から外した（"
              + "／".join(f"{w} {n}" for w, n in top) + "）")
    print(f"すでに持っている {len(owned)} 件を枠から外し／興味なし {len(folded)} 件をその他へ畳んだ"
          + ("（--no-feedback: 反応を読んでいない）" if a.no_feedback else ""))
    a.out.write_text(json.dumps({"favourites": favs, "recommend": scored[:a.top],
                                 # **順位の付いた全件を、画面に出せる形のまま残す。**
                                 # 都道府県で絞り込んだときに **その県から 15 件**を出すには、
                                 # 全国の上位 15 件を切った後の一覧では足りない ── 大阪府で
                                 # 観られる公演は 19 件あるが、全国の上位 15 件に入っているのは
                                 # 1 件だけである。**切る位置を計算の側から画面の側へ移す。**
                                 # `recommend` は全国の答え（提示の記録と週次の指標の分母）
                                 # なので、意味を変えずにそのまま残す
                                 "ranked": scored,
                                 "others": folded, "owned": owned,
                                 # **出さないと決めた語に当たった公演。** 消していない
                                 "declined": declined_rows,
                                 "tracking": track,
                                 # **初日を迎えたので推薦枠から外した公演。** 消さずに残す
                                 # ── これが「間に合わなかった」を数える材料でもある
                                 "started": [c for c in started if c["total"] > 0][:40],
                                 "base": base, "n_cand": len(cands),
                                 "n_scored": len(scored), "feedback": not a.no_feedback,
                                 # **スコアが付いた全件の id と初日を残す。** 3 セットで
                                 # 終える設計（企画書 2 章）では、45 件で在庫が尽きるかと、
                                 # 初日までに出し切れるかを後から数える必要がある
                                 "scored_all": [{"stage_id": c["stage_id"],
                                                 "title": c["title"][:40],
                                                 "period": c["period"],
                                                 "s": c.get("s"), "b": c.get("b"),
                                                 "c": c.get("c"),
                                                 "both": c.get("both"),
                                                 # **あらすじの材料が無いことも残す。** 層の
                                                 # 境目（tier）を後から再構成できないと、
                                                 # 検証 044 の測り直しができない
                                                 "no_c": c.get("no_c_material"),
                                                 "strong": c.get("strong")}
                                                for c in scored]},
                                ensure_ascii=False, default=str, indent=1), encoding="utf-8")
    print(f"書き出し: {a.out}")

    # **出した一覧を、日付つきで残す。** OUT は毎回上書きされるので、再実行すると前の順位が
    # 消える（検証 021 の初回の順位は実際にこれで失われた）。出力側の指標（知らなかった件数・
    # 同点の割合・網ごとの興味あり率）は、その週に何をどの順でどの理由で出したかが
    # 残っていないと後から計算できない。
    if a.no_snapshot:
        return 0
    con = FB.connect()
    _n, _label = FB.snapshot(con, a.out, a.today)
    print(f"presented に {_n} 件を保存（label={_label}）")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
