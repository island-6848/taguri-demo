// An inclusive overlap with a performance's run, independent of attendance.
import {isDay} from '../client/import-parse.js';

const LEGACY_PARTS = {none: [], month: ['month'], monthday: ['month', 'day'], year: ['year'], yearmonth: ['year', 'month'], date: ['year', 'month', 'day']};
const pad = n => String(n).padStart(2, '0');
const daysInMonth = (y, m) => [31, y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
const anyRun = () => ({matches: () => true, from: '', to: ''});

export function scheduleFilter(params) {
  const bad = () => {throw new Error('上演日程を正しく入力してください。')};
  const read = part => {
    const value = (params.get('schedule_' + part) || '').trim();
    const max = {year: 9999, month: 12, day: 31}[part];
    if (!/^\d{1,4}$/.test(value) || Number(value) < 1 || Number(value) > max) bad();
    return Number(value);
  };
  let year, month, day;
  const supplied = ['year', 'month', 'day'].filter(part => (params.get('schedule_' + part) || '').trim());
  // Accept previous cached clients, but the new form only sends filled fields.
  const precision = params.get('schedule_precision');
  if (precision !== null) {
    if (!Object.hasOwn(LEGACY_PARTS, precision || 'none')) bad();
    const parts = LEGACY_PARTS[precision || 'none'];
    if (!parts.length) return anyRun();
    [year, month, day] = ['year', 'month', 'day'].map(part => parts.includes(part) ? read(part) : undefined);
  } else if (!supplied.length && params.get('date')) {
    const legacy = params.get('date');
    if (!isDay(legacy)) bad();
    [year, month, day] = legacy.split('-').map(Number);
  } else {
    [year, month, day] = ['year', 'month', 'day'].map(part => supplied.includes(part) ? read(part) : undefined);
  }
  if (!year && !month && !day) return anyRun();
  if (month && day && day > daysInMonth(year ?? 2000, month)) bad();
  const date = (y, m, d) => `${String(y).padStart(4, '0')}-${pad(m)}-${pad(d)}`;
  const from = year ? date(year, month || 1, month ? (day || 1) : 1) : '';
  const to = year ? date(year, month || 12, month ? (day || daysInMonth(year, month)) : 31) : '';
  const overlap = (a, b, start, end) => start <= b && a <= end;
  return {
    from, to,
    matches(start, end) {
      end = end || start;
      if (!isDay(start) || !isDay(end) || end < start) return false;
      if (from && !overlap(from, to, start, end)) return false;
      if (year && !day) return true; // The year/month range already overlaps.
      const first = year || Number(start.slice(0, 4));
      const last = year || Math.min(Number(end.slice(0, 4)), first + 8);
      // At most nine years and twelve months, even for a very long run.
      // Eight years includes the leap-day gap at non-leap century boundaries.
      for (let y = first; y <= last; y++) {
        for (let m = month || 1; m <= (month || 12); m++) {
          if (day && day > daysInMonth(y, m)) continue;
          const a = date(y, m, day || 1), b = date(y, m, day || daysInMonth(y, m));
          if (overlap(a, b, start, end)) return true;
        }
      }
      return false;
    },
  };
}
