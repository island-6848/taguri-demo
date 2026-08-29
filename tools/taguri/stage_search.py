#!/usr/bin/env python3
"""手で足す欄の「検索」── 手元に無い公演を、その場で公演情報から拾う。

起案者の指示（2026-08-24）──「『手で足す』のところに『るつぼ』って入れても候補が
出てこないのなら『検索』のボタンをおして、その場で情報を拾ってきて登録できるように
してほしい」。

## なぜ要るのか

**手で足す欄の候補は、手元にあるものしか出さない。** 引き出しは 3 つ（自分の記録・
これから／最近の公演・公演ページの控え）で、**そのどれにも無い公演は、白紙に打つしか
なかった。** 実際に起きたのが『るつぼ The Crucible』（東京芸術劇場・2026/03/14〜03/29）
である ── 今年観た公演なのに、候補に 1 件も出なかった。

終わった公演を候補に 180 日ぶん残すようにしたので手元の守備範囲は広がったが、
**それより古い公演は依然として出ない。** 招待・当日券・人に取ってもらった観劇は購入確認
メールに残らないため、こういう公演ほど手で足すことになる。

## 押したときだけ外に行く

**打っている最中には行かない。** 1 つの相手には 1.1 秒に 1 回までを守るので、1 回の検索に
最大 8 要求＝8 秒ほどかかる。文字を打つたびに走らせると、打ち直すたびにやり直しになり、
待っているのか壊れているのか本人には分からない。**押した人が待っていると分かる形にする。**

## 探し方は更新の段と同じものを使う

`link_works.search_stages` を呼ぶ。**探し方を 2 通り作らない** ── 同じ題名で画面と更新の段の
結果が違うと、どちらが正しいのか確かめようがない。

## 当てるのは題名だけで、選ぶのは本人である

更新の段（`link_works.find`）は**観劇日が上演期間の中にあること**を必ず要求する。
同じ戯曲の別の上演を当てないための条件だが、**この欄では観劇日がまだ無い** ── 題名を
打った時点で押すので、日付はこれから入る。

そこで**題名の重なりだけで当て、当たった公演を並べて本人に選ばせる。** 実測で『るつぼ
The Crucible』は東京・兵庫・豊橋の 3 件が別の公演として登録されており、**どれを観たのかを
知っているのは本人だけである。**

## 選んだ公演は、登録したその場で手元の控えに写す（`adopt`）

**「材料は次の更新のときに入る」という作りは誤りだった。** 更新の段が見るのは評価が付いた
記録だけなので、観た帰りに評価を付けるまで空のままになり、画面には「手元のデータに
見当たりません」と出ていた ── 詳しくは `adopt` の注記に書いた。**登録のときに写す。**
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in ("credits", "review", "tickets"):
    _s = str(ROOT / "tools" / _p)
    if _s not in sys.path:
        sys.path.insert(0, _s)


def search(q: str, limit: int = 6) -> dict:
    """題名で公演を探して、手で足す欄の行の形で返す。

    **失敗しても画面は壊さない。** 外に行く処理なので落ちることがある ── 落ちたことを
    文で返し、手で入れる道を残す（`error`）。
    """
    import link_works as L
    import rate_performances as R

    q = (q or "").strip()
    if len(R.title_key(q)) < 2:
        return {"q": q, "rows": [], "error": "題名を 2 文字以上入れてください"}
    try:
        found = L.search_stages(q, limit=limit)
    except Exception as e:                                          # noqa: BLE001
        return {"q": q, "rows": [],
                "error": f"公演情報を探せませんでした（{type(e).__name__}）。"
                         "お手数ですが、手で入れてください"}
    rows = []
    for r in found:
        # **見分けが付く形で並べる。** 同じ題名の公演が複数当たるのが普通なので、
        # 劇場と期間を必ず添える ── これが無いと、どれを選ぶのか決められない
        #
        # **取得元を「CoRich」と名前で書く**（起案者の指示・2026-08-26 ──「それを
        # 『CoRichにて検索』など明記して」）。「外の公演情報」では、どこを見に行った
        # のか読み手には分からない
        note = "／".join(x for x in ("CoRichの公演情報", r.get("period") or "") if x)
        rows.append({"kind": "stage", "key": r["stage_id"],
                     "title": r.get("page_title") or q,
                     "date": r.get("date") or "",
                     "venue": r.get("venue") or "",
                     "note": note, "times": 1, "stage_id": r["stage_id"],
                     # **出演を少しだけ添える。** 同じ劇場で再演している公演を、
                     # 期間だけで見分けられないことがある
                     "cast": ((r.get("fields") or {}).get("出演") or "")[:60]})
    return {"q": q, "rows": rows, "error": ""}


PICKED = ROOT / "data" / "review" / "picked.jsonl"


def _pool_row(sid: str, c: dict, title: str = "") -> dict:
    """公演ページの中身を、候補の控えと同じ形にそろえる。

    **形をそろえるのは、読む側を 1 通りにするためである。** 候補・カレンダー・お気に入りで
    直接引いた分と同じ鍵にしておけば、推薦の計算も探す画面も、どこから来た公演かを
    気にせずに済む。

    **都道府県と団体は入らない。** どちらも一覧のページにしか無く、公演ページからは
    取れない ── **空で置く**（当て推量で埋めない）。
    """
    # **HTML の実体参照をほどく。** 公演ページから取り出した文字は `&#39;` のような形の
    # ままなので、画面に出すときに `&` が二重に escape されて `&#39;` と読めてしまう
    # （実測 ──「少女ハムレット〜茜色の事件簿〜&#39;26」）。**控えに入れる時点で直す。**
    import html as _h
    f = {k: (_h.unescape(v) if isinstance(v, str) else v)
         for k, v in (c.get("fields") or {}).items()}
    price = next((v for k, v in f.items() if k.startswith("料金")), "")
    return {"stage_id": str(sid),
            "title": _h.unescape(title or c.get("page_title") or ""),
            "group": "", "theater": f.get("劇場", ""), "venue": f.get("劇場", ""),
            "pref": "", "period": _h.unescape(c.get("period") or f.get("期間", "")),
            "price": (price or "").split("\n")[0].strip(),
            "status": "", "fields": f,
            "url": f"https://stage.corich.jp/stage/{sid}",
            "source": "探して拾った"}


def search_full(q: str, limit: int = 6) -> dict:
    """題名で公演を探し、**候補の控えと同じ形**で返す（探す画面が使う）。

    起案者の指摘（2026-08-24）──「おすすめの 15 件とかにもまだ載ってないけど今後の情報を
    検索して探したいときとかは？」。**手元の 1,301 件は、月 1 回の取得で集めた分でしかない**
    ── そこに無い公演は、いくら探しても出てこない。**押したときだけ外に行く**（手で足す欄と
    同じ約束・同じ経路）。
    """
    import link_works as L
    import rate_performances as R
    q = (q or "").strip()
    if len(R.title_key(q)) < 2:
        return {"q": q, "rows": [], "error": "2 文字以上入れてから押してください"}
    try:
        found = L.search_stages(q, limit=limit)
    except Exception as e:                                          # noqa: BLE001
        return {"q": q, "rows": [],
                "error": f"公演情報を探せませんでした（{type(e).__name__}）"}
    rows = [_pool_row(r["stage_id"], r, r.get("page_title") or "") for r in found]
    return {"q": q, "rows": rows, "error": ""}


def lookup_one(q: str, limit: int = 3) -> dict:
    """題名で公演を探し、**演者とあらすじの材料になる 1 件**を返す。

    「観ればよかった」の登録が使う。**手で足す欄と違って、選ぶ本人がいない**
    ── 見逃した公演なので観劇日が無く、同じ題名の公演が複数当たっても、
    どれを観る予定だったのかを決める材料が無い。ここでは表示するだけで記録には
    結び付けないので、機械が題名の当たりがいちばん良い 1 件（`search_stages` が
    返す並びの先頭）を選ぶ。探し方は `search_full` と同じものを使う ──
    探し方を 2 通り作らない。
    """
    r = search_full(q, limit=limit)
    if r["error"] or not r["rows"]:
        return {"ok": False, "why": r["error"] or "この題名の公演ページが見つかりませんでした"}
    top = r["rows"][0]
    return {"ok": True, "n": len(r["rows"]), "stage_id": top["stage_id"],
            "venue": top.get("venue", ""), "period": top.get("period", ""),
            "fields": top.get("fields") or {}}


def pick(stage_id: str) -> dict:
    """探して見つけた公演を、**手元の候補に加える。**

    ## なぜ加えるのか

    **反応（興味あり・すでに持っている・興味なし）は公演の id に対して保存されるが、
    「追いかけている一覧」は候補の控えから組む。** 手元に無い公演に「興味あり」を押すと、
    **押した記録は残るのに、どの一覧にも出てこない** ── 押した本人からは消えたように見える。

    ## 置き場所を分ける

    `candidates.jsonl` は月 1 回の取得で**丸ごと書き直される**ので、そこに書くと次の取得で
    消える。**`picked.jsonl` は書き足すだけの控え**で、誰も上書きしない。

    **通信は 0 回で済む**（探したときに公演ページを控えている）。
    """
    import fetch_credits as FC
    sid = str(stage_id or "").strip()
    if not sid.isdigit():
        return {"ok": False, "why": "id が数字ではない"}
    if sid in {str(c.get("stage_id")) for c in load_picked()}:
        return {"ok": True, "why": "もう控えにある", "wrote": False}
    try:
        c = FC.credits_of(sid)
    except Exception as e:                                          # noqa: BLE001
        return {"ok": False, "why": f"{type(e).__name__}"}
    row = _pool_row(sid, c)
    if not row["title"]:
        return {"ok": False, "why": "題名を取れなかった"}
    with PICKED.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"ok": True, "wrote": True, "title": row["title"]}


def load_picked() -> list[dict]:
    """探して拾った公演の控え。**無ければ空**（初めて使う端末には無い）。"""
    if not PICKED.exists():
        return []
    return [json.loads(l) for l in PICKED.read_text(encoding="utf-8").split("\n")
            if l.strip()]


def _known_stage_ids() -> set[str]:
    """**中身のあるクレジットを手元に持っている公演の id。**"""
    import measure_nets as M
    return {sid for sid, f in M._fields_by_stage().items() if f}


def adopt(stage_id: str, work_key: str = "", title: str = "", date: str = "") -> dict:
    """検索から選んだ公演を、**その場で手元の控えに写す。**

    ## なぜ登録のときに写すのか ── 「次の更新で入る」では入らなかった

    はじめは「選ぶと id が付き、材料は次の更新のときに入る」という作りにした。
    **これは誤りだった**（起案者の報告 2026-08-24 ──「推薦に使う公演／公演 428905
    （手元のデータに見当たりません）ってなるんだけどういうこと？」）。

    2 つ抜けていた。

    1. **更新の段が見るのは、評価が付いた記録だけである**（`measure_nets.load_rated` は
       `verdict` が無い行を落とす）。観た帰りに評価を付けるまで**何日でも空のまま**になる。
       実測で、登録された『るつぼ The Crucible』は更新の段の対象 39 件に入っていなかった。
    2. **画面の「推薦に使う公演」は手元の 3 つの控えから題名を引く。** どこにも無いので
       「手元のデータに見当たりません」と出た ── **本人が選んで結び付けた直後に、
       壊れているように見える。**

    **写す先は `linked.jsonl` である。** 更新の段が書くのと同じ控え・同じ形にする ──
    置き場所を 2 つにすると、読む側が両方を見なければならなくなる。

    **通信は 0 回で済む。** 検索したときに公演ページを控えに入れてあるので、
    `fetch_one` はそこから読む（控えが無いときだけ 1 要求）。

    **登録を失敗させない。** ここが落ちても記録そのものは残っているべきなので、
    例外は飲んで理由を返す。
    """
    import link_works as L
    sid = str(stage_id or "").strip()
    if not sid:
        return {"ok": False, "why": "id が無い"}
    try:
        if sid in _known_stage_ids():
            return {"ok": True, "why": "もう手元にある", "wrote": False}
        r = L.fetch_one(sid)
        row = {"work_key": work_key, "title": title, "date": date, **r}
        with L.OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return {"ok": True, "wrote": True, "page_title": r.get("page_title", ""),
                "period": r.get("period", ""), "n_fields": len(r.get("fields") or {})}
    except Exception as e:                                          # noqa: BLE001
        return {"ok": False, "why": f"{type(e).__name__}: {e}"}
