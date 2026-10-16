"""過去の公演のポスター（posters.fetch_past、起案者の指示 2026-10-16「過去の公演の全てのポスターデータも欲しい」）。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import posters as P  # noqa: E402

IMG_URL = "https://stage-image.corich.jp/img_stage/l/409/stage_409242.jpg"
PAGE = f'<img src="https://stage-image.corich.jp/img_stage/m/1/nophoto_stage.png"><img src="{IMG_URL}">'


class PastPosterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = (P.IMG, P.PAST_URLS, P.uploaded, P.shrink)
        P.IMG, P.PAST_URLS = self.tmp / "img", self.tmp / "poster_urls.json"
        P.uploaded = lambda: {"9": "9.webp"}
        P.shrink = lambda path: False
        self.pages, self.images = [], []

    def tearDown(self):
        P.IMG, P.PAST_URLS, P.uploaded, P.shrink = self.saved

    def run_past(self, rows, **kw):
        page = lambda sid: (self.pages.append(sid), PAGE)[1]
        image = lambda url: (self.images.append(url), b"jpg")[1]
        return P.fetch_past(rows=rows, page=page, image=image, **kw)

    def test_reads_the_page_only_when_the_row_has_no_url_and_copies_shared_images(self):
        rows = [{"stage_id": "1"}, {"stage_id": "2", "poster": IMG_URL}, {"stage_id": "3", "poster": ""},
                {"stage_id": "9", "poster": IMG_URL}]
        n = self.run_past(rows)
        self.assertEqual(self.pages, ["1"])                    # 2 は行に URL がある、3 は画像なし、9 は R2 に入れ終えた
        self.assertEqual(self.images, [IMG_URL])               # 同じ画像は 1 回だけ取る
        self.assertEqual((n["取得"], n["写し"], n["画像なし"], n["済み"]), (1, 1, 1, 1))
        self.assertTrue((P.IMG / "1.jpg").exists() and (P.IMG / "2.jpg").exists())
        self.assertEqual(json.loads(P.PAST_URLS.read_text(encoding="utf-8")), {"1": IMG_URL})
        # 2 回目は何も取らない（取り込んだもの・控えた URL は飛ばす）
        self.pages, self.images = [], []
        self.run_past(rows)
        self.assertEqual((self.pages, self.images), ([], []))

    def test_url_in_skips_nophoto(self):
        self.assertEqual(P.url_in(PAGE), IMG_URL)
        self.assertEqual(P.url_in('<img src="https://stage-image.corich.jp/img_stage/l/1/nophoto_stage.png">'), "")

    def test_limit_stops_early(self):
        self.run_past([{"stage_id": "1"}, {"stage_id": "4"}], limit=1)
        self.assertEqual(self.pages, ["1"])


if __name__ == "__main__":
    unittest.main()
