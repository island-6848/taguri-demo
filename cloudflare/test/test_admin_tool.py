"""管理画面（tools/admin/admin.py）: 本番の D1 の代わりに、migration を当てた sqlite で確かめる。"""
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "admin"))
import admin as A  # noqa: E402

MIG = ROOT / "cloudflare" / "migrations"


class FakeD1:
    """wrangler d1 execute の代わり（--json --command は読み出し、--file は書き込み）。"""

    def __init__(self):
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        for f in sorted(MIG.glob("*.sql")):
            self.db.executescript(f.read_text(encoding="utf-8"))
        self.files = []

    def run(self, args):
        if args[0] == "--json":
            rows = [dict(r) for r in self.db.execute(args[2]).fetchall()]
            return json.dumps([{"results": rows, "success": True}])
        sql = Path(args[1]).read_text(encoding="utf-8")
        self.files.append(sql)
        self.db.executescript(sql)
        return "ok"


def png() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (800, 1100), (40, 60, 120)).save(buf, "PNG")
    return buf.getvalue()


class AdminTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.fake = FakeD1()
        self.d1 = A.D1(self.fake.run)
        x = self.fake.db
        x.execute("INSERT INTO rec_meta(k,v) VALUES('current','v1'),('rec_card','c1')")
        x.execute("INSERT INTO rec_stage(ver,stage_id,title,grp,start,end,credits,entry) VALUES('v1','101','港の三婆','劇団甲','2026-11-01','2026-11-10','[]',?)",
                  (json.dumps({"theater": "劇場A", "pref": "東京都", "fields": {"料金（1枚あたり）": "5,000円"}}, ensure_ascii=False),))
        x.execute("INSERT INTO rec_card(ver,stage_id,html,title,tour,start,end,pref,gnz,blob,ws,synz) VALUES('c1','101',?,'港の三婆','','2026-11-01','2026-11-10','東京都','','','','')",
                  ('<article class="ticket recommend"><div class="syn" data-stage="101"><p class="txt">元のあらすじ</p><div class="tags"><span class="tag">#港</span></div></div></article>',))
        x.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def test_search_and_read_a_stage(self):
        rows = A.search(self.d1, "三婆")
        self.assertEqual([(r["stage_id"], r["poster"], r["edited"]) for r in rows], [("101", None, None)])
        s = A.stage(self.d1, "101")
        self.assertEqual((s["title"], s["venue"], s["synopsis"], s["themes"], s["override"]), ("港の三婆", "劇場A", "元のあらすじ", ["港"], None))
        with self.assertRaises(A.AdminError):
            A.stage(self.d1, "../x")

    def test_save_writes_the_override_and_the_log_in_d1_and_locally(self):
        r = A.save(self.d1, self.data, "101", synopsis="手で入れたあらすじ", themes="家族、 #港町 , x",
                   info={"venue": "劇場B", "fields": {"料金（1枚あたり）": "6,000円", "知らない欄": "捨てる"}})
        self.assertTrue(r["changed"])
        row = dict(self.fake.db.execute("SELECT * FROM stage_override").fetchone())
        self.assertEqual((row["synopsis"], json.loads(row["themes"]), json.loads(row["info"])),
                         ("手で入れたあらすじ", ["家族", "港町"], {"venue": "劇場B", "fields": {"料金（1枚あたり）": "6,000円"}}))
        logs = self.fake.db.execute("SELECT stage_id,action,detail FROM admin_log").fetchall()
        self.assertEqual([(x["stage_id"], x["action"]) for x in logs], [("101", "edit")])
        self.assertEqual(json.loads(logs[0]["detail"])["before"]["synopsis"], None)
        self.assertEqual(A.read_log(self.data, "101")[0]["action"], "edit")
        # 同じ中身は書かない（無料枠）。空にすると手で直した分が消える（記録は残る）
        self.assertFalse(A.save(self.d1, self.data, "101", synopsis="手で入れたあらすじ")["changed"])
        A.save(self.d1, self.data, "101", synopsis="", themes=[], info={})
        self.assertIsNone(self.fake.db.execute("SELECT * FROM stage_override").fetchone())
        self.assertEqual(len(A.read_log(self.data, "101")), 2)
        # 書いた分は無料枠の控えに数えてある
        self.assertEqual(A.FT.load(self.data)["admin_d1"][A.FT.today()], 2 * A.WRITES_SAVE)

    def test_the_admin_write_cap_stops_before_writing(self):
        u = A.FT.load(self.data)
        u["admin_d1"] = {A.FT.today(): A.FT.CAPS["admin_d1_writes_day"]}
        A.FT.save(self.data, u)
        with self.assertRaises(A.AdminError):
            A.save(self.d1, self.data, "101", synopsis="x")
        self.assertEqual(self.fake.files, [])

    def test_poster_is_shrunk_put_under_a_versioned_name_and_logged(self):
        put = []
        r = A.add_poster(self.d1, self.data, "101", png(), put=lambda a, t, b, k, body, ct: put.append((k, ct, len(body))))
        self.assertRegex(r["file"], r"^101-a\d{14}\.webp$")
        self.assertEqual(put[0][0], r["file"])
        self.assertEqual(put[0][1], "image/webp")
        self.assertEqual(self.fake.db.execute("SELECT file FROM poster WHERE stage_id='101'").fetchone()[0], r["file"])
        u = A.FT.load(self.data)
        self.assertEqual(u["admin_posters"][A.FT.month()], 1)
        self.assertEqual(u["r2"]["sizes"][r["file"]], put[0][2])
        self.assertEqual(A.read_log(self.data, "101")[0]["action"], "poster")
        with self.assertRaises(A.AdminError):
            A.add_poster(self.d1, self.data, "101", b"not an image", put=lambda *a: None)

    def test_the_llm_queue_is_answered_by_claude_code_without_the_api_key(self):
        A.queue_add(self.data, "101", "港町で暮らす三人の老女が、家族の秘密に向き合う。", "港の三婆")
        prompt = A.prompt_for(A.queue_list(self.data))
        self.assertIn("stage_id: 101", prompt)
        seen = {}

        def fake_claude(p):
            seen["p"] = p
            return '答え: [{"stage_id": "101", "themes": ["港町", "家族", "#老い", "劇団甲"]}, {"stage_id": "999", "themes": ["x"]}]'
        got = A.analyze_now(self.d1, self.data, ["101"], run=fake_claude)
        self.assertEqual([g["stage_id"] for g in got], ["101"])
        self.assertEqual(json.loads(self.fake.db.execute("SELECT themes FROM stage_override").fetchone()[0]), ["港町", "家族", "老い", "劇団甲"])
        self.assertEqual(A.queue_list(self.data), [])
        self.assertEqual(json.loads(self.fake.db.execute("SELECT detail FROM admin_log").fetchone()[0])["by"], "Claude Code（管理画面から）")
        with self.assertRaises(A.AdminError):
            A.parse_answer("no json here")

    def test_fix_requests_are_listed_and_resolved_with_a_log(self):
        self.fake.db.execute("INSERT INTO fix_request(stage_id,user_id,kind,message,created_at) VALUES('101','u1','料金','6,000 円です','2026-10-17T01:00:00Z')")
        self.fake.db.commit()
        rows = A.requests(self.d1)
        self.assertEqual([(r["id"], r["title"], r["kind"], r["status"]) for r in rows], [(1, "港の三婆", "料金", "open")])
        self.assertTrue(A.resolve(self.d1, self.data, 1, "done", "料金を直した")["changed"])
        self.assertEqual(A.requests(self.d1), [])
        done = A.requests(self.d1, "done")[0]
        self.assertEqual((done["note"], bool(done["resolved_at"])), ("料金を直した", True))
        self.assertEqual(A.read_log(self.data, "101")[0]["detail"], {"request": 1, "before": "open", "after": "done", "note": "料金を直した"})
        self.assertFalse(A.resolve(self.d1, self.data, 1, "done", "料金を直した")["changed"])
        A.resolve(self.d1, self.data, 1, "open")
        self.assertIsNone(A.requests(self.d1)[0]["resolved_at"])
        with self.assertRaises(A.AdminError):
            A.resolve(self.d1, self.data, 99, "done")
        with self.assertRaises(A.AdminError):
            A.resolve(self.d1, self.data, 1, "maybe")

    def test_the_body_font_goes_to_r2_unchanged_and_counted(self):
        f = self.data / "Mamelon-3-Hi-Regular.otf"
        f.write_bytes(b"OTTO" + b"x" * 100)
        put = []
        r = A.upload_font(self.data, f, put=lambda a, t, b, k, body, ct: put.append((k, ct, body)))
        self.assertEqual((r["key"], put[0][0], put[0][1], put[0][2]), ("mamelon-3-hi-regular.otf", "mamelon-3-hi-regular.otf", "font/otf", f.read_bytes()))
        u = A.FT.load(self.data)
        self.assertEqual(u["r2"]["sizes"]["mamelon-3-hi-regular.otf"], 104)
        self.assertEqual(A.read_log(self.data)[0]["action"], "font")
        bad = self.data / "x.otf"
        bad.write_bytes(b"not a font")
        with self.assertRaises(A.AdminError):
            A.upload_font(self.data, bad, put=lambda *a: None)

    def test_sql_values_are_quoted(self):
        A.save(self.d1, self.data, "101", synopsis="it's 「引用」'); DROP TABLE poster; --")
        self.assertEqual(self.fake.db.execute("SELECT synopsis FROM stage_override").fetchone()[0], "it's 「引用」'); DROP TABLE poster; --")
        self.assertIsNotNone(self.fake.db.execute("SELECT count(*) FROM poster").fetchone())


if __name__ == "__main__":
    unittest.main()
