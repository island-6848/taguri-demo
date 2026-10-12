"""Independent exposure storage and authenticated HTTP regression tests.

All records use temporary databases; no real user data or external network.
Run: python3 tools/taguri/test_recommendation_exposure.py
"""
from __future__ import annotations

import os
import tempfile
from unittest.mock import patch
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recommendation_exposure as EX


class ExposureStorageTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.store = EX.Store(self.con)
        self.pid = self.store.register("alice", [{"stage_id": "stage-a", "title": "秘密の題名"},
                                                  {"stage_id": "stage-b"}], ["東京都"])
        self.body = {"presentation_id": self.pid, "visit_id": "v" * 24, "source": "network"}

    def tearDown(self):
        self.con.close()

    def test_contact_requires_begin_and_registered_candidate(self):
        with self.assertRaises(ValueError):
            self.store.contact("alice", {**self.body, "stage_id": "stage-a"})
        self.store.begin("alice", self.body)
        with self.assertRaises(ValueError):
            self.store.contact("alice", {**self.body, "stage_id": "unknown"})

    def test_user_separation_and_duplicate_contact(self):
        with self.assertRaises(ValueError):
            self.store.begin("bob", self.body)
        self.store.begin("alice", self.body)
        good = {"presentation_id": self.pid, "visit_id": self.body["visit_id"], "stage_id": "stage-a"}
        with self.assertRaises(ValueError):
            self.store.contact("bob", good)
        self.assertFalse(self.store.contact("alice", good)["duplicate"])
        self.assertTrue(self.store.contact("alice", good)["duplicate"])
        self.assertEqual(self.con.execute("SELECT count(*) FROM recommendation_contacts").fetchone()[0], 1)

    def test_cache_revisit_counts_separately_without_another_fetch(self):
        self.store.fetched("alice", self.pid)
        self.store.begin("alice", self.body)
        self.store.contact("alice", {"presentation_id": self.pid, "visit_id": self.body["visit_id"], "stage_id": "stage-a"})
        revisit = {**self.body, "visit_id": "w" * 24, "source": "cache"}
        self.store.begin("alice", revisit)
        self.store.contact("alice", {"presentation_id": self.pid, "visit_id": revisit["visit_id"], "stage_id": "stage-a"})
        self.assertEqual(self.con.execute("SELECT count(*) FROM recommendation_contacts").fetchone()[0], 2)
        self.assertEqual(self.con.execute("SELECT count(*) FROM recommendation_fetches").fetchone()[0], 1)

    def test_duplicate_begin_and_server_owned_rank(self):
        self.store.begin("alice", self.body)
        self.store.begin("alice", self.body)
        self.store.contact("alice", {"presentation_id": self.pid,
                           "visit_id": self.body["visit_id"], "stage_id": "stage-b"})
        self.assertEqual(self.con.execute("SELECT count(*) FROM recommendation_visits").fetchone()[0], 1)
        self.assertEqual(self.con.execute("SELECT rank FROM recommendation_contacts").fetchone()[0], 2)

    def test_strict_fields_and_identifiers(self):
        for field in ("user_id", "rank", "title", "note", "token", "visible_ms", "ratio"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.store.begin("alice", {**self.body, field: "untrusted"})
        for value in (None, 1, True, [], {}, "", "short", "a" * 81, "a b" * 8):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.store.begin("alice", {**self.body, "visit_id": value})
        for value in (None, 1, True, [], {}, "", "wrong"):
            with self.subTest(source=value), self.assertRaises(ValueError):
                self.store.begin("alice", {**self.body, "source": value})
        self.store.begin("alice", self.body)
        good = {"presentation_id": self.pid, "visit_id": self.body["visit_id"], "stage_id": "stage-a"}
        for field in ("user_id", "rank", "title", "note", "token", "visible_ms", "ratio"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.store.contact("alice", {**good, field: "untrusted"})
        for value in (None, 1, True, [], {}, "", "a" * 81):
            with self.subTest(stage=value), self.assertRaises(ValueError):
                self.store.contact("alice", {**good, "stage_id": value})

    def test_fill_registration_rank_and_no_sensitive_payload_persisted(self):
        filled = self.store.register("alice", [{"stage_id": "stage-c", "title": "秘密の題名",
                                               "note": "秘密の感想", "token": "秘密のトークン"}], [],
                                     kind="fill", start_rank=16)
        body = {"presentation_id": filled, "visit_id": "f" * 24, "source": "fill"}
        self.store.begin("alice", body)
        self.store.contact("alice", {k: v for k, v in body.items() if k != "source"} | {"stage_id": "stage-c"})
        self.assertEqual(self.con.execute("SELECT rank FROM recommendation_contacts").fetchone()[0], 16)
        tables = [r[0] for r in self.con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        serialized = repr([self.con.execute("SELECT * FROM " + table).fetchall() for table in tables])
        for secret in ("秘密の題名", "秘密の感想", "秘密のトークン"):
            self.assertNotIn(secret, serialized)


import test_demo_stability as DS


class ExposureHTTPTests(DS.DemoStabilityTests):
    @classmethod
    def setUpClass(cls):
        cls.exposure_tmp = tempfile.TemporaryDirectory()
        cls.exposure_env = patch.dict(os.environ, {"TAGURI_EXPOSURE_DB": str(Path(cls.exposure_tmp.name) / "exposure.db")})
        cls.exposure_env.start()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        if getattr(cls.srv, "exposure_con", None):
            cls.srv.exposure_con.close()
        super().tearDownClass()
        cls.exposure_env.stop()
        cls.exposure_tmp.cleanup()

    def presentation(self):
        return self.srv.exposure.register(self.users[0][0], [{"stage_id": "stage-a"}], [])

    def test_exposure_authenticated_dispatch_and_user_separation(self):
        pid = self.presentation()
        visit = {"presentation_id": pid, "visit_id": "h" * 24, "source": "network"}
        status, _ = self.request("/api/recommendation/visit", body=visit)
        self.assertEqual(status, 200)
        contact = {"presentation_id": pid, "visit_id": visit["visit_id"], "stage_id": "stage-a"}
        status, result = self.request("/api/recommendation/contact", body=contact)
        self.assertEqual(status, 200)
        self.assertFalse(result["duplicate"])
        status, result = self.request("/api/recommendation/contact", body=contact)
        self.assertTrue(result["duplicate"])
        status, _ = self.request("/api/recommendation/contact", body=contact, user=1)
        self.assertEqual(status, 400)

    def test_exposure_post_keeps_screen_cache_and_rejects_extra_fields(self):
        pid = self.presentation()
        body = {"presentation_id": pid, "visit_id": "i" * 24, "source": "cache"}
        self.srv.screen_cache_set(self.users[0][0], "exposure-sentinel", {"ok": True})
        with patch.object(self.srv, "invalidate_user_cache") as invalidate:
            self.assertEqual(self.request("/api/recommendation/visit", body=body)[0], 200)
            invalidate.assert_not_called()
        self.assertIsNotNone(self.srv.screen_cache_get(self.users[0][0], "exposure-sentinel"))
        self.assertEqual(self.request("/api/recommendation/visit", body={**body, "user_id": "spoof"})[0], 400)

    def test_missing_invalid_and_revoked_cookie_cannot_claim_another_presentation(self):
        import auth as AU
        pid = self.presentation()
        visit = {"presentation_id": pid, "visit_id": "m" * 24, "source": "network"}
        self.assertEqual(self.request("/api/recommendation/visit", body=visit)[0], 200)
        contact = {"presentation_id": pid, "visit_id": visit["visit_id"], "stage_id": "stage-a"}
        revoked = AU.create_session(self.users[0][0])
        AU.revoke_session(revoked)
        # The existing public demo creates a fresh guest for a missing/invalid
        # session. That guest must never acquire the old guest's presentation.
        with patch.object(DS.S, "_seed_demo"):
            for cookie in ("", "tg_session=invalid-session", "tg_session=" + revoked):
                with self.subTest(cookie_kind="missing" if not cookie else "invalid_or_revoked"):
                    self.assertEqual(self.request("/api/recommendation/visit", body=visit,
                                                  extra={"Cookie": cookie})[0], 400)
                    self.assertEqual(self.request("/api/recommendation/contact", body=contact,
                                                  extra={"Cookie": cookie})[0], 400)
        self.assertEqual(self.srv.exposure_con.execute(
            "SELECT count(*) FROM recommendation_contacts WHERE presentation_id=?", (pid,)).fetchone()[0], 0)

    def test_storage_failure_does_not_break_ui_or_event_response(self):
        pid = self.presentation()
        with patch.object(self.srv.exposure, "register", side_effect=sqlite3.OperationalError("disk full")):
            self.assertEqual(self.srv.register_exposure(self.users[0][0], [{"stage_id": "other"}], []), "")
        with patch.object(self.srv.exposure, "fetched", side_effect=sqlite3.OperationalError("disk full")):
            self.srv.record_exposure_fetch(self.users[0][0], '<div data-exposure-presentation="' + pid + '">')
        with patch.object(self.srv.exposure, "begin", side_effect=sqlite3.OperationalError("disk full")):
            status, result = self.request("/api/recommendation/visit", body={"presentation_id": pid, "visit_id": "k" * 24, "source": "cache"})
            self.assertEqual(status, 200)
            self.assertTrue(result["disabled"])

    def test_recommendation_http_recomputes_and_logs_each_delivery(self):
        import app as APP
        self.srv.invalidate_user_cache(self.users[0][0])
        before = self.srv.exposure_con.execute("SELECT count(*) FROM recommendation_fetches").fetchone()[0]
        def render(user, prefs):
            pid = self.srv.register_exposure(user, [{"stage_id": "stage-http"}], prefs)
            return '<section data-exposure-presentation="' + pid + '"><article data-stage="stage-http"></article></section>'
        with patch.object(APP, "_recommend_body", side_effect=render) as rendered:
            status, first = self.request("/api/screen/recommend")
            self.assertEqual(status, 200, first)
            status, second = self.request("/api/screen/recommend")
            self.assertEqual(status, 200, second)
            self.assertNotEqual(first["body_html"], second["body_html"])
            self.assertEqual(rendered.call_count, 2)
        after = self.srv.exposure_con.execute("SELECT count(*) FROM recommendation_fetches").fetchone()[0]
        self.assertEqual(after - before, 2)

    def test_fill_preserves_candidate_order_and_legacy_owner_only_recording(self):
        import app as APP
        import render_recommend as RR
        candidates = [{"stage_id": "already"}, {"stage_id": "fill-next"}, {"stage_id": "fill-last"}]
        with patch.object(APP, "_load", return_value=({}, None)), patch.object(RR, "filtered", return_value=(candidates, 3)), patch.object(RR, "card", return_value='<article class="ticket recommend" data-stage="fill-next"></article>') as card, patch.object(self.srv, "record_presented") as legacy:
            result = self.srv.fill_slot(self.users[0][0], ["already"], "already")
            legacy.assert_not_called()
            card.assert_called_once_with(2, candidates[1])
        self.assertIn('data-exposure-presentation=', result["html"])
        row = self.srv.exposure_con.execute("SELECT stage_id,rank FROM recommendation_candidates WHERE stage_id='fill-next'").fetchone()
        self.assertEqual(row, ("fill-next", 2))

    def test_exposure_database_is_outside_replaceable_catalog(self):
        path = self.srv.exposure_con.execute("PRAGMA database_list").fetchone()[2]
        self.assertEqual(Path(path), Path(self.exposure_tmp.name) / "exposure.db")
        self.assertNotIn("data", Path(path).parts)

    def test_local_layout_embeds_shared_tracker_and_start(self):
        import app as APP
        with patch.object(APP, "ROOT", Path(__file__).resolve().parents[2]):
            html = APP.layout("おすすめ", "/recommend", "<p>fixture</p>", "")
        self.assertIn('global.TaguriExposure =', html)
        self.assertIn('TaguriExposure.start(document,"local")', html)

    def test_local_endpoint_requires_server_token_and_uses_local_identity(self):
        import auth as AU
        pid = self.srv.exposure.register(AU.LOCAL_USER_ID, [{"stage_id": "local-stage"}], [])
        visit = {"presentation_id": pid, "visit_id": "l" * 24, "source": "local"}
        with patch.object(self.srv, "public", False):
            self.assertEqual(self.request("/api/recommendation/visit", body=visit)[0], 403)
            self.assertEqual(self.request("/api/recommendation/visit", body=visit, extra={"X-Taguri-Token": self.srv.token})[0], 200)
            contact = {"presentation_id": pid, "visit_id": visit["visit_id"], "stage_id": "local-stage"}
            self.assertEqual(self.request("/api/recommendation/contact", body=contact, extra={"X-Taguri-Token": self.srv.token})[0], 200)
        recorded = self.srv.exposure_con.execute("SELECT user_id FROM recommendation_contacts WHERE stage_id='local-stage'").fetchone()
        self.assertEqual(recorded[0], AU.LOCAL_USER_ID)

    def test_exposure_origin_and_json_guards(self):
        pid = self.presentation()
        body = {"presentation_id": pid, "visit_id": "j" * 24, "source": "network"}
        self.assertEqual(self.request("/api/recommendation/visit", body=body, origin="https://foreign.invalid")[0], 403)
        self.assertEqual(self.request("/api/recommendation/visit", body=body, ctype="text/plain")[0], 415)
        self.assertEqual(self.request("/api/recommendation/visit", raw=b"[]")[0], 400)

    def test_public_telemetry_preflight_and_session_cookie_allow_credentials(self):
        handler = object.__new__(DS.S.Handler)
        handler.server = self.srv
        self.assertEqual(handler._cors_headers(), {
            "Access-Control-Allow-Origin": "https://island-6848.github.io",
            "Access-Control-Allow-Credentials": "true", "Vary": "Origin"})
        with patch.object(handler, "_send") as send:
            handler.do_OPTIONS()
        args = send.call_args.args
        self.assertEqual(args[:3], (204, b"", "text/plain"))
        self.assertIn("POST", args[3]["Access-Control-Allow-Methods"])
        self.assertIn("Content-Type", args[3]["Access-Control-Allow-Headers"])
        cookie = handler._set_session_cookie("fixture-token")["Set-Cookie"]
        for attribute in ("HttpOnly", "SameSite=None", "Secure"):
            self.assertIn(attribute, cookie)


if __name__ == "__main__":
    unittest.main()
