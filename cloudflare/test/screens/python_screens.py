"""Run screen scenarios on the Python app (the Render server) and print every
response as JSON. test/screens.test.js runs the same scenarios on the Worker
and must get the same screens.

    python3 cloudflare/test/screens/python_screens.py scenarios.json > answers.json

- service edition, public mode (like Render), temporary databases, no network;
- the code is copied into a temporary root so every path the app derives
  from its own location (data/...) points at the synthetic catalogue;
- the date is frozen (FROZEN_TODAY) for date.today() and datetime.now().
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import catalogue as CAT                                             # noqa: E402

FROZEN_TODAY = _dt.date.fromisoformat(CAT.TODAY)


class FrozenDate(_dt.date):
    @classmethod
    def today(cls):
        return cls(FROZEN_TODAY.year, FROZEN_TODAY.month, FROZEN_TODAY.day)


class FrozenDateTime(_dt.datetime):
    @classmethod
    def now(cls, tz=None):
        base = cls(FROZEN_TODAY.year, FROZEN_TODAY.month, FROZEN_TODAY.day, 12, 0, 0)
        return base.replace(tzinfo=tz) if tz else base

    @classmethod
    def today(cls):
        return cls.now()


def prepare_root() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="taguri-screens-"))
    shutil.copytree(REPO / "tools", tmp / "tools", ignore=shutil.ignore_patterns("__pycache__", "test_*"))
    for rel, text in CAT.files().items():
        path = tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (tmp / "state").mkdir()
    return tmp


def main() -> int:
    scenarios = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root = prepare_root()
    os.environ["TAGURI_STATE_DIR"] = str(root / "state")
    os.environ.pop("TAGURI_EXPOSURE_DB", None)
    # The app logs operational events to stdout; keep stdout for the answers.
    real_stdout, sys.stdout = sys.stdout, sys.stderr
    _dt.date = FrozenDate
    _dt.datetime = FrozenDateTime
    for sub in ("tools/taguri", "tools/review", "tools/lib", "tools/tickets", "tools/credits", "tools"):
        sys.path.insert(0, str(root / sub))
    import http.client
    from unittest.mock import patch
    import serve as S
    import auth as AU
    with patch("urllib.request.urlopen", side_effect=AssertionError("network")), \
         patch("http.server.ThreadingHTTPServer.__init__", return_value=None):
        srv = S.Server("service", 0, public=True, edition="service")
        srv.server_port = 8000
        out = []
        for sc in scenarios:
            # A fresh user per scenario (the Worker side signs in a fresh account).
            uid, _ = AU.access_or_register(AU.generate_recovery_code())
            token = AU.create_session(uid)
            srv.screen_cache.clear()
            steps = []
            for step in sc["steps"]:
                status, payload = request(srv, S, step, token)
                steps.append({"status": status, "body": clean(payload, srv.token)})
            out.append({"name": sc["name"], "steps": steps})
    json.dump(out, real_stdout, ensure_ascii=False, indent=1)
    shutil.rmtree(root, ignore_errors=True)
    return 0


def clean(payload, token):
    """Drop what differs by design between the two servers."""
    if isinstance(payload, dict):
        payload = {k: v for k, v in payload.items() if k not in ("storage",)}
    return json.loads(json.dumps(payload, ensure_ascii=False).replace(token, "__TAGURI_TOKEN__"))


def request(srv, S, step, token):
    import http.client
    path = step.get("get") or step.get("post")
    body = step.get("body")
    method = "POST" if "post" in step else "GET"
    data = json.dumps(body, ensure_ascii=False).encode() if method == "POST" else b""
    headers = {"Host": "127.0.0.1:8000", "Connection": "close", "Cookie": "tg_session=" + token,
               "Origin": "http://127.0.0.1:8000", "Content-Type": "application/json",
               "Content-Length": str(len(data))}
    raw = (method + " " + path + " HTTP/1.1\r\n" + "".join(k + ": " + v + "\r\n" for k, v in headers.items())
           + "\r\n").encode() + data

    class T:
        def __init__(self):
            self.output = bytearray()
        def makefile(self, *a):
            return io.BytesIO(raw)
        def sendall(self, d):
            self.output.extend(d)
    t = T()
    S.Handler(t, ("127.0.0.1", 12345), srv)

    class R:
        def makefile(self, *a):
            return io.BytesIO(t.output)
    res = http.client.HTTPResponse(R())
    res.begin()
    payload = res.read()
    if res.getheader("Content-Type", "").startswith("application/json"):
        return res.status, json.loads(payload)
    return res.status, payload.decode("utf-8", "replace")


if __name__ == "__main__":
    raise SystemExit(main())
