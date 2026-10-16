#!/usr/bin/env python3
"""公演のポスター（チラシ）画像を端末内に取り込み、画面に出せるようにする。

## なぜ端末内に置くのか

**画面から外部サイトを叩かない**（企画書 5 章の守り 5）。画像の URL をそのまま
`<img src>` に書くと、**一覧を開くたびにブラウザが外部へ 1 件ずつ要求を出す** ──
取得の範囲と間隔（1 リクエスト／秒）を 1 か所で守るという方針が崩れ、
どの公演を見たかが相手のサーバに残る。

**そこで、取り込みは更新の段で行い、画面には端末内の道（`/img/<id>`）だけを書く。**

## どこから取るか

CoRich の公演ページに `stage-image.corich.jp/img_stage/l/…/stage_NNNN.jpg` の形で
入っている。**ページはすでにキャッシュしてあるので、画像の URL を得るのに追加の
要求は要らない**（`data/credits/pages/`）。

**`nophoto_stage.png` は取り込まない。** 画像が無いことを表す共通の画像なので、
これを保存すると「ポスターがある」と「無い」の区別が付かなくなる。
"""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))
import polite_http as PH                                   # noqa: E402  取得の作法（名乗り・robots.txt・間隔）

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "data" / "credits" / "pages"
IMG = ROOT / "data" / "review" / "img"
CREDITS = ROOT / "data" / "credits" / "credits.jsonl"

# **画面に出す幅まで縮める。** 元の画像は 1 枚 300KB〜1.3MB あり、1 ページに 30 枚出すと
# 9MB を読み込むことになる ── 開いた瞬間に固まるので、体験として成立しない。
#
# **Pillow が無い環境でも動くようにする。** `tools/README.md` の方針（標準ライブラリだけで
# 動かす）を崩さないため、**無ければ縮めずにそのまま置く** ── 遅くなるが壊れない。
MAX_W = 360
JPEG_Q = 82

SRC_RE = re.compile(r"https://stage-image\.corich\.jp/img_stage/([lm])/\d+/stage_\d+\.(jpg|jpeg|png)")
UA = PH.UA


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", re.sub(r"[\s　『』「」]", "", s or "")).lower()


def page_of(stage_id) -> Path:
    return PAGES / f"https___stage_corich_jp_stage_{stage_id}.html"


def poster_url(stage_id) -> str:
    """キャッシュ済みのページから画像の URL を取り出す。無ければ空。大きい版（l）を優先する。"""
    f = page_of(stage_id)
    if not f.exists():
        return ""
    h = f.read_text(encoding="utf-8", errors="ignore")
    best = ""
    for m in SRC_RE.finditer(h):
        if "nophoto" in m.group(0):
            continue
        if m.group(1) == "l":
            return m.group(0)
        best = best or m.group(0)
    return best


def have() -> dict[str, str]:
    """取り込み済みのポスター。stage_id → ファイル名。"""
    IMG.mkdir(parents=True, exist_ok=True)
    return {f.stem: f.name for f in IMG.iterdir() if f.is_file()}


def uploaded() -> dict[str, str]:
    """R2 に入れ終えたポスター（stage_id → ファイル名）。`cloudflare/scripts/deliver_posters.py` が書く。

    **R2 にあるものは取り直さない。** 入れ終えた分は作業データ（state ブランチ）に残さない
    （crawler_state.py）ので、手元のファイルだけを見ると毎回すべて取り直すことになる
    （docs/knowledge の dec-posters-r2）。"""
    p = ROOT / "data" / "r2" / "posters.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except ValueError:
        return {}


def fetch(stage_ids, *, sleep: float = 0.0, limit: int = 0) -> dict[str, int]:
    """まだ無いものだけ取り込む。**間隔（同じホストに 1.1 秒に 1 回）は polite_http が守る。**"""
    IMG.mkdir(parents=True, exist_ok=True)
    got = {**uploaded(), **have()}
    n = {"済み": len(got), "取得": 0, "画像なし": 0, "失敗": 0}
    todo = [s for s in dict.fromkeys(str(x) for x in stage_ids) if s and s not in got]
    if limit:
        todo = todo[:limit]
    for i, sid in enumerate(todo, 1):
        url = poster_url(sid)
        if not url:
            n["画像なし"] += 1
            continue
        ext = ".jpg" if url.rstrip("0123456789?").endswith((".jpg", ".jpeg")) or ".jpg" in url else ".png"
        try:
            data = PH.fetch(url, timeout=20, max_bytes=12_000_000)   # 作法は polite_http
            (IMG / f"{sid}{ext}").write_bytes(data)
            shrink(IMG / f"{sid}{ext}")
            n["取得"] += 1
        except Exception:                                            # noqa: BLE001
            n["失敗"] += 1
        if i % 25 == 0:
            print(f"    ポスター {i}/{len(todo)}", flush=True)
        time.sleep(sleep)
    return n


def shrink(path: Path) -> bool:
    """幅 MAX_W まで縮めて上書きする。**Pillow が無ければ何もしない。**"""
    try:
        from PIL import Image
    except ImportError:
        return False
    try:
        with Image.open(path) as im:
            if im.width <= MAX_W:
                return False
            h = round(im.height * MAX_W / im.width)
            im = im.convert("RGB").resize((MAX_W, h), Image.LANCZOS)
            im.save(path.with_suffix(".jpg"), "JPEG", quality=JPEG_Q, optimize=True)
        if path.suffix != ".jpg":
            path.unlink()
        return True
    except Exception:                                                # noqa: BLE001
        return False


def shrink_all() -> dict[str, int]:
    """すでに取り込んだ分をまとめて縮める（1 度だけ走らせる）。"""
    n = {"縮めた": 0, "そのまま": 0}
    for f in sorted(IMG.iterdir()):
        n["縮めた" if f.is_file() and shrink(f) else "そのまま"] += 1
    return n


def work_index() -> dict[str, list[tuple[str, str]]]:
    """日付 → [(正規化した件名, stage_id)]。**記録の画面でポスターを出すために要る。**"""
    by_date: dict[str, list[tuple[str, str]]] = {}
    if not CREDITS.exists():
        return {}
    for line in CREDITS.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        c = json.loads(line)
        by_date.setdefault(c.get("date") or "", []).append(
            (_norm(c.get("mail_title") or ""), str(c.get("stage_id") or "")))
    return by_date


def match(work_title: str, first_date: str, index: dict) -> str:
    """作品と日付から stage_id を引く。

    **日付が同じ行のうち題名が重なるものを採る。** 重ならなければ日付だけで決める
    ── 同じ日に 2 本観た場合はどちらかになるが、出すのはポスターなので致命的でない。
    """
    rows = index.get(first_date or "", [])
    t = _norm(work_title)
    for title, sid in rows:
        if title and (title in t or t in title or (len(t) >= 8 and t[:8] in title)):
            return sid
    return rows[0][1] if rows else ""


def candidate_ids() -> list[str]:
    """**手で足す欄の候補になる公演。** 一覧に出るかどうかとは別に、選ぶときに絵が要る。

    起案者の指示（2026-08-24）──「手で足すとき検索した候補、できればポスター画像も
    ほしい」。**同じ題名の公演が並ぶことがある**（再演・ツアー・同じ戯曲の別上演）ので、
    文字だけだと日付と劇場を読み比べないと選べない。

    **画像の URL は控えたページから取れるので、追加の要求は要らない**（`poster_url`）。
    実測（2026-08-24）── 候補 818 件はすべてページの控えを持っており、そのうち画像を
    取り込み済みなのは 172 件だった。**残りを取るのに約 11 分かかるので、月 1 回の
    `--fetch` のときだけ取る**（候補の一覧が入れ替わるのもそのときである）。
    """
    ids: list[str] = []
    for f in (ROOT / "data" / "review" / "candidates.jsonl",
              ROOT / "data" / "credits" / "linked.jsonl"):
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            c = json.loads(line)
            if c.get("stage_id"):
                ids.append(str(c["stage_id"]))
    return ids


def main(all_candidates: bool = False) -> int:
    """更新の段から呼ぶ。**ふだんは、いま画面に出るものだけ取り込む**（全件は取らない）。

    `all_candidates` は月 1 回の `--fetch` のときだけ真になる（`candidate_ids`）。
    """
    sys.path.insert(0, str(ROOT / "tools" / "review"))
    ids: list[str] = []
    rec = ROOT / "data" / "review" / "recommend2.json"
    if rec.exists():
        d = json.loads(rec.read_text(encoding="utf-8"))
        # **`ranked`（順位の付いた全件）も取る。** 都道府県で絞ると、全国の上位 15 件に
        # 入っていない公演がカードとして出る ── 上位 15 件だけを取り込むと、
        # **絞り込んだ利用者にだけポスターの無い一覧を出すことになる。**
        # 他会場のぶんも取る ── 絞り込むと、その会場が主たる会場としてカードに出る
        for k in ("recommend", "ranked", "favourites", "tracking", "owned"):
            for c in (d.get(k) or []):
                ids.append(str(c["stage_id"]))
                ids += [str(t["stage_id"]) for t in (c.get("tours") or [])]
    for rows in work_index().values():
        ids += [sid for _t, sid in rows]
    if all_candidates:
        ids += candidate_ids()
    n = fetch(ids)
    print("ポスター ── " + "／".join(f"{k} {v}" for k, v in n.items()))
    return 0


# ---------------------------------------------------------------- 過去の公演
# 起案者の指示（2026-10-16）「過去の公演の全てのポスターデータも欲しい」。過去の公演の一覧
# （data/past/stages.jsonl、fetch_past_stages.py が作る。2019 年以降）は、ページの HTML を残さないので
# 画像の URL が手元に無い。これから読むページは行に `poster`（画像の URL）を残す。それより前に読んだ行は、
# ページを読み直して URL だけを data/past/poster_urls.json に控える（1 公演 1 回だけ）。
# - 公演ページ（stage.corich.jp）と画像（stage-image.corich.jp）は別のホストなので、polite_http の
#   「同じホストへ 1.1 秒に 1 回」を守ったまま交互に読める（1 公演およそ 1.2 秒）
# - 同じ画像（ツアーの各会場など）は 1 回だけ取り、ほかの公演には写しを置く
# - 時間の上限（--max-minutes）で止め、次の回は続きから（取り込んだ・控えたものは飛ばす）
# - R2 と D1 へは、これまでどおり deliver_posters.py が無料枠の控えを見ながら入れる
PAST_ROWS = ROOT / "data" / "past" / "stages.jsonl"
PAST_URLS = ROOT / "data" / "past" / "poster_urls.json"


def past_rows() -> list[dict]:
    """過去の公演（上演の新しい順）。"""
    if not PAST_ROWS.exists():
        return []
    rows = []
    for line in PAST_ROWS.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    rows.sort(key=lambda r: (r.get("start") or "", str(r.get("stage_id") or "")), reverse=True)
    return rows


def url_in(html: str) -> str:
    """ページの HTML から画像の URL（大きい版を優先。nophoto は無し）。"""
    best = ""
    for m in SRC_RE.finditer(html or ""):
        if "nophoto" in m.group(0):
            continue
        if m.group(1) == "l":
            return m.group(0)
        best = best or m.group(0)
    return best


def fetch_past(*, max_minutes: float = 0, limit: int = 0, page=None, image=None, rows=None) -> dict[str, int]:
    """過去の公演のポスターを取り込む。`page(sid) -> html`・`image(url) -> bytes` は試験で差し替える。"""
    page = page or (lambda sid: PH.fetch(f"https://stage.corich.jp/stage/{sid}", timeout=45).decode("utf-8", "replace"))
    image = image or (lambda url: PH.fetch(url, timeout=20, max_bytes=12_000_000))
    IMG.mkdir(parents=True, exist_ok=True)
    urls = json.loads(PAST_URLS.read_text(encoding="utf-8")) if PAST_URLS.exists() else {}
    got = {**uploaded(), **have()}
    by_url = {}                                    # 今回取った画像の URL → ファイル
    n = {"済み": 0, "取得": 0, "写し": 0, "画像なし": 0, "ページ": 0, "失敗": 0}
    t0 = time.monotonic()
    done = 0
    try:
        for r in (rows if rows is not None else past_rows()):
            sid = str(r.get("stage_id") or "")
            if not sid:
                continue
            if sid in got:
                n["済み"] += 1
                continue
            if max_minutes and (time.monotonic() - t0) / 60 > max_minutes:
                print(f"時間の上限（{max_minutes} 分）に来たので、ここまでにする")
                break
            if limit and done >= limit:
                break
            done += 1
            url = r["poster"] if "poster" in r else urls.get(sid)
            if url is None:
                try:
                    url = url_in(page(sid))
                except PH.Skipped as e:            # ホストから手を引いた（robots.txt・429 が続いた等）
                    print(f"取得をやめる: {e}")
                    break
                except Exception:                  # noqa: BLE001  消えたページ・一時的な失敗は次の回に
                    n["失敗"] += 1
                    continue
                urls[sid] = url
                n["ページ"] += 1
            if not url:
                n["画像なし"] += 1
                continue
            ext = ".png" if url.endswith(".png") else ".jpg"
            if url in by_url:
                src = by_url[url]
                (IMG / f"{sid}{src.suffix}").write_bytes(src.read_bytes())
                got[sid] = f"{sid}{src.suffix}"
                n["写し"] += 1
                continue
            try:
                (IMG / f"{sid}{ext}").write_bytes(image(url))
            except PH.Skipped as e:
                print(f"取得をやめる: {e}")
                break
            except Exception:                      # noqa: BLE001
                n["失敗"] += 1
                continue
            shrink(IMG / f"{sid}{ext}")
            f = next((x for x in IMG.glob(f"{sid}.*")), IMG / f"{sid}{ext}")
            by_url[url] = f
            got[sid] = f.name
            n["取得"] += 1
            if n["取得"] % 50 == 0:
                print(f"    過去のポスター {n['取得']} 枚", flush=True)
    finally:
        PAST_URLS.parent.mkdir(parents=True, exist_ok=True)
        PAST_URLS.write_text(json.dumps(urls, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return n


def cli() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shrink-existing", action="store_true",
                    help="すでに取り込んだ画像をまとめて縮める")
    ap.add_argument("--all-candidates", action="store_true",
                    help="手で足す欄の候補になる公演のぶんも取り込む（月 1 回・約 11 分）")
    ap.add_argument("--past", action="store_true",
                    help="過去の公演（data/past/stages.jsonl）のポスターを、上演の新しい順に取り込む")
    ap.add_argument("--max-minutes", type=float, default=0, help="--past の時間の上限（分）")
    a = ap.parse_args()
    if a.past:
        if a.max_minutes <= 0:
            print("過去のポスター ── 今日は時間の割り当てが無いので取らない")
            return 0
        print("過去のポスター ── " + "／".join(f"{k} {v}" for k, v in fetch_past(max_minutes=a.max_minutes).items()))
        return 0
    if a.shrink_existing:
        print("ポスターを縮めた ── " + "／".join(f"{k} {v}" for k, v in shrink_all().items()))
        return 0
    return main(all_candidates=a.all_candidates)


if __name__ == "__main__":
    raise SystemExit(cli())
