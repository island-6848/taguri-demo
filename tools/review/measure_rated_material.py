#!/usr/bin/env python3
"""網 C の材料が学習側（評価済みの作品）で薄い理由を、段ごとに数える。

## なぜ測るか

検証 034 は「学習側であらすじが実在したのは 31 作品」と件数だけを書いており、
**どの段で落ちているかを分けていない。** 検証 022 は候補側で「落ちる主因はあらすじが
無いことではなく、あらすじがあるページに辿り着いていないこと（公演固有でない URL が 47%）」
と測ったが、**学習側で URL の種別を数えた記録が無い。**

**辿り直し（企画書 5 章）でどこまで回収できるかは、落ちている段が分からないと言えない。**
そこで学習側を 3 段に分けて数える。

  段 1 ── 突き合わせ。CoRich の行を (観劇日, メールの件名) で引く。**引けなければ材料が無い。**
  段 2 ── 突き合わせの正否。**引けた行が別公演なら、別公演の要素が網 C の学習に入る**
           （検証 023 で規則ベースの抽出について測った誤りと同じ質で、段が違う）。
  段 3 ── ページの質。CoRich の公演ページと公式サイトの本文に、その公演の物語があるか。

**新しい取得は 1 回も発生しない**（`fetch=False`）。キャッシュにあるページだけで数える。

## 判定が目視である箇所

**段 2 の正否と、公式 URL の種別は目視で決めた**（検証 022 と同じ方式）。
機械の照合（CoRich ページの題名と作品名の一致率）で 14 件が引っかかり、
そのうち 9 件が別公演、5 件は表記の違い（日程変更の注記・全角半角）だった。
**判定は下の表に 1 件ずつ残してあるので、読み直して覆せる。**

    python3 tools/review/measure_rated_material.py
"""
from __future__ import annotations

import collections
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "credits"))
sys.path.insert(0, str(ROOT / "tools" / "review"))
import extract_theme_llm as E                                 # noqa: E402
import measure_nets as M                                      # noqa: E402
import rate_performances as R                                 # noqa: E402

CREDITS = ROOT / "data" / "credits" / "credits.jsonl"
THEMES = ROOT / "data" / "credits" / "themes.jsonl"
OUT = ROOT / "docs" / "verification" / "data-038-rated-material.json"

# **段 2 ── 目視で「別公演を指している」と判定した突き合わせ。**
# 機械の照合に引っかかった 14 件を 1 件ずつ読み、別公演だったものだけを残した。
#
# **2026-08-28 訂正（検証 050 追記 1）── 8 件を外した。** 題名を渡す抽出（c3 以降）が
# 導入された後、本文を読み直すと以下は「別公演を指している」のではなく、**その公演自身の
# 正しいあらすじが本文に載っていた**（`targets()` が引く URL がその後の修正で本来の
# 個別ページに直っていたため。デカローグ 1・3・4・5・6 は当時「デカローグ5・6（プログラムC）」
# のページを引いていたが、いまは各話ごとに正しい「デカローグ1〜4（プログラムA・B）」
# 「デカローグ5・6（プログラムC）」に分かれて引ける）。
# 「劇壇ガルバ」「ゴツプロ『流浪樹」「CAMPだGO」「デカローグ1〜6（1・3・4・5・6）」を外し、
# 判定は `FAIL_CAUSE` の「取りこぼし」（本文に物語があるのに抽出が見送っていた）に差し替えた。
# **残した「俺たちのBANG」は今回も本文を読み直して確認済み** ── ページは劇場窓口の案内
# だけで、物語はどこにも無い。別公演を指している判定のままでよい。
WRONG_JOIN = {
    "俺たちのBANG": "1993-The Bang Bang Club-（件名の部分一致による誤り）",
}

# **段 3 ── 公式 URL の種別。** 46 本の URL を目視で分類した。
# 「公演固有」はその公演だけのページ（公演専用ドメインを含む）、
# 「一覧」は劇団・劇場のトップまたは公演一覧、「複数公演」は 1 ページに複数の公演を並べたもの、
# 「別公演」は当該公演でないページ（ドメイン失効・現行公演への差し替えを含む）、
# 「プレイガイド」はチケット販売ページ、「SNS」は X の投稿。
URL_TYPE = {
    "austramacondo.com": "公演固有",
    "chekhov2026.jp": "公演固有",
    "haiyuza.net": "公演固有",
    "shika564.com": "公演固有",
    "stage.parco.jp": "公演固有",
    "subaruhall.org": "公演固有",
    "tspnet.co.jp": "公演固有",
    "www.rkx-i.jp": "公演固有",
    "www.sankeihallbreeze.com": "公演固有",
    "www.seinenza.com": "公演固有",
    "www.shinkabukiza.co.jp": "公演固有",
    "www.shochiku.co.jp": "公演固有",
    "www.thirdstage.com": "公演固有",
    "www.umegei.com": "公演固有",
    "www.vi-shinkansen.co.jp": "公演固有",
    "musical-smoke.com": "公演固有",
    "www.musical-wtrouble.jp": "公演固有",
    "anumber2022.srptokyo.com": "公演固有",
    "www.hakataza.co.jp": "公演固有",
    "www.ktv.jp": "公演固有",
    "yomi-h.jp": "公演固有",
    "www.tohostage.com": "公演固有",
    "www.nntt.jac.go.jp": "公演固有",
    "52pro.info": "一覧",
    "bloch-web.net": "一覧",
    "www.komatsuza.co.jp": "一覧",
    "www.haiyuzagekijou.co.jp": "一覧",
    "doshin-playguide.jp": "プレイガイド",
    "kyodo-osaka.co.jp": "プレイガイド",
    "live.yoshimoto.co.jp": "プレイガイド",
    "x.com": "SNS",
    "pando.life": "別公演",
    "autumnmeteorite.jp": "別公演",
    "www.vincent-in-brixton.jp": "別公演",
}
# **1 本の URL でも、指している先が公演固有か複数公演かは公演によって変わる。**
# 劇場3のデカローグは 1 ページに 4 演目を並べており、tohostage の一部は現行公演に
# 差し替わっている。**URL 単位ではなく作品単位で上書きする。**
TYPE_OVERRIDE = {
    "dekalog-de": "複数公演",
    "abc-z": "別公演",       # 作品は ABC 座 2022、ページは ABC 座 2024
}

# **段 3 の失敗の内訳 ── 材料が無いのか、抽出が取りこぼしたのかを目視で分けた。**
# あらすじが取れなかった 25 件について、CoRich の公演ページに渡した本文を 1 件ずつ読んだ。
#   「取りこぼし」 ── その公演の物語が本文にあるのに、抽出が空を返した（再現率の不足）
#   「誤マッチ」   ── 別公演の物語が本文にある。**空を返したのは正しい挙動である**
#   「材料なし」   ── 本文が出演者・日程・注意書き・クチコミだけで、物語がどこにも無い
#
# **2026-08-28 訂正 1（検証 042）── 石川啄木を「取りこぼし」から「材料なし」に直した。**
# 本文を読み直すと啄木の物語は無く、あるのは題名の行と 2 行のキャッチコピーだけ。
# 公式サイト（こまつ座のトップページ）に載っているのは『組曲虐殺』など別公演のあらすじで、
# 空を返すのが正しい挙動だった。
#
# **2026-08-28 訂正 2（検証 050 追記 1）── 6 件を「誤マッチ」から「取りこぼし」に直した。**
# 「劇壇ガルバ」「デカローグ1・3・4・5・6」は、`WRONG_JOIN` の訂正と同じ理由（本文に
# その公演自身の正しいあらすじが載っていた）で、空を返すのは正しい挙動ではなく見送りだった。
# あわせて「ゴツプロ『流浪樹」「CAMPだGO」の 2 件を新規に追加した ── この 2 件は当時の
# `themes.jsonl` に別公演の要素が入っていた（`synopsis` は真）ため `WRONG_JOIN` 側の
# 分岐で判定されていたが、本文には当該公演自身のあらすじも別途載っており、**正しい
# 抽出はそちらを取ることだった。** `fail_cause` を優先させて判定を上書きする。
FAIL_CAUSE = {
    "ミュージカルsmoke#2024-03-15": "取りこぼし",
    "2月平日ジョジョの奇妙な冒険#2024-02-13": "取りこぼし",
    "ヴィンセントインブリクストン#2022-10-06": "取りこぼし",
    "anumber#2022-10-07": "取りこぼし",
    "ミュージカルダブルトラブルamusicaltourdefarce2022夏seasonb兄ジミー林翔太×弟ボビー寺西拓人#2022-08-21": "取りこぼし",
    "きまぐれポニーテールkingofrocknroll札幌演劇シーズン2021夏#2021-08-06": "取りこぼし",
    "こまつ座泣き虫なまいき石川啄木#2025-12-11": "材料なし",
    "劇壇ガルバ第7回公演theweir堰#2026-02-11": "取りこぼし",
    "デカローグ5ある殺人に関する物語#2024-05-23": "取りこぼし",
    "デカローグ6ある愛に関する物語#2024-05-23": "取りこぼし",
    "デカローグ4ある父と娘に関する物語#2024-04-22": "取りこぼし",
    "デカローグ1ある運命に関する物語#2024-04-21": "取りこぼし",
    "デカローグ3あるクリスマスイヴに関する物語#2024-04-21": "取りこぼし",
    "ゴツプロ流浪樹#2025-06-06": "取りこぼし",
    "ふぉゆ×specialcampだgo#2025-01-19": "取りこぼし",
    "lovelywife#2025-03-13": "材料なし",
    "熟年団チェリーホープを知ってるかい#2024-12-05": "材料なし",
    "endlessshock#2024-08-01": "材料なし",
    "帝国劇場2024年新春公演#2024-01-03": "材料なし",
    "7月showboy#2023-07-10": "材料なし",
    "endlessshocketernal#2023-04-23": "材料なし",
    "johnnysworldnextstage#2023-01-04": "材料なし",
    "abc座10thanniversaryジャニーズ伝説2022atimperialtheatre#2022-12-11": "材料なし",
    "少年たちあの空を見上げて#2022-09-21": "材料なし",
    "dreamboys#2022-09-19": "材料なし",
    "endlessshock#2022-09-06": "材料なし",
    "endlessshocketernal#2022-04-30": "材料なし",
}


def nz(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").lower()
    return re.sub(r"[^0-9a-z぀-ヿ一-鿿]", "", s)


def url_type(url: str, title: str) -> str:
    for k, v in TYPE_OVERRIDE.items():
        if k in url:
            return v
    return URL_TYPE.get(urlparse(url).netloc, "未分類")


def join_map() -> tuple[dict, dict]:
    """CoRich の行を (観劇日, 件名) で引く表と、題名だけで引く表を作る。"""
    by_key: dict[tuple, str] = {}
    by_title: dict[str, set] = collections.defaultdict(set)
    for line in CREDITS.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        c = json.loads(line)
        if not c.get("stage_id"):
            continue
        by_key[(c.get("date"), c.get("mail_title"))] = str(c["stage_id"])
        by_title[nz(c.get("mail_title"))].add(str(c["stage_id"]))
    return by_key, by_title


def main() -> int:
    themes = {}
    for line in THEMES.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            r = json.loads(line)
            if r["side"] == "rated":
                themes[r["id"]] = r

    rows = E.targets("rated", fetch=False)
    by_key, by_title = join_map()
    con = R.connect()
    state = R.State("material", con, R.load_purchases())
    works = {w["work_key"]: w for w in state.works}

    recs = []
    for r in rows:
        w = works.get(r["id"], {})
        shows = [state.by_uid[s["uid"]] for s in w.get("shows", [])]
        dates = [p.get("date") for p in shows]
        cand: set = set()
        for p in shows:
            cand |= by_title.get(nz(p.get("title")), set())
        sid = r.get("stage_id") or ""
        html = E.cached(r["url"]) if r["url"] else ""
        # **あらすじの出どころを分ける。** 抽出には CoRich の公演ページと公式サイトの
        # 両方を渡しているので、**公式ページの質が効いているかは出どころを見ないと言えない。**
        # 突き合わせは検証 034 の実在検査（12 字の窓 5 つのうち 3 つ）をそのまま使い、
        # 渡したときと同じ切り方（CoRich 2,500 字・公式 3,500 字）で比べる。
        syn = themes.get(r["id"], {}).get("synopsis", "")
        src = ""
        if syn:
            in_cor = E.verbatim(syn, E.corich_text(sid, 2500)) if sid else False
            in_off = E.verbatim(syn, E.prep(html, 3500)) if html else False
            src = {(True, True): "両方", (True, False): "CoRich",
                   (False, True): "公式", (False, False): "不明"}[(in_cor, in_off)]
        wrong = next((v for k, v in WRONG_JOIN.items() if k in r["title"]), "")
        rec = {
            "key": r["id"], "title": r["title"], "verdict": r.get("verdict"),
            "stage_id": sid, "url": r["url"],
            "undated": all(d is None for d in dates) if dates else True,
            "title_only_hits": len(cand),
            "corich_len": len(E.corich_text(sid, 99999)) if sid else 0,
            "official_len": len(E.prep(html, 99999)) if html else 0,
            "url_type": url_type(r["url"], r["title"]) if r["url"] else "",
            "wrong_join": wrong,
            "fail_cause": FAIL_CAUSE.get(r["id"], ""),
            "synopsis": bool(syn),
            "source": src,
            "elements": [e["word"] for e in themes.get(r["id"], {}).get("elements", [])],
        }
        recs.append(rec)
    con.close()

    n = len(recs)
    have = [r for r in recs if r["stage_id"]]
    none = [r for r in recs if not r["stage_id"]]
    print(f"## 段 1 ── 突き合わせ（評価済み {n} 作品）")
    print(f"CoRich の行が引けた                {len(have):>3} 件")
    print(f"引けなかった                      {len(none):>3} 件")
    print(f"  うち観劇日が無い（キーを作れない）  {sum(1 for r in none if r['undated']):>3} 件")
    print(f"  うち日付はあるが件名で引けない      {sum(1 for r in none if not r['undated']):>3} 件")
    print(f"  題名だけに緩めれば一意に引ける      {sum(1 for r in none if r['title_only_hits'] == 1):>3} 件"
          f"（候補が複数で確定できない {sum(1 for r in none if r['title_only_hits'] > 1)} 件）")

    bad = [r for r in have if r["wrong_join"]]
    print(f"\n## 段 2 ── 引けた行の正否（{len(have)} 件）")
    print(f"別公演を指していた                {len(bad):>3} 件（{len(bad) / len(have):.0%}）")
    print(f"  うちあらすじが取れた（学習に入った） {sum(1 for r in bad if r['synopsis']):>3} 件")
    for r in bad:
        mark = "要素が入った" if r["synopsis"] else "取れず"
        print(f"    {mark:<6} {r['title'][:26]:<26} → {r['wrong_join']}")

    print(f"\n## 段 3 ── ページの質（{len(have)} 件）")
    print(f"あらすじが取れた                  {sum(1 for r in have if r['synopsis']):>3} 件"
          f"（{sum(1 for r in have if r['synopsis']) / len(have):.0%}）")
    tab = collections.Counter()
    for r in have:
        tab[(r["url_type"] or "URL 欄が空", r["synopsis"])] += 1
    print(f"\n{'公式 URL の種別':<14}{'件数':>6}{'あらすじ':>8}{'取得率':>8}")
    for t in ["公演固有", "複数公演", "一覧", "別公演", "プレイガイド", "SNS", "URL 欄が空", "未分類"]:
        tot = tab[(t, True)] + tab[(t, False)]
        if not tot:
            continue
        print(f"{t:<14}{tot:>6}{tab[(t, True)]:>8}{tab[(t, True)] / tot:>8.0%}")

    got = [r for r in have if r["synopsis"]]
    srct = collections.Counter(r["source"] for r in got)
    print(f"\n{'あらすじの出どころ':<18}{'件数':>6}")
    for k in ["両方", "CoRich", "公式", "不明"]:
        if srct[k]:
            print(f"{k:<18}{srct[k]:>6}")
    print("**公式サイトにしか無かったのは "
          f"{srct['公式']} 件である。** CoRich の公演ページで足りたのが {srct['CoRich'] + srct['両方']} 件")

    lost = [r for r in have if not r["synopsis"]]
    ct = collections.Counter(r["fail_cause"] or "未分類" for r in lost)
    print(f"\n{'取れなかった 25 件の内訳':<22}{'件数':>6}")
    for k in ["材料なし", "取りこぼし", "誤マッチ", "未分類"]:
        if ct[k]:
            print(f"{k:<22}{ct[k]:>6}")
    print("**材料が無いのは "
          f"{ct['材料なし']} 件で、{ct['取りこぼし']} 件は本文に物語があるのに抽出が空を返している。**")

    cache = [r for r in have if r["url"] and r["official_len"] == 0]
    thin = [r for r in have if 0 < r["official_len"] < 200]
    print(f"\n公式 URL があるのに本文が無い（未取得・404）      {len(cache):>3} 件")
    print(f"本文が 200 字未満（宣伝画像だけのページ）        {len(thin):>3} 件")
    print(f"CoRich の公演ページの本文が 200 字未満          "
          f"{sum(1 for r in have if r['corich_len'] < 200):>3} 件")

    # **◎ が何件届いているかを別に数える。** 網 C は ◎ の出現率で強さを出すので、
    # **薄さは「作品の 3 分の 1」ではなく「正例の半分」として効く。**
    def mar(rs):
        return sum(1 for r in rs if r["verdict"] == "◎")
    print(f"\n## ◎ の届き方（◎ は全部で {mar(recs)} 件）")
    print(f"網 C の学習に入った ◎              {mar([r for r in recs if r['synopsis']]):>3} 件")
    print(f"突き合わせで落ちた ◎              {mar(none):>3} 件")
    for k in ["材料なし", "取りこぼし", "誤マッチ"]:
        print(f"{k} で落ちた ◎{'':<10}{mar([r for r in have if r['fail_cause'] == k]):>3} 件")

    OUT.write_text(json.dumps(recs, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\n1 件ずつの判定を {OUT.relative_to(ROOT)} に残した")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
