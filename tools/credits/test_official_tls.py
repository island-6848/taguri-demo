"""公式サイトの取得が、証明書とホスト名を確かめていることの検査（#179）。

手元に HTTPS の仮サーバーを立て、自己署名・期限切れ・ホスト名違いの証明書を
**取得失敗として控える**ことを確かめる。外部へは通信しない。証明書は試験のたびに
openssl で作る（無い環境では飛ばす）。

    python3 tools/credits/test_official_tls.py
"""
from __future__ import annotations

import http.server
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_official_credits as F                                   # noqa: E402

F.PH.INTERVAL = 0.0            # 試験を速くする（本番は 1.1 秒）

CA_CONF = """[ca]
default_ca = d
[d]
dir = {dir}
database = {dir}/index.txt
new_certs_dir = {dir}
serial = {dir}/serial
default_md = sha256
policy = p
copy_extensions = copy
unique_subject = no
x509_extensions = leaf
[leaf]
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid
[p]
commonName = supplied
"""


def _ssl(*args: str, cwd: Path) -> None:
    subprocess.run(["openssl", *args], cwd=cwd, check=True, capture_output=True)


def _leaf(d: Path, name: str, san: str, *, start: str = "", end: str = "") -> None:
    """CA が署名した証明書を作る。`start`/`end` を渡すと有効期間をその日付にする。"""
    _ssl("req", "-newkey", "rsa:2048", "-nodes", "-keyout", f"{name}.key", "-out", f"{name}.csr",
         "-subj", f"/CN={name}", "-addext", f"subjectAltName={san}", cwd=d)
    dates = ["-startdate", start, "-enddate", end] if start else ["-days", "1"]
    _ssl("ca", "-batch", "-config", "ca.cnf", "-cert", "ca.crt", "-keyfile", "ca.key",
         "-in", f"{name}.csr", "-out", f"{name}.crt", *dates, cwd=d)


class _H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.server.hits.append(self.path)
        if self.path == "/robots.txt":
            self.send_response(404)
            self.end_headers()
            return
        body = "<html><body>美術 ある名前</body></html>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)


@unittest.skipUnless(shutil.which("openssl"), "openssl が無い")
class OfficialTlsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp())
        d = cls.dir
        (d / "ca.cnf").write_text(CA_CONF.format(dir=d), encoding="utf-8")
        (d / "index.txt").write_text("", encoding="utf-8")
        (d / "serial").write_text("01\n", encoding="utf-8")
        _ssl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "ca.key", "-out", "ca.crt",
             "-days", "2", "-subj", "/CN=test-ca",
             "-addext", "keyUsage=critical,keyCertSign,cRLSign", cwd=d)
        _leaf(d, "good", "IP:127.0.0.1")
        _leaf(d, "other", "DNS:other.example")
        _leaf(d, "expired", "IP:127.0.0.1", start="20200101000000Z", end="20200102000000Z")
        _ssl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "self.key", "-out", "self.crt",
             "-days", "1", "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1", cwd=d)
        # 試験用の CA だけを足す。**検証そのものは本番と同じ context が行う**
        F._ctx.load_verify_locations(str(d / "ca.crt"))

    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.patches = [patch.object(F, "CACHE", tmp / "pages"),
                        patch.object(F, "FAILS", tmp / "fail.json"),
                        patch.object(F, "_fails", None),
                        patch.object(F, "_fail_dirty", False)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def _serve(self, name: str) -> tuple[str, list]:
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _H)
        srv.hits = []
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(self.dir / f"{name}.crt"), str(self.dir / f"{name}.key"))
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        return f"https://127.0.0.1:{srv.server_address[1]}/stage", srv.hits

    def test_valid_certificate_is_fetched(self):
        url, _ = self._serve("good")
        html, err = F.get(url)
        self.assertEqual(err, "")
        self.assertIn("美術", html)

    def test_bad_certificates_are_recorded_as_failures(self):
        for name in ("self", "expired", "other"):
            with self.subTest(cert=name):
                url, hits = self._serve(name)
                html, err = F.get(url)
                self.assertEqual(html, "")
                self.assertNotEqual(err, "")
                self.assertIn(url, F._load_fails())
                self.assertNotIn("/stage", hits)


if __name__ == "__main__":
    unittest.main()
