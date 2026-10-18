"""free_tier: Actions minutes never plan past the cap; R2 and D1 stop before their caps."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import deliver_posters as DP  # noqa: E402
import free_tier as FT  # noqa: E402

NOW = dt.datetime(2026, 10, 14, 19, 30, tzinfo=dt.timezone.utc)


class ActionsTest(unittest.TestCase):
    def test_minutes_round_up_per_job_and_count_running_jobs(self):
        runs = {'workflow_runs': [{'id': 1}, {'id': 2}]}
        jobs = {
            1: {'jobs': [{'started_at': '2026-10-14T19:00:00Z', 'completed_at': '2026-10-14T19:00:01Z'},
                         {'started_at': '2026-10-13T10:00:00Z', 'completed_at': '2026-10-13T11:30:30Z'}]},
            2: {'jobs': [{'started_at': '2026-10-14T19:20:00Z', 'completed_at': None},   # still running
                         {'started_at': None}]},
        }

        def get(url, _token):
            return jobs[int(url.split('/runs/')[1].split('/')[0])] if '/jobs' in url else runs
        by_day = FT.job_minutes_by_day('o/r', 't', NOW, get=get)
        self.assertEqual(by_day[0], 1 + 10)
        self.assertEqual(by_day[1], 91)

    def test_every_31_day_window_stays_under_the_cap(self):
        # Whatever was used, a plan's own minutes plus the Catalog estimate never break any window.
        for used in ([0] * 31, [200] + [0] * 30, [45] * 31, [0] * 30 + [900], [140] * 10 + [0] * 21):
            for mode in ('daily', 'weekly'):
                p = FT.plan(list(used), mode)
                if not p['run']:
                    continue
                today = (used[0] + FT.CATALOG_MINUTES[p['mode']] + p['past_minutes'] + FT.AFTER_PAST_MINUTES
                         + (p.get('poster_minutes', 0) + FT.POSTER_AFTER_MINUTES if p.get('poster_minutes') else 0))
                for k in range(31):
                    window = today + sum(used[1:31 - k]) + FT.future_catalog(k)
                    self.assertLessEqual(window, FT.CAPS['actions_minutes_31d'], (used[:3], mode, k))

    def test_past_posters_share_the_room(self):
        # 起案者の指示 2026-10-16「過去の公演の全てのポスターデータも欲しい」: 余裕があれば毎日回し、少なければ回さない
        self.assertEqual(FT.plan([0] * 31, 'daily')['poster_minutes'], FT.POSTER_MAX_MINUTES)
        tight = FT.plan([44] * 31, 'daily')
        if tight['run']:
            self.assertLessEqual(tight['poster_minutes'], tight['past_minutes'] or FT.POSTER_MAX_MINUTES)

    def test_heavy_recent_days_do_not_stop_the_daily_update(self):
        # Catalog #11（2026-10-17）: 直近 5 日で 682 分。先の週 1 の上乗せまで数えて、毎日の更新まで止まっていた
        used = [1, 175, 180, 170, 156] + [0] * 26
        for mode in ('daily', 'weekly'):
            p = FT.plan(list(used), mode)
            self.assertTrue(p['run'], (mode, p))

    def test_stops_when_the_cap_is_near(self):
        p = FT.plan([60] * 31, 'daily')
        self.assertFalse(p['run'])
        self.assertEqual(p['past_minutes'], 0)

    def test_weekly_falls_back_to_daily_and_past_shrinks(self):
        p = FT.plan([0] * 20 + [350] + [0] * 10, 'weekly')
        self.assertTrue(p['run'])
        self.assertLessEqual(p['past_minutes'], FT.PAST_MAX_MINUTES)
        # Lots of room at the start of a window: past stages get the full day.
        self.assertEqual(FT.plan([0] * 31, 'daily')['past_minutes'], FT.PAST_MAX_MINUTES)

    def test_unknown_usage_reads_no_past_stages(self):
        p = FT.plan(None, 'weekly')
        self.assertEqual((p['run'], p['mode'], p['past_minutes']), (True, 'daily', 0))


    def test_index_only_run_reads_nothing_and_keeps_the_daily_reserve(self):
        # 索引だけの手動実行（q-index-load-now）: 取り直しも過去の公演も読まない
        p = FT.plan([0] * 31, 'index')
        self.assertEqual((p['run'], p['mode'], p['past_minutes'], p['catalog_minutes']), (True, 'index', 0, 1))
        self.assertFalse(FT.plan([60] * 31, 'index')['run'])
        self.assertFalse(FT.plan(None, 'index')['run'])

    def test_replay_runs_only_with_room_left_after_the_daily_updates(self):
        self.assertTrue(FT.plan([0] * 31, 'replay')['run'])
        self.assertFalse(FT.plan(None, 'replay')['run'])
        # 毎日の更新の分（31 日 × 15 分）と今日の分を取っておくと、残りが REPLAY_MINUTES に足りない
        tight = FT.CAPS['actions_minutes_31d'] - FT.future_catalog(30) - FT.CATALOG_MINUTES['daily'] - FT.REPLAY_MINUTES + 1
        self.assertFalse(FT.plan([tight] + [0] * 30, 'replay')['run'])
        self.assertTrue(FT.plan([tight - 1] + [0] * 30, 'replay')['run'])

class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / 'data'
        img = self.data / 'review' / 'img'
        img.mkdir(parents=True)
        for n in ('1.jpg', '2.jpg', '3.jpg'):
            (img / n).write_bytes(b'x' * 100)
        self.out = Path(self.tmp.name) / 'out'
        self.caps = dict(FT.CAPS)

    def tearDown(self):
        FT.CAPS.clear()
        FT.CAPS.update(self.caps)
        self.tmp.cleanup()

    def test_the_estimate_is_replaced_by_what_d1_counted(self):
        # d1-upsert-counts: 書く前に見積もりを足し、入れ終えたら D1 の rows_written に置き換える
        day = FT.today(NOW)
        FT.d1_spend(self.data, 10_000, NOW)          # an earlier delivery the same day
        FT.d1_spend(self.data, 27_578, NOW)          # this one's estimate
        self.assertEqual(FT.d1_settle(self.data, day, 27_578, 15_548), 25_548)
        # A count above the estimate is taken too (never less than what D1 says).
        self.assertEqual(FT.d1_settle(self.data, day, 100, 400), 25_848)
        log = '🚣 Executed 14 queries ("Rows written": 8706)\n[{"meta": {"rows_read": 8615, "rows_written": 8706}}]'
        self.assertEqual(FT.rows_written(log), 8706)
        self.assertIsNone(FT.rows_written('✘ [ERROR] Upstream service unavailable [code: 7009]'))

    def test_d1_writes_are_counted_per_utc_day(self):
        FT.d1_spend(self.data, 70_000, NOW)
        self.assertEqual(FT.d1_left(self.data, NOW), FT.CAPS['d1_writes_day'] - 70_000)
        self.assertEqual(FT.d1_left(self.data, NOW + dt.timedelta(days=1)), FT.CAPS['d1_writes_day'])

    def test_r2_storage_cap_stops_uploads(self):
        FT.CAPS['r2_bytes'] = 250
        put = []
        got = DP.build(self.data, self.out, bucket='b', limit=10, put=lambda *a: put.append(a[3]))
        self.assertEqual((got['uploaded'], put), (2, ['1.jpg', '2.jpg']))
        self.assertIn('保存', got['stopped'])
        u = FT.load(self.data)
        self.assertEqual((FT.r2_bytes(u), FT.r2_class_a(u)), (200, 2))

    def test_r2_class_a_cap_counts_failed_puts(self):
        FT.CAPS['r2_class_a_month'] = 1

        def fail(*_a):
            raise OSError('reset')
        got = DP.build(self.data, self.out, bucket='b', limit=10, put=fail)
        self.assertEqual(got['uploaded'], 0)
        self.assertEqual(FT.r2_class_a(FT.load(self.data)), 1)
        again = DP.build(self.data, self.out, bucket='b', limit=10, put=lambda *a: None)
        self.assertEqual(again['uploaded'], 0)
        self.assertIn('書き込み', again['stopped'])

    def test_posters_respect_the_d1_day(self):
        FT.d1_spend(self.data, FT.CAPS['d1_writes_day'] - 4)
        got = DP.build(self.data, self.out, bucket='b', limit=10, put=lambda *a: None)
        self.assertEqual(got['uploaded'], 2)
        self.assertEqual(FT.d1_left(self.data), 0)

    @unittest.skipUnless(__import__('importlib').util.find_spec('PIL'), 'Pillow が無い環境では縮めない（元のまま入れる）')
    def test_posters_are_shrunk_to_webp_and_old_ones_reshrunk(self):
        from PIL import Image
        import io
        img = self.data / 'review' / 'img'
        for f in img.iterdir():
            f.unlink()
        def jpeg(w, h):
            b = io.BytesIO(); Image.new('RGB', (w, h), (120, 30, 40)).save(b, 'JPEG', quality=95); return b.getvalue()
        (img / '10.jpg').write_bytes(jpeg(1200, 1700))          # これからの公演
        (img / '20.jpg').write_bytes(jpeg(1200, 1700))          # 終わった公演（粗め）
        (self.data / 'review' / 'candidates.jsonl').write_text(
            '{"stage_id": "10", "period": "2099/01/01 ～ 2099/01/05"}\n{"stage_id": "20", "period": "2020/01/01 ～ 2020/01/05"}\n',
            encoding='utf-8')
        store = {}
        got = DP.build(self.data, self.out, bucket='b', limit=10, put=lambda a, t, b, k, body, ct: store.__setitem__(k, (body, ct)))
        self.assertEqual(sorted(store), ['10.webp', '20.webp'])
        self.assertEqual(store['10.webp'][1], 'image/webp')
        w10 = Image.open(io.BytesIO(store['10.webp'][0])).width
        w20 = Image.open(io.BytesIO(store['20.webp'][0])).width
        self.assertEqual((w10, w20), (DP.UPCOMING['width'], DP.ENDED['width']))
        self.assertIn("('10','10.webp')", (self.out / 'posters-upload.sql').read_text(encoding='utf-8'))
        # すでに R2 に大きいまま入っている分は、取り出して縮め直し、古いものを消す
        DP.commit(self.data, self.out)
        (self.data / 'r2' / 'posters.json').write_text('{"30": "30.jpg"}', encoding='utf-8')
        u = FT.load(self.data); u['r2']['sizes']['30.jpg'] = 500_000; FT.save(self.data, u)
        deleted = []
        again = DP.build(self.data, self.out, bucket='b', limit=10, reshrink=5,
                         put=lambda a, t, b, k, body, ct: store.__setitem__(k, (body, ct)),
                         get=lambda a, t, b, k: jpeg(1200, 1700), delete=lambda a, t, b, k: deleted.append(k))
        self.assertEqual((again['reshrunk'], deleted), (1, ['30.jpg']))
        u = FT.load(self.data)
        self.assertNotIn('30.jpg', u['r2']['sizes'])
        self.assertEqual(FT.r2_class_b(u), 1)
        self.assertIn('"30": "30.webp"', (self.out / 'pending.json').read_text(encoding='utf-8'))

    def test_check_flags_over_eighty_percent_and_unread_minutes(self):
        FT.d1_spend(self.data, int(FT.CAPS['d1_writes_day'] * 0.9), NOW)
        rows = {r['what']: r for r in FT.check(self.data, None, {'r2_get:2026-10': 10}, NOW)}
        self.assertFalse(rows['D1 の書き込み（今日・取得の分）']['ok'])
        self.assertFalse(rows['GitHub Actions（直近 31 日・分）']['ok'])
        self.assertTrue(rows['R2 の Class B（今月・Worker と取得の合計）']['ok'])
        self.assertEqual(json.loads((self.data / FT.LEDGER).read_text())['d1_writes'], {'2026-10-14': 72000})


if __name__ == '__main__':
    unittest.main()
