// 記録の日付の部品。row.js（サーバー）と、眺めるの図（people.js・trace.js、ブラウザーでも動く）の両方から使う
const WEEK = '月火水木金土日';
/** app._date_parts: (年, 月.日, 曜日), or empty when date.fromisoformat fails. */
export function dateParts(iso) {
  const m = Array.from(iso || '').slice(0, 10).join('').match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return ['', '', ''];
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const dim = [31, (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (y < 1 || mo < 1 || mo > 12 || d < 1 || d > dim[mo - 1]) return ['', '', ''];
  const dt = new Date(0);
  dt.setUTCFullYear(y, mo - 1, d);
  return [String(y), `${mo}.${String(d).padStart(2, '0')}`, WEEK[(dt.getUTCDay() + 6) % 7]];
}

/**
 * 利用者の記録の日付は、どの画面も「2026.10.13(水) 13:00」の形（起案者の指示 2026-10-24「全ページ共通でユーザが追加した
 * 公演記録の日付の表記、2026.10.13(水) 13:00表記を採用して」）。時刻は分かるときだけ。日付が読めなければ空
 */
export function recDate(iso, time = '') {
  const [y, md, wd] = dateParts(iso);
  if (!md) return '';
  const [mo, dd] = md.split('.');
  return `${y}.${mo.padStart(2, '0')}.${dd}(${wd})${time ? ` ${time}` : ''}`;
}
