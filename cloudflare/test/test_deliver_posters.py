"""deliver_posters: uploads only new files, stops safely without R2 access, writes D1 rows."""
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import deliver_posters as DP  # noqa: E402


class DeliverPostersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / 'data'
        img = self.data / 'review' / 'img'
        img.mkdir(parents=True)
        for n in ('1.jpg', '2.png', '3.jpg'):
            (img / n).write_bytes(b'x')
        self.out = Path(self.tmp.name) / 'out'

    def tearDown(self):
        self.tmp.cleanup()

    def test_uploads_new_files_then_skips_them(self):
        put = []
        got = DP.build(self.data, self.out, bucket='b', limit=2, put=lambda a, t, b, k, body, ct: put.append((k, ct)))
        self.assertEqual(got['uploaded'], 2)
        self.assertEqual(put, [('3.jpg', 'image/jpeg'), ('2.png', 'image/png')])   # 新しい公演（番号の大きいほう）から
        sql = (self.out / 'posters-upload.sql').read_text(encoding='utf-8')
        self.assertIn("('3','3.jpg')", sql)
        DP.commit(self.data, self.out)
        put.clear()
        again = DP.build(self.data, self.out, bucket='b', limit=10, put=lambda a, t, b, k, body, ct: put.append(k))
        self.assertEqual((again['uploaded'], again['already'], put), (1, 2, ['1.jpg']))

    def test_a_passing_r2_error_is_retried_and_the_rest_still_goes(self):
        # Catalog #12（2026-10-18）: HTTP 500 が 1 回出ただけで、残りを全部見送っていた
        calls, waits = [], []

        def flaky(a, t, b, k, body, ct):
            calls.append(k)
            if len(calls) == 1:
                raise urllib.error.HTTPError('u', 500, 'Internal Server Error', {}, None)

        got = DP.build(self.data, self.out, bucket='b', limit=10, put=flaky, sleep=waits.append)
        self.assertEqual(got['stopped'], '')
        self.assertEqual(waits, [DP.RETRY_WAITS[0]])
        self.assertEqual(got['left'], 0)
        self.assertGreaterEqual(got['uploaded'], 2)

    def test_r2_keeps_failing_stops_after_the_retries(self):
        waits = []

        def down(a, t, b, k, body, ct):
            raise urllib.error.HTTPError('u', 503, 'Unavailable', {}, None)

        got = DP.build(self.data, self.out, bucket='b', limit=10, put=down, sleep=waits.append)
        self.assertIn('HTTP 503', got['stopped'])
        self.assertEqual(waits, list(DP.RETRY_WAITS))
        self.assertEqual(got['uploaded'], 0)
        self.assertGreater(got['left'], 0)

    def test_retries_stop_at_the_class_a_cap(self):
        # issue #139: 上限の 2 回手前で R2 が 5xx を返し続けても、やり直しで上限を越えない
        FT = DP.FT
        u = FT.load(self.data)
        u['r2']['class_a'][FT.month()] = FT.CAPS['r2_class_a_month'] - 2
        FT.save(self.data, u)
        calls = []

        def down(a, t, b, k, body, ct):
            calls.append(k)
            raise urllib.error.HTTPError('u', 503, 'Unavailable', {}, None)

        got = DP.build(self.data, self.out, bucket='b', limit=10, put=down, sleep=lambda s: None)
        self.assertEqual(len(calls), 2)
        self.assertEqual(FT.r2_class_a(FT.load(self.data)), FT.CAPS['r2_class_a_month'])
        self.assertIn('上限', got['stopped'])
        self.assertEqual(got['uploaded'], 0)

    def test_no_r2_access_changes_nothing(self):
        def deny(*_a):
            raise urllib.error.HTTPError('u', 403, 'Forbidden', {}, None)
        got = DP.build(self.data, self.out, bucket='b', limit=10, put=deny)
        self.assertEqual(got['uploaded'], 0)
        self.assertIn('403', got['stopped'])
        self.assertFalse((self.out / 'posters-upload.sql').exists())
        self.assertEqual(json.loads((self.out / 'pending.json').read_text()), {})


if __name__ == '__main__':
    unittest.main()
