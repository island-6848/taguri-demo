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

    def test_title_pairs_newest_first_and_shared_with_the_worker(self):
        # 題名の途中の語でも引けるように、題名の鍵の 2 文字ずつの組 → 公演（起案者の指示 2026-10-24）
        t = PI.title_shards(self.d)
        def lookup(g):
            return t.get(PI.shard_of(g), {}).get('grams', {}).get(g, [])
        self.assertEqual(lookup('の果'), ['31', '30'])          # 新しい番号が先
        self.assertEqual(lookup('果て'), ['31', '30'])
        self.assertEqual(lookup('劇団'), [])                    # 団体の名前は入れない（題名だけ）
        self.assertEqual([PI.shard_of('果て'), PI.shard_of('白酒')], [0xd7, 0x18])   # stage-search.test.js の gramShard と同じ値

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
        self.assertEqual(r['sent'], r['shards'] + r['title_shards'])   # 初回はすべて（名前の索引と題名の索引）
        self.assertTrue(all(k.startswith(('pastidx/v1/', 'pasttitle/v1/')) and k.endswith('.json') for k, _ in sent))
        sent.clear()
        self.assertEqual(PI.deliver(self.d, bucket='b', put=put)['sent'], 0)
        rows = ROWS + [{"stage_id": "32", "title": "新しい舞台", "start": "2025-01-01", "end": "2025-01-02", "fields": {"出演": "上村聡"}}]
        (self.d / 'past' / 'stages.jsonl').write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n', encoding='utf-8')
        r = PI.deliver(self.d, bucket='b', put=put)
        names = [k for k, _ in sent if k.startswith('pastidx/v1/')]
        self.assertEqual(names, [f"pastidx/v1/{PI.shard_of(PI.nz('上村聡')):02x}.json"])   # 名前は「上村聡」の入ったファイルだけ
        # 題名は「新しい舞台」の組の入ったファイルだけ
        want = sorted({f"pasttitle/v1/{PI.shard_of(g):02x}.json" for g in ('新し', 'しい', 'い舞', '舞台')})
        self.assertEqual(sorted(k for k, _ in sent if k.startswith('pasttitle/v1/')), want)


if __name__ == '__main__':
    unittest.main()
