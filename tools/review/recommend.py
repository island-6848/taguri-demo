#!/usr/bin/env python3
"""いま観られる公演から、お気に入りの新着と推薦 15 件を出す。

## 何をしているか

    ① 候補     ステイジーズカレンダーの「まだ観られる公演」
    ② 網 A     申告した名前（[検証 003](../../docs/verification/003-declared-preferences.md)）と照合 → **お気に入り**
    ③ 会場      履歴の会場ごとの当たり率（評価から作る）
    ④ 網 B     名簿（履歴のクレジット × 評価）と候補のクレジットを照合
    ⑤ 提示      理由と出典を付けて 15 件

**③まではカレンダーの表だけで計算できる。④は候補のクレジットを取りに行く必要があるので、
③までで上位に来たものに限って取得する**（全 800 件に取りに行くのは費用が見合わない）。

**申告した名前（網 A）は推薦と混ぜない。** 推定の的中率が水増しされるため
（企画書 2 章）、「お気に入りの新着」として別に出す。

    python3 tools/review/recommend.py --today 2026-08-20
"""

from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "tools" / "credits"))
import measure_nets as M                                    # noqa: E402
from fetch_credits import search, credits_of, clean_title   # noqa: E402
import fetch_official_credits as OF                         # noqa: E402

SHEET = "1OtXzChuCUfy2AnyuRW5ZgnMbsKHUwlCEF9keTA0Gb8c"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET}/export?format=csv&gid=0"

# 検証 003 で凍結した、**起案者本人の**申告（本人の言葉のまま）。
# **申告した名前は、コードではなくファイルに置く。**
#
# もとはこの辞書がそのまま登録の実体だったが、**画面から登録・解除できるようにした**
# （企画書 1 章「お気に入りの登録と解除は、画面 ① の中で行う」）。コードに書いてあると、
# 利用者は名前を 1 つ足すのにソースを編集することになり、**機能として存在しないのと同じである。**
#
# **この辞書を初期値として自動で書き出してはいけない**（2026-08-24 の指示で撤回した）。
# 以前は「ファイルが無い環境で空から始めると実測が再現できない」という理由で、
# `declared.json` が無いときにこれを書き出していた。**これは検証の都合であって、
# 使う人の都合ではない。** 起案者以外が使い始めると、身に覚えの無い 36 の名前が
# 「自分が登録したもの」として並び、初日からお気に入りの新着が 28 件出る
# （実測 2026-08-24）。**本人の好みに合わせる道具なのだから、初期状態は空である。**
# 起案者が自分の端末で戻すときは `--restore-declared` を明示的に実行する。
DECLARED_SEED = {
    "団体": ["劇団1", "劇団2", "劇団6", "劇団7", "劇団4", "劇団3"],
    # **作り手15を足した。** 企画書 4 枚目の登録例には載っていたのに実装に無く、
    # 「まだ言葉になっていない作り手」の側に出ていた（11 本・評価済み 9 本のうち ◎ 6 本）。
    # 起案者の確認 ──「「作り手15」は「見逃したくないもの」です。企画書の内容があっています」
    "人": ["作り手24", "作り手9", "作り手17", "作り手11", "作り手31", "作り手12",
           "作り手25", "作り手1", "作り手22", "作り手15",
           # **ここから下は「決め手」で名指しされた分**（起案者の判断でまとめて昇格させた）。
           # 出どころは reaction.decider='person' の 9 行と、decider='group' の 1 行
           # （「阿佐ヶ谷スパイダース／作り手28（演出）」）である。**推定が出した名前を
           # 申告に上げる経路そのもの**で、企画書 8 枚目「理由の欄が登録の入口になる」に当たる。
           "作り手23", "作り手32", "作り手30", "作り手27", "作り手13",
           "作り手10", "作り手14", "作り手6", "作り手5", "作り手28",
           # **表記の揺れは両方並べる**（ヴ／ブ。「劇団1／劇団2」と同じ扱い）
           "作り手3", "作り手2"],
    "主催": ["劇場3", "劇場2"],
    "作品": ["作品1", "エンドレスショック"],
    "原作者": ["作品3"],
    # **「題材2」と「題材1」は同義として扱う**（起案者の確認）。企画書 4 枚目の例は
    # 「題材1」、下書きの申告表は「題材2」で、どちらも同じ登録を指していた。
    # **表記の揺れは両方並べる**（「劇団1／劇団2」と同じ扱い）。
    "題材": ["題材3", "題材2", "題材1"],
}
DECLARED_FILE = ROOT / "data" / "review" / "declared.json"
KINDS = ("団体", "人", "主催", "作品", "原作者", "題材")

# **お気に入りの裏返し ── 出さないと決めた語。**
#
# 起案者の指摘（2026-08-24）──「今なぜ興味ないのかで入力した理由は今後の推薦には
# 反映されていますか」。**反映していなかった。** 見送った理由は畳んだ束に出すだけで、
# 推薦の計算には 1 文字も使っていなかった。
#
# **反映しない前提が、実データで崩れていた。** 理由を書かない設計にした根拠は
# 「『興味なし』の多くは日程・場所・予算の都合だから、好みとして学ぶと歪む」だったが、
# 実際に書かれた 5 件は**すべて好みの話**で、都合の話は 1 件も無かった。しかも
# **5 件のうち 3 件が同じこと（バレエ・オペラ）を言っていた** ── 同じ理由を 3 回
# 書かせているのは、書いたことが効いていない証拠である。
#
# **申告（お気に入り）が勝つ。** 登録した名前は「内容を問わず知りたい」と本人が言って
# いるものなので、除外の語に当たっても新着からは外さない。
DECLINED_FILE = ROOT / "data" / "review" / "declined.json"


def load_declared() -> dict[str, list[str]]:
    """申告した名前を読む。**無ければ空である**（種から作らない）。

    **初めて使う人の登録は 0 件から始まる。** ファイルが無いことは「まだ何も登録して
    いない」という意味であって、誰かの登録を引き継ぐ理由にはならない
    （`DECLARED_SEED` の注記を参照）。
    """
    if DECLARED_FILE.exists():
        d = json.loads(DECLARED_FILE.read_text(encoding="utf-8"))
        return {k: list(d.get(k) or []) for k in KINDS}
    return {k: [] for k in KINDS}


def load_declined() -> list[str]:
    """出さないと決めた語。**無ければ空**（初めから何かを外している状態にはしない）。"""
    if not DECLINED_FILE.exists():
        return []
    try:
        d = json.loads(DECLINED_FILE.read_text(encoding="utf-8"))
    except ValueError:
        return []
    return [w for w in (d.get("words") or []) if isinstance(w, str) and w.strip()]


def save_declined(words) -> None:
    """**種類で分けない。** 照合は題名・団体・劇場・出演・題材の文字に対して行うので、
    その語が「人」なのか「題材」なのかを決める必要が無い ── **決められないものを
    決めた形で保存しない。**"""
    DECLINED_FILE.parent.mkdir(parents=True, exist_ok=True)
    seen, out = set(), []
    for w in words:
        w = (w or "").strip()[:40]
        if w and w not in seen:
            seen.add(w)
            out.append(w)
    DECLINED_FILE.write_text(json.dumps({"words": out}, ensure_ascii=False, indent=1),
                             encoding="utf-8")


def restore_declared_seed() -> dict[str, list[str]]:
    """**起案者が自分の端末で、検証 003 の申告を書き戻す。**

    実測（検証 003 以降）を再現するには申告が要るが、**それは検証をする人が明示的に
    行うことである。** 画面を開いただけで起きてはいけない。
    """
    DECLARED_FILE.parent.mkdir(parents=True, exist_ok=True)
    save_declared(DECLARED_SEED)
    return load_declared()


def save_declared(d: dict) -> None:
    """**種類ごとに重複を潰して書く。** 同じ名前が 2 行あると理由文が 2 回出る。"""
    out = {k: sorted(dict.fromkeys(x for x in (d.get(k) or []) if x.strip())) for k in KINDS}
    DECLARED_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


DECLARED = load_declared()
GRADE_W = {"◎": 1.0, "○": 0.7, "△": 0.3, "×": 0.0}

# **団体の当たり率から除く「既に説明できる」作品。** 申告した人・作品と、その系列。
# ここを除かずに数えると、団体が原因であるかのように見える（下記 troupe の注記）。
EXPLAINED_BY = (DECLARED["人"] + DECLARED["作品"] + DECLARED["団体"]
                + ["DREAM BOYS", "ABC座", "JOHNNYS", "SHOW BOY", "少年たち", "ジャニーズ"])


def nz(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "")).replace(" ", "").lower()


def parse_date(s: str):
    for f in ("%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.datetime.strptime(s.strip(), f).date()
        except ValueError:
            pass
    return None


def load_candidates(today: datetime.date) -> list[dict]:
    with urllib.request.urlopen(CSV_URL, timeout=60) as r:
        rows = list(csv.reader(io.StringIO(r.read().decode("utf-8"))))
    hdr = rows[1]
    col = {n: hdr.index(n) for n in ("都道府県", "劇場名", "公演団体名", "初日", "楽日", "リンク")}
    out = []
    for r in rows[2:]:
        if not r or not r[0].strip().isdigit():
            continue
        end, start = parse_date(r[col["楽日"]]), parse_date(r[col["初日"]])
        if not end or end < today:
            continue
        out.append({"pref": r[col["都道府県"]].strip(), "venue": r[col["劇場名"]].strip(),
                    "troupe": r[col["公演団体名"]].strip(), "start": start, "end": end,
                    "url": r[col["リンク"]].strip()})
    return out


# 申告は「劇場3**主催の演劇**」なので、オペラ・バレエ・ダンスは対象外。
# 会場名だけでは足りない ── ロームシアター京都のオペラ、福岡市民ホールのバレエが混ざった。
NOT_PLAY_VENUE = ("オペラパレス",)
NOT_PLAY_URL = ("/ballet/", "/dance/", "/opera/", "/kabuki/", "/bunraku/")
# 演劇でない上演。**「能」「狂言」のような 1〜2 字の語は「可能」「芸能」に当たる**ので、
# 誤って落とさない長さの語だけを置く
NOT_PLAY_TITLE = ("バレエ", "オペラ", "ダンス", "DANCE", "Ballet", "Opera", "文楽", "歌舞伎",
                  "落語", "独演会", "寄席", "講談", "浪曲", "漫才", "能楽", "狂言",
                  "コンサート", "歌謡ショー", "音楽祭", "リサイタル")

# リンク先が公演の個別ページでないことを示す語（検証 002 で既知の問題）
INDEX_PAGE = ("上演作品", "公演情報", "ラインアップ", "ラインナップ", "年度", "一覧")


def is_play(c: dict) -> bool:
    if any(v in c["venue"] for v in NOT_PLAY_VENUE):
        return False
    if any(k in (c.get("url") or "") for k in NOT_PLAY_URL):
        return False
    # **題名だけでは足りない。** 「お気に入り65」には「オペラ」の語が無く、
    # ジャンルが分かるのは概要（「オペラ鑑賞教室」）のほうだった。
    t = (c.get("show_title") or "") + " " + (c.get("summary") or "")
    return not any(k in t for k in NOT_PLAY_TITLE)


def net_a(c: dict) -> list[str]:
    """申告した名前と照合する。

    **主催・団体は「公演団体名」だけで照合し、劇場名では照合しない。**
    劇場名を混ぜると貸館公演を誤って拾う ── 実際、最初の実装で
    劇場3を会場とする日本テレビ・朝日新聞社・NHK エンタープライズの
    公演が「劇場3主催」として 15 件出てしまった。
    [検証 003](../../docs/verification/003-declared-preferences.md) で
    「主催は会場でも団体でもない」と書いた当の誤りである。
    """
    if any(v in c["venue"] for v in NOT_PLAY_VENUE):
        return []
    hits = []
    troupe = nz(c["troupe"])
    for kind in ("団体", "主催"):
        for w in DECLARED[kind]:
            if nz(w) and nz(w) in troupe:
                hits.append(f"{kind}「{w}」")
    return sorted(set(hits))


def troupe_of(stage_id: str) -> str:
    """CoRich の公演ページから団体名を取る（キャッシュ済みの HTML から読むだけ）。

    **カレンダーで全候補に付いている軸は「公演団体名」しかない**（公演名の列が無い）。
    履歴側にも団体名を持たせないと、候補と突き合わせる軸が会場しか残らず、
    会場の一致は候補の 8% しかない。
    """
    f = ROOT / "data" / "credits" / "pages" / (
        re.sub(r"[^A-Za-z0-9]", "_", f"https://stage.corich.jp/stage/{stage_id}")[-120:] + ".html")
    if not f.exists():
        return ""
    m = re.search(r'href="/troupe/\d+"[^>]*>\s*([^<]{2,40}?)\s*<', f.read_text(encoding="utf-8"))
    return m.group(1).strip() if m else ""


def summary_of(url: str) -> str:
    """候補のリンク先から概要を取る（meta description / og:description）。

    **一覧は読み手が「何のことか」分かる形でなければ意味がない。**
    企画書 2 章の「1 件に表示するもの」は識別（題名・団体・劇場・期間）を必須にしている。
    """
    html, err = OF.get(url)
    if err or not html:
        return ""
    for pat in (r'<meta[^>]+property="og:description"[^>]+content="([^"]{10,300})"',
                r'<meta[^>]+name="description"[^>]+content="([^"]{10,300})"',
                r'<meta[^>]+content="([^"]{10,300})"[^>]+name="description"'):
        m = re.search(pat, html, re.I)
        if m:
            t = unicodedata.normalize("NFKC", re.sub(r"\s+", " ", m.group(1))).strip()
            if len(t) >= 10:
                return t
    return ""


def title_of(url: str) -> str:
    """候補のリンク先から公演名を取る。**カレンダーに公演名の列が無いため。**"""
    html, err = OF.get(url)
    if err or not html:
        return ""
    m = re.search(r"<title[^>]*>(.{2,120}?)</title>", html, re.S)
    if not m:
        return ""
    t = unicodedata.normalize("NFKC", re.sub(r"\s+", " ", m.group(1))).strip()
    return re.split(r"[|｜\-–—]", t)[0].strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--today", default="2026-08-20")
    ap.add_argument("--fetch", type=int, default=40, help="クレジットを取りに行く上位件数")
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today)

    rated = M.load_rated()
    base = sum(GRADE_W.get(r["verdict"], 0) for r in rated) / max(len(rated), 1)
    roster = M.build_roster(rated, lambda v: GRADE_W.get(v, 0.0))

    # 履歴の作品に団体名を付ける
    creds = {(c.get("date"), c.get("mail_title")): c
             for c in (json.loads(l) for l in
                       (ROOT / "data/credits/credits.jsonl").read_text(encoding="utf-8").split("\n") if l.strip())}
    tt: dict = {}
    vt: dict = {}
    for r in rated:
        w = GRADE_W.get(r["verdict"], 0.0)
        for v in r["venues"]:
            e = vt.setdefault(nz(v), [0, 0.0, v]); e[0] += 1; e[1] += w
        # **団体は交絡しやすい。** 既に説明できる作品を除いた「残差」だけで数える。
        #
        # 実測: 団体「東宝」は 11 作品・当たり率 0.89 で最上位に来ていたが、
        # 中身は 作品1 4 本ほかジャニーズ系の舞台が 9 本で、
        # **「東宝が好き」ではなく「好きな出演者の公演がたまたま東宝製作に集中していた」**
        # だけだった。残差で数えると n=11 → n=2 になり、信頼度が 0.73 → 0.40 に落ちる。
        # 対して劇場3は n=8 がそのまま残る（本当に団体で観ている）。
        explained = any(k and nz(k) in nz(r["title"]) for k in EXPLAINED_BY)
        for (d, mt), c in creds.items():
            if d == r["date"] and c.get("stage_id"):
                g = troupe_of(c["stage_id"])
                if g and not explained:
                    e = tt.setdefault(nz(g), [0, 0.0, g]); e[0] += 1; e[1] += w
                break

    def rate(tbl):
        return {k: ((((o + 1) / (n + 2)) - base) * (n / (n + 3)), n, o, disp)
                for k, (n, o, disp) in tbl.items()}
    troupe_rate, venue_rate = rate(tt), rate(vt)
    print(f"評価済み {len(rated)} 作品／名簿 {len(roster)} 件／団体 {len(troupe_rate)} 件"
          f"／会場 {len(venue_rate)} 件／全体の当たり率 {base:.2f}")

    cands = load_candidates(today)
    print(f"まだ観られる公演 {len(cands)} 件")

    fav, rest = [], []
    for c in cands:
        if any(v in c["venue"] for v in NOT_PLAY_VENUE) or any(k in c["url"] for k in NOT_PLAY_URL):
            continue          # 申告は「演劇」。オペラ・バレエ・ダンスは対象外
        c["a"] = net_a(c)
        c["tr"] = c["vr"] = 0.0
        c["why_pre"] = []
        for k, (sc, n, o, disp) in troupe_rate.items():
            ct = nz(c["troupe"])
            # **包含は一方向だけ見る ── 履歴の団体名が候補の団体名に含まれる場合のみ。**
            # 双方向にすると「国立劇場」が履歴の「劇場3」に一致して、
            # 文楽鑑賞教室が上位に来た。空文字も全一致するので弾く。
            if not k or not ct or len(k) < 2:
                continue
            if k in ct and sc > c["tr"]:
                c["tr"] = sc; c["why_pre"] = [f"団体「{disp}」（観た {n} 本・当たり率 {(o+1)/(n+2):.2f}）"]
        v = venue_rate.get(nz(c["venue"]))
        if v and v[0] > 0:
            c["vr"] = v[0]
            c["why_pre"].append(f"会場「{v[3]}」（観た {v[1]} 本・当たり率 {(v[2]+1)/(v[1]+2):.2f}）")
        c["pre"] = c["tr"] + c["vr"]
        (fav if c["a"] else rest).append(c)

    # **お気に入りにも題名と概要を付ける。** 団体名と会場だけでは何の公演か分からない
    print(f"お気に入り {len(fav)} 件の題名と概要を取得します…", flush=True)
    for n, c in enumerate(fav, 1):
        c["show_title"] = title_of(c["url"]) if c["url"].startswith("http") else ""
        c["summary"] = summary_of(c["url"]) if c["url"].startswith("http") else ""
        # 題名が団体名そのものなら、リンク先は団体のトップページで公演の個別ページではない
        c["index_page"] = (any(k in (c["show_title"] or "") for k in INDEX_PAGE)
                           or (c["show_title"] and nz(c["show_title"]) in nz(c["troupe"]))
                           or not c["show_title"])
        print(f"  {n}/{len(fav)}", end="\r", flush=True)
    fav = [c for c in fav if is_play(c)]
    print(f"\n  演劇でないもの（バレエ・オペラ・ダンス）を除いて {len(fav)} 件")

    rest.sort(key=lambda x: (-x["pre"], x["end"]))
    short = [c for c in rest if c["pre"] > 0][:a.fetch]
    print(f"お気に入り {len(fav)} 件／団体か会場で当たりのある候補 "
          f"{sum(1 for c in rest if c['pre'] > 0)} 件／上位 {len(short)} 件のクレジットを取る…", flush=True)

    for n, c in enumerate(short, 1):
        c["people"] = []
        c["show_title"] = title_of(c["url"]) if c["url"].startswith("http") else ""
        c["summary"] = summary_of(c["url"]) if c["url"].startswith("http") else ""
        if c["show_title"]:
            for w in clean_title(c["show_title"]):
                found = False
                for sid in search(w)[:4]:
                    try:
                        cr = credits_of(sid)
                    except Exception:
                        continue
                    if str(c["start"].year) in cr["period"] or str(c["end"].year) in cr["period"]:
                        c["people"] = M.parse_credits(cr["fields"]); found = True; break
                if found:
                    break
        print(f"  {n}/{len(short)}  クレジット取得 "
              f"{sum(1 for x in short[:n] if x['people'])}", end="\r", flush=True)

    for c in short:
        parts = []
        for role, person in c["people"]:
            nn, oo = roster.get((role, person), (0, 0))
            if nn == 0:
                continue
            rr = (oo + M.SMOOTH_A) / (nn + M.SMOOTH_B)
            contrib = (rr - base) * (nn / (nn + M.CONF_K)) * M.ROLE_WEIGHT.get(role, M.DEFAULT_ROLE_WEIGHT)
            if contrib > 0:
                parts.append((contrib, role, person, nn, oo))
        parts.sort(reverse=True)
        c["b"] = sum(p[0] for p in parts[:M.TOP_N])
        c["why"] = parts[:3]
        c["total"] = c["b"] + c["pre"]

    short.sort(key=lambda x: -x["total"])
    out = {"favourites": fav, "recommend": short[:15], "base": base,
           "n_cand": len(cands), "n_rated": len(rated),
           "n_scored": sum(1 for c in rest if c["pre"] > 0)}
    (ROOT / "data" / "review" / "recommend.json").write_text(
        json.dumps(out, ensure_ascii=False, default=str, indent=1), encoding="utf-8")
    print("\n書き出し: data/review/recommend.json")
    return 0


if __name__ == "__main__":
    # **申告の書き戻しは、明示的に頼まれたときだけ行う。**（`restore_declared_seed`）
    if "--restore-declared" in sys.argv:
        d = restore_declared_seed()
        print(f"検証 003 の申告を {DECLARED_FILE} に書き戻した"
              f"（{sum(len(v) for v in d.values())} 件）")
        raise SystemExit(0)
    raise SystemExit(main())
