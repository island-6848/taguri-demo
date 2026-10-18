// 毎日の更新（公演の取得。taguri-crawler の Catalog ワークフロー）が始まる時刻。画面の「次回は○月○日 4 時台」は
// ここからだけ作る（#101）。tools/taguri/deploy/github-actions/catalog.yml の cron '17 19 * * …'（UTC）＝日本時間 4:17。
// test/crawl-time.test.js が、その cron と同じかを確かめる。
export const CRAWL_UTC_HOUR = 19, CRAWL_UTC_MINUTE = 17;
// GitHub の定期実行は遅れることがある（予定の 19:17 から約 3 時間遅れた例: docs/knowledge dec-index-first-load）。
// 予定からこの時間が過ぎるまでは、その回はまだ済んでいないとみなす
export const CRAWL_LATE_HOURS = 6;
const DAY = 864e5, HOUR = 36e5, JST = 9 * HOUR;

/** その日（UTC）の予定の時刻 */
const slotOf = ms => { const d = new Date(ms); return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), CRAWL_UTC_HOUR, CRAWL_UTC_MINUTE); };
/** いまより後の、最初の更新の予定（UTC の ms） */
export function nextCrawl(nowMs) {
  const t = slotOf(nowMs);
  return t > nowMs ? t : t + DAY;
}
/** 遅れの余裕を見て、済んだとみなせる最後の更新の予定（UTC の ms） */
export function lastCrawlDone(nowMs) {
  const edge = nowMs - CRAWL_LATE_HOURS * HOUR;
  const t = slotOf(edge);
  return t <= edge ? t : t - DAY;
}
/** fromMs のあと、済んだとみなせる更新の回数 */
export function crawlsSince(fromMs, nowMs) {
  const last = lastCrawlDone(nowMs);
  if (!(fromMs < last)) return 0;
  return Math.ceil((last - fromMs) / DAY);
}
/** 「10月19日 4時台（日本時間）」 */
export function crawlLabel(ms) {
  const d = new Date(ms + JST);
  return `${d.getUTCMonth() + 1}月${d.getUTCDate()}日 ${d.getUTCHours()}時台（日本時間）`;
}
/** 日本時間の日付「10月18日」 */
export function jstDay(ms) {
  const d = new Date(ms + JST);
  return `${d.getUTCMonth() + 1}月${d.getUTCDate()}日`;
}

// 「次の更新で探してもらう」の依頼（D1 の search_request）を、毎日の更新が読んで CoRich で探す段は、まだ無い
// （q-search-request-crawl。2026-10-18 にコードで確かめた: Worker に /api/catalog/search-requests が無く、取得の
// catalog.yml も TAGURI_NAMES_URL を渡さないので、run.py の fetch_requests.py は「未設定なので飛ばす」）。
// その段ができたら requests を true にする。false のあいだ、画面は「次回の更新で探します」と約束しない。
// テストが両方の書き方を確かめるので、定数ではなくオブジェクトにしてある
export const crawlSearch = {requests: false};
