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
                today = used[0] + FT.CATALOG_MINUTES[p['mode']] + p['past_minutes'] + FT.AFTER_PAST_MINUTES
                for k in range(31):
                    window = today + sum(used[1:31 - k]) + FT.future_catalog(k)
                    self.assertLessEqual(window, FT.CAPS['actions_minutes_31d'], (used[:3], mode, k))

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

    def test_check_flags_over_eighty_percent_and_unread_minutes(self):
        FT.d1_spend(self.data, int(FT.CAPS['d1_writes_day'] * 0.9), NOW)
        rows = {r['what']: r for r in FT.check(self.data, None, {'r2_get:2026-10': 10}, NOW)}
        self.assertFalse(rows['D1 の書き込み（今日・取得の分）']['ok'])
        self.assertFalse(rows['GitHub Actions（直近 31 日・分）']['ok'])
        self.assertTrue(rows['R2 の Class B（今月・Worker）']['ok'])
        self.assertEqual(json.loads((self.data / FT.LEDGER).read_text())['d1_writes'], {'2026-10-14': 72000})


if __name__ == '__main__':
    unittest.main()
