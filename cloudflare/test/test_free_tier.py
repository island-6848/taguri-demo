"""free_tier: Actions minutes never plan past the cap; R2 and D1 stop before their caps."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
        for used in ([0] * 31, [200] + [0] * 30, [45] * 31, [0] * 30 + [900], [140] * 10 + [0] * 21,
                     [1, 101, 1, 22, 146, 574, 1, 22, 98, 175, 360] + [0] * 20):
            for mode in ('daily', 'weekly'):
                p = FT.plan(list(used), mode)
                if not p['run']:
                    continue
                today = used[0] + FT.planned_minutes(p)
                for k in range(31):
                    window = today + sum(used[1:31 - k]) + FT.future_catalog(k)
                    # 下位の処理は余白（BACKGROUND_MARGIN）を残す: 見積もりより長くかかっても、毎日の更新の取り置きは残る
                    self.assertLessEqual(window, FT.CAPS['actions_minutes_31d'] - (FT.BACKGROUND_MARGIN if FT.planned_minutes(p) > FT.CATALOG_MINUTES['daily'] + (FT.WEEKLY_EXTRA if p['mode'] == 'weekly' else 0) else 0), (used[:3], mode, k))

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


    def test_stories_run_takes_what_is_left_after_the_daily_reserve(self):
        # 起案者の指示 2026-10-18「ページを取る時間を増やして」: 本文だけを取る実行（stories.yml）
        p = FT.plan([0] * 31, 'stories')
        self.assertEqual((p['run'], p['past_minutes']), (True, FT.STORIES_MAX_MINUTES))
        self.assertEqual(p['past_limit'], int(FT.STORIES_MAX_MINUTES * 60 / FT.PAST_SECONDS_PER_PAGE))
        # 毎日の更新の分を食わない: 残りが少なければ、その分だけ（10 分未満なら動かさない）
        small = FT.plan([46] * 31, 'stories')                 # 残り（上限 - 46×31 - 毎日の 15 分）。上限 1,500 なら 59 分
        left = FT.CAPS['actions_minutes_31d'] - 46 * 31 - FT.CATALOG_MINUTES['daily'] - FT.BACKGROUND_MARGIN
        self.assertEqual((small['run'], small['past_minutes']), (True, left - FT.STORIES_AFTER_MINUTES))
        self.assertFalse(FT.plan([60] * 31, 'stories')['run'])
        self.assertFalse(FT.plan(None, 'stories')['run'])

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
        tight = (FT.CAPS['actions_minutes_31d'] - FT.future_catalog(30) - FT.CATALOG_MINUTES['daily'] - FT.BACKGROUND_MARGIN
                 - FT.REPLAY_MINUTES + 1)
        self.assertFalse(FT.plan([tight] + [0] * 30, 'replay')['run'])
        self.assertTrue(FT.plan([tight - 1] + [0] * 30, 'replay')['run'])

    def test_restore_drill_runs_only_with_its_20_minutes_left(self):
        # 控えから戻す予行（restore-drill.yml）も、毎日の更新の分を取っておいて DRILL_MINUTES が残るときだけ（issue #139）
        self.assertTrue(FT.plan([0] * 31, 'drill')['run'])
        self.assertFalse(FT.plan(None, 'drill')['run'])
        tight = (FT.CAPS['actions_minutes_31d'] - FT.future_catalog(30) - FT.CATALOG_MINUTES['daily'] - FT.BACKGROUND_MARGIN
                 - FT.DRILL_MINUTES + 1)
        self.assertFalse(FT.plan([tight] + [0] * 30, 'drill')['run'])
        self.assertTrue(FT.plan([tight - 1] + [0] * 30, 'drill')['run'])

    def test_background_work_never_takes_the_daily_reserve(self):
        # dec-crawl-tiers: 下位の処理（過去の公演・ポスター）が残りを使い切っても、毎日の更新は次の日も動ける
        used = [0] * 31
        for day in range(40):
            p = FT.plan(list(used), 'daily')
            self.assertTrue(p['run'], (day, p))
            used = [FT.planned_minutes(p)] + used[:30]          # 計画の上限まで使い切った日が続く

    def test_lower_tiers_get_only_what_is_left_in_order(self):
        rich = FT.plan([0] * 31, 'daily')
        self.assertEqual((rich['catalog_minutes'], rich['discover_minutes']), (FT.CATALOG_MINUTES['daily'], FT.DISCOVER_MINUTES))
        self.assertEqual(rich['past_minutes'], FT.PAST_MAX_MINUTES)
        self.assertTrue(rich['past_index'])
        self.assertGreater(rich['upload_minutes'], 0)
        self.assertLessEqual(rich['upload_minutes'], FT.POSTER_UPLOAD_MAX_MINUTES)
        # 残りが少ない日: 過去の公演が先、ポスターはあと
        for n in range(30, 60):
            p = FT.plan([n] * 31, 'daily')
            if p['run'] and p['poster_minutes']:
                self.assertEqual(p['past_minutes'], FT.PAST_MAX_MINUTES, n)
        # 毎日の更新の分しか無い日: 下位の処理は 0、毎日の更新は動く
        cap, core = FT.CAPS['actions_minutes_31d'], FT.CATALOG_MINUTES['daily']
        just = [cap - core - FT.future_catalog(30)] + [0] * 30
        p = FT.plan(just, 'daily')
        self.assertEqual((p['run'], p['past_minutes'], p['poster_minutes'], p['upload_minutes'], p['past_index']),
                         (True, 0, 0, 0, False))

    def test_a_stopped_plan_does_not_fail_the_workflow(self):
        # 予算不足で止めるのはエラーではない（使う前に止めるのが守り）。毎日の更新が止まったときは issue で知らせる
        sent = []
        with mock.patch.object(FT, '_actions', return_value=[60] * 31), \
             mock.patch.object(FT, 'notify', side_effect=lambda t, b: sent.append(t)), \
             mock.patch.object(sys, 'argv', ['x', 'plan', '--mode', 'daily']), mock.patch('sys.stdout'):
            with mock.patch.dict('os.environ', {'TAGURI_PLAN_SOFT_STOP': '1'}):
                self.assertEqual(FT.main(), 0)
            self.assertEqual(sent, [FT.NOTIFY_TITLE])
            # 古い catalog.yml（あとの段が run を見ない）では、これまでどおり失敗にしてあとの段を止める
            with mock.patch.dict('os.environ', {'TAGURI_PLAN_SOFT_STOP': ''}):
                self.assertEqual(FT.main(), 1)

    def test_separate_caps_keep_the_sum_under_the_free_tier(self):
        # 取得と管理画面の控えは別のファイル。足しても無料枠の 9 割に届かないこと（issue #139）
        self.assertLessEqual(FT.CAPS['r2_bytes'] + FT.CAPS['admin_r2_bytes'], 0.9 * FT.FREE['r2_bytes'])
        self.assertLessEqual(FT.CAPS['r2_class_a_month'] + FT.CAPS['admin_posters_month'] + 1, 0.9 * FT.FREE['r2_class_a_month'])
        self.assertLessEqual(FT.CAPS['d1_writes_day'] + FT.CAPS['admin_d1_writes_day'] + FT.CAPS['drill_d1_writes'],
                             0.95 * FT.FREE['d1_writes_day'])

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

    def test_poster_upload_stops_at_its_time_limit_and_resumes(self):
        # dec-crawl-tiers: ポスターを R2 に入れる段にも時間の上限を付ける。入れた分は控え、続きは次回
        t = iter([0, 0])                                          # 2 回目に見たときには 1 分を過ぎている
        put = []
        got = DP.build(self.data, self.out, bucket='b', limit=10, put=lambda *a: put.append(a[3]),
                       max_minutes=1, clock=lambda: next(t, 999))
        self.assertIn('時間の上限', got['stopped'])
        self.assertEqual(len(put), got['uploaded'])
        self.assertGreater(got['left'], 0)
        DP.commit(self.data, self.out)
        rest = []
        DP.build(self.data, self.out, bucket='b', limit=10, put=lambda *a: rest.append(a[3]))
        self.assertFalse(set(put) & set(rest))                    # 入れ直さない

    def test_r2_storage_cap_stops_uploads(self):
        FT.CAPS['r2_bytes'] = 250
        put = []
        got = DP.build(self.data, self.out, bucket='b', limit=10, put=lambda *a: put.append(a[3]))
        self.assertEqual((got['uploaded'], put), (2, ['3.jpg', '2.jpg']))   # 新しい公演（番号の大きいほう）から入る
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

    def test_d1_reads_and_the_run_steps_are_counted(self):
        # dec-crawl-tiers: D1 の読み出し（wrangler d1 info の rows_read_24h）と、取得の段の rows_read（ログ）を数える
        info = self.data / 'd1-info.json'
        info.write_text(json.dumps({'rows_read_24h': 2_900_000}))
        self.assertEqual(FT.d1_reads_24h(info), 2_900_000)
        self.assertIsNone(FT.d1_reads_24h(self.data / 'none.json'))
        log = self.data / 'past.log'
        log.write_text('[{"meta": {"rows_read": 600, "rows_written": 150}}, {"meta": {"rows_read": 61}}]')
        self.assertEqual(FT.rows_read_in_logs([log, self.data / 'missing.log']), 661)
        rows = {r['what']: r for r in FT.check(self.data, [0] * 31, {}, NOW, 2_900_000)}
        self.assertFalse(rows['D1 の読み出し（直近 24 時間・Worker と取得の合計）']['ok'])
        # 読めなかったときは注意を出すが、取得の守りは別にあるので点検を失敗にしない
        rows = {r['what']: r for r in FT.check(self.data, [0] * 31, {}, NOW, None)}
        self.assertTrue(rows['D1 の読み出し（直近 24 時間・Worker と取得の合計）']['ok'])
        # 段ごとの時間: 毎日の更新（1〜3）と下位の処理（4・5）に分けて控える
        steps = [('Rebuild the catalog', 70), ('Deliver the catalogue to D1 (changed rows only)', 40),
                 ('Read past stage pages (2019 onwards, newest first)', 600), ('Upload posters to R2 (new ones only)', 120)]
        row = FT.record_run(self.data, '1', 'daily', steps, NOW)
        self.assertEqual((row['core_seconds'], row['background_seconds']), (110, 720))
        self.assertEqual(FT.core_minutes_measured(self.data), [1.8])

    def test_warnings_do_not_fail_but_unread_minutes_do(self):
        sent = []
        usage = self.data / 'usage.json'
        usage.write_text(json.dumps([{'results': [{'k': 'r2_get:2026-10', 'n': 5}]}]))
        def run(by_day):
            with mock.patch.object(FT, '_actions', return_value=by_day), \
                 mock.patch.object(FT, 'notify', side_effect=lambda t, b: sent.append(t)), \
                 mock.patch.object(sys, 'argv', ['x', 'check', '--data', str(self.data), '--d1-usage', str(usage)]), \
                 mock.patch('sys.stdout'):
                return FT.main()
        self.assertEqual(run([50] * 31), 0)                       # 上限の 8 割を越えた: 注意と issue だけ
        self.assertEqual(sent, [FT.NOTIFY_TITLE])
        self.assertEqual(run(None), 1)                            # 分数が読めない: 本当のエラーは隠さない


if __name__ == '__main__':
    unittest.main()
