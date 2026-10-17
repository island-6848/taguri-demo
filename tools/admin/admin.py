"""たぐりの管理画面の中身（起案者の指示 2026-10-17「管理者画面を作成して。あくまでこのパソコンとかで開く用。
どうしてもポスターがない画像に自分で足したり、詳細を編集したり、あらすじを追加したりする。個人で手動で追加した
ものは、LLM解析が必要なものはこのclaudeを呼び出して行ったり、自動的にデータベースやログに書き込まれるように」）。

- 公演を探す・今の中身を見る: 本番の D1 を読む（wrangler d1 execute --remote。読み出しは無料枠が大きい）
- 直す: 手で直した分は D1 の stage_override に置く（migration 0028）。カードは取得のたびに作り直されるので、
  Worker が画面に出すときに重ねる（cloudflare/src/screens/override.js）
- ポスター: 縮めて（deliver_posters.encode）R2 に入れ、poster の行を書く。名前は版付き（<id>-a<時刻>.webp）。
  Worker はポスターを 7 日間「変わらない」として控えるので、同じ名前で差し替えると古い絵が残るため
- 記録: 直すたびに、手元の data/admin/log.jsonl と D1 の admin_log に同じ中身を書く
- LLM の読み取り（あらすじ → 題材）: 有料の API は使わない（無料枠の約束）。data/admin/llm_queue.jsonl に積み、
  Claude Code に読ませる。① 画面の「Claude で読み取る」で手元の `claude -p` を呼ぶ（ANTHROPIC_API_KEY は
  渡さない ── 渡すと従量課金の API になる）。② 動かせないときは積んだままにし、Claude Code のセッションで
  `python3 tools/admin/admin.py queue` → 読み取り → `python3 tools/admin/admin.py answer 答え.json`
- 無料枠: 書く前に数える（free_tier.CAPS の admin_d1_writes_day・admin_posters_month と、取得と共通の上限）
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "cloudflare" / "scripts"))
import free_tier as FT          # noqa: E402
import deliver_posters as DP    # noqa: E402

DATA = Path(os.environ.get("TAGURI_ADMIN_DATA", ROOT / "data" / "admin"))
LOG = "log.jsonl"
QUEUE = "llm_queue.jsonl"
DB_NAME = "taguri-demo"
BUCKET = os.environ.get("TAGURI_POSTER_BUCKET", "taguri-posters")
SID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
PRICE_FIELD = "料金（1枚あたり）"
# 管理画面で直せる欄（公演ページの表の欄の名前のまま。カードと日程の表がこの名前で読む）
FIELDS = ("劇場", PRICE_FIELD, "タイムテーブル", "出演", "演出", "脚本", "スタッフ", "公式／劇場サイト", "その他注意事項")
INFO_KEYS = ("venue", "pref", "period", "url")
MAX_THEMES = 6
WRITES_SAVE = 4        # stage_override の行と索引（2）＋ admin_log の行と索引（2）を多めに
WRITES_POSTER = 4      # poster の行と索引（2）＋ admin_log（2）


class AdminError(Exception):
    pass


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sq(v) -> str:
    """SQL の値（D1 に文で送るので、文字列は ' を重ねて囲む）。"""
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


# ── D1（本番）── 差し替えられるようにしてある（テストは node:sqlite ではなく sqlite3 の偽物を使う）
def wrangler_run(args: list[str]) -> str:
    npx = shutil.which("npx") or shutil.which("npx.cmd")      # Windows は npx.cmd
    if not npx:
        raise AdminError("Node.js（npx）が見つかりません。https://nodejs.org から入れてから、もう一度開いてください")
    cmd = [npx, "--yes", "wrangler@4", "d1", "execute", DB_NAME, "--remote", *args]
    try:
        r = subprocess.run(cmd, cwd=ROOT / "cloudflare", capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300)
    except subprocess.TimeoutExpired as e:
        raise AdminError("D1 から返事がありませんでした（初めての実行は wrangler の取り込みに時間がかかります。もう一度押してください）") from e
    if r.returncode:
        raise AdminError("D1 に届きませんでした（wrangler にログインしているか確かめてください）: " + (r.stderr or r.stdout)[-400:])
    return r.stdout


class D1:
    def __init__(self, run=wrangler_run):
        self.run = run

    def query(self, sql: str) -> list[dict]:
        out = self.run(["--json", "--command", sql])
        try:
            got = json.loads(out[out.index("["):])
        except ValueError as e:
            raise AdminError("D1 の返事が読めませんでした") from e
        rows = []
        for part in got:
            rows += part.get("results") or []
        return rows

    def execute(self, statements: list[str]) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as f:
            f.write("\n".join(s.rstrip(";") + ";" for s in statements) + "\n")
            name = f.name
        try:
            self.run(["--file", name])
        finally:
            os.unlink(name)


# ── 無料枠 ──
def _ledger_day(u: dict) -> int:
    return int(u.setdefault("admin_d1", {}).get(FT.today(), 0))


def spend_d1(data: Path, writes: int) -> None:
    """書く前に数える。管理画面の分の上限と、取得と共通の上限の両方を見る。"""
    u = FT.load(data)
    if _ledger_day(u) + writes > FT.CAPS["admin_d1_writes_day"]:
        raise AdminError(f"今日の管理画面の書き込みが上限（{FT.CAPS['admin_d1_writes_day']:,} 行）に届くので止めました（無料枠を守るため）")
    if FT.d1_left(data) < writes:
        raise AdminError("今日の D1 の書き込みの残りが無いので止めました（無料枠を守るため）")
    u["admin_d1"][FT.today()] = _ledger_day(u) + writes
    FT.save(data, u)
    FT.d1_spend(data, writes)


def spend_poster(data: Path, size: int) -> None:
    u = FT.load(data)
    m = FT.month()
    n = int(u.setdefault("admin_posters", {}).get(m, 0))
    if n + 1 > FT.CAPS["admin_posters_month"]:
        raise AdminError(f"今月の管理画面からのポスターが上限（{FT.CAPS['admin_posters_month']} 枚）に届くので止めました")
    if FT.r2_bytes(u) + size > FT.CAPS["r2_bytes"]:
        raise AdminError("R2 の保存が上限に届くので止めました（R2 は越えると請求されるため）")
    if FT.r2_class_a(u) + 1 > FT.CAPS["r2_class_a_month"]:
        raise AdminError("今月の R2 の書き込みが上限に届くので止めました")
    u["admin_posters"][m] = n + 1
    u["r2"]["class_a"][m] = FT.r2_class_a(u) + 1       # 送る前に数える（失敗しても少なく数えない）
    FT.save(data, u)


# ── 記録 ──
def log_entry(data: Path, stage_id: str, action: str, detail: dict) -> tuple[dict, str]:
    e = {"at": now_iso(), "stage_id": stage_id, "action": action, "detail": detail}
    data.mkdir(parents=True, exist_ok=True)
    with (data / LOG).open("a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    sql = (f"INSERT INTO admin_log(at,stage_id,action,detail) VALUES({sq(e['at'])},{sq(stage_id)},{sq(action)},"
           f"{sq(json.dumps(detail, ensure_ascii=False))})")
    return e, sql


def read_log(data: Path, stage_id: str = "", limit: int = 50) -> list[dict]:
    p = data / LOG
    if not p.exists():
        return []
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    if stage_id:
        rows = [r for r in rows if r.get("stage_id") == stage_id]
    return rows[-limit:][::-1]


# ── 読む ──
def norm_words(words) -> list[str]:
    if isinstance(words, str):
        words = re.split(r"[、,，\s]+", words)
    out: list[str] = []
    for w in words or []:
        w = unicodedata.normalize("NFKC", str(w)).strip().lstrip("#＃")
        if len(w) >= 2 and w not in out and len(w) <= 20:
            out.append(w)
    return out[:MAX_THEMES]


def search(db: D1, q: str, limit: int = 30) -> list[dict]:
    q = unicodedata.normalize("NFKC", q or "").strip()
    if not q:
        return []
    like = sq("%" + q.replace("%", "").replace("_", "") + "%")
    rows = db.query(
        "SELECT s.stage_id, s.title, s.start, s.end, json_extract(s.entry,'$.theater') AS venue, "
        "(SELECT file FROM poster p WHERE p.stage_id=s.stage_id) AS poster, "
        "(SELECT 1 FROM stage_override o WHERE o.stage_id=s.stage_id) AS edited "
        "FROM rec_stage s WHERE s.ver=(SELECT v FROM rec_meta WHERE k='current') "
        f"AND (s.title LIKE {like} OR s.stage_id={sq(q)}) ORDER BY s.start DESC LIMIT {int(limit)}")
    seen = {r["stage_id"] for r in rows}
    if len(rows) < limit:
        for r in db.query(
                "SELECT c.id AS stage_id, c.title, c.date AS start, json_extract(c.metadata,'$.end_date') AS end, c.venue, "
                "(SELECT file FROM poster p WHERE p.stage_id=c.id) AS poster, "
                "(SELECT 1 FROM stage_override o WHERE o.stage_id=c.id) AS edited "
                f"FROM catalogue c WHERE c.title LIKE {like} OR c.id={sq(q)} ORDER BY c.date DESC LIMIT {int(limit)}"):
            if r["stage_id"] not in seen and len(rows) < limit:
                rows.append(r)
    return rows


def _unhtml(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"), ("&amp;", "&")):
        s = s.replace(a, b)
    return s.strip()


def stage(db: D1, sid: str) -> dict:
    if not SID.match(sid or ""):
        raise AdminError("公演の番号がおかしい")
    s = sq(sid)
    idx = db.query(f"SELECT stage_id,title,start,end,entry FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id={s}")
    cat = db.query(f"SELECT id,title,date,venue,url,metadata FROM catalogue WHERE id={s}")
    card = db.query(f"SELECT html FROM rec_card WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND stage_id={s}")
    ov = db.query(f"SELECT synopsis,themes,info,updated_at FROM stage_override WHERE stage_id={s}")
    pic = db.query(f"SELECT file FROM poster WHERE stage_id={s}")
    if not idx and not cat:
        raise AdminError("その番号の公演が見つかりません")
    entry = json.loads(idx[0]["entry"] or "{}") if idx else {}
    meta = json.loads(cat[0]["metadata"] or "{}") if cat else {}
    html = card[0]["html"] if card else ""
    txt = re.search(r'<p class="txt">([\s\S]*?)</p>', html)
    syn_div = re.search(r'<div class="syn[^"]*" data-stage="[^"]*">([\s\S]*?)(?:<details|</div>)', html)
    themes = [_unhtml(m) for m in re.findall(r'<span class="tag">#([\s\S]*?)</span>', syn_div.group(0) if syn_div else "")]
    o = ov[0] if ov else {}
    return {
        "stage_id": sid,
        "title": (idx[0]["title"] if idx else cat[0]["title"]),
        "start": (idx[0]["start"] if idx else cat[0]["date"]) or "",
        "end": (idx[0]["end"] if idx else meta.get("end_date")) or "",
        "venue": entry.get("theater") or entry.get("venue") or (cat[0]["venue"] if cat else ""),
        "pref": entry.get("pref") or "",
        "period": entry.get("period") or "",
        "url": entry.get("url") or (cat[0]["url"] if cat else ""),
        "fields": entry.get("fields") or meta.get("fields") or {},
        "synopsis": _unhtml(txt.group(1)) if txt else (meta.get("synopsis") or ""),
        "themes": themes or list(meta.get("words") or [])[:MAX_THEMES],
        "has_card": bool(card),
        "poster": pic[0]["file"] if pic else "",
        "override": {"synopsis": o.get("synopsis"), "themes": json.loads(o["themes"]) if o.get("themes") else None,
                     "info": json.loads(o["info"]) if o.get("info") else {}, "updated_at": o.get("updated_at")} if o else None,
        "corich": f"https://stage.corich.jp/stage/{sid}" if sid.isdigit() else "",
    }


# ── 直す ──
def _clean_info(info: dict | None) -> dict:
    out: dict = {}
    for k in INFO_KEYS:
        v = (info or {}).get(k)
        if isinstance(v, str) and v.strip():
            out[k] = v.strip()[:500]
    fields = {k: str(v).strip()[:4000] for k, v in ((info or {}).get("fields") or {}).items()
              if k in FIELDS and isinstance(v, str) and v.strip()}
    if fields:
        out["fields"] = fields
    return out


def save(db: D1, data: Path, sid: str, *, synopsis=None, themes=None, info=None, by: str = "管理画面") -> dict:
    """手で直した分を D1 と記録に書く。None は「直さない」、"" / [] は「手で直した分を消す（元に戻す）」。"""
    if not SID.match(sid or ""):
        raise AdminError("公演の番号がおかしい")
    cur = db.query(f"SELECT synopsis,themes,info FROM stage_override WHERE stage_id={sq(sid)}")
    old = cur[0] if cur else {"synopsis": None, "themes": None, "info": None}
    new = dict(old)
    if synopsis is not None:
        new["synopsis"] = synopsis.strip()[:4000] or None
    if themes is not None:
        ws = norm_words(themes)
        new["themes"] = json.dumps(ws, ensure_ascii=False) if ws else None
    if info is not None:
        ci = _clean_info(info)
        new["info"] = json.dumps(ci, ensure_ascii=False) if ci else None
    if new == old:
        return {"changed": False}
    spend_d1(data, WRITES_SAVE)
    stmts = []
    if new["synopsis"] is None and new["themes"] is None and new["info"] is None:
        stmts.append(f"DELETE FROM stage_override WHERE stage_id={sq(sid)}")
    else:
        stmts.append("INSERT INTO stage_override(stage_id,synopsis,themes,info,updated_at) VALUES("
                     f"{sq(sid)},{sq(new['synopsis'])},{sq(new['themes'])},{sq(new['info'])},{sq(now_iso())}) "
                     "ON CONFLICT(stage_id) DO UPDATE SET synopsis=excluded.synopsis,themes=excluded.themes,"
                     "info=excluded.info,updated_at=excluded.updated_at")
    detail = {"by": by, "before": old, "after": new}
    entry, log_sql = log_entry(data, sid, "edit", detail)
    stmts.append(log_sql)
    db.execute(stmts)
    return {"changed": True, "log": entry}


def add_poster(db: D1, data: Path, sid: str, body: bytes, *, put=None, ended: bool = False) -> dict:
    if not SID.match(sid or ""):
        raise AdminError("公演の番号がおかしい")
    if not body or len(body) > 20 * 1024 * 1024:
        raise AdminError("画像が空か、大きすぎます（20 MB まで）")
    small = DP.encode(body, coarse=ended)
    if not small:
        raise AdminError("画像を読めませんでした（JPEG・PNG・WebP を選んでください。縮めるのに Pillow が要ります）")
    out, ext, ctype = small
    key = f"{sid}-a{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')}{ext}"
    spend_d1(data, WRITES_POSTER)
    spend_poster(data, len(out))
    account, token = os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""), os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if put is None:
        if not account or not token:
            raise AdminError("CLOUDFLARE_ACCOUNT_ID と CLOUDFLARE_API_TOKEN（R2 の書き込み権限）を環境変数に入れてください")
        put = DP.put_object
    put(account, token, BUCKET, key, out, ctype)
    u = FT.load(data)
    u["r2"]["sizes"][key] = len(out)
    FT.save(data, u)
    old = db.query(f"SELECT file FROM poster WHERE stage_id={sq(sid)}")
    # 原本は手元に残す（取得の作業データと同じ置き場所の名前で）
    keep = data / "posters"
    keep.mkdir(parents=True, exist_ok=True)
    (keep / f"{key.rsplit('.', 1)[0]}.orig").write_bytes(body)
    entry, log_sql = log_entry(data, sid, "poster", {"file": key, "bytes": len(out), "before": old[0]["file"] if old else None})
    db.execute([f"INSERT OR REPLACE INTO poster(stage_id,file) VALUES({sq(sid)},{sq(key)})", log_sql])
    return {"file": key, "bytes": len(out), "log": entry}


# ── 公演修正依頼（利用者から。migration 0030、Worker の src/screens/fixrequest.js が受けてメールで知らせる）──
STATUS = {"open": "未対応", "done": "直した", "dropped": "見送った"}


def requests(db: D1, status: str = "open", limit: int = 100) -> list[dict]:
    if status not in STATUS and status != "all":
        raise AdminError("状態がおかしい")
    where = "" if status == "all" else f"WHERE r.status={sq(status)}"
    return db.query(
        "SELECT r.id, r.stage_id, r.kind, r.message, r.created_at, r.status, r.note, r.resolved_at, r.mailed, "
        "COALESCE((SELECT title FROM rec_stage s WHERE s.ver=(SELECT v FROM rec_meta WHERE k='current') AND s.stage_id=r.stage_id),"
        " (SELECT title FROM catalogue c WHERE c.id=r.stage_id), '') AS title "
        f"FROM fix_request r {where} ORDER BY r.created_at DESC LIMIT {int(limit)}")


def resolve(db: D1, data: Path, req_id: int, status: str, note: str = "") -> dict:
    """依頼を「直した」「見送った」にする（未対応に戻すこともできる）。D1 と記録に書く。"""
    if status not in STATUS:
        raise AdminError("状態がおかしい")
    cur = db.query(f"SELECT id, stage_id, status, note FROM fix_request WHERE id={int(req_id)}")
    if not cur:
        raise AdminError("その依頼が見つかりません")
    old = cur[0]
    note = (note or "").strip()[:1000]
    if old["status"] == status and (old.get("note") or "") == note:
        return {"changed": False}
    spend_d1(data, WRITES_SAVE)
    at = now_iso() if status != "open" else None
    entry, log_sql = log_entry(data, old["stage_id"], "request", {"request": int(req_id), "before": old["status"], "after": status, "note": note})
    db.execute([f"UPDATE fix_request SET status={sq(status)}, note={sq(note or None)}, resolved_at={sq(at)} WHERE id={int(req_id)}", log_sql])
    return {"changed": True, "log": entry}


# ── LLM の読み取り（Claude Code）──
PROMPT = """あなたは演劇公演の紹介文から「題材」の語を読み取る係です。次の公演ごとに、あらすじに書かれている内容から、
おすすめの手がかりになる題材の語を最大 {n} 語選んでください（例: 家族、戦争、港町、落語、人情、恋愛、介護、宇宙）。
- あらすじに書かれていないことは足さない。出演者・劇団・劇場の名前は入れない
- 1 語は 2〜10 字の名詞。ジャンル（コメディ・ミュージカルなど）は、あらすじにそう書いてあるときだけ
答えは JSON だけを返してください（前後に文を付けない）: [{{"stage_id": "…", "themes": ["…"]}}]

{items}"""


def queue_add(data: Path, sid: str, synopsis: str, title: str = "") -> dict:
    task = {"stage_id": sid, "title": title, "synopsis": synopsis.strip()[:4000], "kind": "themes", "at": now_iso()}
    data.mkdir(parents=True, exist_ok=True)
    rows = [t for t in queue_list(data) if t["stage_id"] != sid]
    rows.append(task)
    (data / QUEUE).write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in rows), encoding="utf-8")
    return task


def queue_list(data: Path) -> list[dict]:
    p = data / QUEUE
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def queue_drop(data: Path, sids: set[str]) -> None:
    rows = [t for t in queue_list(data) if t["stage_id"] not in sids]
    (data / QUEUE).write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in rows), encoding="utf-8")


def prompt_for(tasks: list[dict]) -> str:
    items = "\n\n".join(f"stage_id: {t['stage_id']}\n題名: {t.get('title', '')}\nあらすじ: {t['synopsis']}" for t in tasks)
    return PROMPT.format(n=MAX_THEMES, items=items)


def parse_answer(text: str) -> list[dict]:
    m = re.search(r"\[[\s\S]*\]", text or "")
    if not m:
        raise AdminError("Claude の答えに JSON がありませんでした")
    try:
        got = json.loads(m.group(0))
    except ValueError as e:
        raise AdminError("Claude の答えの JSON が読めませんでした") from e
    return [{"stage_id": str(a.get("stage_id", "")), "themes": norm_words(a.get("themes") or [])}
            for a in got if isinstance(a, dict)]


def apply_answers(db: D1, data: Path, answers: list[dict], by: str) -> list[dict]:
    """読み取った題材を、手で直した分として書く（積んだ読み取りに無い公演の答えは捨てる）。"""
    pending = {t["stage_id"]: t for t in queue_list(data)}
    done, out = set(), []
    for a in answers:
        t = pending.get(a["stage_id"])
        if not t:
            continue
        ws = a["themes"]
        r = save(db, data, a["stage_id"], themes=ws, by=by)
        out.append({"stage_id": a["stage_id"], "themes": ws, **r})
        done.add(a["stage_id"])
    queue_drop(data, done)
    return out


def claude_cli() -> str:
    return shutil.which("claude") or ""


def run_claude(prompt: str, timeout: int = 300) -> str:
    """手元の Claude Code（`claude -p`）に読ませる。ANTHROPIC_API_KEY は外す（入れると従量課金の API になる）。"""
    exe = claude_cli()
    if not exe:
        raise AdminError("このパソコンに claude（Claude Code）が見つかりません。読み取りは積んだままにしました")
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    r = subprocess.run([exe, "-p", prompt, "--output-format", "text"], capture_output=True, text=True,
                       timeout=timeout, env=env, cwd=ROOT)
    if r.returncode:
        raise AdminError("Claude Code が答えませんでした: " + (r.stderr or r.stdout)[-300:])
    return r.stdout


def analyze_now(db: D1, data: Path, sids: list[str] | None = None, run=run_claude) -> list[dict]:
    tasks = [t for t in queue_list(data) if not sids or t["stage_id"] in sids]
    if not tasks:
        return []
    return apply_answers(db, data, parse_answer(run(prompt_for(tasks))), by="Claude Code（管理画面から）")


# ── 本文のお試しの文字（マメロン）を R2 に置く（起案者の回答 2026-10-18「R2 から配る」「太さ 3」）──
# 配布元の readme は Web フォントでの利用を認め（ファイル名は変えてよい）、無断での改変・二次配布は控えるよう求めている。
# 公開リポジトリには入れず、ファイルは変換せずに R2 に置き、Worker の /img/<名前>（ログインした人だけ）で配る。
# theme.css の @font-face が /img/mamelon-3-hi-regular.otf を読む
FONT_KEY = "mamelon-3-hi-regular.otf"
FONT_MAX = 10 * 1024 * 1024


def upload_font(data: Path, src: Path, *, put=None) -> dict:
    body = Path(src).read_bytes()
    if not body[:4] in (b"OTTO", b"\x00\x01\x00\x00", b"true"):
        raise AdminError("OpenType（.otf / .ttf）のフォントのファイルを選んでください")
    if len(body) > FONT_MAX:
        raise AdminError("フォントのファイルが大きすぎます（10 MB まで）")
    u = FT.load(data)
    if FT.r2_bytes(u) + len(body) > FT.CAPS["r2_bytes"] or FT.r2_class_a(u) + 1 > FT.CAPS["r2_class_a_month"]:
        raise AdminError("R2 の上限に届くので止めました（R2 は越えると請求されるため）")
    u["r2"]["class_a"][FT.month()] = FT.r2_class_a(u) + 1       # 送る前に数える
    FT.save(data, u)
    account, token = os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""), os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if put is None:
        if not account or not token:
            raise AdminError("CLOUDFLARE_ACCOUNT_ID と CLOUDFLARE_API_TOKEN（R2 の書き込み権限）を環境変数に入れてください")
        put = DP.put_object
    ctype = "font/otf" if body[:4] == b"OTTO" else "font/ttf"
    put(account, token, BUCKET, FONT_KEY, body, ctype)
    u = FT.load(data)
    u["r2"]["sizes"][FONT_KEY] = len(body)
    FT.save(data, u)
    data.mkdir(parents=True, exist_ok=True)
    with (data / LOG).open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": now_iso(), "stage_id": "", "action": "font", "detail": {"key": FONT_KEY, "bytes": len(body), "from": Path(src).name}}, ensure_ascii=False) + "\n")
    return {"key": FONT_KEY, "bytes": len(body)}


def main(argv: list[str]) -> int:
    """Claude Code のセッションから積んだ読み取りを片付ける:
      python3 tools/admin/admin.py queue           積んだ読み取りと、そのまま読める指示を出す
      python3 tools/admin/admin.py answer FILE     答え（JSON）を確かめて D1 と記録に書く
    本文のお試しの文字（マメロン 3）を R2 に置く（1 回だけ）:
      python3 tools/admin/admin.py font Mamelon-3-Hi-Regular.otf
    """
    if len(argv) >= 2 and argv[0] == "font":
        r = upload_font(DATA, Path(argv[1]))
        print(f"R2 に入れました: {r['key']}（{r['bytes']:,} バイト）。次に開いた画面から本文がマメロンになります")
        return 0
    if len(argv) >= 1 and argv[0] == "queue":
        tasks = queue_list(DATA)
        print(prompt_for(tasks) if tasks else "積んだ読み取りはありません")
        return 0
    if len(argv) >= 2 and argv[0] == "answer":
        res = apply_answers(D1(), DATA, parse_answer(Path(argv[1]).read_text(encoding="utf-8")), by="Claude Code（セッション）")
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    print(main.__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
