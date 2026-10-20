#!/usr/bin/env python3
"""過去の公演の一覧を、CoRich の公演ページから少しずつ作る（記録を自動で結び付けるため）。

    python3 tools/review/fetch_past_stages.py --limit 6000 --since 2019-01-01
    python3 tools/review/fetch_past_stages.py --report

## なぜ要るのか

起案者の指示（2026-10-13）「いちいち結びつけなくても、過去の公演の情報紐づいてほしい」。
記録（観た日・題名）を公演ページに結び付けると、出演者・作り手・あらすじが記録に付き、
おすすめの材料にもなる。ところが手元にある公演の一覧は「これから」と「終わって 180 日以内」
（candidates.jsonl）だけで、それより古い公演は照合の相手がいない（docs/knowledge の
auto-link-current-state）。CoRich の検索ページはデータセンターからは断られる（corich-search-waf-403）
ので、サイトマップに載っている公演ページの番号を **新しいほうから** 1 枚ずつ読む。

## 決めたこと（q-auto-link-past・起案者の指示「2019年以降、1日6000件で進めて」）

- **範囲は 2019 年以降。** 番号は登録の順なので新しいほうから読み、会期の終わりが `--since` より前の
  ページが続けて `--stop-after` 枚出たら読み終わりとする（古い公演があとから登録されることもあるので、
  1 枚で止めない）
- **1 回に読むのは `--limit` 枚（既定 6,000）。** 取得の作法は polite_http（名乗り・robots.txt・
  同じホストへ 1.1 秒の間隔）に任せる。6,000 枚でおよそ 110 分
- **手元に置くのは照合とおすすめに要る分だけ:** 題名・会期・劇場・団体・都道府県と、出演・作り手の欄。
  **ページの HTML は残さない**（fetch_credits.get はページを data/credits/pages に溜めるが、ここでは
  使わない ── 数万枚を作業データに積むと state ブランチが膨らむ）。外へは配らない
  （catalog-terms-no-redistribution）
- 1 回で読み切れなくても、読んだところまでは `progress.json` に残る（途中で止まっても続きから読む）

## あらすじ（2 周目、起案者の指示 2026-10-18「サービス化するなら全件読み直さないとだめだよね？」「claude でやろう」）

一覧を読み終えたら（`done`）、同じ段・同じ時間の枠で、**一覧の公演ページを新しい順にもう一度 1 枚ずつ読み**、
本文（`extract_theme_llm.corich_text` と同じ切り出し）を**あらすじの読み取り待ち**（`synopsis_queue.jsonl`、
side `past`）に積む。読むのは起案者の Claude（`--print-queue`→`--import-answers`、本文に実在するかを検査）。
- **ページも本文も手元に溜めない。** 待ちに積むだけで、読んだら待ちから消える。待ちが `STORY_QUEUE_MAX` 件を
  越えたら、その日は積まない（読む速さより速く積まない。state ブランチを膨らませない）
- 本文が `MIN_STORY_TEXT` 字未満の公演は、読まずに「本文が短い」（model `rule`）として題材の表に残す
- すでに題材の表にある公演（これからの公演だったときに読んだもの）は読み直さない
- 進み具合は `progress.json` の `story_line`（一覧の何行目まで済んだか）。一覧は新しい順に足されるので、新しい公演から進む

## 作るもの

- `data/past/stages.jsonl` ── 1 公演 1 行（追記）。`{stage_id, title, period, start, end, group,
  theater, pref, fields}`。`start`・`end` は YYYY-MM-DD
- `data/past/progress.json` ── `{cursor, top, done, old_streak, read, skipped, updated}`。
  `cursor` は次に読む番号の上限（これより小さい番号を読む）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools" / "credits"))
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_credits as FC                           # noqa: E402
import polite_http as PH                             # noqa: E402

PAST = ROOT / "data" / "past"
ROWS = PAST / "stages.jsonl"
PROGRESS = PAST / "progress.json"
CANDIDATES = ROOT / "data" / "review" / "candidates.jsonl"
STORY_SIDE = "past"
STORY_SHARE = 0.4          # 一覧を読み終える前は、その日の時間の 4 割をあらすじに回す（最近の公演のあらすじから先に揃える）
# 前に取った行の題名に冠名・サブタイトルを足すため、読み直す時間の割合（起案者の指示 2026-10-20「過去の公演もお願いします」、
# dec-title-crown-subtitle）。あらすじの 2 周目で読むページはそのついでに直すので、ここで読むのは 2 周目が通り過ぎた行だけ。
# 読み直す行が無くなれば 0（その日の時間はもとの割り当てに戻る）。Actions の分数は増えない（Plan の段の past_minutes の中）
RETITLE_SHARE = 0.3
STORY_QUEUE_MAX = 6_000     # 読み取り待ちの上限（1 件およそ 5〜7 KB。state ブランチを 40 MB ほどまでにする。起案者のセッションが続けて読む）

# 照合とおすすめに使う欄だけを残す（料金・問い合わせなどは持たない）
KEEP_FIELDS = set(FC.ROLE_KEYS) | {"劇場", "スタッフ"}

_DATE = re.compile(r"(20\d\d)/(\d{1,2})/(\d{1,2})")


def span(period: str) -> tuple[str, str]:
    """会期の文字から (初日, 千秋楽) を YYYY-MM-DD で。読めなければ空文字。"""
    ds = []
    for y, m, d in _DATE.findall(period or ""):
        try:
            ds.append(date(int(y), int(m), int(d)).isoformat())
        except ValueError:
            continue
    if not ds:
        return "", ""
    return min(ds), max(ds)


def row_from_html(html: str, sid: str) -> dict:
    """公演ページ 1 枚から、手元に置く 1 行を作る（fetch_candidates.stage_row と同じ読み方）。"""
    import fetch_candidates as FCand
    c = FC.parse_stage(html, sid)
    f = c["fields"]
    mp = re.search(r'<span class="pref">(.*?)</span>', html, re.S)
    theater = re.sub(r"\(.*?\)$", "", FCand.pick(html, "theater")).strip()
    period = re.sub(r"\s*\([^)]*\)", "", c["period"] or "").replace("～", "〜").strip()
    start, end = span(period)
    import unicodedata
    return {
        "stage_id": str(sid),
        # 題名は冠名・タイトル・サブタイトルをつなげたもの。照合の鍵はタイトルだけ（title_main、dec-title-crown-subtitle）
        "title": unicodedata.normalize("NFKC", c.get("full_title") or c["page_title"] or "").strip(),
        "title_main": unicodedata.normalize("NFKC", c["page_title"] or "").strip(),
        "period": period,
        "start": start,
        "end": end,
        "group": FCand.pick(html, "group"),
        "theater": theater or f.get("劇場", ""),
        "pref": FCand.txt(mp.group(1)).strip("()（）") if mp else "",
        "fields": {k: v for k, v in f.items() if k in KEEP_FIELDS and v},
        # ポスターの画像の URL（無ければ空）。ページは残さないので、ここで控える
        # （起案者の指示 2026-10-16「過去の公演の全てのポスターデータも欲しい」、posters.fetch_past）
        "poster": _poster_url(html),
    }


def titles_of(html: str, sid) -> tuple[str, str]:
    """公演ページの (冠名・サブタイトルを含めた題名, タイトルだけ)。NFKC（row_from_html と同じ）"""
    import unicodedata
    c = FC.parse_stage(html, str(sid))
    nf = lambda t: unicodedata.normalize("NFKC", t or "").strip()      # noqa: E731
    return nf(c.get("full_title") or c["page_title"]), nf(c["page_title"])


def apply_titles(titled: dict[str, tuple[str, str]]) -> int:
    """手元の一覧（ROWS）の題名を、読み直した題名に書き換える。行の順と数は変えない（配送は行の数で送った所を数える）。
    読めなかった公演（タイトルが空）は、もとの題名をタイトルとして控え、次から読み直さない"""
    if not titled or not ROWS.exists():
        return 0
    lines = ROWS.read_text(encoding="utf-8").split("\n")
    n = 0
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        r = json.loads(line)
        got = titled.get(str(r.get("stage_id") or ""))
        if not got or "title_main" in r:
            continue
        full, main = got
        if main:
            r["title"], r["title_main"] = full or main, main
        else:
            r["title_main"] = r.get("title") or ""
        lines[i] = json.dumps(r, ensure_ascii=False)
        n += 1
    tmp = ROWS.with_suffix(".part")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    tmp.replace(ROWS)
    return n


def retitle_targets(p: dict) -> int:
    """題名をまだ読み直していない行のうち、この段で読む行の数（2 周目が通り過ぎた行。2 周目が止まっていれば全部）。"""
    if not ROWS.exists():
        return 0
    lines = [l for l in ROWS.read_text(encoding="utf-8").split("\n") if l.strip()]
    end = len(lines) if p.get("story_blocked") else min(len(lines), int(p.get("story_line") or 0))
    return sum(1 for l in lines[:end] if "title_main" not in json.loads(l))


def retitle(p: dict, *, limit: int, max_minutes: float, fetch) -> dict:
    """前に取った行の題名を、公演ページを読み直して冠名・サブタイトル込みにする（dec-title-crown-subtitle）。"""
    lines = [l for l in ROWS.read_text(encoding="utf-8").split("\n") if l.strip()] if ROWS.exists() else []
    end = len(lines) if p.get("story_blocked") else min(len(lines), int(p.get("story_line") or 0))
    t0 = time.monotonic()
    titled: dict[str, tuple[str, str]] = {}
    got = {"retitled": 0, "skipped": 0}
    for line in lines[:end]:
        if len(titled) >= limit or (max_minutes and (time.monotonic() - t0) / 60 > max_minutes):
            break
        r = json.loads(line)
        sid = str(r.get("stage_id") or "")
        if not sid or "title_main" in r or sid in titled:
            continue
        try:
            titled[sid] = titles_of(fetch(int(sid)), sid)
        except PH.Skipped as e:
            print(f"取得をやめる: {e}")
            break
        except Exception as e:                    # 消えたページは、もとの題名のまま控える（読み直さない）
            titled[sid] = ("", "")
            got["skipped"] += 1
            print(f"{sid}: 読めなかった（{type(e).__name__}）")
    got["retitled"] = apply_titles(titled)
    got["left"] = retitle_targets(p)
    print(f"題名の読み直し: {got['retitled']} 件／読めなかった {got['skipped']} 件／残り {got['left']} 件")
    return got


def _poster_url(html: str) -> str:
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import posters
    return posters.url_in(html)


def load_progress() -> dict:
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    return {"cursor": None, "top": None, "done": False, "old_streak": 0, "read": 0, "skipped": 0}


def save_progress(p: dict) -> None:
    PAST.mkdir(parents=True, exist_ok=True)
    p["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tmp = PROGRESS.with_suffix(".part")
    tmp.write_text(json.dumps(p, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(PROGRESS)


def known_ids() -> set[str]:
    """もう手元にある公演（読んだ過去の公演と、毎日の一覧にある公演）。読み直さない。"""
    out: set[str] = set()
    for path in (ROWS, CANDIDATES):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                try:
                    out.add(str(json.loads(line).get("stage_id") or ""))
                except ValueError:
                    continue
    out.discard("")
    return out


def plan(ids: list[int], progress: dict, known: set[str], limit: int) -> list[int]:
    """今回読む番号（新しいほうから `limit` 枚）。`cursor` より小さく、まだ手元に無いもの。"""
    cur = progress.get("cursor")
    out = []
    for i in sorted(ids, reverse=True):
        if cur is not None and i >= cur:
            continue
        if str(i) in known:
            continue
        out.append(i)
        if len(out) >= limit:
            break
    return out


def run(ids: list[int], *, limit: int, since: str, stop_after: int, max_minutes: float,
        fetch=None) -> dict:
    """読む。`fetch(sid) -> html` は試験で差し替える。戻り値は今回の数え。"""
    fetch = fetch or (lambda sid: PH.fetch(f"{FC.BASE}/stage/{sid}", timeout=45).decode("utf-8", "replace"))
    p = load_progress()
    # 前に取った行の題名の読み直し（あれば時間の RETITLE_SHARE。dec-title-crown-subtitle）
    retitled = None
    if max_minutes and retitle_targets(p):
        rt_minutes, rt_limit = max_minutes * RETITLE_SHARE, int(limit * RETITLE_SHARE)
        max_minutes, limit = max_minutes - rt_minutes, limit - rt_limit
        retitled = retitle(p, limit=rt_limit, max_minutes=rt_minutes, fetch=fetch)
    if p.get("done"):
        got = stories(p, limit=limit, max_minutes=max_minutes, fetch=fetch)
        save_progress(p)
        return {"read": 0, "kept": 0, "skipped": 0, "done": True, "cursor": p.get("cursor"), "stories": got,
                **({"retitle": retitled} if retitled else {})}
    if p.get("top") is None and ids:
        p["top"] = max(ids)
    # 一覧を読み終える前も、時間の上限が決まっている実行（毎日の取得）では、残りの 4 割であらすじも進める
    share = STORY_SHARE if max_minutes else 0
    if share:
        story_minutes, max_minutes = max_minutes * share, max_minutes * (1 - share)
        story_limit, limit = int(limit * share), limit - int(limit * share)
    todo = plan(ids, p, known_ids(), limit)
    t0 = time.monotonic()
    got = {"read": 0, "kept": 0, "skipped": 0, "old": 0}
    PAST.mkdir(parents=True, exist_ok=True)
    with ROWS.open("a", encoding="utf-8") as out:
        for n, sid in enumerate(todo, 1):
            if max_minutes and (time.monotonic() - t0) / 60 > max_minutes:
                print(f"時間の上限（{max_minutes} 分）に来たので、ここまでにする")
                break
            try:
                html = fetch(sid)
            except PH.Skipped as e:
                # ホストから手を引いた（robots.txt・429 が続いた等）なら、この実行はここまで（あらすじも読まない）
                print(f"取得をやめる: {e}")
                share = 0
                break
            except Exception as e:                    # 消えたページ・一時的な失敗は飛ばす
                got["skipped"] += 1
                p["skipped"] = p.get("skipped", 0) + 1
                p["cursor"] = sid
                print(f"{sid}: 読めなかった（{type(e).__name__}）")
                continue
            row = row_from_html(html, str(sid))
            got["read"] += 1
            p["read"] = p.get("read", 0) + 1
            p["cursor"] = sid
            if row["end"] and row["end"] < since:
                p["old_streak"] = p.get("old_streak", 0) + 1
                got["old"] += 1
            else:
                p["old_streak"] = 0
            if row["title"] and row["start"] and not (row["end"] and row["end"] < since):
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                got["kept"] += 1
            if p["old_streak"] >= stop_after:
                p["done"] = True
                print(f"会期が {since} より前の公演が {stop_after} 枚続いたので、読み終わりとする")
                break
            if n % 100 == 0:
                out.flush()
                save_progress(p)
    if not todo:
        p["done"] = True
    if share:
        got["stories"] = stories(p, limit=story_limit, max_minutes=story_minutes, fetch=fetch)
    save_progress(p)
    got.update(done=p.get("done", False), cursor=p.get("cursor"))
    if retitled:
        got["retitle"] = retitled
    return got


def stories(p: dict, *, limit: int, max_minutes: float, fetch) -> dict:
    """2 周目: 一覧の公演ページの本文を、あらすじの読み取り待ちに積む（題材は起案者の Claude が読む）。"""
    import extract_theme_llm as EX
    lines = [l for l in ROWS.read_text(encoding="utf-8").split("\n") if l.strip()] if ROWS.exists() else []
    seen = set()
    for path in (EX.OUT, EX.QUEUE):
        for row in EX._read_jsonl(path):
            seen.add(str(row.get("id")))
    queue = EX._read_jsonl(EX.QUEUE)
    room = STORY_QUEUE_MAX - sum(1 for q in queue if q.get("side") == STORY_SIDE)
    got = {"queued": 0, "short": 0, "skipped": 0, "left": 0, "room": max(0, room)}
    # 読み取り待ちが一杯で 2 周目が止まっている間は、題名の読み直しが 2 周目の先の行も読む（retitle_targets）
    p["story_blocked"] = room <= 0
    if room <= 0:
        got["left"] = len(lines) - int(p.get("story_line") or 0)
        print(f"あらすじの読み取り待ちが {STORY_QUEUE_MAX} 件あるので、今日は積まない")
        return got
    t0 = time.monotonic()
    i = int(p.get("story_line") or 0)
    add, short = [], []
    titled: dict[str, tuple[str, str]] = {}           # 読んだページの題名（冠名・サブタイトル込み）。最後に一覧へ書き戻す
    # 今年に終わった公演を先に読む（起案者の指示 2026-10-19「2026 年の過去公演とれるところまで取って」）。
    # 一覧は番号の順で、番号は登録の順なので、今年の公演でも先の行に散らばっている（2026 年の未読 159 件は
    # 2,156〜6,155 行目にあった）。ここで読んだ行は seen に入るので、あとの順送りでは飛ばす。story_line は動かさない
    year = str(date.today().year)
    for j in range(i, len(lines)):
        if len(add) >= min(room, limit) or (max_minutes and (time.monotonic() - t0) / 60 > max_minutes):
            break
        r = json.loads(lines[j])
        if str(r.get("end") or r.get("start") or "")[:4] != year:
            continue
        stop = _story(r, seen, add, short, got, fetch, titled)
        if stop:
            break
    while i < len(lines) and len(add) < min(room, limit):
        if max_minutes and (time.monotonic() - t0) / 60 > max_minutes:
            print(f"時間の上限（{max_minutes} 分）に来たので、ここまでにする")
            break
        if _story(json.loads(lines[i]), seen, add, short, got, fetch, titled):
            break
        i += 1
    if add:
        with EX.QUEUE.open("a", encoding="utf-8") as fp:
            fp.write("".join(json.dumps({**q, "prompt_version": EX.PROMPT_VERSION}, ensure_ascii=False) + "\n" for q in add))
        EX.QUEUE_PROMPT.write_text(EX.PROMPTS[EX.PROMPT_VERSION], encoding="utf-8")
    if short:
        today = date.today().isoformat()
        with EX.OUT.open("a", encoding="utf-8") as fp:
            fp.write("".join(json.dumps({"side": STORY_SIDE, "id": q["id"], "title": q["title"], "url": "", "synopsis": "",
                                         "elements": [], "reason": "本文が短い", "model": "rule",
                                         "prompt_version": EX.PROMPT_VERSION, "at": today}, ensure_ascii=False) + "\n"
                              for q in short))
    p["story_line"] = i
    got["retitled"] = apply_titles(titled)
    got.update(queued=len(add), short=len(short), left=len(lines) - i)
    print(f"あらすじ: 待ちに {len(add)} 件積んだ／本文が短い {len(short)} 件／読めなかった {got['skipped']} 件／残り {got['left']} 行")
    return got


def report() -> None:
    p = load_progress()
    n = sum(1 for line in ROWS.read_text(encoding="utf-8").split("\n") if line.strip()) if ROWS.exists() else 0
    print(json.dumps({**p, "rows": n}, ensure_ascii=False, indent=1))


def _story(r: dict, seen: set, add: list, short: list, got: dict, fetch, titled: dict | None = None) -> bool:
    """1 公演の本文を取り、読み取り待ち（add）か本文が短い（short）に入れる。取得をやめるときは True。"""
    import extract_theme_llm as EX
    sid = str(r.get("stage_id") or "")
    if not sid or sid in seen:
        return False
    try:
        html = fetch(int(sid))
    except PH.Skipped as e:
        print(f"取得をやめる: {e}")
        return True
    except Exception as e:                    # 消えたページ・一時的な失敗は飛ばす（次の周で読み直さない）
        got["skipped"] += 1
        print(f"{sid}: 読めなかった（{type(e).__name__}）")
        seen.add(sid)
        return False
    if titled is not None and "title_main" not in r:
        titled[sid] = titles_of(html, sid)            # ついでに題名も冠名・サブタイトル込みに（取得は増えない）
    text = EX.prep(EX.strip_reviews(html), 2500)
    row = {"side": STORY_SIDE, "id": sid, "title": (r.get("title") or "")[:60], "url": "", "text": text}
    (add if len(text) >= EX.MIN_STORY_TEXT else short).append(row)
    seen.add(sid)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limit", type=int, default=6000, help="1 回に読む公演ページの枚数")
    ap.add_argument("--since", default="2019-01-01", help="会期の終わりがこの日より前の公演は残さない")
    ap.add_argument("--stop-after", type=int, default=300,
                    help="--since より前の公演がこの枚数続いたら読み終わりとする")
    ap.add_argument("--max-minutes", type=float, default=0, help="この分数を過ぎたら止める（0 は無制限）")
    ap.add_argument("--report", action="store_true", help="今どこまで読んだかを出す")
    ap.add_argument("--stories-only", action="store_true",
                    help="一覧は読まず、あらすじの本文だけを読み取り待ちに積む（stories.yml）")
    a = ap.parse_args()
    if a.report:
        report()
        return 0
    if a.stories_only:
        p = load_progress()
        fetch = lambda sid: PH.fetch(f"{FC.BASE}/stage/{sid}", timeout=45).decode("utf-8", "replace")   # noqa: E731
        limit, minutes, retitled = a.limit, a.max_minutes, None
        if minutes and retitle_targets(p):
            retitled = retitle(p, limit=int(limit * RETITLE_SHARE), max_minutes=minutes * RETITLE_SHARE, fetch=fetch)
            limit, minutes = limit - int(limit * RETITLE_SHARE), minutes * (1 - RETITLE_SHARE)
        got = stories(p, limit=limit, max_minutes=minutes, fetch=fetch)
        if retitled:
            got["retitle"] = retitled
        save_progress(p)
        print(json.dumps(got, ensure_ascii=False))
        return 0
    import fetch_candidates as FCand
    ids = FCand.sitemap_stage_ids()
    print(f"サイトマップの公演ページ: {len(ids)} 枚（最大の番号 {max(ids) if ids else '-'}）")
    got = run(ids, limit=a.limit, since=a.since, stop_after=a.stop_after, max_minutes=a.max_minutes)
    print(json.dumps(got, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
