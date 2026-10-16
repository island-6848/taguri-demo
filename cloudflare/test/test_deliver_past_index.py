"""deliver_past_index: names → past stages, split into 256 R2 files; unchanged files are not sent again."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('deliver_past_index', HERE.parent / 'scripts' / 'deliver_past_index.py')
PI = importlib.util.module_from_spec(spec)
sys.modules['deliver_past_index'] = PI
spec.loader.exec_module(PI)

ROWS = [
    {"stage_id": "30", "title": "夜の果て", "start": "2024-03-01", "end": "2024-03-10", "theater": "本多劇場",
     "group": "劇団あおば", "pref": "東京都", "fields": {"出演": "上村 聡、鈴木花子", "演出": "上村聡史"}},
    {"stage_id": "31", "title": "夜の果て", "start": "2024-04-01", "end": "2024-04-03", "theater": "梅田劇場",
     "group": "劇団あおば", "pref": "大阪府", "fields": {"出演": "上村聡"}},
]


class PastIndexTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.d = Path(self.t.name)
        (self.d / 'past').mkdir()
        (self.d / 'past' / 'stages.jsonl').write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in ROWS) + '\n', encoding='utf-8')

    def tearDown(self):
        self.t.cleanup()

    def test_names_whole_and_shared_with_the_worker(self):
        s = PI.shards(self.d)
        def lookup(name):
            k = PI.nz(name)
            return s.get(PI.shard_of(k), {}).get('names', {}).get(k, [])
        self.assertEqual(lookup('上村聡'), ['30', '31'])        # 「上村 聡」も同じ名前
        self.assertEqual(lookup('上村聡史'), ['30'])            # 別人は別の名前
        self.assertEqual(lookup('劇団あおば'), ['30', '31'])
        sh = s[PI.shard_of(PI.nz('上村聡'))]
        self.assertEqual(sh['stages']['31'][:4], ['夜の果て', sh['stages']['31'][1], '2024-04-01', '2024-04-03'])
        # Worker の lists.pastShard と同じ値になること（FNV-1a）。値は JS で求めたもの（lists-screen.test.js と同じ）
        self.assertEqual(PI.shard_of('上村聡'), 0x9b)

    def test_only_changed_files_are_sent(self):
        sent = []
        put = lambda account, token, bucket, key, body, ctype: sent.append((key, body))
        r = PI.deliver(self.d, bucket='b', put=put)
        self.assertEqual(r['sent'], r['shards'])                # 初回はすべて
        self.assertTrue(all(k.startswith('pastidx/v1/') and k.endswith('.json') for k, _ in sent))
        sent.clear()
        self.assertEqual(PI.deliver(self.d, bucket='b', put=put)['sent'], 0)
        rows = ROWS + [{"stage_id": "32", "title": "新しい舞台", "start": "2025-01-01", "end": "2025-01-02", "fields": {"出演": "上村聡"}}]
        (self.d / 'past' / 'stages.jsonl').write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n', encoding='utf-8')
        r = PI.deliver(self.d, bucket='b', put=put)
        self.assertEqual(r['sent'], 1)                          # 変わったのは「上村聡」の入ったファイルだけ
        self.assertIn(f"pastidx/v1/{PI.shard_of(PI.nz('上村聡')):02x}.json", [k for k, _ in sent])


if __name__ == '__main__':
    unittest.main()
