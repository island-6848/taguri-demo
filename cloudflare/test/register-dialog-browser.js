// Run by visual-check.js after Playwright is installed in CI.
import assert from 'node:assert/strict';
import {registerScreen} from '../src/screens/settings.js';

export async function checkRegisterDialog(browser, base) {
  const statement = {bind() {return this}, async all() {return {results: []}}};
  const screen = await registerScreen({}, {db: {prepare: () => statement}, uid: 'fixture', today: '2026-10-19', now: Date.parse('2026-10-19T00:00:00Z')});
  for (const width of [1280, 390]) {
    const page = await browser.newPage({viewport: {width, height: 900}});
    const errors = [], requests = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/config.js') return route.fulfill({contentType: 'text/javascript', body: 'window.TAGURI={edition:"service",api:location.origin,base:"",demoBase:""};'});
      if (url.pathname.startsWith('/api/screen/')) return route.fulfill({json: {ok: true, ...screen}});
      if (url.pathname === '/api/suggest') {
        if (url.searchParams.get('advanced') === '1') requests.push(url);
        return route.fulfill({json: {rows: [{kind: 'stage', stage_id: '99', title: '夜の果て', venue: '本多劇場', date: '', note: '劇団甲／2026/10/1〜10/31'}]}});
      }
      if (url.pathname.startsWith('/api/')) return route.fulfill({json: {ok: true}});
      return url.origin === base ? route.continue() : route.abort();
    });
    try {
      await page.goto(base + '/register');
      const button = page.locator('[data-register-search]');
      await button.waitFor();
      const dialog = page.locator('#register-search-dialog');
      assert.equal(await dialog.count(), 1);
      assert.equal(await dialog.isVisible(), false);
      await page.locator('#w-title').fill('夜の果て');
      await button.click();
      await dialog.waitFor({state: 'visible'});
      for (const [name, label] of [['q', '公演名'], ['group', '団体名'], ['venue', '劇場'], ['schedule_precision', '指定の細かさ']]) {
        const field = dialog.locator(`[name="${name}"]`);
        assert.ok(await field.isVisible(), `${width}: ${label} missing`);
        assert.ok(await field.evaluate((el, text) => [...el.labels].some(l => l.textContent.includes(text)), label));
      }
      assert.equal(await dialog.locator('[name=q]').inputValue(), '夜の果て');
      await dialog.locator('[name=schedule_precision]').selectOption('month');
      assert.ok(await dialog.locator('[name=schedule_month]').isVisible());
      assert.equal(await dialog.locator('[name=schedule_year]').isVisible(), false);
      await dialog.locator('[name=schedule_month]').selectOption('10');
      await page.screenshot({path: `/tmp/taguri-visual/register-dialog-${width}.png`, fullPage: true});
      await dialog.getByRole('button', {name: '検索する', exact: true}).click();
      const pick = dialog.locator('[data-pick]');
      await pick.waitFor();
      assert.equal(requests.length, 1);
      assert.equal(requests[0].searchParams.get('schedule_month'), '10');
      assert.ok(!requests[0].searchParams.has('schedule_year'));
      await page.screenshot({path: `/tmp/taguri-visual/register-dialog-results-${width}.png`, fullPage: true});
      await pick.click();
      await dialog.waitFor({state: 'hidden'});
      assert.equal(await page.locator('#w-stage').inputValue(), '99');
      assert.equal(await page.locator('#w-venue').inputValue(), '本多劇場');
      assert.equal(await page.locator('#w-date').inputValue(), '');
      await button.click();
      await dialog.waitFor({state: 'visible'});
      assert.ok(await dialog.locator('[name=q]').isVisible());
      await dialog.getByRole('button', {name: '検索する', exact: true}).click();
      await page.waitForFunction(() => !document.querySelector('#register-search-dialog button[type=submit]').disabled);
      assert.equal(requests.length, 2, 'reopening must not duplicate submit handlers');
      await page.keyboard.press('Escape');
      await dialog.waitFor({state: 'hidden'});
      assert.ok(await button.evaluate(el => document.activeElement === el));
      assert.deepEqual(errors, [], `${width}: detail dialog JavaScript errors`);
      console.log(`register dialog/${width}: fields visible, month filter, selection, reopen, Escape passed`);
    } catch (error) {
      await page.screenshot({path: `/tmp/taguri-visual/register-dialog-failure-${width}.png`, fullPage: true});
      console.error('Detail dialog page errors:', errors);
      throw error;
    } finally {await page.close()}
  }
}
