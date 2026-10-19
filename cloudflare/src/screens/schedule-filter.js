// An inclusive overlap with a performance's run, independent of attendance.
import {isDay} from '../client/import-parse.js';

const MODES = new Set(['none', 'month', 'monthday', 'year', 'yearmonth', 'date']);
const pad = n => String(n).padStart(2, '0');
const daysInMonth = (y, m) => [31, y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];

export function scheduleFilter(params) {
  // Retain the exact-day parameter for clients with the previous cached UI.
  const legacy = !params.has('schedule_precision') && params.get('date');
  const mode = params.get('schedule_precision') || (legacy ? 'date' : 'none');
  const bad = () => {throw new Error('上演日程を正しく入力してください。')};
  if (!MODES.has(mode)) bad();
  if (mode === 'none') return {matches: () => true, from: '', to: ''};
  const read = (key, min, max) => {
    const value = params.get('schedule_' + key) || '';
    if (!/^\d{1,4}$/.test(value) || Number(value) < min || Number(value) > max) bad();
    return Number(value);
  };
  let year, month, day;
  if (legacy) {
    if (!isDay(legacy)) bad();
    [year, month, day] = legacy.split('-').map(Number);
  } else {
    if (['year', 'yearmonth', 'date'].includes(mode)) year = read('year', 1, 9999);
    if (['month', 'monthday', 'yearmonth', 'date'].includes(mode)) month = read('month', 1, 12);
    if (['monthday', 'date'].includes(mode)) day = read('day', 1, 31);
  }
  if (day && day > daysInMonth(year ?? 2000, month)) bad();
  const interval = y => {
    const ys = String(y).padStart(4, '0');
    if (mode === 'year') return [ys + '-01-01', ys + '-12-31'];
    if (day) {
      if (day > daysInMonth(y, month)) return null;
      const date = `${ys}-${pad(month)}-${pad(day)}`;
      return [date, date];
    }
    return [`${ys}-${pad(month)}-01`, `${ys}-${pad(month)}-${daysInMonth(y, month)}`];
  };
  const absolute = year ? interval(year) : null;
  const overlap = (range, start, end) => !!range && start <= range[1] && range[0] <= end;
  return {
    from: absolute?.[0] || '', to: absolute?.[1] || '',
    matches(start, end) {
      end = end || start;
      if (!isDay(start) || !isDay(end) || end < start) return false;
      if (absolute) return overlap(absolute, start, end);
      const first = Number(start.slice(0, 4)), last = Number(end.slice(0, 4));
      // A valid annual date recurs within eight years, including the leap-year
      // gap at non-leap centuries. Keep work bounded for very long runs.
      for (let y = first; y <= Math.min(last, first + 8); y++) {
        if (overlap(interval(y), start, end)) return true;
      }
      return false;
    },
  };
}
