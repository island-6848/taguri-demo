// おすすめのカードの日程（起案者の指示 2026-10-17: 会場ごとの行・おすすめの会場は帯・各行の下に公演日時の暦・会場で違う料金は表）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseTimetable, timetableGrid, priceRows, tourBlock} from '../src/screens/schedule.js';

const flat = m => Object.fromEntries([...m].map(([d, ps]) => [d, ps.map(p => (p.m || '') + p.t)]));

test('timetable lines as the crawled pages write them', () => {
  // 丘の家（歩・印は出演者の組）
  assert.deepEqual(flat(parseTimetable('10月21日(水) 歩19:00\n10月23日(金) 歩13:00／印18:00\n10月25日(日) 歩12:00／印16:00', '2026-10-21', '2026-10-25')),
    {'2026-10-21': ['歩19:00'], '2026-10-23': ['歩13:00', '印18:00'], '2026-10-25': ['歩12:00', '印16:00']});
  // 全角・丸数字・「開演」付き
  assert.deepEqual(flat(parseTimetable('① １２月３日（木）１９：００開演\n② １２月５日（土）１３：００開演\n③ １２月５日（土）１７：００開演\n全６回公演／受付開始は開演１時間前',
    '2026-12-03', '2026-12-06')), {'2026-12-03': ['19:00'], '2026-12-05': ['13:00', '17:00']});
  // 月だけの見出しの行と、時刻の後ろの印
  assert.deepEqual(flat(parseTimetable('10月\n27日（火）19：00 A\n30日（金）14：00 B／19：00 A\n11月\n1日（日）13：00 B', '2026-10-27', '2026-11-03')),
    {'2026-10-27': ['A19:00'], '2026-10-30': ['B14:00', 'A19:00'], '2026-11-01': ['B13:00']});
  assert.deepEqual(flat(parseTimetable('2026年11月\n24日(火)休演日\n25日(水)14:00 Z / 19:00 W', '2026-11-20', '2026-11-29')), {'2026-11-25': ['Z14:00', 'W19:00']});
  // 時刻の無い日・マチネ/ソワレ
  assert.deepEqual(flat(parseTimetable('2月5日(金)\n2月6日(土) マチネ/ソワレ', '2027-02-05', '2027-02-10')), {'2027-02-05': [''], '2027-02-06': ['マチネ', 'ソワレ']});
  // 年をまたぐ公演・期間の行・本文だけの欄
  assert.deepEqual(Object.keys(flat(parseTimetable('12月31日(木) 18:00\n1月2日(土) 13:00', '2026-12-30', '2027-01-03'))), ['2026-12-31', '2027-01-02']);
  assert.equal(parseTimetable('10月21日(水)〜25日(日) 19:00', '2026-10-21', '2026-10-25').size, 0);
  assert.equal(parseTimetable('上演時間は約90分を予定しております。', '2026-10-21', '2026-10-25').size, 0);
});

test('the weekly calendar: times on their days, 休演 inside the run, blank outside, weekend colours', () => {
  const perf = parseTimetable('10月8日(水) 18:30\n10月9日(木) 13:30／18:30\n10月11日(土) 13:00／18:00', '2025-10-08', '2025-10-12');
  const html = timetableGrid(perf, '2025-10-08', '2025-10-12', '2025-10-01');
  assert.match(html, /<thead><tr><th>月<\/th><th>火<\/th><th>水<\/th><th>木<\/th><th>金<\/th><th class="sat">土<\/th><th class="sun">日<\/th><\/tr><\/thead>/);
  assert.match(html, /<td><span class="d">9<\/span><span class="tm">13:30<\/span><span class="tm">18:30<\/span><\/td>/);
  assert.match(html, /<td><span class="d">10<\/span><span class="off">休演<\/span><\/td>/);   // 金: 休演日
  assert.match(html, /<td class="out"><span class="d">10\/6<\/span><\/td>/);                // 月: 期間の外
  assert.equal(timetableGrid(new Map(), '2025-10-08', '2025-10-12', '2025-10-01'), '');
});

test('price rows: 券種と金額, sale-date lines left out', () => {
  assert.deepEqual(priceRows('2,750円 ～ 7,150円\n\n 【発売日】2026/03/01\n\n 【全席指定】\n前売：6,600円\n当日：7,150円'),
    [['2,750円 ~ 7,150円'], ['前売', '6,600円'], ['当日', '7,150円']]);
});

test('the tour block: one row per venue in date order, the shown one marked, prices per venue only when they differ', () => {
  const v = (sid, start, end, venue, pref, price, tt = '') => ({stage_id: sid, start, end, venue, pref, fields: {'料金（1枚あたり）': price, 'タイムテーブル': tt}});
  const same = tourBlock([v('2', '2026-11-06', '2026-11-08', 'ささしまスタジオ', '愛知県', '一般：5,000円'), v('1', '2026-10-28', '2026-11-01', '恵比寿・エコー劇場', '東京都', '一般：5,000円', '10月28日(水) 19:00')], '2', '2026-10-20');
  assert.equal(same.perVenuePrice, false);
  assert.match(same.html, /<div class="tf-row"><div class="tf-head"><span class="tf-when">10\/28〜11\/1<\/span><span class="tf-loc">恵比寿・エコー劇場（東京都）<\/span><\/div><details class="tf-tt"><summary>公演日時（1 回）<\/summary>/);
  assert.match(same.html, /<div class="tf-row here"><div class="tf-head"><span class="tf-when"><span class="tf-star" title="おすすめに出ている会場">★<\/span>11\/6〜11\/8<\/span><span class="tf-loc">ささしまスタジオ（愛知県）<\/span><\/div><\/div>/);
  assert.ok(same.html.indexOf('恵比寿') < same.html.indexOf('ささしま'));
  // 会場が 1 つなら印を付けない
  const one = tourBlock([v('1', '2026-10-28', '2026-11-01', 'A', '東京都', '一般：5,000円')], '1', '2026-10-20');
  assert.doesNotMatch(one.html, /here|★/);
  const diff = tourBlock([v('1', '2026-10-28', '2026-11-01', 'A', '東京都', 'S席：12,000円\nA席：9,500円'), v('2', '2026-11-06', '2026-11-08', 'B', '愛知県', '全席：8,000円')], '1', '2026-10-20');
  assert.equal(diff.perVenuePrice, true);
  assert.match(diff.html, /<table class="ptb"><tr><th>S席<\/th><td>12,000円<\/td><\/tr><tr><th>A席<\/th><td>9,500円<\/td><\/tr><\/table>/);
});
