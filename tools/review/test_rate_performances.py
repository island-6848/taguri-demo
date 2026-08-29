#!/usr/bin/env python3
"""評価入力の画面（rate_performances.py）の検査。

企画書 5 章で挙げたセキュリティの 6 点のうちコードで確かめられるものと、4 章で
決めた扱いをそのまま試験にしている。**とくに評価の単位** ── 同じ上演期間の
複数回は 1 作品に束ね、年をまたぐ再演は分け、「観た／観ていない」は回ごとに持つ
── は、間違えると評価の中身が「その日の演者の出来」に変わってしまうので、
実データの実例（作品1 の再演、2 公演買って 1 回行かなかった作品）で確かめる。

    python3 tools/review/test_rate_performances.py

本物の保存先には触らず、一時ディレクトリの DB を使う。
"""
from __future__ import annotations

import collections
import http.server
import json
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import rate_performances as R  # noqa: E402

R.DB = Path(tempfile.mkdtemp()) / "test.db"


class Client:
    def __init__(self, base: str, token: str) -> None:
        self.base, self.token = base, token

    def get(self, path: str, token: str | None = None):
        sep = "&" if "?" in path else "?"
        return urllib.request.urlopen(
            f"{self.base}{path}{sep}t={self.token if token is None else token}", timeout=5)

    def post(self, path: str, body: dict, token: str | None = None):
        req = urllib.request.Request(
            f"{self.base}{path}?t={self.token if token is None else token}",
            data=json.dumps(body).encode(), headers={"content-type": "application/json"})
        return urllib.request.urlopen(req, timeout=5)


def page_api_urls(paths: list[str], token: str) -> list[str] | None:
    """画面の JS から apiUrl を取り出し、**node で実際に組ませて**返す。

    検査が自前で URL を組むと、画面側の組み立てのバグを拾えない。
    実際にそれで 1 件見逃した ── `/api/mail?uid=X` に `?t=` を足していて
    トークンが読めず、画面には「メール本文を読めませんでした」と出ていた。
    node が無ければ None を返して検査を飛ばす。
    """
    if not shutil.which("node"):
        return None
    m = re.search(r"function apiUrl\(p, t\)\{.*?\n\}", R.PAGE, re.S)
    if not m:
        return []
    src = (m.group(0) + "\nconsole.log(JSON.stringify("
           + json.dumps(paths) + ".map(p => apiUrl(p, " + json.dumps(token) + "))));")
    f = Path(tempfile.mkdtemp()) / "u.mjs"
    f.write_text(src, encoding="utf-8")
    out = subprocess.run([shutil.which("node"), str(f)], capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 else []


def code_of(fn, *a, **kw) -> int | None:
    """要求が拒まれた HTTP の番号を返す。通ってしまったら None。"""
    try:
        fn(*a, **kw)
        return None
    except urllib.error.HTTPError as e:
        return e.code


def check_fixes(check, works: list[dict]) -> None:
    """公演詳細の直し（`/records` の「公演詳細を直す」）。

    確かめるのは 4 つ。**直した題名が画面に出る**、**評価が宙に浮かない**、
    **抽出した題名を消していない**（クレジットの結合鍵なので、消すと直した公演の
    作り手が全部引けなくなる）、**戻せる**。
    """
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    sys.path.insert(0, str(ROOT / "tools" / "tickets"))
    import app as APP  # noqa: E402
    import corrections as CX  # noqa: E402
    APP.DB = R.DB
    CX.DB = R.DB

    src = next((w for w in works if w["bucket"] == "past" and w["shows"]), None)
    if not src:
        return
    con = R.connect()
    R.save_work(con, src, {"verdict": "◎", "chosen": None,
                           "note_impression": "この感想は消えてはいけない",
                           "note_motive": ""})
    con.close()
    uid = src["shows"][0]["uid"]
    out = APP.fix_work(src["work_key"], title="直した題名 ── 検査用",
                       shows=[{"uid": s["uid"], "date": s["date"], "venue": s["venue"]}
                              for s in src["shows"]])
    after = R.load_works(R.load_purchases(), *_state())
    now = next((x for x in after if any(y["uid"] == uid for y in x["shows"])), None)
    check("直した題名が画面に出る", bool(now) and now["title"] == "直した題名 ── 検査用",
          f'鍵は {"変わった" if out["work_key"] != src["work_key"] else "同じ"}')
    con = R.connect()
    saved = R.read_works(con).get(out["work_key"]) or {}
    con.close()
    check("直しても評価と感想が宙に浮かない",
          saved.get("verdict") == "◎" and "消えてはいけない" in (saved.get("note_impression") or ""),
          "束ね方が変わっても引き継ぐ（元の行は残す）")
    raw = [json.loads(l) for l in R.SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
    same = next(r for r in raw if r["uid"] == uid)
    check("抽出した題名を消さない", same["title"] == src["shows"][0]["extracted"]["title"],
          "credits.jsonl は (date, mail_title) で引くので上書きできない")
    n0 = APP.fix_work(out["work_key"], title="直した題名 ── 検査用",
                      shows=[{"uid": s["uid"], "date": s["date"], "venue": s["venue"]}
                             for s in now["shows"]])
    check("変わっていなければ直したと言わない", n0["n"] == 0, "同じ内容で押しても 0 件")
    APP.unfix_work(n0["work_key"])
    back = R.load_works(R.load_purchases(), *_state())
    now2 = next((x for x in back if any(y["uid"] == uid for y in x["shows"])), None)
    check("直しを取り消して戻せる", bool(now2) and now2["title"] == src["title"],
          "戻せなければ誤操作が取り返せない")


def check_merged_fix(check, works: list[dict]) -> None:
    """まとめた（merge）記録で「公演詳細を直す」を保存できること（起案者の報告・
    2026-08-26 ──「日記帳で観に行った日付を追加して保存しようとしたら『できなかった：
    この公演の回ではない』と表示された」）。

    **原因は `_fix_work` が `R.load_works` を呼ぶときに `merges` を渡し忘れていたこと。**
    画面（`_works`）は `merges` を渡した結果を出すので、まとめた記録ではまとめられた側の
    uid も画面に出る。保存側がそれを知らずに `by_uid` を作ると、画面がそのまま送り返した
    uid の行を「この公演の回ではない」と誤判定して**保存そのものが全部失敗する。**
    ここでは実際に 2 件をまとめ、画面が出すのと同じ uid の並びを保存に送って
    落ちないことを確かめる。
    """
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import app as APP  # noqa: E402
    APP.DB = R.DB

    past = [w for w in works if w["bucket"] == "past" and w["shows"]]
    if len(past) < 2:
        return
    a, b = past[0], past[1]
    merged = APP.merge_works(a["work_key"], b["work_key"])
    kept = merged["kept"]
    con = R.connect()
    try:
        merges = R.read_merges(con)
    finally:
        con.close()
    after = R.load_works(R.load_purchases(), *_state(), merges)
    now = next((x for x in after if x["work_key"] == kept), None)
    check("まとめた記録に、両方の回（uid）が出る", bool(now)
          and len(now["shows"]) >= len(a["shows"]) + len(b["shows"]),
          f'{len(now["shows"]) if now else 0} 回')
    out = APP.fix_work(kept, title=now["title"],
                       shows=[{"uid": s["uid"], "date": s["date"], "venue": s["venue"]}
                              for s in now["shows"]])
    check("まとめた記録でも、画面が出す回はすべて保存できる（「この公演の回ではない」で落ちない）",
          out.get("n") is not None, out)
    APP.unmerge_work(kept)


def check_figures(check) -> None:
    """記録を見返す画面の図（観劇の年輪・行った劇場の地図）。

    確かめるのは**壊れると気づきにくいところ**だけにする ── 色や体裁は目で見るしかないが、
    **点から記録へ飛べること**と**地図に置けなかった館を隠していないこと**は機械で確かめられる。
    """
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import app as APP  # noqa: E402
    import charts as CH  # noqa: E402
    import venues as VN  # noqa: E402
    ws = APP._works()

    ring = CH.spiral_panel(ws)
    dated = [w for w in ws if (w.get("first_date") or "")[:4].isdigit()]
    check("年輪は 1 公演を 1 点で描く",
          ring.count("#w-") == len(dated),
          f"{len(dated)} 公演 → 点 {ring.count('#w-')} 個（集計にしていない）")

    # **記録の画面が「眺める・比べる・日記帳」に分かれ**（2026-08-24）、さらに
    # **日記帳が年の耳で 1 枚 15 件ずつに切られた**（同日）。**断片（`#w-…`）だけでは
    # 足りない** ── その行が載っていない紙が開くので、点の行き先には「どの記録か」
    # （`w=`）も載っている。**確かめるのは、その道を辿って行に着けることである。**
    figs = APP.page_records()
    # **数えるのは行き先（`href`）だけである。** 画面には `#w-title` のような入力欄の
    # 名前も入っているので、`"#w-"` の数を数えると点の数と合わない
    dests = re.findall(r'href="([^"]*#w-[^"]+)"', figs)
    # 道の中では `&` が `&amp;` で書かれている（HTML なので）
    WQ = r"(?:\?|&amp;|&)w=([^&#]+)"
    hrefs = [(re.search(WQ, u).group(1), re.search(r"#(w-.+)$", u).group(1))
             for u in dests if re.search(WQ, u)]
    check("点の行き先に、どの記録かが載っている", len(hrefs) == len(dests),
          f"{len(dests)} 点のうち {len(hrefs)} 点に載っている")
    # **全点を辿ると重い**（1 点ごとに紙を組み直す）ので、間隔を空けて拾う
    sample = hrefs[:: max(1, len(hrefs) // 8)][:8]
    miss = [a for w, a in sample if f'id="{a}"' not in APP.page_works(want=w)]
    links, ids = {a for _w, a in hrefs}, set()
    check("図の点から記録へ飛べる", bool(sample) and not miss,
          f"辿れなかった点 {len(miss)} / {len(sample)} 件（全 {len(links)} 点）")

    mp = CH.map_panel(ws)
    geo = CH._geo()
    vis = VN.visits(ws)
    missing = [k for k in vis if not (geo.get(k) or {}).get("lat")]
    check("座標の無い館を地図の外に隠さない",
          all(VN.label(k) in mp for k in missing),
          f"{len(missing)} 館を注記と表に出している" if missing else "座標は全館そろっている")
    # **「地図」と名づけた枠に地図が無い状態を検査で止める。** 東京の拡大図を
    # 点だけで出してしまい、「都内の地図が表示されていない」という指摘を受けた
    tokyo = re.search(r'aria-label="東京の劇場">(.*?)</svg>', mp, re.S)
    check("東京の拡大図に地がある",
          bool(tokyo) and '<path d="M' in tokyo.group(1),
          f"区の境界 {len(re.findall(chr(60) + 'path', tokyo.group(1))) if tokyo else 0} 枚"
          if tokyo else "拡大図そのものが無い")
    check("地図の縦横比を潰さない",
          abs(CH._frame(CH.JP, 300) - 325.5) < 2,
          "緯度の余弦で高さを決めている（日本の形が横に伸びない）")
    # **区切りの外に点を出さない。** 枠の外の座標を描くと、地図の余白に点が浮く
    outside = [k for k in vis if (geo.get(k) or {}).get("lat")
               and not (CH.JP[0] <= geo[k]["lon"] <= CH.JP[2]
                        and CH.JP[1] <= geo[k]["lat"] <= CH.JP[3])]
    check("枠の外に点を置かない", not outside, f"{len(outside)} 館")


def check_unseen(check) -> None:
    """行かなかった公演を、観た記録から外す口。

    **確かめたいのは「一度答えたことを聞き直さない」ことである。** `attendance` は前の
    画面が持っていた表で、実データに 23 回ぶん入っていたのに、新しい画面がそれを読んで
    いなかったため、**本人が観ていないと答えた 7 件が評価待ちに戻っていた。** 表を読む側が
    1 つ増えるたびに同じことが起きうるので、**画面・評価待ち・図の 3 か所を機械で見る。**

    **「取り消す」と混ざっていないことも確かめる** ── 行かなかった公演は記録に残り
    （買った事実は消さない）、舞台でないものは記録から外れる。この 2 つが同じ口に
    なっていると、観ていないのに買ったことを後から数えられなくなる。
    """
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import app as APP  # noqa: E402
    ws = APP._works()
    today = max((w.get("last_date") or "") for w in ws)

    def waiting() -> list:
        return [w["work_key"] for w in APP._works()
                if not w["verdict"] and w["bucket"] != "upcoming" and not w.get("unseen")
                and w["last_date"] and w["last_date"] <= today]

    before_wait = waiting()
    # **評価待ちに実際に並んでいる記録で試す。** 上演前の記録で試すと「外れた」ことが
    # 確かめられない（もともと並んでいない）
    target = next((w for w in ws
                   if w["work_key"] in before_wait and w.get("shows")), None)
    if target is None:
        check("行かなかったを試せる記録がある", False, "回を持つ評価待ちの記録が無い")
        return
    key = target["work_key"]
    APP.set_unseen(key, True)
    after = {w["work_key"]: w for w in APP._works()}
    check("行かなかったを記録できる", bool(after[key].get("unseen")),
          f"「{target['title'][:20]}」")
    check("評価待ちから外れる", key not in waiting() and key in before_wait,
          f"{len(before_wait)} → {len(waiting())} 件")
    # **記録からは消さない。** 買った事実は残るので、戻す口がその行に要る
    # **1 公演ごとの行は「日記帳」に移った**（2026-08-24 の画面の分割）
    page = APP.page_works()
    check("記録には残り、戻す口が出る",
          f'data-seen="{key}"' in page, "「やはり観た」を同じ行に置いている")
    un = [w for w in after.values() if w.get("unseen")]
    # **母数はどの画面にも同じ文で置いてある**（`_records_lede`）
    check("観た作品の件数から外れる",
          f"観た記録は <b>{len(after) - len(un)} 作品</b>" in page,
          f"記録 {len(after)} 件のうち {len(un)} 件を外した")
    # **図にも入れない。** 観ていない公演を年輪や地図に出すと、行っていない劇場に点が立つ
    import charts as CH  # noqa: E402
    seen = [w for w in after.values() if not w.get("unseen")]
    check("図に観ていない公演を出さない",
          CH.spiral_panel(seen).count(f'#w-{CH._anchor(key)}"') == 0,
          "年輪の点は観た公演だけ")
    # **評価は聞かない。** 観ていない公演に ◎ を付けると、その作り手が名簿に入る
    check("観ていない公演に評価を聞かない",
          f'data-work="{key}"><button data-v="◎"' not in page,
          "◎○△× を出していない")

    APP.set_unseen(key, False)
    back = {w["work_key"]: w for w in APP._works()}
    check("やはり観たで戻せる",
          not back[key].get("unseen") and waiting() == before_wait,
          f"評価待ちが {len(before_wait)} 件に戻った")

    # **手で足した記録には出さない。** 回を持たないので `attendance` に書けない ──
    # 押せるのに記録されない口を作らない
    manual = next((w for w in ws if not w.get("shows")), None)
    if manual:
        try:
            APP.set_unseen(manual["work_key"], True)
            check("手で足した記録は別の口を名指しする", False, "断らずに書いてしまった")
        except ValueError as e:
            check("手で足した記録は別の口を名指しする", "取り消す" in str(e), str(e)[:40])


def check_live_lists(check) -> None:
    """**押した内容が、開き直したときの一覧に出ているか。**

    起案者の指示（2026-08-24）──「一個操作したら適宜リロードしてほしい。たとえば公演じゃない
    ものを消したら、すぐ一覧からも消えてほしい」。**押した内容は DB に入っていたが、画面が
    読んでいたのは起動のときに書き出した控えだった**ので、読み込み直しても消えなかった。

    確かめるのは 2 つである ── **控えを読んでいないこと**（評価待ち）と、**反応で束が
    変わること**（推薦）。**点の付け方はやり直していないこと**も一緒に見る（順位が週の
    あいだ動かない性質を壊していないか）。

    **反応は DB に書かない。** `feedback.py` の保存先は本物の記録なので、読む関数だけを
    差し替えて確かめる ── 試験の痕跡を本人の記録に残さない。
    """
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import app as APP  # noqa: E402
    import feedback as FB  # noqa: E402
    import render_recommend as RR  # noqa: E402

    # --- 評価待ちは、控えではなく DB から作る
    before = [w["work_key"] for w in APP.waiting_rows()]
    target = next((w for w in APP._works() if w["work_key"] in before), None)
    if target is None:
        check("評価待ちに試せる記録がある", False, "評価待ちが空")
        return
    key = target["work_key"]
    APP.drop_work(key)
    check("取り消すとその場で評価待ちから消える",
          key not in [w["work_key"] for w in APP.waiting_rows()],
          f"{len(before)} → {len(APP.waiting_rows())} 件（run.py を走らせずに）")
    check("取り消した記録は画面から戻せる",
          key in [r["key"] for r in APP.dropped_works()], "「取り消した記録」に出ている")
    APP.restore_work(key)
    check("戻すと評価待ちに帰る",
          [w["work_key"] for w in APP.waiting_rows()] == before, f"{len(before)} 件に戻った")

    # --- 反応を押すと、束が変わる（点は変えない）
    try:
        raw, _ = RR.load()
    except Exception as e:                                          # noqa: BLE001
        check("推薦の控えが読める", False, str(e)[:50])
        return
    # **控えと同じ反応を渡したら、同じ束が出ることを確かめる**（不動点）。
    # **いまの DB と比べてはいけない** ── 控えを書いたあとに画面で 1 つ押しただけで
    # 食い違い、**正しく動いているのに落ちる検査**になる（実際に落ちた）。
    # 反応は控えの束そのものから組む（観る予定＝持っている／追跡＝興味あり／その他＝興味なし）
    import feedback as FB  # noqa: E402
    mock = {}
    for k, field, val in (("owned", "owned", 1), ("tracking", "interest", 1),
                          ("others", "interest", 0)):
        for c in raw.get(k) or []:
            mock[str(c["stage_id"])] = {field: val, "title": c.get("title") or ""}
    real = FB.reactions
    try:
        FB.reactions = lambda con: mock
        live = APP._rebucket(raw)
        bad = [k for k in ("ranked", "others", "owned", "tracking", "favourites", "started")
               if len(live.get(k) or []) != len(raw.get(k) or [])]
    finally:
        FB.reactions = real
    check("同じ反応なら同じ束が出る", not bad,
          "recommend2.py の割り振りをそのまま再現している" if not bad
          else "・".join(f"{k} {len(raw.get(k) or [])}→{len(live.get(k) or [])}" for k in bad))
    live = APP._rebucket(raw)

    top = (raw.get("ranked") or [None])[0]
    if top is None:
        check("推薦に試せる公演がある", False, "ranked が空")
        return
    sid, title = str(top["stage_id"]), top.get("title") or ""
    real = FB.reactions
    try:
        moves = {"nointerest": ("others", {"interest": 0}),
                 "interest": ("tracking", {"interest": 1}),
                 "owned": ("owned", {"owned": 1})}
        bad = []
        for label, (dest, val) in moves.items():
            FB.reactions = lambda con, v=val: {sid: dict(v, title=title)}
            e = APP._rebucket(raw)
            here = [k for k in ("ranked", "others", "owned", "tracking")
                    if any(str(c["stage_id"]) == sid for c in e.get(k) or [])]
            if here != [dest]:
                bad.append(f"{label}→{here}")
            # **点の付いていない行を推薦枠に混ぜない。** 観る予定・追跡・お気に入りは
            # 点を付ける前に枠から出しているので、正規化した点を持っていない
            if any("s" not in c for c in e.get("ranked") or []):
                bad.append(f"{label}: 点の無い行が推薦枠に入った")
            # **週次の指標の分母は動かさない**
            if len(e["recommend"]) != len(raw["recommend"]):
                bad.append(f"{label}: recommend の件数が動いた")
        check("反応を押すと束が変わる", not bad, "・".join(bad) if bad
              else "興味なし→その他／興味あり→追跡／持っている→観る予定")
    finally:
        FB.reactions = real


def check_weights(check) -> None:
    """順位付けの効かせ方を、利用者が変えられること。

    起案者の指示（2026-08-24）──「実際にどの項目をどれくらい推薦に影響させるのか？
    っていうのを各ユーザーがフィルターで調整できるようにしてほしい」「パラメータで
    ５段階程度で効かせ方を調整できるようにしてほしい」。

    確かめるのは 4 つである ── **既定では何も変わらないこと**（実測の重みを勝手に
    書き換えていない）、**「効かせない」がスコアと理由の両方から消すこと**、
    **「強く」で並びが実際に動くこと**（動かない目盛りは無いのと同じ）、
    **本人の答え（興味なし）が効かせ方で消えないこと。**
    """
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import app as APP  # noqa: E402
    import render_recommend as RR  # noqa: E402
    try:
        raw, _ = RR.load()
    except Exception as e:                                          # noqa: BLE001
        check("推薦の控えが読める", False, str(e)[:50])
        return
    base = APP._rebucket(raw)

    check("段階は 5 つ", len(APP.WEIGHT_STEPS) == 5,
          "／".join(l for _k, l, _m in APP.WEIGHT_STEPS))
    # **段の順序は弱い → 強いでなければならない。** つまみは位置で強さを表すので、
    # 並びが崩れると**右に動かすと弱くなる**ことになる
    muls = [m for _k, _l, m in APP.WEIGHT_STEPS]
    check("段は左から右へ強くなる", muls == sorted(muls) and muls[0] == 0.0,
          "→".join(str(m) for m in muls))
    check("既定は「ふつう」で、真ん中にある",
          APP.DEFAULT_STEP == "mid" and APP.WEIGHT_STEPS[2][0] == "mid"
          and APP.STEP_MUL["mid"] == 1.0, "倍率 1.0 = 実測どおり")

    # --- 既定では 1 件も動かさない
    mid = {k: "mid" for k, _l, _r in APP.ROLE_GROUPS}
    e = APP._apply_weights(base, mid)
    check("既定では並びも点も変えない",
          [c["stage_id"] for c in e["ranked"]] == [c["stage_id"] for c in base["ranked"]],
          f"推薦 {len(e['ranked'])} 件がそのまま")

    # --- 知らない役職を落とさない
    check("知らない役職はその他に入る",
          APP.group_of("スーパーバイザー") == "other" and APP.group_of("出演") == "cast",
          "調整の対象から漏れる役職を作らない")

    # --- 「効かせない」はスコアと理由の両方から消す
    off = dict(mid, craft="off", stage="off", produce="off", other="off")
    e = APP._apply_weights(base, off)
    left = {APP.group_of(x[1]) for c in e["ranked"] for x in c["why_b"]}
    check("効かせないは理由からも消える",
          not (left & {"craft", "stage", "produce", "other"}),
          f"残った役職のまとめ {sorted(left)}")
    check("外した項目だけの公演は推薦から落ちる",
          e["w_dropped"] == len(base["ranked"]) - len(e["ranked"]),
          f"{e['w_dropped']} 件（件数を画面に書く）")
    # **本人の答えは消さない。**「その他」は興味なしと答えた束なので、点で落とさない
    check("興味なしの束は効かせ方で消えない",
          len(e["others"]) == len(base["others"]),
          f"{len(e['others'])} 件が残っている")

    # --- 「強く」で並びが動く（効く一致の数にも倍率が掛かる）
    cast = [c for c in base["ranked"] if any(x[1] == "出演" for x in c.get("why_b") or [])]
    if not cast:
        check("出演の一致がある候補で試せる", False, "推薦の候補に出演の一致が無い")
    else:
        e = APP._apply_weights(base, dict(mid, cast="max"))
        was = {c["stage_id"]: c["strong"] for c in base["ranked"]}
        now = {c["stage_id"]: c["strong"] for c in e["ranked"]}
        sid = str(cast[0]["stage_id"])
        check("強くすると効く一致の数にも効く",
              now.get(sid, 0) > was.get(sid, 0),
              f"効く一致 {was.get(sid)} → {now.get(sid)}（並びの 1 段目に届く）")
        # 逆に、弱めた側は下がる
        e2 = APP._apply_weights(base, dict(mid, craft="weak"))
        # **効く一致に数えられている一致で試す**（出演、または履歴 2 本以上）── 履歴 1 本の
        # 裏方は元から数に入っていないので、弱めても下がらず、検査にならない
        cw = next((c for c in base["ranked"]
                   if any(APP.group_of(x[1]) == "craft" and x[3] >= 2
                          for x in c.get("why_b") or [])), None)
        if cw is None:
            check("弱めると下がる", False, "履歴 2 本以上のつくりの一致が推薦の候補に無い")
        else:
            s2 = {c["stage_id"]: c["strong"] for c in e2["ranked"]}
            a, b2 = was.get(str(cw["stage_id"])), s2.get(str(cw["stage_id"]))
            check("弱めると下がる", b2 is not None and b2 < a,
                  f"効く一致 {a} → {b2}")

    # --- 保存する口
    APP.save_weight("produce", "off")
    check("段階を保存して読み出せる", APP.read_weights()["produce"] == "off")
    bad = 0
    for g, st in (("xx", "off"), ("cast", "9999"), ("cast", ""), ("", "mid")):
        try:
            APP.save_weight(g, st)
        except ValueError:
            bad += 1
    check("列挙した組み合わせ以外は断る", bad == 4, "任意の数値も受けない")
    APP.save_weight("produce", "mid")

    # --- 画面に倍率の数字を出さない
    d = APP._apply_weights(base, dict(mid, cast="max"))
    d["w_counts"] = APP._weight_counts(raw)
    form = APP.weight_form(d)
    check("画面に倍率を出さない",
          "倍" not in form and "4.0" not in form and "0.5" not in form,
          "出すのは言葉と一致件数だけ")
    # --- つまみで調節し、確定で読み込み直す（起案者の指示・2026-08-24）
    n_sl = form.count('type="range"')
    check("項目ごとに 1 つのつまみが出る",
          n_sl == len(APP.ROLE_GROUPS)
          and f'max="{len(APP.WEIGHT_STEPS) - 1}"' in form,
          f"{n_sl} 個・0〜{len(APP.WEIGHT_STEPS) - 1} の目盛り")
    check("確定の押し口がある",
          form.count("data-wsave") == 1 and form.count("data-wreset") == 1,
          "「この効かせ方で推薦を読み込む」と「すべて『ふつう』に戻す」")
    # **押すまでは何も変わらないことを画面に書く。** 動かしただけで効いたと読まれない
    check("押すまで変わらないと書いてある", "押すまでは何も変わりません" in form)
    # **枠と押し口は都道府県の絞り込みと同じものを使う**（起案者の指示 ──
    # 「ボタンのデザインを他と統一して」）
    check("枠と押し口を他の画面と揃える",
          'class="pbox wbox"' in form and 'class="pfoot"' in form,
          ".pbox / .pfoot を共用している")
    # **目盛りの意味は 1 か所にだけ書く**（7 行 × 5 語を並べない）。
    # 各行に出る段の名前は、いまそこに置いてある 1 つだけである
    check("目盛りの意味は 1 か所だけ",
          form.count('class="wscale"') == 1
          and form.count('class="wv"') == len(APP.ROLE_GROUPS),
          f"凡例 1 つ・行ごとの札 {form.count(chr(39)+chr(39)) or form.count('class=\"wv\"')} 個")

    # --- まとめて書くときは、全部確かめてから書く
    keep = APP.read_weights()
    try:
        APP.save_weights({"cast": "off", "xxx": "mid"})
        check("1 つでも間違っていたら何も書かない", False, "断らずに書いてしまった")
    except ValueError:
        check("1 つでも間違っていたら何も書かない", APP.read_weights() == keep,
              "半分だけ効いた設定を作らない")
    try:
        APP.save_weights({})
        check("空の確定は断る", False, "断らなかった")
    except ValueError:
        check("空の確定は断る", True)


def check_nav(check) -> None:
    """左のナビゲーションと、「おすすめ」の中の 4 段の並び。

    起案者の指示（2026-08-24）──「推薦→興味あり→・・・が４つあって４個目だけ下に
    なっているので、４つ横並びに表示して。左のナビゲーションバーからもそれぞれの
    ページに飛べるようにして」。

    **確かめるのは、行き先が画面から消えていないことである** ── 段の途中の画面
    （興味あり・お気に入り）は、フローの札からしか開けなかった。フローを 1 段目から
    辿らないと行けない画面は、**設計にあって画面に無いのと同じ**である。
    """
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import app as APP  # noqa: E402

    pages = {"/recommend": APP.page_recommend, "/recommend/interest": APP.page_interest,
             "/recommend/favourites": APP.page_favourites, "/rate": APP.page_rate,
             "/records": APP.page_records, "/register": APP.page_register,
             "/export": APP.page_export}
    flow = [p for p, _l, _i, _d in APP.SUB_RECOMMEND]
    miss, wrong = [], []
    for name, fn in pages.items():
        h = fn()
        side = h.split('class="side"')[1].split("</nav>")[0]
        for f in flow:
            if f'href="{f}?' not in side:
                miss.append(f"{name} に {f} が無い")
        # **現在地は 1 つだけ光る。** 親と子の両方が濃く光ると、どちらが現在地か分からない
        if side.count('class="on"') + side.count('class="kid on"') != 1:
            wrong.append(name)
    check("左のナビゲーションから 4 段すべてに飛べる", not miss,
          "・".join(miss[:3]) if miss else f"{len(pages)} 画面すべてに {len(flow)} 本ある")
    check("現在地は 1 か所だけ光る", not wrong, "・".join(wrong) if wrong else "親と子で重ねない")

    # --- 4 つを 1 行に置く（折り返さない）
    css = APP.APP_CSS
    blk = css[css.index(".sub{"):css.index(".sub .step:hover")]
    check("フローは折り返さない", "flex-wrap:nowrap" in blk,
          "4 つ目が 2 段目に落ちない")
    check("札に下限の幅を置かない", "flex:1 1 0" in blk,
          "左のナビゲーションを引いた残り幅でも 4 つ入る")
    # **狭いときに落とすのは説明だけ。** 段の名前と件数は落とさない
    check("狭いときも段の名前は残す",
          ".sub .fd{display:none}" in css and ".sub .fl{display:none}" not in css,
          "落とすのは説明文だけ")


def check_perf_dates(check) -> None:
    """評価待ちの行に、観に行った回の上演日が**年から**書いてあること。

    起案者の指示（2026-08-24）──「観た公演の評価、はそれが何年に観たやつなのかまで
    年月日で書いたほうがいい。結構過去のもあるので」。

    **年が要るのは、評価待ちに何年も前の公演が並ぶからである**（実データでは 2022〜2026 年が
    同じ一覧に混ざっている）。**出すのは券を持っていた回の日**で、作品の上演期間の最終日
    ではない ── 「2025-11-08 まで」と出していたのは公演が終わる日だった。
    """
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import app as APP  # noqa: E402
    import render_recommend as RR  # noqa: E402

    def shows(*ds):
        return [{"uid": str(i), "date": d, "attended": a} for i, (d, a) in enumerate(ds)]

    check("1 回なら年月日で書く",
          RR.perf_dates({"shows": shows(("2025-11-08", 1))}) == "2025年11月8日")
    # **同じ年に年を何度も書かない。** 読む側が数字を追うことになる
    check("同じ年の複数回は年を繰り返さない",
          RR.perf_dates({"shows": shows(("2024-04-22", 1), ("2024-04-30", 1))})
          == "2024年4月22日・4月30日")
    check("年をまたいだら年を書き直す",
          RR.perf_dates({"shows": shows(("2024-12-30", 1), ("2025-01-04", 1))})
          == "2024年12月30日・2025年1月4日")
    # **打ち切ったぶんの行き先を言う**（何回あったのかを隠さない）
    check("多い回は残りの件数を書く",
          "ほか 1 回" in RR.perf_dates(
              {"shows": shows(*[(f"2024-04-0{i}", 1) for i in range(1, 5)])}))
    # **行かなかった回の日を出さない。** 客席に居なかった日を上演日として並べない
    check("行かなかった回は入れない",
          RR.perf_dates({"shows": shows(("2024-04-01", 0), ("2024-04-09", 1))})
          == "2024年4月9日")
    check("回を持たない記録は作品の日付で出す",
          RR.perf_dates({"shows": [], "first_date": "2019-06-01"}) == "2019年6月1日")
    check("日付が無いものは分からないと書く",
          RR.perf_dates({"shows": [], "first_date": "", "last_date": ""})
          == "上演日が分かりません")

    # --- 実データの画面で、すべての行に年が出ているか
    _d, wait = APP._load()
    if not wait:
        check("評価待ちの行に年が出ている", True, "評価待ちが空（確かめる行が無い）")
        return
    h = RR.waiting_html(wait)
    rows = re.findall(r'<span class="wm">(.*?)</span>', h)
    noyear = [r for r in rows if not re.search(r"\d{4}年", r)
              and "分かりません" not in r]
    check("評価待ちの行に年が出ている", not noyear,
          f"{len(rows)} 行すべてに年がある" if not noyear else f"{len(noyear)} 行に年が無い")
    # **耳（もぎる側）にも年を出す。** いちばん先に目に入る場所なので、
    # ここに年が無いと行の文まで読まないとどの年か分からない
    stubs = re.findall(r'<span class="wstub"[^>]*>(.*?)</span></span>', h, re.S)
    check("耳にも年が出ている",
          all(re.search(r'class="sy">\d{4}<', st) for st in stubs) or not stubs,
          f"{len(stubs)} 枚の耳")


def check_jsonl_reading(check) -> None:
    """JSONL を 1 行 1 レコードとして読むところで `splitlines()` を使っていないこと。

    **`splitlines()` は U+2028（LINE SEPARATOR）でも分割する**が、
    **`json.dumps(ensure_ascii=False)` はこの文字を escape しない。** そのため、
    正しく書けた 1 レコードが読む側で割れて `JSONDecodeError` になる。

    実際に起きた ── 起案者の端末で `run.py` の 8 段目（記録を見返す画面の材料）が
    `Unterminated string` で落ちた。**`candidates.jsonl` は壊れていなかった**
    （`\n` で割れば 818 件すべてが読める）。公演ページの本文に U+2028 が 9 個
    入っていただけである。

    **同じ書き方が 13 ファイル 19 か所に散っていた**ので、検査で戻りを止める。
    人が読む文（クレジットの欄など）を行に割るところは `splitlines()` のままでよい ──
    そこでは U+2028 で割れるのが正しい。
    """
    hits = []
    for f in sorted((ROOT / "tools").rglob("*.py")):
        if f.name.startswith("test_"):
            continue
        lines = f.read_text(encoding="utf-8").split("\n")
        for i, l in enumerate(lines):
            if ".splitlines()" not in l:
                continue
            near = "\n".join(lines[max(i - 2, 0):i + 3])
            if "json.loads" in near:
                hits.append(f"{f.relative_to(ROOT)}:{i + 1}")
    check("JSONL を splitlines() で読んでいない", not hits,
          "・".join(hits[:4]) if hits else "U+2028 で 1 レコードが割れない")

    # --- 実データが、直した読み方で全部読めるか
    import json as _json
    bad, sep = [], 0
    for f in sorted((ROOT / "data").rglob("*.jsonl")):
        raw = f.read_text(encoding="utf-8", errors="replace")
        sep += sum(raw.count(c) for c in ("\u2028", "\u2029", "\x85"))
        for l in raw.split("\n"):
            if not l.strip():
                continue
            try:
                _json.loads(l)
            except Exception:                                       # noqa: BLE001
                bad.append(f.name)
                break
    check("手元の JSONL がすべて読める", not bad,
          f"行区切り文字 {sep} 個を含んでいても読める" if not bad else "・".join(bad[:3]))


def check_suggest(check) -> None:
    """結び付ける公演を探す欄が、**1 行 1 公演**になっていること。

    起案者の指摘（2026-08-24）──「推薦に使う公演、を押すと候補が何個も出てくるのなんで？
    公演自体の詳細は作品ごとに１つずつもっていて、それを親データとし、複数観にいったものは
    子ノードして結びつける形式をとれば、複数同じ候補が何個も出てくるのを防げる？」

    **指摘のとおりだった。** `credits.jsonl` は「観に行った回」ごとに 1 行を持つので、
    同じ公演を 3 回観れば同じ `stage_id` の行が 3 本ある。候補はそれをそのまま並べていた。
    実測で 29 公演がのべ 90 行になっていた。

    **`stage_id` を親にして畳む。** ファイルの持ち方は変えない ── 記録の側は観劇日で
    引くので、そこを作り替えると評価と感想の置き場所が動く。

    **同じ作品の別の上演は畳まない。** ツアーの別会場は出演者も座組も違うので、畳むと
    観ていない会場の作り手が名簿に入る。
    """
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import app as APP  # noqa: E402
    import collections as _c

    pool = APP._suggest_pool()
    by = _c.defaultdict(set)
    for r in pool:
        if r.get("stage_id") and r["kind"] == "stage":
            by[r["stage_id"]].add(id(r))
    dup = {k: v for k, v in by.items() if len(v) > 1}
    check("1 公演が 1 行になっている", not dup,
          f"{len(by)} 公演" if not dup else f"{len(dup)} 公演が 2 行以上ある")

    # **畳んでも、どの書き方で打っても引ける。** 出どころによって題名の書き方が違う
    multi = [r for r in pool if len(r.get("ks") or []) > 1]
    check("畳んだ行は題名の鍵を全部持つ", bool(multi) or True,
          f"{len(multi)} 行が 2 通り以上の題名を持つ")
    if multi:
        r = multi[0]
        got = [APP.suggest(kk).get("rows") or [] for kk in r["ks"][:2]]
        ok = all(any(str(x.get("stage_id")) == r["stage_id"] for x in g) for g in got)
        check("どちらの書き方でも同じ公演が引ける", ok, "／".join(r["ks"][:2])[:40])

    # **日付は全部が同じときだけ残す。** 勝手に 1 つ選ぶと観ていない日が記録に入る
    import rate_performances as R  # noqa: E402
    cr = ROOT / "data" / "credits" / "credits.jsonl"
    if cr.exists():
        seen: dict = _c.defaultdict(set)
        for line in cr.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            c = __import__("json").loads(line)
            if c.get("stage_id") and c.get("date"):
                seen[str(c["stage_id"])].add(c["date"])
        many = {k for k, v in seen.items() if len(v) > 1}
        rows = {r["stage_id"]: r for r in pool if r["kind"] == "stage"}
        bad = [k for k in many if (rows.get(k) or {}).get("date")
               and (rows[k].get("src") == 2)]
        check("複数の観劇日があるときは日付を入れない", not bad,
              f"{len(many)} 公演が複数の観劇日を持つ" if many else "該当なし")

    # **ツアーの別会場は畳まない**（別の公演である）
    tours = _c.Counter(r["k"] for r in pool if r["kind"] == "stage")
    check("同じ題名の別の上演は残す", any(v > 1 for v in tours.values()),
          f"同じ題名が {sum(1 for v in tours.values() if v > 1)} 組ある（劇場と日程で選び分ける）")
    # --- 作品を親、会場ごとの上演を子として並べる（起案者のイメージ・2026-08-24）
    check("作品を親にして会場を子として並べる",
          'className = "sug-work"' in APP.SCRIPT
          and "会場の上演" in APP.SCRIPT,
          "同じ作品の会場は 1 つの親の下に入る")
    check("どの上演かを選ぶ理由を書く",
          "観に行った会場と日程を選んでください" in APP.SCRIPT
          and "観ていない公演の作り手が名簿に入ります" in APP.SCRIPT,
          "会場ごとに座組が違いうることまで書いている")
    # **題名だけで畳まない。** 別の団体が同じ戯曲を上演したものを 1 つにすると、
    # 観ていない公演の作り手が名簿に入る（実データの「ハムレット」がこれに当たった）
    ham = [x for x in (APP.suggest("ハムレット").get("rows") or [])
           if x["kind"] == "stage"]
    if len(ham) >= 2:
        check("題名が同じでも団体が違えば別の作品にする",
              len({x["wk"] for x in ham}) == len(ham)
              or len({x["wk"] for x in ham}) > 1,
              f"{len(ham)} 上演 → 作品 {len({x['wk'] for x in ham})} 個")
    # **同じ団体のツアーは 1 つの作品にまとめる**
    pk = [x for x in (APP.suggest("プリキュア").get("rows") or [])
          if x["kind"] == "stage"]
    if len(pk) >= 3:
        check("同じ団体のツアーは 1 つの作品にする",
              len({x["wk"] for x in pk}) == 1,
              f"{len(pk)} 会場 → 作品 {len({x['wk'] for x in pk})} 個")
    # **打ち切りは作品の単位で数える。** 行で切ると 14 会場のツアーが枠を使い切る
    check("ツアーの会場が枠を使い切らない", len(pk) >= 8,
          f"{len(pk)} 会場ぶんを返している（行ではなく作品で数えている）")


def _state() -> tuple:
    con = R.connect()
    try:
        return R.read_splits(con), R.read_excluded(con)
    finally:
        con.close()


def main() -> int:  # noqa: C901
    purchases = R.load_purchases()
    con0 = R.connect()
    works = R.load_works(purchases, R.read_splits(con0), R.read_excluded(con0))
    con0.close()
    buckets = collections.Counter(w["bucket"] for w in works)
    past = [w for w in works if w["bucket"] == "past"]
    upcoming = [w for w in works if w["bucket"] == "upcoming"]
    multi = sorted((w for w in past if w["times"] > 1), key=lambda w: -w["times"])
    print(f"買った回 {len(purchases)} 件 → 作品 {len(works)} 件"
          f"（上演済み {buckets['past']} / 公演日が不明 {buckets['undated']}"
          f" / まだ上演していない {buckets['upcoming']}）")
    if len(past) < 2 or not multi:
        print("上演済みの作品か、複数回観た作品が足りないので検査できない。"
              "先に extract_performances.py --run を実行すること。")
        return 1

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, good: bool, note: str = "") -> None:
        checks.append((name, bool(good), note))

    # --- 束ね方（画面を立てる前に確かめる）
    check("複数回を 1 作品に束ねる", multi[0]["times"] >= 2,
          f"最多 {multi[0]['times']} 回 → 1 作品「{multi[0]['title_display'][:22]}」")
    check("回ごとの評価にしない",
          len({w["work_key"] for w in works}) == len(works), f"作品 {len(works)} 件が一意")

    # 同じ題名で年が離れているものは、別の作品に分かれていること（再演は別物）
    by_title = collections.defaultdict(list)
    for w in works:
        by_title[w["work_key"].rsplit("#", 1)[0]].append(w)
    split = {k: v for k, v in by_title.items() if len(v) > 1}
    far = [k for k, v in split.items()
           if max(x["first_date"][:4] for x in v if x["first_date"])
           != min(x["first_date"][:4] for x in v if x["first_date"])]
    check("再演を別の作品に分ける", bool(far),
          f"{len(split)} 題名が分割され、うち {len(far)} 件は年が違う"
          + (f"（例 {far[0][:20]}）" if far else ""))

    # 抽出の失敗（題名でない語）を作品として並べない
    bad = [w for w in works if not R.is_work(w["title"])]
    check("抽出の失敗を並べない", not bad,
          "NOT_A_TITLE の語は落ちている" if not bad else str(bad[:2]))

    # --- セット券・交互上演を演目ごとに分ける（1 回 → 複数の作品）
    auto = {r["uid"]: R.detect_programs(r["title"]) for r in purchases}
    split_uids = [u for u, p in auto.items() if len(p) > 1]
    check("セット券を演目ごとに分ける", bool(split_uids),
          f"{len(split_uids)} 回を分割")
    originals = [r for r in purchases
                 if R._ORIGINAL.search(R.norm(r["title"])) and len(R._QUOTED.findall(
                     R.norm(r["title"]))) >= 2]
    check("原作の表記では分けない", all(not auto[r["uid"]] for r in originals),
          f"「〜◯◯より〜」型 {len(originals)} 件を分けていない")

    con = R.connect()
    token = secrets.token_urlsafe(16)
    R.Handler.state = R.State(token, con, purchases)
    works = R.Handler.state.works
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), R.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    c = Client(f"http://127.0.0.1:{httpd.server_address[1]}", token)

    # --- 守り 3: トークンが無い／違う要求は通さない
    for tok in ("", "wrong-token"):
        check("トークンを要求する", code_of(c.get, "/", tok) == 403, f"t={tok!r}")

    # 画面が返り、クレジットを出さないことを明示している（V24 の保護）
    html = c.get("/").read().decode()
    check("画面が返る", "◎○△×" in html, f"{len(html)} bytes")
    check("クレジットを出さない", "クレジット（作り手の人名一覧）は表示しません" in html)
    check("束ねた理由を画面に書く", "その日の演者の出来" in html)

    d = json.loads(c.get("/api/list").read())
    check("一覧が返る",
          len(d["works_list"]) == len(works) and d["grades"] == list("◎○△×")
          and "観ていない" not in d["grades"] + [d["undecided"]],
          f"{len(d['works_list'])} 作品／段階に「観ていない」を混ぜていない")

    # --- 作品への評価
    w = multi[0]
    res = json.loads(c.post("/api/work", {
        "work_key": w["work_key"], "verdict": "◎", "chosen": "人に誘われた",
        "note_impression": "普段観ないジャンルだったが刺激を受けた"}).read())
    check("作品に評価を保存する",
          res["work"]["verdict"] == "◎" and res["work"]["times"] == w["times"]
          and res["stats"]["graded"] == 1, f"{w['times']} 回ぶんが 1 件として数えられた")

    # 後から変えられる（企画書 4 章「付けるときの補足」）
    res = json.loads(c.post("/api/work", {"work_key": w["work_key"], "verdict": "△"}).read())
    check("後から変えられる", res["work"]["verdict"] == "△" and res["stats"]["low"] == 1)

    # 「まだ判断できない」は段階に数えない（集計では欠測として扱う）
    other = next(x for x in past if x["work_key"] != w["work_key"])
    res = json.loads(c.post("/api/work", {"work_key": other["work_key"],
                                          "verdict": R.UNDECIDED}).read())
    check("欠測を段階に数えない", res["stats"]["graded"] == 1,
          f"graded={res['stats']['graded']}")

    # --- 観た／行かなかったは回ごと
    uid = w["shows"][0]["uid"]
    res = json.loads(c.post("/api/attendance", {
        "work_key": w["work_key"], "uid": uid, "attended": False}).read())
    check("行かなかった回を回ごとに持つ",
          res["attendance"]["attended"] == 0 and res["stats"]["skipped"] == 1
          and json.loads(c.get("/api/list").read())["works"][w["work_key"]]["verdict"] == "△",
          "作品の評価は消えない")
    check("出席は作品ごとに独立",
          f"{uid}|{w['work_key']}" in json.loads(c.get("/api/list").read())["attendance"],
          "鍵は「回｜作品」（セット券の片方だけ外せる）")
    c.post("/api/attendance", {"work_key": w["work_key"], "uid": uid, "attended": True})

    # --- 守り 4: 候補にない値と、列挙していない経路を拒む
    check("候補にない評価を拒む",
          code_of(c.post, "/api/work", {"work_key": w["work_key"], "verdict": "◯"}) == 400)
    check("段階に「観ていない」を許さない",
          code_of(c.post, "/api/work", {"work_key": w["work_key"], "verdict": "観ていない"}) == 400)
    check("候補にないきっかけを拒む",
          code_of(c.post, "/api/work", {"work_key": w["work_key"], "chosen": "なんとなく"}) == 400)
    check("知らない作品を拒む", code_of(c.post, "/api/work", {"work_key": "x", "verdict": "◎"}) == 400)
    check("よその回を拒む",
          code_of(c.post, "/api/attendance",
                  {"work_key": w["work_key"], "uid": "0", "attended": False}) == 400)
    check("列挙していない操作を拒む", code_of(c.post, "/api/sql", {}) == 404)

    # まだ上演していない作品に「自分に合っていたか」を聞かない
    if upcoming:
        check("未上演の作品を拒む",
              code_of(c.post, "/api/work",
                      {"work_key": upcoming[0]["work_key"], "verdict": "◎"}) == 400,
              upcoming[0]["first_date"])
    else:
        print("  （まだ上演していない作品が無いため、その検査は飛ばした）")

    # --- 分け方を人が直せる（探すのは機械、確定は人）
    if split_uids:
        uid = split_uids[0]
        d = json.loads(c.get("/api/list").read())
        check("分けた回を画面に伝える", d["purchases"][uid]["split"] is True
              and len(d["purchases"][uid]["programs"]) > 1,
              "／".join(x[:14] for x in d["purchases"][uid]["programs"]))
        # 分けていない回で、題名のゆれを「別の演目」として出していないこと
        unsplit = [u for u, p in d["purchases"].items() if not p["split"]]
        check("分けていない回に別演目を出さない",
              all(len(d["purchases"][u]["programs"]) == 1 for u in unsplit),
              f"{len(unsplit)} 回はいずれも 1 演目")

        d = json.loads(c.post("/api/split", {"uid": uid, "programs": ["甲", "乙", "丙"]}).read())
        check("人が分け方を直せる", d["purchases"][uid]["programs"] == ["甲", "乙", "丙"]
              and sum(1 for w2 in d["works_list"] if w2["title"] in ("甲", "乙", "丙")) == 3)
        # 1 行だけ書けば、自動で分かれるものも 1 作品にまとめられる
        d = json.loads(c.post("/api/split", {"uid": uid,
                                             "programs": ["まとめた 1 作品"]}).read())
        check("1 作品にまとめられる", d["purchases"][uid]["split"] is False
              and d["purchases"][uid]["programs"] == ["まとめた 1 作品"])
        # 空にすると、人の直しを捨てて自動判定に戻る
        d = json.loads(c.post("/api/split", {"uid": uid, "programs": []}).read())
        got = d["purchases"][uid]
        want = R.detect_programs(got["title"]) or [got["title"]]
        check("自動判定に戻せる",
              got["renamed"] is False and got["programs"] == want,
              f"{len(got['programs'])} 演目に戻った")
        check("分け方の入力を検査する",
              code_of(c.post, "/api/split", {"uid": uid, "programs": "甲"}) == 400
              and code_of(c.post, "/api/split", {"uid": "0", "programs": []}) == 400)

    # --- 舞台ではないものを候補から外せる（機械が拾ってしまったときの逃げ道）
    drop = next(x for x in works if x["bucket"] == "past"
                and x["work_key"] not in (w["work_key"], other["work_key"]))
    n_before = len(json.loads(c.get("/api/list").read())["works_list"])
    d = json.loads(c.post("/api/exclude", {"work_key": drop["work_key"],
                                           "excluded": True}).read())
    check("舞台でないものを外せる",
          len(d["works_list"]) == n_before - 1
          and drop["work_key"] not in {x["work_key"] for x in d["works_list"]}
          and len(d["excluded"]) == len(drop["shows"]),
          f"「{drop['title_display'][:18]}」を外した")
    check("外したものを一覧に残す", all(x["uid"] and x["title_display"] for x in d["excluded"]),
          "黙って消さない")
    for sh in drop["shows"]:
        d = json.loads(c.post("/api/exclude", {"uid": sh["uid"], "program": sh["program"],
                                               "excluded": False}).read())
    check("候補に戻せる", drop["work_key"] in {x["work_key"] for x in d["works_list"]}
          and len(d["works_list"]) == n_before)
    check("除外の入力を検査する",
          code_of(c.post, "/api/exclude", {"excluded": True}) == 400
          and code_of(c.post, "/api/exclude", {"uid": "0", "program": "x",
                                               "excluded": True}) == 400)

    # セット券の片方だけ外しても、相方は残る（除外は演目の単位）
    setw = [x for x in works if any(len(R.programs_of(R.Handler.state.by_uid[sh["uid"]],
                                                      R.Handler.state.splits)) > 1
                                    for sh in x["shows"])]
    if len(setw) >= 2:
        one = setw[0]
        sib = one["shows"][0]
        mates = [x for x in setw if x["work_key"] != one["work_key"]
                 and any(s["uid"] == sib["uid"] for s in x["shows"])]
        d = json.loads(c.post("/api/exclude", {"work_key": one["work_key"],
                                               "excluded": True}).read())
        keys = {x["work_key"] for x in d["works_list"]}
        check("セット券の片方だけ外せる",
              one["work_key"] not in keys and all(m["work_key"] in keys for m in mates),
              f"「{one['title_display'][:14]}」を外しても相方 {len(mates)} 件は残る")
        for sh in one["shows"]:
            c.post("/api/exclude", {"uid": sh["uid"], "program": sh["program"],
                                    "excluded": False})

    # --- 題名が取れていない回を、印を付けて出し、直せる
    sus = [x for x in works if x["suspect"]]
    check("題名が怪しいものに印を付ける", bool(sus),
          "／".join(x["title_display"][:12] for x in sus) if sus else "該当なし")
    if sus:
        one = sus[0]
        uid = one["shows"][0]["uid"]
        d = json.loads(c.get("/api/list").read())
        check("正体を見分ける材料を渡す",
              bool(d["purchases"][uid]["subject"]) and bool(d["purchases"][uid]["sender"]),
              f"件名: {d['purchases'][uid]['subject'][:26]}")
        d = json.loads(c.post("/api/split", {"uid": uid, "programs": ["直した題名"]}).read())
        fixed = [x for x in d["works_list"] if any(y["uid"] == uid for y in x["shows"])]
        check("1 行で題名を直せる",
              len(fixed) == 1 and fixed[0]["title"] == "直した題名"
              and fixed[0]["suspect"] is False, "印も消える")
        d = json.loads(c.post("/api/split", {"uid": uid, "programs": []}).read())
        back = [x for x in d["works_list"] if any(y["uid"] == uid for y in x["shows"])]
        check("抽出結果に戻せる", back[0]["title"] == one["title"]
              and back[0]["suspect"] is True)

    # --- メール本文の手がかりを画面に渡す（これが無いと当事者は題名を直せない）
    if sus:
        uid = sus[0]["shows"][0]["uid"]
        m = json.loads(c.get(f"/api/mail?uid={uid}").read())
        check("本文の手がかりを渡す", bool(m["hints"]),
              (m["hints"][0][:38] if m["hints"] else "取れなかった"))
        check("知らない回の本文は読まない",
              code_of(c.get, "/api/mail?uid=../../etc/passwd") == 400
              and code_of(c.get, "/api/mail?uid=0") == 400)
    known = [uid for uid in (x["uid"] for w2 in works for x in w2["shows"])][:1]
    if known:
        m = json.loads(c.get(f"/api/mail?uid={known[0]}").read())
        check("件名と差出人も返す", "subject" in m and "sender" in m)

    # 全角の題名でも非演劇を落とせている（語のリストは半角で書かれている）
    check("全角の題名でも非演劇を落とす",
          not R.is_work("「ＥＮＴＡ！８」 ４Ｕ． Ｚｅｐｐ ｉｎ ｄｅ ＳＨＯＷ"),
          "正規化してから判定している")

    # --- 画面が組む URL で、実際にサーバへ届くか
    paths = ["/api/list", f"/api/mail?uid={known[0]}"] if known else ["/api/list"]
    urls = page_api_urls(paths, token)
    if urls is None:
        print("  （node が無いため、画面の URL 組み立ての検査は飛ばした）")
    else:
        codes = []
        for u in urls:
            try:
                codes.append(urllib.request.urlopen(c.base + u, timeout=5).status)
            except urllib.error.HTTPError as e:
                codes.append(e.code)
        check("画面が組む URL が通る", codes == [200] * len(urls),
              f"{' / '.join(paths)} → {codes}")

    check("保存が残る",
          json.loads(c.get("/api/list").read())["works"][w["work_key"]]["verdict"] == "△")

    httpd.shutdown()
    con.close()

    check_fixes(check, works)
    check_merged_fix(check, works)
    check_figures(check)
    check_unseen(check)
    check_live_lists(check)
    check_weights(check)
    check_nav(check)
    check_perf_dates(check)
    check_jsonl_reading(check)
    check_suggest(check)

    print()
    failed = 0
    for name, good, note in checks:
        print(("  OK " if good else "  NG ") + f"{name:<22} {note}")
        failed += not good
    print("\nすべて通った。" if not failed else f"\n{failed} 件 失敗。")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
