"""取得の毎日の配送（catalog.yml が wrangler d1 execute --file で送る SQL）は、利用者の表を消さず・変えない（issue #137）。

本物の配送のコードで SQL を作り、利用者の行が入った D1（全 migration を当てた SQLite）に流して確かめる:
- 一覧（deliver_catalogue.build の catalogue.sql）を 2 回（公演が変わり、終わった公演が出る日も）
- 推薦の索引（build_recommend_index: 版ごとの to_sql と、差分の diff_sql を 2 回）
- カード（build_cards.to_sql を 2 版）・公演の見出し（build_stage_labels.to_sql を 2 版）
- 過去の公演（deliver_past.build）・ポスター（deliver_posters.build、R2 への送信は偽物）
SQLite の authorizer で、流した文が書いた表を全部集め、配送の表だけであることも確かめる。
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CF = HERE.parent
ROOT = CF.parent
sys.path.insert(0, str(HERE / "screens"))
sys.path.insert(0, str(CF / "scripts"))
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
sys.path.insert(0, str(ROOT / "tools" / "review"))
import catalogue as CAT                                              # noqa: E402
import user_recommender as UR                                        # noqa: E402
import app as APP                                                    # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name, CF / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load("deliver_catalogue")
BI = _load("build_recommend_index")
BC = _load("build_cards")
BL = _load("build_stage_labels")
DPAST = _load("deliver_past")
DPOST = _load("deliver_posters")

# 配送が書いてよい表（公演の情報と、その控え）
DELIVERY_TABLES = {"catalogue", "venue_pref", "venue_census", "rec_meta", "rec_stage", "rec_credit", "rec_people",
                   "rec_gram", "rec_card", "stage_label", "past_stage", "poster"}
WRITE_ACTIONS = {sqlite3.SQLITE_INSERT: "INSERT", sqlite3.SQLITE_UPDATE: "UPDATE", sqlite3.SQLITE_DELETE: "DELETE",
                 sqlite3.SQLITE_DROP_TABLE: "DROP", sqlite3.SQLITE_ALTER_TABLE: "ALTER",
                 sqlite3.SQLITE_CREATE_TABLE: "CREATE", sqlite3.SQLITE_DROP_TRIGGER: "DROP TRIGGER",
                 sqlite3.SQLITE_DROP_INDEX: "DROP INDEX"}
USERS = ("user-a", "user-b")


def user_tables(con) -> list[str]:
    names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    return sorted(t for t in names
                  if t == "users" or any(c[1] == "user_id" for c in con.execute(f"PRAGMA table_info({t})")))


def seed(con) -> None:
    """利用者 2 人に、利用者の表すべての行（1 表 2 行。主キーが利用者だけの表は 1 行）"""
    fixed = {"reactions.status": "interest", "webauthn_challenges.purpose": "login"}
    for t in ["users"] + [t for t in user_tables(con) if t != "users"]:
        cols = list(con.execute(f"PRAGMA table_info({t})"))
        pk = [c[1] for c in cols if c[5]]
        rows = 1 if pk in (["id"], ["user_id"]) else 2
        for n, uid in enumerate(USERS):
            for i in range(rows):
                vals = []
                for c in cols:
                    name, typ = c[1], c[2]
                    key = f"{t}.{name}"
                    if key == "users.id" or name == "user_id":
                        vals.append(uid)
                    elif key in fixed:
                        vals.append(fixed[key])
                    elif key == "fix_request.id":
                        vals.append(n * 10 + i + 1)
                    elif "INT" in typ.upper():
                        vals.append(n * 10 + i + 1)
                    elif "REAL" in typ.upper():
                        vals.append(0.5)
                    else:
                        # stage_id は配送の公演と同じ番号（公演が変わっても、利用者の行の stage_id は変えない）
                        vals.append(("101", "102")[i] if name == "stage_id" else f"{t}.{name}.{uid}.{i}")
                con.execute(f"INSERT INTO {t}({','.join(c[1] for c in cols)}) VALUES({','.join('?' * len(cols))})", vals)
    con.commit()


def snapshot(con) -> dict:
    return {t: sorted(map(tuple, con.execute(f"SELECT * FROM {t}"))) for t in user_tables(con)}


def candidate(sid, title, period, **kw):
    return {"stage_id": sid, "title": title, "period": period, "group": "劇団", "theater": "劇場",
            "fields": {"出演": "俳優甲", "公式／劇場サイト": "https://example.com/x"}, **kw}


class DeliveryKeepsRecordsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.con = sqlite3.connect(":memory:")
        self.addCleanup(self.con.close)
        self.con.execute("PRAGMA foreign_keys=ON")         # D1 は外部キーを確かめる
        for f in sorted((CF / "migrations").glob("*.sql")):
            self.con.executescript(f.read_text(encoding="utf-8"))
        seed(self.con)
        self.before = snapshot(self.con)
        self.written: set[tuple[str, str]] = set()

        def watch(action, arg1, _arg2, _db, _trigger):
            if action in WRITE_ACTIONS:
                self.written.add((WRITE_ACTIONS[action], arg1 or ""))
            return sqlite3.SQLITE_OK
        self.con.set_authorizer(watch)
        self.sent: list[str] = []

    def run_sql(self, text: str) -> None:
        self.sent.append(text)
        self.con.executescript(text)

    def deliver_catalogue(self, rows, today):
        data = self.dir / "data"
        (data / "review").mkdir(parents=True, exist_ok=True)
        (data / "credits").mkdir(exist_ok=True)
        (data / "review" / "candidates.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        (data / "review" / "candidates_scan.json").write_text(json.dumps({"date": "2026-10-13T20:00"}))
        out = self.dir / "out"
        D.build(data, out, today, False, D.WRITE_BUDGET)
        for f in D.sent_files(out):
            self.run_sql(f.read_text(encoding="utf-8"))
        D.commit(data, out)

    def test_every_daily_delivery_leaves_the_user_tables_as_they_were(self):
        today = datetime.date.fromisoformat(CAT.TODAY)
        # 一覧: 1 日目と、題名が変わり公演が終わった 2 日目
        self.deliver_catalogue([candidate("101", "これから", "2026/11/01 ～ 2026/11/09"),
                                candidate("102", "もうすぐ", "2026/10/20 ～ 2026/10/22")], today)
        self.deliver_catalogue([candidate("101", "これから（改題）", "2026/11/01 ～ 2026/11/09"),
                                candidate("102", "もうすぐ", "2026/10/20 ～ 2026/10/22", ended=True)],
                               today + datetime.timedelta(days=1))
        # 推薦の索引: 版ごとの全部入れ替えと、差分（公演が減る日・戻る日）
        pool = UR.candidate_pool({}, CAT.CANDIDATES)
        fields = {c["stage_id"]: c["fields"] for c in CAT.CANDIDATES if c["fields"]}
        full = BI.build_index(pool, fields, APP.group_of)
        fewer = BI.build_index(UR.candidate_pool({}, CAT.CANDIDATES[:3]), fields, APP.group_of)
        self.run_sql("\n".join(BI.to_sql(full, BI.version_of(full))))
        stmts, hashes, _ = BI.diff_sql(full, {}, ["101"])
        self.run_sql("\n".join(stmts))
        stmts, hashes, _ = BI.diff_sql(fewer, hashes)
        self.run_sql("\n".join(stmts))
        stmts, _hashes, _ = BI.diff_sql(full, hashes)
        self.run_sql("\n".join(stmts))
        # カード・見出し: 2 版（前の版を消す）
        self.run_sql("\n".join(BC.to_sql(BC.build(pool, {}, today))))
        self.run_sql("\n".join(BC.to_sql(BC.build(pool, {}, today + datetime.timedelta(days=1)))))
        self.run_sql("\n".join(BL.to_sql({"101": ("これから／劇場", "これから")})))
        self.run_sql("\n".join(BL.to_sql({"101": ("これから（改題）／劇場", "これから（改題）")})))
        # 過去の公演とポスター
        data = self.dir / "data"
        (data / "past").mkdir(parents=True, exist_ok=True)
        (data / "past" / "stages.jsonl").write_text(json.dumps(
            {"stage_id": "30", "title": "夜の果て", "start": "2024-03-01", "end": "2024-03-10", "fields": {"出演": "俳優甲"}},
            ensure_ascii=False) + "\n", encoding="utf-8")
        DPAST.build(data, self.dir / "past-out", DPAST.BUDGET)
        self.run_sql((self.dir / "past-out" / "past-upload.sql").read_text(encoding="utf-8"))
        (data / "review" / "img").mkdir(parents=True, exist_ok=True)
        (data / "review" / "img" / "101.jpg").write_bytes(b"x")
        DPOST.build(data, self.dir / "posters-out", bucket="b", limit=10, put=lambda *a: None)
        self.run_sql((self.dir / "posters-out" / "posters-upload.sql").read_text(encoding="utf-8"))

        self.con.set_authorizer(None)
        self.assertEqual(snapshot(self.con), self.before)
        self.assertEqual(self.con.execute("PRAGMA foreign_key_check").fetchall(), [])
        tables = {t for _a, t in self.written}
        self.assertTrue(tables, "配送の文が流れていない")
        self.assertLessEqual(tables, DELIVERY_TABLES, f"配送が書いた表: {sorted(tables)}")
        self.assertFalse(tables & set(user_tables(self.con)))
        self.assertFalse({a for a, _t in self.written} - {"INSERT", "UPDATE", "DELETE"}, "配送は表の形を変えない")
        # 配送の SQL の文面にも、利用者の表の名前が書き込みの先として出てこない
        writes = re.compile(r"\b(?:DELETE\s+FROM|(?<!DO )UPDATE|INSERT(?:\s+OR\s+\w+)?\s+INTO|REPLACE\s+INTO|DROP\s+TABLE|ALTER\s+TABLE)\s+([A-Za-z_]+)", re.I)
        named = {m.group(1) for text in self.sent for m in writes.finditer(text)}
        self.assertLessEqual(named, DELIVERY_TABLES)

    def test_the_delivery_scripts_name_no_user_table_as_a_write_target(self):
        """作る SQL の文面（スクリプトのソース）に、利用者の表へ書く文が無い"""
        user = set(user_tables(self.con))
        target = re.compile(r"\b(?:DELETE\s+FROM|(?<!DO )UPDATE|INSERT(?:\s+OR\s+\w+)?\s+INTO|REPLACE\s+INTO|DROP\s+TABLE|ALTER\s+TABLE)\s+([A-Za-z_]+)\b")
        for f in sorted((CF / "scripts").glob("*.py")):
            for m in target.finditer(f.read_text(encoding="utf-8")):
                self.assertNotIn(m.group(1), user, f"{f.name}: {m.group(0)}")
        # catalog.yml が --command で直接流す SQL は読むだけ
        for f in (ROOT / "tools" / "taguri" / "deploy" / "github-actions").glob("*.yml"):
            for m in re.finditer(r'--command\s+"([^"]+)"', f.read_text(encoding="utf-8")):
                self.assertRegex(m.group(1), r"^\s*SELECT\b", f.name)


if __name__ == "__main__":
    unittest.main()
