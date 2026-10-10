#!/usr/bin/env python3
"""Public demo HTTP regressions; all writes use temporary databases.

    python3 tools/taguri/test_demo_stability.py
"""
from __future__ import annotations

import contextlib
import http.client
import json
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
import serve as S
import auth as AU
import app as APP
import feedback as FB
import rate_performances as R
import stage_search as SS


class DemoStabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = contextlib.ExitStack()
        tmp = Path(cls.stack.enter_context(tempfile.TemporaryDirectory()))
        (tmp / "review").mkdir()
        for mod, attr, value in (
            (AU, "DB_PATH", tmp / "auth/auth.db"),
            (AU, "PEPPER_PATH", tmp / "pepper.txt"),
            (FB, "DB", tmp / "review/ratings.db"),
            (R, "DB", tmp / "review/ratings.db"),
            (R, "SRC", tmp / "tickets/performances.jsonl"),
            (APP, "DB", tmp / "review/ratings.db"),
            (APP, "ROOT", tmp),
        ):
            cls.stack.enter_context(patch.object(mod, attr, value))
        cls.stack.enter_context(patch("urllib.request.urlopen", side_effect=AssertionError("external network forbidden")))
        cls.adopt = cls.stack.enter_context(patch.object(SS, "adopt", side_effect=AssertionError("catalog adoption forbidden")))
        cls.search = cls.stack.enter_context(patch.object(SS, "search", side_effect=AssertionError("external search forbidden")))
        cls.search_full = cls.stack.enter_context(patch.object(SS, "search_full", side_effect=AssertionError("external search forbidden")))
        # Exercise real HTTP parsing and dispatch through an in-memory transport.
        # No listening socket or extra network permission is needed.
        with patch("http.server.ThreadingHTTPServer.__init__", return_value=None):
            cls.srv = S.Server("demo-test", 0, demo_mode=True,
                               cors_origin="https://island-6848.github.io")
        cls.srv.server_port = 8000
        cls.users = []
        for _ in range(2):
            uid, _ = AU.access_or_register(AU.generate_recovery_code())
            cls.users.append((uid, AU.create_session(uid)))

    @classmethod
    def tearDownClass(cls):
        cls.srv.con.close()
        cls.stack.close()

    def request(self, path, *, user=0, body=None, origin="https://island-6848.github.io",
                ctype="application/json", raw=None, extra=None):
        headers = {"Host": "127.0.0.1:8000", "Connection": "close",
                   "Cookie": "tg_session=" + self.users[user][1], "Origin": origin,
                   "Content-Type": ctype, **(extra or {})}
        method = "POST" if body is not None or raw is not None else "GET"
        data = raw if raw is not None else json.dumps(body).encode() if body is not None else b""
        headers.setdefault("Content-Length", str(len(data)))
        request = (method + " " + path + " HTTP/1.1\r\n"
                   + "".join(k + ": " + v + "\r\n" for k, v in headers.items())
                   + "\r\n").encode() + data

        class Transport:
            def __init__(self):
                self.output = bytearray()
            def makefile(self, *args):
                return io.BytesIO(request)
            def sendall(self, data):
                self.output.extend(data)

        transport = Transport()
        S.Handler(transport, ("127.0.0.1", 12345), self.srv)
        class ResponseTransport:
            def makefile(self, *args):
                return io.BytesIO(transport.output)
        res = http.client.HTTPResponse(ResponseTransport())
        res.begin()
        payload = res.read()
        return res.status, json.loads(payload) if res.getheader("Content-Type", "").startswith("application/json") else payload

    def test_foreign_origin_cannot_write(self):
        with patch.object(self.srv, "on_note") as write:
            status, _ = self.request("/api/note", body={}, origin="https://other.invalid")
        self.assertEqual(status, 403)
        write.assert_not_called()

    def test_simple_cross_site_json_is_rejected(self):
        with patch.object(self.srv, "on_note") as write:
            status, _ = self.request("/api/note", body={}, ctype="text/plain")
        self.assertEqual(status, 415)
        write.assert_not_called()

    def test_shared_catalog_and_image_edits_are_disabled(self):
        with patch.object(APP, "save_hand_theme") as theme, patch.object(APP, "save_hand_poster") as image:
            for op in ("hand_theme", "hand_poster"):
                status, _ = self.request("/api/" + op, body={"stage_id": "123", "work_key": "same"})
                self.assertEqual(status, 403)
        theme.assert_not_called()
        image.assert_not_called()

    def test_missed_registration_does_not_enqueue_external_lookup(self):
        with patch.object(self.srv, "enqueue") as enqueue:
            status, result = self.request("/api/missed", body={"title": "デモの舞台"})
        self.assertEqual(status, 200)
        self.assertTrue(result["ok"])
        enqueue.assert_not_called()

    def test_add_and_link_use_only_local_catalog(self):
        with patch.object(self.srv, "enqueue") as enqueue, patch.object(APP, "_suggest_pool", return_value=[
            {"kind": "stage", "key": "123", "title": "デモ公演"}
        ]):
            status, result = self.request("/api/add_work", body={"title": "デモ公演", "date": "2026-09-01", "stage_id": "123"})
            self.assertEqual(status, 200)
            key = result["work_key"]
            status, _ = self.request("/api/link_stage", body={"work_key": key, "stage_id": "123"})
            self.assertEqual(status, 200)
            status, _ = self.request("/api/link_stage", body={"work_key": key, "stage_id": "999999"})
            self.assertEqual(status, 400)
        enqueue.assert_not_called()
        self.adopt.assert_not_called()

    def test_external_search_falls_back_to_local_suggestions(self):
        with patch.object(APP, "suggest", return_value={"rows": [{"kind": "stage", "title": "デモ公演"}]}) as local:
            status, result = self.request("/api/suggest_web?q=demo")
        self.assertEqual(status, 200)
        self.assertEqual(result["rows"][0]["title"], "デモ公演")
        local.assert_called_once_with(self.users[0][0], "demo")
        self.search.assert_not_called()
        self.assertIn("デモ", APP._web_hits(self.users[0][0], "demo", True))
        self.search_full.assert_not_called()

    def test_notes_and_ratings_remain_private_and_saved(self):
        status, result = self.request("/api/add_work", body={"title": "感想の確認", "date": "2026-09-02"})
        self.assertEqual(status, 200)
        key = result["work_key"]
        for op, body in (
            ("rate", {"work_key": key, "verdict": "◎"}),
            ("note", {"work_key": key, "note_impression": "保存した感想"}),
        ):
            status, _ = self.request("/api/" + op, body=body)
            self.assertEqual(status, 200)
        with contextlib.closing(R.connect()) as con:
            mine = R.read_works(con, user_id=self.users[0][0])[key]
            others = R.read_works(con, user_id=self.users[1][0])
        self.assertEqual(mine["verdict"], "◎")
        self.assertEqual(mine["note_impression"], "保存した感想")
        self.assertNotIn(key, others)

    def test_write_invalidates_only_writing_visitors_fragments(self):
        a, b = self.users[0][0], self.users[1][0]
        self.srv.screen_cache_set(a, "notes?", {"body_html": "old"})
        self.srv.screen_cache_set(b, "notes?", {"body_html": "other"})
        status, _ = self.request("/api/missed", body={"title": "キャッシュの確認"})
        self.assertEqual(status, 200)
        self.assertIsNone(self.srv.screen_cache_get(a, "notes?"))
        self.assertEqual(self.srv.screen_cache_get(b, "notes?")["body_html"], "other")

    def test_invalid_and_oversized_bodies_are_rejected(self):
        for raw, extra, expected in ((b"[]", {}, 400), (b"{}", {"Content-Length": "9000"}, 413),
                                     (b"{}", {"Content-Length": "-1"}, 400)):
            status, _ = self.request("/api/note", raw=raw, extra=extra)
            self.assertEqual(status, expected)
        status, result = self.request("/api/missed", body={"title": "エラー後も操作できます"})
        self.assertEqual(status, 200)
        self.assertTrue(result["ok"])

    def test_recovery_form_on_api_origin_still_works(self):
        code = AU.generate_recovery_code()
        AU.access_or_register(code)
        status, _ = self.request("/api/recover", raw=("code=" + code).encode(),
                                 ctype="application/x-www-form-urlencoded",
                                 origin=f"http://127.0.0.1:{self.srv.server_port}")
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
