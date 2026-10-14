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
        self.assertEqual(put, [('1.jpg', 'image/jpeg'), ('2.png', 'image/png')])
        sql = (self.out / 'posters-upload.sql').read_text(encoding='utf-8')
        self.assertIn("('1','1.jpg')", sql)
        DP.commit(self.data, self.out)
        put.clear()
        again = DP.build(self.data, self.out, bucket='b', limit=10, put=lambda a, t, b, k, body, ct: put.append(k))
        self.assertEqual((again['uploaded'], again['already'], put), (1, 2, ['3.jpg']))

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
