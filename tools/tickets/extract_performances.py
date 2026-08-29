#!/usr/bin/env python3
"""購入確認メールから、観た（買った）公演の一覧を作る。

## 位置づけ

抽出は 3 段に分かれている（[検証 004](../../docs/verification/004-purchase-mail.md)）。

    ① 件名の網            → tools/tickets/fetch_purchase_mail.py
    ② 購入確認かの判定    → 本スクリプトの CONFIRM / APPLY / LOTTERY
    ③ 項目の抽出          → 本スクリプトの PARSERS

## ②で「応募」と「購入」を分ける理由

件名に「申込完了」とあっても、**抽選への応募が完了しただけで買えていない**ことがある。
実測では応募 2,237 通に対し確定は 437 通で、混ぜると履歴が 5 倍に水増しされる。
抽選は当落が本文にしか無いので、確定・当落・応募の 3 つに分けて扱う。

## ③で発行元ごとに書くのは、②と違って発散しないため

②の判定は発行元を列挙できない（次に別の劇団から買えばまた漏れる）が、③は
**「この発行元のこの書式」と分かった後の処理**なので、本文の雛形に沿って書ける。
実測では確定 437 通のうち上位 10 発行元で大半を占める。**雛形の無い発行元は
汎用の規則で拾い、取れなかった件数を必ず表示する**（黙って落とさない）。

## 使い方

    python3 tools/tickets/extract_performances.py --run
    python3 tools/tickets/extract_performances.py --run --limit 30   # 試し
    python3 tools/tickets/extract_performances.py --reparse          # 規則だけ直して読み直す

出力は `data/tickets/performances.jsonl`（リポジトリには入れない）。

## 本文は保存しない（企画書 2 章・5 章）

**本文は抽出のその場でしか使わない。** 読んだら公演名・日付・劇場だけを取り出して捨て、
端末にファイルとしては残さない。**2026-08-27 まではメール ID ごとに `data/tickets/bodies/`
へ平文でキャッシュしており、これは「本文は保存しない」という企画書の約束と食い違って
いた**（[000007-taguri-security-review.md](../../docs/000007-taguri-security-review.md)）。
キャッシュを廃止し、`--reparse`（抽出規則を直したときの読み直し）も含めて**必要になる
たびに Gmail から読み直す**形にした。外部サイトのスクレイピングと違って自分の受信箱を
読むだけで他人のサーバに負荷をかけないため、390 通程度の読み直しでも遅くはならない。
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan_ticket_mail import Gmail, _decode, _domain  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data" / "tickets"
OUT = DATA / "performances.jsonl"

# ---- 進み具合を、呼んだ側へ渡す ---------------------------------------------
#
# 起案者の指示（2026-08-25）──「購入確認メールから取り込む、の際、経過がわかるような
# バーがほしい。進行状況を一目でわかるように」。
#
# **この処理は数分から数十分かかる**（初回は数千通を走査する）。端末から叩くときは
# `n/総数` を `\r` で書き換えれば済むが、**画面のボタンから呼ばれたときは受け取る側が
# 別のプロセスである** ── `\r` で上書きする形は 1 行にまとまらず、終わるまで何も
# 読めない。そこで**端末に居るかどうかで出し方を変える**：
#
# | 呼ばれ方 | 出し方 |
# |---|---|
# | 端末（`--run` を手で叩く） | これまでどおり同じ行を書き換える |
# | 画面のボタン（`serve.py`） | 1 行 1 件の JSON を流す。受け取る側が帯に変える |
#
# **段の数はここが持つ。** 画面の側に写すと、段を足したときに帯の目盛りだけが古くなる。
STEPS = 3
_TTY = sys.stdout.isatty()


def tick(step: int, name: str, n: int = 0, total: int = 0) -> None:
    """いまどの段の何通目かを 1 行で知らせる。

    **総数が分からない段（メールを探している間）は `total=0` で呼ぶ。**
    受け取る側はそれを「何割まで来たかはまだ言えない」として扱う ──
    伸びていない帯を出すより、分からないことが形に出るほうがよい。
    """
    if _TTY:
        if total:
            print(f"  {name} {n}/{total}", end="\r", flush=True)
        return
    print("@@TAGURI " + json.dumps(
        {"step": step, "steps": STEPS, "name": name, "n": n, "total": total},
        ensure_ascii=False), flush=True)


def tock(summary: str, titles: list | None = None) -> None:
    """**終わったときに画面へ出す 1 行と、今回入った公演の題名を、こちらから名乗る。**

    以前は呼んだ側が標準出力の最後の 1 行を拾っていたが、この処理の最後に出るのは
    「題名が取れなかった発行元」の集計表である ── **取り込みが終わった知らせとして
    「   12  eplus.jp」が出ていた。** 何通読んで何件入ったのかは、ここでしか分からない。

    **題名も一緒に渡す**（起案者の指示・2026-08-25 ──「押したら実際に今回取り込まれた
    公演タイトルを表示してほしい」）。件数だけでは、入ったのが自分の知っている公演か
    どうかが分からない ── **入ったことを確かめられるのは題名だけである。**
    """
    # **端末では、書き換えていた行を消してから出す。** `tick` が同じ行に
    # 「7/10」を書いているので、消さないと数字の尻尾が知らせの後ろに残る
    print(("\r" + " " * 60 + "\r\n") if _TTY else "", end="")
    print(summary, flush=True)
    for t in titles or []:
        print(f"   ・{t}", flush=True)
    if not _TTY:
        print("@@TAGURI " + json.dumps(
            {"summary": summary, "titles": list(titles or [])}, ensure_ascii=False),
            flush=True)


def new_titles(rows: list) -> list:
    """**今回はじめて入った公演の題名。**

    書き出しは毎回すべてを入れ替える形なので、「今回入った分」は**前の書き出しに
    無かったメール**（`uid`）から出すしかない。前の書き出しが無い（初回の）ときは
    全部が新しいが、**そのときに数百件を並べても読めない**ので、呼んだ側で切る。

    **受取・発券の通知と、演劇でないものは並べない。** 前者は公演名を含まず
    （引換票番号だけ）、後者は同じ受信箱に混ざる展覧会や配信である ──
    どちらも「観に行く公演が入りました」として出すものではない。
    **同じ題名は 1 つにまとめる**（同じ作品を別の日に 2 回買うことは実際にある）。
    """
    seen = set()
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                seen.add(json.loads(line).get("uid"))
    fresh = [r for r in rows
             if r.get("uid") not in seen and r.get("title")
             and not r.get("pickup") and is_theater(r["title"])]
    fresh.sort(key=lambda r: r.get("date") or r.get("mail_date") or "")
    out, done = [], set()
    for r in fresh:
        t = r["title"].strip()
        if t not in done:
            done.add(t)
            out.append(t)
    return out


# 購入が確定したことを表す件名（応募・受付だけのものは入れない）
CONFIRM = ["チケット購入確認", "購入完了", "ご購入完了", "入金確認", "決済完了",
           "決済の承認完了", "ご注文確認メール", "注文確認", "チケットお申し込みの確認",
           "申し込みの確認", "お申込完了", "予約完了", "ご予約内容", "ご購入ありがとう",
           "購入手続き完了",
           # 受取・発券の通知も網には入れる。購入の唯一の証拠である発行元があるため
           "店頭発券", "発券のお知らせ", "チケット受取", "受取完了", "引換票"]

# **受取・発券の通知は購入ではない。** 引換票番号しか書かれておらず公演名を含まない。
# 同じ公演の購入確認が別に届いているので、これを抽出の失敗として数えると
# 取得率が実際より悪く見える。**別の種類として数える。**
PICKUP = ["店頭発券", "発券のお知らせ", "チケット受取", "受取完了", "引換票"]


def is_pickup(subject: str) -> bool:
    return (any(k in subject for k in PICKUP)
            and not any(k in subject for k in
                        ["購入確認", "購入完了", "お申込完了", "予約完了", "注文確認"]))

# 観劇と無関係な発行元。**通販・旅行・金融は件名が同じ形をしているので必ず落とす**
NOISE = ("skymark.jp", "apa.co.jp", "kuronekoyamato.co.jp", "sharp.co.jp", "tsite.jp",
         "honto.jp", "rakuten.co.jp", "amazon.co.jp", "yodobashi.com", "airdo.co.jp",
         "bookoffonline.jp", "omni7.jp", "towerrecords.co.jp", "zaim.net", "jalan.net",
         "grailnet.jp", "eyecity.jp", "01epos.jp", "google.com", "gladd.jp",
         "johnnys-shop.jp", "animate.co.jp", "animate-onlineshop.jp", "toranoana.co.jp",
         "surugaya.jp", "suruga-ya.jp", "solaseedair.jp", "expy.jp", "nta.co.jp",
         "keisei.co.jp", "takarakuji-official.jp", "kawai-juku.ac.jp", "fujisan.co.jp",
         "print-gakufu.com", "enish-games.com", "minne.com", "cardservice.co.jp",
         "form-mailer.jp", "hmv.co.jp", "go.hmv.co.jp", "rurubu.travel")

DATE = r"(20\d\d)[/年](\d{1,2})[/月](\d{1,2})"
TIME = r"(\d{1,2})[:：時](\d{2})"

# 「上演日」を指す語と、指さない語。**予約日時・発売日・発券期限は上演日ではない。**
# この規則は [検証 014](../../docs/verification/014-matching-and-dates.md) で 99.2% が出た
# ものだが、**測定用の tools/review/measure_matching.py にしか入っていなかった。**
# 抽出側は「本文の最初の日付」を取っていたので、予約日時を上演日として書き出していた。
NEAR = ("開演", "開場", "公演日", "上演", "観劇日", "ご来場", "来場日")
AWAY = ("申込", "購入", "入金", "決済", "発売", "受付", "予約日", "注文", "支払",
        "期限", "締切", "引取", "引き取り", "発券", "引換", "配信")


def perf_date(t: str) -> str | None:
    """本文から上演日を選ぶ。決められなければ None を返す。

    **日付の直後 25 字に「開演」「開場」があれば、それで決める。** 周りに「支払」
    「受取」があっても関係ない ── 実データでは「2025/11/8(土) 18:30開場 19:00開演」の
    下に受取方法の案内が続いており、減点で打ち消すと本物の上演日を捨てる。
    """
    best = None
    for m in re.finditer(DATE, t):
        d = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        tail = t[m.end():m.end() + 25]
        around = t[max(0, m.start() - 60):m.end() + 60].replace("\n", " ")
        if any(k in tail for k in ("開演", "開場")):
            score = 10
        else:
            score = sum(2 for k in NEAR if k in around) - sum(3 for k in AWAY if k in around)
        if score > 0 and (best is None or score > best[0]):
            best = (score, d)
    return best[1] if best else None


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip(" 　:：")


def unwrap(s: str) -> str:
    """題名を囲む鉤括弧を外す。**全体が囲まれているときだけ外す。**

    以前は `strip("『』「」")` で両端の括弧を落としていた。**これが題名の閉じ括弧を
    消していた** ── 「【Premium限定】KERA CROSS『シャープさんフラットさん』」の
    先頭は 【 なので `『` は落ちず、末尾の `』` だけが落ちて
    「…フラットさん」になる。実データでは、括弧が閉じていない題名 24 件のうち
    **23 件がこれが原因**で、本文には閉じ括弧まで書かれていた。

    団体名や企画名を冠に持つ題名（「団体『演目』」）はこの形が普通なので、
    **囲みを外すのは題名そのものが囲まれている場合に限る。**
    """
    t = s.strip()
    again = True
    while again:
        again = False
        for a, b in (("『", "』"), ("「", "」")):
            if len(t) < 2 or not (t.startswith(a) and t.endswith(b)):
                continue
            # **先頭の括弧と末尾の括弧が対になっているかを深さで見る。** 件数で
            # 見ると「団体『演目』ほか『演目』」を外してしまい、深さを見ないと
            # 「『団体『演目』』」の外側 1 組を外せない
            depth, early = 0, False
            for i, ch in enumerate(t):
                depth += (ch == a) - (ch == b)
                if depth == 0 and i < len(t) - 1:
                    early = True
                    break
            if not early and depth == 0:
                t, again = t[1:-1].strip(), True
    return t


def p_pia(t: str) -> dict:
    """ぴあ系（劇場3 Web ボックスオフィスなど）。項目名が全角コロンで並ぶ。"""
    d = {}
    if m := re.search(r"公演名[:：](.+)", t):
        d["title"] = _clean(m.group(1))
    if m := re.search(r"公演日[:：]\s*" + DATE, t):
        d["date"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    if m := re.search(r"開演時刻[:：]\s*" + TIME, t):
        d["time"] = f"{int(m.group(1)):02d}:{m.group(2)}"
    if m := re.search(r"会場名[:：](.+)", t):
        d["venue"] = _clean(re.sub(r"\(.+?\)", "", m.group(1)))
    return d


def p_okepi(t: str) -> dict:
    """おけぴ。角括弧のラベル。"""
    d = {}
    if m := re.search(r"\[公演名\]\s*(.+)", t):
        d["title"] = unwrap(_clean(m.group(1)))
    if m := re.search(r"\[公演日時\]\s*" + DATE, t):
        d["date"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    if m := re.search(r"\[公演日時\].*?" + TIME, t):
        d["time"] = f"{int(m.group(1)):02d}:{m.group(2)}"
    if m := re.search(r"\[劇場\]\s*(.+)", t):
        d["venue"] = _clean(m.group(1))
    return d


def p_ltike(t: str) -> dict:
    """ローチケ。全角の■ラベルに全角スペースが挟まる。"""
    d = {}
    if m := re.search(r"■公演タイトル[　\s]*[:：](.+)", t):
        d["title"] = _clean(m.group(1))
    if m := re.search(r"■公演日[　\s]*[:：]\s*" + DATE, t):
        d["date"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    if m := re.search(r"(\d{1,2})[:：](\d{2})\s*開[　\s]*演", t):
        d["time"] = f"{int(m.group(1)):02d}:{m.group(2)}"
    if m := re.search(r"■会場名[　\s]*[:：](.+)", t):
        d["venue"] = _clean(m.group(1))
    return d


def p_toho(t: str) -> dict:
    """東宝ナビザーブ。■ラベルの**次の行**に値が来る。"""
    d = {}
    if m := re.search(r"■公演名\s*\n\s*(.+)", t):
        d["title"] = _clean(m.group(1))
    if m := re.search(r"■劇場\s*\n\s*(.+)", t):
        d["venue"] = _clean(m.group(1))
    if m := re.search(r"■公演日時\s*\n\s*" + DATE, t):
        d["date"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    if m := re.search(r"■公演日時[\s\S]{0,60}?(\d{1,2}):(\d{2})\s*開演", t):
        d["time"] = f"{int(m.group(1)):02d}:{m.group(2)}"
    return d


def p_fanclub(subject: str) -> dict:
    """ジャニーズ系・ファミリークラブ。**本文に公演日が無い**ので件名から題名だけ取る。

    「◯◯ 入金確認のご案内」のように、件名の末尾が定型句で題名が頭に来る。
    **公演日は取れないと記録する。** 取れないものを取れたことにしない。
    """
    s = re.sub(r"[【\[].{0,20}?[】\]]", "", subject)
    s = re.sub(r"(入金確認のご案内|申込完了のご案内|抽選結果のお知らせ|"
               r"当選のご案内|決済完了のお知らせ|お知らせ|ご案内)\s*$", "", s).strip()
    return {"title": unwrap(_clean(s)), "date_unknown": True}


# 汎用の規則が題名として拾ってしまう、題名でない語。**これは分類ではなく抽出の失敗**
NOT_A_TITLE = {"購入履歴", "引換票番号(13桁)", "払込・引換票番号（13桁）", "申込確認",
               "マイページ", "会員登録", "購入内容", "お申込内容", "ご購入内容", "予約履歴",
               "重要", "注意", "Myチケット", "マイチケット", "JTBトラベルメンバーID",
               "ＪＲ東海の指定席券売機", "MOALA Pocketアプリ", "LivePocket-Ticket-",
               "Famiパス", "佐賀新聞", "申込状況確認ページ", "チケットのご利用方法について",
               "決済完了の", "タイトル未定", "がぶ飲みワインと肉 ビストロ千住MEAT", "旧るるぶトラベル会員ID",
               "予約／購入履歴", "指定席券売機", "るるぶトラベル会員ID",
               "受取コード", "確認コード", "宿泊済"}

# 演劇でないもの。**この企画は演劇の推薦なので、対象外は取り込みの段階で落とす。**
# 判定を本人に投げない（調べれば分かる分類は機械の側でやる）。
NON_THEATER_WORDS = (
    "CONCERT", "コンサート", "LIVE TOUR", "ライブツアー", "ドキュメンタリー",
    "フェスティバル", "ドリームフェス", "Paradise", "パラダイス", "サマステ",
    "ミュージアム", "武道館", "ZEPP", "Zepp", "舞台挨拶", "上映", "試写",
    "with Friends", "とうちあわせ", "_meeting", "GREATEST SHOW-NEN",
    "IsLAND", "TrackONE", "CHANGE THE ERA", "Only 1, NOT No.1", "Only1 NOT No.1",
    "慣声の法則", "VVS", "Re:ERA", "ROCK'N'DOL", "I LOVE YoU",
)
# 語では切れない個別の非演劇。**純烈は歌謡グループで、ホール公演は歌謡ショーである**
NON_THEATER_TITLES = ("純烈", "２０ｔｈ Ｃｅｎｔｕｒｙ", "20th Century",
                      "しんじゅく酒井祭", "徹子の部屋",
                      "テレビ朝日ドリームフェスティバル")

# 上の語に当たるが**演劇である**もの。除外より先に見る。
# 純烈の座長公演（明治座・新歌舞伎座・御園座）は**第一部が芝居**の二部構成なので舞台にあたる。
THEATER_EXCEPTIONS = ("座長公演", "明治座", "新歌舞伎座", "御園座")


# **部分一致で落とす語。** NOT_A_TITLE は完全一致の一覧なので、案内文の中の鉤括弧
# （「マルチコピー機」「払込・引換票番号（13桁）」）には届かなかった。
NOT_A_TITLE_PARTS = ("マルチコピー機", "券売機", "専用機", "発券", "引換", "払込", "支払", "決済", "手数料",
                     "セブン", "ローソン", "ファミリーマート", "コンビニ", "会員登録",
                     "マイページ", "購入履歴", "予約／購入履歴", "ログイン", "手続き",
                     "お問合せ", "お問い合わせ", "利用規約")
# **「受取」は入れない。** 『受取人不明 ADDRESS UNKNOWN』が題名から消える


def is_theater(title: str) -> bool:
    if any(t in title for t in THEATER_EXCEPTIONS):
        return True
    if any(w in title for w in NON_THEATER_WORDS):
        return False
    if any(t in title for t in NON_THEATER_TITLES):
        return False
    return True


def p_gekidan(t: str) -> dict:
    """劇団のオンラインチケットサービス。劇団4・劇団7などが同じ雛形を使う。

    **発行元でなく本文の雛形で見分ける。** 同じ業者のシステムを複数の劇団が使うので、
    ドメインで分けると劇団の数だけ規則が要る。
    """
    d = {}
    # **番号の呼び名は劇団で違う。** 劇団4は「予約番号」、劇団6は「申込番号」で、
    # 雛形は同じ（番号の次の行が題名）。片方だけ見ていたので劇団6が generic に落ちていた。
    if m := re.search(r"(?:予約|申込)番号[:：]\s*\S+\s*\n+\s*(.+)", t):
        d["title"] = unwrap(_clean(m.group(1)).split("★")[0])
    head = max(t.find("予約番号"), t.find("申込番号"))
    if got := perf_date(t[head:] if head >= 0 else t):
        d["date"] = got
    elif m := re.search(DATE + r"\(.\)", t[head:] if head >= 0 else t):
        d["date"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        d["date_unsure"] = True
    if m := re.search(r"(\d{1,2}):(\d{2})\s*開演", t):
        d["time"] = f"{int(m.group(1)):02d}:{m.group(2)}"
    return d


def p_generic(t: str) -> dict:
    """雛形の分からない発行元。二重鉤括弧の題名と、最初の日付を拾う。"""
    d = {}
    for pat in (r"公演名[:：]?\s*(.+)", r"公演タイトル[:：]?\s*(.+)",
                r"『(.{2,60}?)』", r"「(.{2,60}?)」"):
        for m in re.finditer(pat, t):
            cand = unwrap(_clean(m.group(1)))
            if (cand and cand not in NOT_A_TITLE
                    and not any(w in cand for w in NOT_A_TITLE_PARTS)
                    and not re.fullmatch(r"[\d\-（）()桁 ]+", cand)):
                d["title"] = cand
                break
        if d.get("title"):
            break
    # **上演日を選ぶ規則を通す。** 決められないときだけ最初の日付に落とすが、
    # そのときは印を付ける ── 予約日時を上演日として黙って出さないためである。
    if got := perf_date(t):
        d["date"] = got
    elif m := re.search(DATE, t):
        d["date"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        d["date_unsure"] = True
    if m := re.search(r"(\d{1,2}):(\d{2})\s*開演", t):
        d["time"] = f"{int(m.group(1)):02d}:{m.group(2)}"
    return d


PARSERS = [("pia.co.jp", p_pia), ("okepi.jp", p_okepi),
           ("l-tike.com", p_ltike), ("toho-navi.com", p_toho)]
# 本文に公演日が無く、件名からしか題名が取れない発行元
SUBJECT_ONLY = ("johnnys-net.jp", "familyclub.jp", "j-island.net")


def parse(domain: str, text: str, subject: str) -> tuple[dict, str]:
    # **「オンライン」に限らない。** 劇団4の本文は「インターネット・チケットサービス」で、
    # 雛形は同じなのに generic に落ちて、案内文から題名を拾っていた（存在証明 → マルチコピー機）。
    if re.search(r"チケットサービス", text) and re.search(r"(予約|申込)番号", text):
        got = p_gekidan(text)
        if got.get("title"):
            return got, "劇団のチケットサービス"
    for key, fn in PARSERS:
        if domain.endswith(key):
            got = fn(text)
            if got.get("title"):
                return got, key
    if any(domain.endswith(k) for k in SUBJECT_ONLY):
        return p_fanclub(subject), "fanclub(件名のみ)"
    return p_generic(text), "generic"


def body_text(gm: Gmail, uid: str) -> str:
    """メール本文を取ってくる。**呼ぶたびに読みに行き、端末には残さない**（本文を
    保存しないという企画書の約束を守るため）。MIME を解いて本文を返す処理そのものは
    `Gmail.body_text`（`scan_ticket_mail.py`）に置き、判定は 1 か所に集める。"""
    return gm.body_text(uid)


def run(limit: int) -> None:
    # **探している間も知らせる。** 受信箱の走査は何通あるかが分かる前の待ち時間で、
    # ここが一番長いこともある（認証の待ちもここに入る）
    tick(1, "購入確認メールを探しています")
    gm = Gmail()
    q = "subject:(" + " OR ".join(f'"{k}"' for k in CONFIRM) + ") -in:chats -from:me"
    ids = gm.ids(q, cap=20000)
    print(f"確定を表す件名に一致: {len(ids)} 通。差出人を確認します…", flush=True)

    heads = {}
    for i in range(0, len(ids), 200):
        chunk = ids[i:i + 200]
        for uid, r in zip(chunk, gm.headers_many(chunk)):
            heads[uid] = r
        tick(2, "差出人を確かめています", min(i + 200, len(ids)), len(ids))
    target = [u for u in ids
              if not any(_domain(heads[u]["from"]).endswith(d) for d in NOISE)]
    print(f"観劇と無関係な発行元を除いて {len(target)} 通")
    if limit:
        target = target[-limit:]

    rows, by_parser, failed = [], collections.Counter(), []
    for n, uid in enumerate(target, 1):
        h = heads[uid]
        dom = _domain(h["from"])
        got, which = parse(dom, body_text(gm, uid), h["subject"])
        by_parser[which] += 1
        rec = {"uid": uid, "from": dom, "subject": h["subject"],
               "mail_date": h["date"][:31], **got}
        rows.append(rec)
        rec["pickup"] = is_pickup(h["subject"])
        # **知らせるのは `continue` より先。** 受取・発券の通知はここで飛ばすので、
        # 後ろに置くと**その通が続いた間だけ帯が止まって見える**（進んではいる）
        tick(3, "本文から公演を取り出しています", n, len(target))
        if rec["pickup"]:
            continue
        if not got.get("title") or (not got.get("date") and not got.get("date_unknown")):
            failed.append(rec)

    # **今回入った分を、書き出す前に数える。** 書き出しは毎回すべてを入れ替える形
    # なので、書いてしまうと「前からあった分」と区別が付かなくなる
    fresh = new_titles(rows)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    tock((f"新しく入った公演 {len(fresh)} 件" if fresh else "新しく入った公演はありません")
         + f"（{len(rows)} 通を読みました"
         + (f"／題名が取れなかったもの {len(failed)} 通" if failed else "") + "）",
         titles=fresh)
    print(f"\n{OUT} に書き出しました。")
    print("\n■ 使った規則")
    for k, n in by_parser.most_common():
        print(f"   {n:>4}  {k}")
    print(f"\n■ 受取・発券の通知（購入ではない）: {sum(1 for r in rows if r.get('pickup'))} 通")
    print(f"■ 公演名または日付が取れなかったもの: {len(failed)} 通 "
          f"（{len(failed) / max(len(rows), 1) * 100:.0f}%）")
    for r in collections.Counter(x["from"] for x in failed).most_common(12):
        print(f"   {r[1]:>4}  {r[0]}")


def norm_title(t: str) -> str:
    t = re.sub(r"[【〈\[].{0,24}?[】〉\]]", "", t)
    return re.sub(r"[『』「」\"'　 ・･\.\-−ー〜~！!？?]", "", t).lower()


def listing() -> None:
    """重複を潰して公演の一覧にする。

    **同じ公演について購入確認と発券通知の 2 通が届く**ことがあるため、
    日付と開演時刻が同じものは 1 公演にまとめ、情報の多い行を残す。
    同じ作品を別の日に複数回観るのは実際にあるので、題名では潰さない。
    """
    if not OUT.exists():
        raise SystemExit(f"{OUT} がありません。先に --run を実行してください。")
    rows = [json.loads(l) for l in OUT.read_text(encoding="utf-8").split("\n") if l.strip()]
    # 受取通知は「抽出の失敗」には数えないが、**公演の証拠としては使う。**
    # 発券通知しか残っていない公演があり、除くと 2024 年が 35 → 23 件に落ちた。
    dated = [r for r in rows if r.get("date") and r.get("title")]
    undated = [r for r in rows if r.get("date_unknown") and r.get("title")]
    lost = [r for r in rows if not r.get("title") and not r.get("pickup")]
    pickups = [r for r in rows if r.get("pickup")]

    best: dict = {}
    for r in dated:
        k = (r["date"], r.get("time", ""))
        score = len(r.get("title", "")) + (30 if r.get("venue") else 0)
        if k not in best or score > best[k][0]:
            best[k] = (score, r)
    uniq = sorted((v[1] for v in best.values()), key=lambda x: x["date"])

    plays = [r for r in uniq if is_theater(r["title"])]
    dropped = [r for r in uniq if not is_theater(r["title"])]
    u_plays = [r for r in undated if is_theater(r["title"])]

    print(f"確定購入 {len(rows)} 通 → 日付つき {len(dated)} 件 → 重複を潰して {len(uniq)} 公演")
    print(f"  うち演劇 {len(plays)} 公演 / 演劇でないもの {len(dropped)} 件を落とした")
    print(f"公演日が本文に無い（ファンクラブ経由） {len(undated)} 件 → うち演劇 {len(u_plays)} 件")
    print(f"受取・発券の通知 {len(pickups)} 件（購入ではないが公演の証拠には使う）")
    print(f"**題名が取れなかった {len(lost)} 件**（黙って落とさない）")
    print("\n■ 演劇でないとして落としたもの")
    for t, n in collections.Counter(r["title"][:40] for r in dropped).most_common():
        print(f"   {n:>2}  {t}")
    uniq = plays
    print("\n■ 年ごと（演劇のみ）")
    c = collections.Counter(r["date"][:4] for r in uniq)
    for y in sorted(c):
        print(f"   {y}  {c[y]:>3} 件  {'█' * c[y]}")
    print("\n■ 一覧")
    for r in uniq:
        print(f"  {r['date']}  {r.get('time', '--:--'):<6} "
              f"{r['title'][:46]:<48} {str(r.get('venue', ''))[:24]}")


def reparse() -> None:
    """受信箱の走査（件名の網 → 発行元の確認）は省き、**確定済みの通だけ本文を
    読み直して規則をかけ直す。**

    ## なぜ受信箱の走査と分けるのか

    抽出の規則を直したときに要るのは、**新しいメールではなく、新しい読み方**である。
    `--run` は件名の網から発行元の確認までを毎回やり直すので遅い。**どの通が対象かは
    前回の `performances.jsonl` に残っている**ので、ここでは対象を選び直さず、
    その通ぶんだけ本文を Gmail から読み直す。**本文は保存しない**（企画書 2 章）ので
    キャッシュは無い ── 自分の受信箱を読むだけで他人のサーバに負荷をかけないため、
    390 通程度の読み直しでも遅くはならない（詳しくはモジュールの docstring）。

    ## 公演ページとの結び付きを同じ 1 回で直す

    `data/credits/credits.jsonl` は `(date, mail_title)` を鍵に公演ページと結び付いて
    いて、この鍵は**抽出した題名**でできている。題名の読み方を直すと鍵が合わなくなり、
    **クレジットが引けなくなる**（実データでは 34 通の題名が変わり、そのうち 14 通は
    公演ページに結び付いていた）。**取り直しと、使える形にすることを別の実行に分けると、
    片方だけ進んだ状態が出力に出る**ので、鍵の付け替えをここで一緒に行う。

    公演ページそのものを取り直す必要はない（`stage_id` と中身は変わらない）。
    """
    if not OUT.exists():
        raise SystemExit(f"{OUT} がありません。先に --run を実行してください。")
    rows = [json.loads(l) for l in OUT.read_text(encoding="utf-8").split("\n") if l.strip()]
    gm = Gmail()
    out, changed, no_body = [], [], 0
    by_parser: collections.Counter = collections.Counter()
    for r in rows:
        try:
            text = body_text(gm, r["uid"])
        except Exception:
            # **読めなかった 1 通のために全体を止めない。** 削除・移動されたメールも
            # ありうる ── 前回の抽出結果をそのまま残す
            out.append(r)
            no_body += 1
            continue
        if not text:
            out.append(r)
            no_body += 1
            continue
        got, which = parse(r["from"], text, r["subject"])
        by_parser[which] += 1
        rec = {"uid": r["uid"], "from": r["from"], "subject": r["subject"],
               "mail_date": r["mail_date"], **got, "pickup": is_pickup(r["subject"])}
        if rec.get("title") != r.get("title") and not rec["pickup"]:
            changed.append((r.get("date") or "", r.get("title") or "", rec.get("title") or ""))
        out.append(rec)

    with OUT.open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(out)} 通を読み直しました"
          + (f"（本文が読めず前回のまま残したもの {no_body} 通）" if no_body else ""))
    print("\n■ 使った規則")
    for k, n in by_parser.most_common():
        print(f"   {n:>4}  {k}")
    print(f"\n■ 題名が変わった: {len(changed)} 通")
    for d, a, b in changed[:40]:
        print(f"   {d}  「{a}」\n            → 「{b}」")
    print(_relink([(d, a, b) for d, a, b in changed]))


def _relink(changed: list[tuple[str, str, str]]) -> str:
    """公演ページとの結び付き（`credits.jsonl` の `mail_title`）を新しい題名に付け替える。

    **公演ページを取り直さない。** 変わったのは題名の読み方だけで、結び付いた先の
    公演（`stage_id`）と中身は同じものである。取り直すと CoRich へ 130 件の要求を
    出すことになる。
    """
    cred = ROOT / "data" / "credits" / "credits.jsonl"
    if not cred.exists() or not changed:
        return ""
    rows = [json.loads(l) for l in cred.read_text(encoding="utf-8").split("\n") if l.strip()]
    fix = {(d, a): b for d, a, b in changed}
    n = 0
    for r in rows:
        b = fix.get((r.get("date") or "", r.get("mail_title") or ""))
        if b:
            r["mail_title"] = b
            n += 1
    if n:
        with cred.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return (f"\n■ 公演ページとの結び付きを {n} 件付け替えました"
            f"（credits.jsonl の mail_title。公演ページは取り直していません）")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--reparse", action="store_true",
                    help="メールを取り直さず、保存済みの本文に規則をかけ直す")
    ap.add_argument("--list", action="store_true", help="重複を潰して一覧にする")
    ap.add_argument("--limit", type=int, default=0, help="末尾 N 通だけ処理する（試し）")
    a = ap.parse_args()
    if a.run:
        run(a.limit)
    elif a.reparse:
        reparse()
    elif a.list:
        listing()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
