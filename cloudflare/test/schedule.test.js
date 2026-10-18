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
  assert.match(html, /<thead><tr><th class="sun">日<\/th><th>月<\/th><th>火<\/th><th>水<\/th><th>木<\/th><th>金<\/th><th class="sat">土<\/th><\/tr><\/thead>/);
  assert.match(html, /<td><span class="d">9<\/span><span class="tm">13:30<\/span><span class="tm">18:30<\/span><\/td>/);
  assert.match(html, /<td><span class="d">10<\/span><span class="off">休演<\/span><\/td>/);   // 金: 休演日
  assert.match(html, /<td class="sun out"><span class="d">10\/5<\/span><\/td><td class="out"><span class="d">6<\/span><\/td>/);   // 日曜はじまり: 期間の外
  assert.equal(timetableGrid(new Map(), '2025-10-08', '2025-10-12', '2025-10-01'), '');
});

test('price rows: 券種と金額, sale-date lines left out', () => {
  assert.deepEqual(priceRows('2,750円 ～ 7,150円\n\n 【発売日】2026/03/01\n\n 【全席指定】\n前売：6,600円\n当日：7,150円'),
    [['2,750円 ~ 7,150円'], ['前売', '6,600円'], ['当日', '7,150円']]);
  // ツアーの各会場の行では、値段の幅だけの行は出さない（明細があるとき）
  assert.deepEqual(priceRows('2,750円 ～ 7,150円\n前売：6,600円', {dropRange: true}), [['前売', '6,600円']]);
  assert.deepEqual(priceRows('2,750円 ～ 7,150円', {dropRange: true}), [['2,750円 ~ 7,150円']]);
});

test('the tour block: a bulleted row per venue in date order, ★ on the filtered prefectures, the count beside the dates, prices per venue only when they differ', () => {
  const v = (sid, start, end, venue, pref, price, tt = '') => ({stage_id: sid, start, end, venue, pref, fields: {'料金（1枚あたり）': price, 'タイムテーブル': tt}});
  const same = tourBlock([v('2', '2026-11-06', '2026-11-08', 'ささしまスタジオ', '愛知県', '一般：5,000円'), v('1', '2026-10-28', '2026-11-01', '恵比寿・エコー劇場', '東京都', '一般：5,000円', '10月28日(水) 19:00')], '2', '2026-10-20');
  assert.equal(same.perVenuePrice, false);
  assert.match(same.html, /<details class="tf-row"><summary class="tf-head"><span class="tf-when"><span class="tf-dot" aria-hidden="true">・<\/span>10\/28〜11\/1<span class="tf-cnt">（1 回）<\/span><\/span><span class="tf-loc">恵比寿・エコー劇場（東京都）<\/span><span class="tf-more">詳細<\/span><\/summary><div class="tf-body"><table class="ttb"/);
  assert.match(same.html, /<div class="tf-row"><div class="tf-head"><span class="tf-when"><span class="tf-dot" aria-hidden="true">・<\/span>11\/6〜11\/8<\/span><span class="tf-loc">ささしまスタジオ（愛知県）<\/span><\/div><\/div>/);
  assert.doesNotMatch(same.html, /tf-n|★/);
  // 都道府県で絞っているときは、その県の会場の行頭が ★
  const filtered = tourBlock([v('2', '2026-11-06', '2026-11-08', 'ささしまスタジオ', '愛知県', '一般：5,000円'), v('1', '2026-10-28', '2026-11-01', '恵比寿・エコー劇場', '東京都', '一般：5,000円', '10月28日(水) 19:00')], '1', '2026-10-20', ['愛知県']);
  assert.match(filtered.html, /<div class="tf-row here"><div class="tf-head"><span class="tf-when"><span class="tf-star" title="絞り込んだ都道府県の会場">★<\/span>11\/6〜11\/8/);
  assert.match(filtered.html, /<details class="tf-row"><summary class="tf-head"><span class="tf-when"><span class="tf-dot"/);
  assert.ok(same.html.indexOf('恵比寿') < same.html.indexOf('ささしま'));
  // 会場が 1 つなら印を付けない
  const one = tourBlock([v('1', '2026-10-28', '2026-11-01', 'A', '東京都', '一般：5,000円')], '1', '2026-10-20');
  assert.doesNotMatch(one.html, /here|★/);
  assert.doesNotMatch(one.html, /tf-loc/);   // 1 か所なら会場の名前は出さない
  const diff = tourBlock([v('1', '2026-10-28', '2026-11-01', 'A', '東京都', 'S席：12,000円\nA席：9,500円'), v('2', '2026-11-06', '2026-11-08', 'B', '愛知県', '全席：8,000円')], '1', '2026-10-20');
  assert.equal(diff.perVenuePrice, true);
  assert.match(diff.html, /<table class="ptb"><tr><th>S席<\/th><td>12,000円<\/td><\/tr><tr><th>A席<\/th><td>9,500円<\/td><\/tr><\/table>/);
});

test('mark legends from the stage page, and an honest line for marks it does not explain', async () => {
  const {markLegend, timetableGrid: grid} = await import('../src/screens/schedule.js');
  const L = markLegend(['★', '◆', 'A', '歩'], ['10月8日(水) ★13:00\n★・・・鑑賞マナーゆるめの回(4歳~客席入場OK)', '◆:鑑賞サポートあり(音声ガイド) A=小野桜介 B=駒井末宙']);
  assert.equal(L.get('★'), '鑑賞マナーゆるめの回(4歳~客席入場OK)');
  assert.equal(L.get('◆'), '鑑賞サポートあり(音声ガイド)');
  assert.equal(L.get('A'), '小野桜介');
  assert.equal(L.has('歩'), false);
  const perf = parseTimetable('10月8日(水) ★13:00／歩18:00', '2025-10-08', '2025-10-08');
  const html = grid(perf, '2025-10-08', '2025-10-08', '2025-10-01', ['★・・・アフタートークあり']);
  assert.match(html, /<ul class="ttb-legend"><li><b>★<\/b>アフタートークあり<\/li><li class="miss"><b>歩<\/b>公演ページに印の説明がありません<\/li><\/ul>/);
});

test('times on the line after the date (三婆), 「- -」 as no performance, 貸切 as a performance', () => {
  const tt = '11月03日( 火 )\n13:00 -\n\n11月04日( 水 )\n11:00 貸切\n\n11月05日( 木 )\n- -\n\n11月06日( 金 )\n11:00 15:30\n※開場は開演の30分前';
  assert.deepEqual(flat(parseTimetable(tt, '2026-11-03', '2026-11-25')),
    {'2026-11-03': ['13:00'], '2026-11-04': ['11:00', '貸切'], '2026-11-06': ['11:00', '15:30']});
});

test('「19時」「14時半」「午後7時」「1830開演」, 開場/終演/上演時間 dropped, 開演 on the next line', () => {
  const tt = '12月4日（金）19時～\n12月5日（土）14時半／18時\n12月6日(日)\n開場 15:00\n開演 15:30\n12月7日1830開演\n12月8日(火)\n・壱ノ回 13時 開演\n・弐ノ回 17時 開演\n12月12日(土)\n1回目　9:30開場／10:30開演\n2回目　13:00開場／14:00開演\n12月9日(水)午後7時開演（午後8時30分終演予定）\n12月10日(木)\n開場：午後5時45分　開演：午後6時30分\n12月11日(金) 14:00\n●13:15開場／上演時間約2時間20分';
  assert.deepEqual(flat(parseTimetable(tt, '2026-12-04', '2026-12-12')),
    {'2026-12-04': ['19:00'], '2026-12-05': ['14:30', '18:00'], '2026-12-06': ['15:30'], '2026-12-07': ['18:30'], '2026-12-08': ['13:00', '17:00'], '2026-12-09': ['19:00'], '2026-12-10': ['18:30'], '2026-12-11': ['14:00'], '2026-12-12': ['10:30', '14:00']});
});

test('#76 ranges: 「各」 ranges are read day by day; days of lines it cannot read are 公式で確認, not 休演', () => {
  const tt = '10月20日(火) 19:00\n10月21日(水) 14:00／19:00\n10月22日(木)〜23日(金) 各19:00';
  const perf = parseTimetable(tt, '2026-10-20', '2026-10-23');
  assert.deepEqual(flat(perf), {'2026-10-20': ['19:00'], '2026-10-21': ['14:00', '19:00'], '2026-10-22': ['19:00'], '2026-10-23': ['19:00']});
  const html = timetableGrid(perf, '2026-10-20', '2026-10-23', '2026-10-01');
  assert.doesNotMatch(html, /休演|公式で確認/);
  assert.match(html, /<td><span class="d">23<\/span><span class="tm">19:00<\/span><\/td>/);
  // 月の見出しの下の期間・月をまたぐ期間・月/日の期間
  assert.deepEqual(flat(parseTimetable('10月\n22日(木)〜23日(金) 各19:00', '2026-10-20', '2026-10-23')), {'2026-10-22': ['19:00'], '2026-10-23': ['19:00']});
  assert.deepEqual(Object.keys(flat(parseTimetable('10月30日(金)〜11月1日(日) 各14:00', '2026-10-30', '2026-11-01'))), ['2026-10-30', '2026-10-31', '2026-11-01']);
  assert.deepEqual(Object.keys(flat(parseTimetable('10/22(木)〜10/23(金) 各日19:00', '2026-10-20', '2026-10-23'))), ['2026-10-22', '2026-10-23']);
  // 「各」の無い期間の行は読まない。その日は休演ではなく「公式で確認」で、回数は「以上」
  const part = parseTimetable('10月20日(火) 19:00\n10月21日(水)〜23日(金) 14:00／19:00', '2026-10-20', '2026-10-24');
  assert.deepEqual(flat(part), {'2026-10-20': ['19:00']});
  const g = timetableGrid(part, '2026-10-20', '2026-10-24', '2026-10-01');
  assert.match(g, /<td><span class="d">21<\/span><span class="unk">公式で確認<\/span><\/td>/);
  assert.match(g, /<td class="sat"><span class="d">24<\/span><span class="off">休演<\/span><\/td>/);   // どの行にも無い日は休演のまま
  assert.match(g, /aria-label="公演日時（1 回以上）"/);
  assert.match(g, /<p class="ttb-note">「公式で確認」の日は/);
  // 上演期間を書いただけの見出しの行は、日ごとの行の邪魔をしない。「休演」と書いた期間は休演
  const hd = parseTimetable('10月20日(火)〜24日(土)\n10月20日(火) 19:00\n10月21日(水)〜22日(木) 休演\n10月23日(金) 19:00', '2026-10-20', '2026-10-24');
  const hg = timetableGrid(hd, '2026-10-20', '2026-10-24', '2026-10-01');
  assert.doesNotMatch(hg, /公式で確認/);
  assert.match(hg, /<td><span class="d">21<\/span><span class="off">休演<\/span><\/td>/);
  // 日付が 2 つある行も「公式で確認」
  assert.match(timetableGrid(parseTimetable('10月20日(火) 19:00\n10月21日(水) 19:00 / 10月22日(木) 14:00', '2026-10-20', '2026-10-22'), '2026-10-20', '2026-10-22', '2026-10-01'),
    /<span class="d">21<\/span><span class="unk">公式で確認<\/span>.*<span class="d">22<\/span><span class="unk">公式で確認<\/span>/);
  // ツアーの行の回数も「以上」
  const tb = tourBlock([{stage_id: '1', start: '2026-10-20', end: '2026-10-24', venue: 'A', pref: '東京都', fields: {'タイムテーブル': '10月20日(火) 19:00\n10月21日(水)〜23日(金) 14:00'}}], '1', '2026-10-01');
  assert.match(tb.html, /<span class="tf-cnt">（1 回以上）<\/span>/);
});

test('#77 午前/午後 12時 and out-of-range times', () => {
  const tt = '10月20日(火) 午前12時30分\n10月21日(水) 午後12時30分\n10月22日(木) 23:59\n10月23日(金) 29:99\n10月24日(土) 午前0時\n10月25日(日) 午後11時59分／24:00\n10月26日(月) 午前12:30／午後12:00';
  assert.deepEqual(flat(parseTimetable(tt, '2026-10-20', '2026-10-26')), {
    '2026-10-20': ['0:30'], '2026-10-21': ['12:30'], '2026-10-22': ['23:59'], '2026-10-23': [''],
    '2026-10-24': ['0:00'], '2026-10-25': ['23:59'], '2026-10-26': ['0:30', '12:00']});
  assert.deepEqual(flat(parseTimetable('10月20日(火) 12:60／19:30', '2026-10-20', '2026-10-20')), {'2026-10-20': ['19:30']});
});
