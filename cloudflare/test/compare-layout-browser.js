import assert from 'node:assert/strict';
import {CRAFTS, rows, panel, popNote} from '../src/screens/compare.js';

// Render the production comparison markup, including long labels and empty-world ratios.
export async function checkCompareLayout(browser, base) {
  const labels = CRAFTS.map(c => c[1]);
  const html = popNote([{date: '2019-01-01'}, {date: '2026-10-01'}],
    {n: 4200, n_upcoming: 3000, n_running: 1000, n_ended: 200, first: '2026-09-01', last: '2027-03-01', other: 5100})
    + panel({craft: [rows(labels, {[labels[0]]: 2, [labels[1]]: 1}, {[labels[0]]: 10}, 12, 4200), 12, 4200]});
  for (const width of [320, 390, 1280]) {
    const page = await browser.newPage({viewport: {width, height: 900}});
    try {
      await page.route('**/*', route => {
        const url = new URL(route.request().url());
        if (url.pathname === '/compare-layout-fixture') return route.fulfill({contentType: 'text/html', body:
          `<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/theme.css"><main style="max-width:1100px;margin:auto;padding:12px;box-sizing:border-box">${html}</main>`});
        return url.origin === base ? route.continue() : route.abort();
      });
      await page.goto(base + '/compare-layout-fixture');
      await page.evaluate(() => document.fonts.ready);
      const metrics = await page.evaluate(() => {
        const box = document.querySelector('.compare-table');
        const card = box.closest('.card').getBoundingClientRect();
        return {page: document.documentElement.scrollWidth, viewport: innerWidth,
          cardLeft: card.left, cardRight: card.right, box: box.clientWidth, content: box.scrollWidth};
      });
      assert.ok(metrics.page <= width + 1, `page overflow at ${width}: ${JSON.stringify(metrics)}`);
      assert.ok(metrics.cardLeft >= 0 && metrics.cardRight <= width + 1, `card overflow at ${width}`);
      assert.equal(await page.locator('.compare-table tbody tr').count(), 4);
      if (width < 700) {
        assert.ok(metrics.content > metrics.box, 'wide table scrolls inside its card');
        await page.locator('.compare-table').focus();
        await page.keyboard.press('End');
        await page.locator('.compare-table').evaluate(el => { el.scrollLeft = el.scrollWidth; });
        assert.ok(await page.locator('.compare-table').evaluate(el => el.scrollLeft > 0));
        assert.ok(await page.locator('.compare-scroll-hint').isVisible());
      }
      await page.screenshot({path: `/tmp/taguri-visual/compare-${width}.png`, fullPage: true});
      console.log(`compare/${width}: no page overflow; all columns retained, table scroll checked`);
    } finally { await page.close(); }
  }
}
